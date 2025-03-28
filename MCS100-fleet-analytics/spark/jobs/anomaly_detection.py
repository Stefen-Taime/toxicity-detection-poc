"""
Job Spark pour la détection d'anomalies dans les données de vol
Ce script utilise des techniques avancées de ML pour détecter les anomalies
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, stddev, count, when, lit, expr, window, udf
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType, IntegerType, BooleanType, ArrayType
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator
from pyspark.ml.feature import PCA
import os
import logging
import json
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Fonction principale pour la détection d'anomalies"""
    logger.info("Démarrage de la détection d'anomalies")
    
    # Création de la session Spark
    spark = SparkSession.builder \
        .appName("MCS100 Anomaly Detection") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .getOrCreate()
    
    try:
        # Connexion à TimescaleDB
        jdbc_url = "jdbc:postgresql://timescaledb:5432/mcs100db"
        connection_properties = {
            "user": os.environ.get("POSTGRES_USER", "airbus"),
            "password": os.environ.get("POSTGRES_PASSWORD", "airbus123"),
            "driver": "org.postgresql.Driver"
        }
        
        # Date d'exécution
        execution_date = datetime.now()
        end_date = execution_date.strftime('%Y-%m-%d')
        
        # Période d'analyse (7 derniers jours)
        start_date = (execution_date - timedelta(days=7)).strftime('%Y-%m-%d')
        
        logger.info(f"Détection d'anomalies pour la période {start_date} à {end_date}")
        
        # Lecture des données de vol
        logger.info("Lecture des données de vol")
        flight_data_df = spark.read \
            .jdbc(url=jdbc_url, table="raw.flight_data", properties=connection_properties) \
            .filter(col("event_timestamp").between(start_date, end_date))
        
        # Vérification des données
        if flight_data_df.count() == 0:
            logger.warning("Aucune donnée de vol disponible pour la période spécifiée")
            return
        
        # Préparation des données pour la détection d'anomalies
        logger.info("Préparation des données pour la détection d'anomalies")
        
        # Sélection des colonnes pertinentes
        selected_columns = [
            "aircraft_msn", "flight_id", "event_timestamp",
            "engine_1_temp", "engine_2_temp",
            "engine_1_pressure", "engine_2_pressure",
            "engine_1_vibration", "engine_2_vibration",
            "fuel_flow_rate", "altitude", "speed"
        ]
        
        prepared_df = flight_data_df.select(selected_columns) \
            .na.drop() \
            .filter(
                (col("engine_1_temp") > 0) & 
                (col("engine_2_temp") > 0) & 
                (col("fuel_flow_rate") > 0)
            )
        
        # Analyse par avion
        aircraft_list = prepared_df.select("aircraft_msn").distinct().collect()
        all_anomalies = []
        
        for aircraft_row in aircraft_list:
            aircraft_msn = aircraft_row["aircraft_msn"]
            logger.info(f"Analyse de l'avion {aircraft_msn}")
            
            # Filtrer les données pour cet avion
            aircraft_data = prepared_df.filter(col("aircraft_msn") == aircraft_msn)
            
            if aircraft_data.count() < 100:
                logger.warning(f"Données insuffisantes pour l'avion {aircraft_msn}, passage au suivant")
                continue
            
            # Préparation des features pour le ML
            feature_columns = [
                "engine_1_temp", "engine_2_temp",
                "engine_1_pressure", "engine_2_pressure",
                "engine_1_vibration", "engine_2_vibration",
                "fuel_flow_rate"
            ]
            
            # Assemblage des vecteurs de features
            assembler = VectorAssembler(inputCols=feature_columns, outputCol="features")
            assembled_data = assembler.transform(aircraft_data)
            
            # Normalisation des features
            scaler = StandardScaler(inputCol="features", outputCol="scaled_features", withStd=True, withMean=True)
            scaler_model = scaler.fit(assembled_data)
            scaled_data = scaler_model.transform(assembled_data)
            
            # Méthode 1: K-Means pour la détection d'anomalies
            logger.info(f"Application de K-Means pour l'avion {aircraft_msn}")
            
            # Réduction de dimensionnalité avec PCA
            pca = PCA(k=3, inputCol="scaled_features", outputCol="pca_features")
            pca_model = pca.fit(scaled_data)
            pca_data = pca_model.transform(scaled_data)
            
            # Application de K-Means
            kmeans = KMeans(k=5, seed=42, featuresCol="pca_features", predictionCol="cluster")
            kmeans_model = kmeans.fit(pca_data)
            clustered_data = kmeans_model.transform(pca_data)
            
            # Calcul des distances au centre du cluster
            cluster_centers = kmeans_model.clusterCenters()
            
            # Fonction pour calculer la distance euclidienne
            def euclidean_distance(v1, v2):
                return float(np.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2))))
            
            # UDF pour calculer la distance au centre du cluster
            distance_udf = udf(lambda features, cluster: euclidean_distance(features, cluster_centers[cluster]), DoubleType())
            
            # Calcul des distances
            distances_df = clustered_data.withColumn(
                "distance_to_center", 
                distance_udf(col("pca_features"), col("cluster"))
            )
            
            # Calcul du seuil d'anomalie (95ème percentile des distances)
            threshold = distances_df.selectExpr("percentile_approx(distance_to_center, 0.95) as threshold").collect()[0]["threshold"]
            
            # Identification des anomalies
            kmeans_anomalies = distances_df.filter(col("distance_to_center") > threshold)
            
            logger.info(f"K-Means: {kmeans_anomalies.count()} anomalies détectées pour l'avion {aircraft_msn}")
            
            # Conversion en Pandas pour l'Isolation Forest
            pandas_df = aircraft_data.select(feature_columns).toPandas()
            
            # Méthode 2: Isolation Forest
            logger.info(f"Application d'Isolation Forest pour l'avion {aircraft_msn}")
            
            # Création et entraînement du modèle
            iso_forest = IsolationForest(
                n_estimators=100,
                max_samples='auto',
                contamination=0.05,
                random_state=42
            )
            
            # Entraînement et prédiction
            iso_forest.fit(pandas_df)
            predictions = iso_forest.predict(pandas_df)
            scores = iso_forest.decision_function(pandas_df)
            
            # Conversion des résultats en DataFrame Spark
            pandas_results = pandas_df.copy()
            pandas_results['anomaly'] = predictions == -1
            pandas_results['anomaly_score'] = scores
            
            # Conversion en DataFrame Spark
            schema = StructType([
                StructField("anomaly", BooleanType(), True),
                StructField("anomaly_score", DoubleType(), True)
            ])
            
            for col_name in feature_columns:
                schema.add(StructField(col_name, DoubleType(), True))
            
            iso_results = spark.createDataFrame(pandas_results)
            
            # Jointure avec les données originales
            iso_anomalies = iso_results.filter(col("anomaly") == True) \
                .join(
                    aircraft_data.select("aircraft_msn", "flight_id", "event_timestamp"),
                    on=feature_columns,
                    how="inner"
                )
            
            logger.info(f"Isolation Forest: {iso_anomalies.count()} anomalies détectées pour l'avion {aircraft_msn}")
            
            # Fusion des anomalies détectées
            kmeans_anomalies_list = kmeans_anomalies.select(
                "aircraft_msn", "flight_id", "event_timestamp", 
                lit("K_MEANS").alias("detection_method"),
                col("distance_to_center").alias("anomaly_score")
            ).collect()
            
            iso_anomalies_list = iso_anomalies.select(
                "aircraft_msn", "flight_id", "event_timestamp", 
                lit("ISOLATION_FOREST").alias("detection_method"),
                col("anomaly_score")
            ).collect()
            
            # Ajout des anomalies à la liste globale
            for anomaly in kmeans_anomalies_list + iso_anomalies_list:
                # Détermination des paramètres anormaux
                if anomaly["detection_method"] == "K_MEANS":
                    # Pour K-Means, on récupère les données originales
                    original_data = aircraft_data.filter(
                        (col("flight_id") == anomaly["flight_id"]) & 
                        (col("event_timestamp") == anomaly["event_timestamp"])
                    ).collect()[0]
                    
                    # Calcul des moyennes et écarts-types pour cet avion
                    stats = aircraft_data.agg(
                        *[avg(c).alias(f"avg_{c}") for c in feature_columns],
                        *[stddev(c).alias(f"stddev_{c}") for c in feature_columns]
                    ).collect()[0]
                    
                    # Identification des paramètres anormaux (> 3 écarts-types)
                    abnormal_params = []
                    for param in feature_columns:
                        param_value = original_data[param]
                        param_mean = stats[f"avg_{param}"]
                        param_stddev = stats[f"stddev_{param}"]
                        
                        if param_stddev and abs(param_value - param_mean) > 3 * param_stddev:
                            abnormal_params.append(param)
                else:
                    # Pour Isolation Forest, on utilise le score d'anomalie
                    abnormal_params = ["unknown"]  # Isolation Forest ne donne pas cette information directement
                
                # Création de l'entrée d'anomalie
                anomaly_entry = {
                    "aircraft_msn": anomaly["aircraft_msn"],
                    "flight_id": anomaly["flight_id"],
                    "event_timestamp": str(anomaly["event_timestamp"]),
                    "detection_timestamp": execution_date.isoformat(),
                    "detection_method": anomaly["detection_method"],
                    "anomaly_score": float(anomaly["anomaly_score"]),
                    "abnormal_parameters": abnormal_params,
                    "description": f"Anomalie détectée par {anomaly['detection_method']} dans les paramètres: {', '.join(abnormal_params)}"
                }
                
                all_anomalies.append(anomaly_entry)
        
        # Création d'un DataFrame avec toutes les anomalies
        if all_anomalies:
            logger.info(f"Total des anomalies détectées: {len(all_anomalies)}")
            
            # Schéma pour le DataFrame des anomalies
            anomalies_schema = StructType([
                StructField("aircraft_msn", StringType(), True),
                StructField("flight_id", StringType(), True),
                StructField("event_timestamp", StringType(), True),
                StructField("detection_timestamp", StringType(), True),
                StructField("detection_method", StringType(), True),
                StructField("anomaly_score", DoubleType(), True),
                StructField("abnormal_parameters", StringType(), True),
                StructField("description", StringType(), True)
            ])
            
            # Conversion des listes en chaînes JSON
            for anomaly in all_anomalies:
                anomaly["abnormal_parameters"] = json.dumps(anomaly["abnormal_parameters"])
            
            # Création du DataFrame
            anomalies_df = spark.createDataFrame(all_anomalies, schema=anomalies_schema)
            
            # Écriture des anomalies dans TimescaleDB
            logger.info("Écriture des anomalies dans TimescaleDB")
            anomalies_df.write \
                .jdbc(url=jdbc_url, table="metrics.anomalies", mode="append", properties=connection_properties)
        else:
            logger.info("Aucune anomalie détectée")
        
        logger.info("Détection d'anomalies terminée avec succès")
    
    except Exception as e:
        logger.error(f"Erreur lors de la détection d'anomalies: {e}")
        raise
    
    finally:
        # Arrêt de la session Spark
        spark.stop()

if __name__ == "__main__":
    main()
