"""
Job Spark pour l'optimisation des intervalles de maintenance
Ce script analyse les données historiques pour recommander des intervalles de maintenance optimaux
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, sum, count, when, lit, expr, datediff, to_date, udf
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType, IntegerType, ArrayType
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.regression import RandomForestRegressor
from pyspark.ml.evaluation import RegressionEvaluator
import os
import logging
import json
from datetime import datetime, timedelta
import numpy as np

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Fonction principale pour l'optimisation des intervalles de maintenance"""
    logger.info("Démarrage de l'optimisation des intervalles de maintenance")
    
    # Création de la session Spark
    spark = SparkSession.builder \
        .appName("MCS100 Maintenance Optimization") \
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
        
        # Période d'analyse (180 derniers jours)
        start_date = (execution_date - timedelta(days=180)).strftime('%Y-%m-%d')
        
        logger.info(f"Optimisation des intervalles de maintenance pour la période {start_date} à {end_date}")
        
        # Lecture des événements de maintenance
        logger.info("Lecture des événements de maintenance")
        maintenance_df = spark.read \
            .jdbc(url=jdbc_url, table="raw.maintenance_events", properties=connection_properties) \
            .filter(col("event_timestamp").between(start_date, end_date))
        
        # Lecture des informations sur les composants
        logger.info("Lecture des informations sur les composants")
        components_df = spark.read \
            .jdbc(url=jdbc_url, table="raw.components", properties=connection_properties)
        
        # Lecture des cycles d'utilisation
        logger.info("Lecture des cycles d'utilisation")
        usage_df = spark.read \
            .jdbc(url=jdbc_url, table="raw.usage_cycles", properties=connection_properties) \
            .filter(col("date").between(start_date, end_date))
        
        # Lecture des alertes
        logger.info("Lecture des alertes")
        alerts_df = spark.read \
            .jdbc(url=jdbc_url, table="raw.alerts", properties=connection_properties) \
            .filter(col("event_timestamp").between(start_date, end_date))
        
        # Préparation des données pour l'analyse
        logger.info("Préparation des données pour l'analyse")
        
        # Conversion des timestamps en dates
        maintenance_with_date = maintenance_df \
            .withColumn("event_date", col("event_timestamp").cast("date"))
        
        # Calcul des intervalles entre les maintenances
        maintenance_intervals = maintenance_with_date \
            .filter(col("is_scheduled") == True) \
            .select("aircraft_msn", "component_id", "event_date") \
            .distinct() \
            .orderBy("aircraft_msn", "component_id", "event_date")
        
        # Fonction pour calculer les intervalles
        def calculate_intervals(maintenance_data):
            """Calcule les intervalles entre les maintenances pour chaque composant"""
            results = []
            
            # Regroupement par aircraft_msn et component_id
            grouped_data = {}
            for row in maintenance_data:
                key = (row["aircraft_msn"], row["component_id"])
                if key not in grouped_data:
                    grouped_data[key] = []
                grouped_data[key].append(row["event_date"])
            
            # Calcul des intervalles pour chaque groupe
            for (aircraft_msn, component_id), dates in grouped_data.items():
                sorted_dates = sorted(dates)
                
                if len(sorted_dates) > 1:
                    for i in range(1, len(sorted_dates)):
                        interval_days = (sorted_dates[i] - sorted_dates[i-1]).days
                        
                        if interval_days > 0:
                            results.append({
                                "aircraft_msn": aircraft_msn,
                                "component_id": component_id,
                                "start_date": sorted_dates[i-1],
                                "end_date": sorted_dates[i],
                                "interval_days": interval_days
                            })
            
            return results
        
        # Conversion en Pandas pour le calcul des intervalles
        maintenance_pandas = maintenance_intervals.toPandas()
        intervals_data = calculate_intervals(maintenance_pandas.to_dict('records'))
        
        # Création du DataFrame des intervalles
        intervals_schema = StructType([
            StructField("aircraft_msn", StringType(), True),
            StructField("component_id", StringType(), True),
            StructField("start_date", TimestampType(), True),
            StructField("end_date", TimestampType(), True),
            StructField("interval_days", IntegerType(), True)
        ])
        
        intervals_df = spark.createDataFrame(intervals_data, schema=intervals_schema)
        
        # Calcul des heures de vol dans chaque intervalle
        intervals_with_usage = intervals_df \
            .join(
                usage_df.select(
                    "aircraft_msn", "date", "flight_hours", "takeoffs", "landings"
                ),
                (intervals_df["aircraft_msn"] == usage_df["aircraft_msn"]) & 
                (usage_df["date"].between(intervals_df["start_date"], intervals_df["end_date"])),
                "left"
            ) \
            .groupBy("aircraft_msn", "component_id", "start_date", "end_date", "interval_days") \
            .agg(
                sum("flight_hours").alias("flight_hours_in_interval"),
                sum("takeoffs").alias("takeoffs_in_interval"),
                sum("landings").alias("landings_in_interval")
            )
        
        # Calcul des défaillances non programmées dans chaque intervalle
        intervals_with_failures = intervals_with_usage \
            .join(
                maintenance_df.filter(col("is_scheduled") == False) \
                    .select(
                        "aircraft_msn", "component_id", "event_timestamp"
                    ) \
                    .withColumn("event_date", col("event_timestamp").cast("date")),
                (intervals_with_usage["aircraft_msn"] == maintenance_df["aircraft_msn"]) & 
                (intervals_with_usage["component_id"] == maintenance_df["component_id"]) & 
                (maintenance_df["event_date"].between(intervals_with_usage["start_date"], intervals_with_usage["end_date"])),
                "left"
            ) \
            .groupBy("aircraft_msn", "component_id", "start_date", "end_date", "interval_days", 
                     "flight_hours_in_interval", "takeoffs_in_interval", "landings_in_interval") \
            .agg(
                count("event_timestamp").alias("unscheduled_failures_in_interval")
            )
        
        # Calcul des alertes dans chaque intervalle
        intervals_with_alerts = intervals_with_failures \
            .join(
                alerts_df.select(
                    "aircraft_msn", "component_id", "event_timestamp", "severity"
                ) \
                .withColumn("event_date", col("event_timestamp").cast("date")),
                (intervals_with_failures["aircraft_msn"] == alerts_df["aircraft_msn"]) & 
                (intervals_with_failures["component_id"] == alerts_df["component_id"]) & 
                (alerts_df["event_date"].between(intervals_with_failures["start_date"], intervals_with_failures["end_date"])),
                "left"
            ) \
            .groupBy("aircraft_msn", "component_id", "start_date", "end_date", "interval_days", 
                     "flight_hours_in_interval", "takeoffs_in_interval", "landings_in_interval", 
                     "unscheduled_failures_in_interval") \
            .agg(
                count("event_timestamp").alias("alerts_in_interval"),
                count(when(col("severity") == "CRITICAL", 1)).alias("critical_alerts_in_interval")
            )
        
        # Jointure avec les informations sur les composants
        complete_intervals = intervals_with_alerts \
            .join(
                components_df.select(
                    "component_id", "component_name", "component_type", "recommended_maintenance_interval"
                ),
                "component_id",
                "left"
            )
        
        # Préparation des données pour le modèle de prédiction
        logger.info("Préparation des données pour le modèle de prédiction")
        
        # Calcul du risque de défaillance
        model_data = complete_intervals \
            .withColumn("failure_risk", 
                when(col("flight_hours_in_interval") > 0, 
                     (col("unscheduled_failures_in_interval") * 2 + col("alerts_in_interval")) / col("flight_hours_in_interval") * 100)
                .otherwise(0)
            ) \
            .withColumn("optimal_interval_ratio", 
                when(col("failure_risk") > 5, 0.8)  # Risque élevé: réduire l'intervalle
                .when(col("failure_risk") > 2, 1.0)  # Risque modéré: maintenir l'intervalle
                .otherwise(1.1)  # Risque faible: augmenter l'intervalle
            ) \
            .withColumn("optimal_interval_days", 
                col("recommended_maintenance_interval") * col("optimal_interval_ratio")
            )
        
        # Préparation des features pour le modèle ML
        feature_columns = [
            "interval_days", 
            "flight_hours_in_interval", 
            "takeoffs_in_interval", 
            "landings_in_interval", 
            "unscheduled_failures_in_interval", 
            "alerts_in_interval", 
            "critical_alerts_in_interval"
        ]
        
        # Assemblage des vecteurs de features
        assembler = VectorAssembler(inputCols=feature_columns, outputCol="features")
        assembled_data = assembler.transform(model_data)
        
        # Normalisation des features
        scaler = StandardScaler(inputCol="features", outputCol="scaled_features", withStd=True, withMean=True)
        scaler_model = scaler.fit(assembled_data)
        scaled_data = scaler_model.transform(assembled_data)
        
        # Entraînement du modèle de régression pour prédire le risque de défaillance
        logger.info("Entraînement du modèle de régression")
        
        # Division des données en ensembles d'entraînement et de test
        train_data, test_data = scaled_data.randomSplit([0.8, 0.2], seed=42)
        
        # Entraînement du modèle Random Forest
        rf = RandomForestRegressor(
            featuresCol="scaled_features", 
            labelCol="failure_risk", 
            numTrees=50, 
            maxDepth=5, 
            seed=42
        )
        
        rf_model = rf.fit(train_data)
        
        # Évaluation du modèle
        predictions = rf_model.transform(test_data)
        evaluator = RegressionEvaluator(labelCol="failure_risk", predictionCol="prediction", metricName="rmse")
        rmse = evaluator.evaluate(predictions)
        logger.info(f"Root Mean Squared Error (RMSE): {rmse}")
        
        # Génération des recommandations d'optimisation
        logger.info("Génération des recommandations d'optimisation")
        
        # Calcul des recommandations par composant
        component_recommendations = model_data \
            .groupBy("component_id", "component_name", "component_type", "recommended_maintenance_interval") \
            .agg(
                avg("optimal_interval_days").alias("optimal_interval_days"),
                avg("failure_risk").alias("average_failure_risk"),
                sum("unscheduled_failures_in_interval").alias("total_unscheduled_failures"),
                sum("alerts_in_interval").alias("total_alerts"),
                count("*").alias("interval_count")
            ) \
            .withColumn("recommendation", 
                when(col("average_failure_risk") > 5, "REDUCE_INTERVAL")
                .when(col("average_failure_risk") > 2, "MAINTAIN_INTERVAL")
                .otherwise("EXTEND_INTERVAL")
            ) \
            .withColumn("justification", 
                when(col("average_failure_risk") > 5, "Taux élevé de défaillances non programmées et d'alertes")
                .when(col("average_failure_risk") > 2, "Taux modéré de défaillances non programmées")
                .otherwise("Faible taux de défaillances non programmées")
            ) \
            .withColumn("confidence_score", 
                when(col("interval_count") > 5, 0.9)
                .when(col("interval_count") > 2, 0.7)
                .otherwise(0.5)
            ) \
            .withColumn("analysis_date", lit(end_date))
        
        # Écriture des recommandations dans TimescaleDB
        logger.info("Écriture des recommandations dans TimescaleDB")
        component_recommendations.write \
            .jdbc(url=jdbc_url, table="metrics.maintenance_recommendations", mode="append", properties=connection_properties)
        
        logger.info("Optimisation des intervalles de maintenance terminée avec succès")
    
    except Exception as e:
        logger.error(f"Erreur lors de l'optimisation des intervalles de maintenance: {e}")
        raise
    
    finally:
        # Arrêt de la session Spark
        spark.stop()

if __name__ == "__main__":
    main()
