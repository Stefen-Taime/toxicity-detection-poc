"""
Job Spark pour le traitement des données de vol
Ce script traite les données de vol brutes pour les préparer à l'analyse
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, stddev, count, when, lit, expr, window
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType, IntegerType
import os
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Fonction principale pour le traitement des données de vol"""
    logger.info("Démarrage du traitement des données de vol")
    
    # Création de la session Spark
    spark = SparkSession.builder \
        .appName("MCS100 Flight Data Processing") \
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
        
        # Lecture des données de vol depuis TimescaleDB
        logger.info("Lecture des données de vol depuis TimescaleDB")
        flight_data_df = spark.read \
            .jdbc(url=jdbc_url, table="raw.flight_data", properties=connection_properties)
        
        # Lecture des métadonnées des avions
        logger.info("Lecture des métadonnées des avions")
        aircraft_metadata_df = spark.read \
            .jdbc(url=jdbc_url, table="raw.aircraft_metadata", properties=connection_properties)
        
        # Nettoyage des données
        logger.info("Nettoyage des données de vol")
        cleaned_flight_data = flight_data_df \
            .filter(col("engine_1_temp").isNotNull() & col("engine_2_temp").isNotNull()) \
            .filter(col("engine_1_temp") > 0 & col("engine_2_temp") > 0) \
            .filter(col("fuel_flow_rate").isNotNull() & col("fuel_flow_rate") > 0)
        
        # Jointure avec les métadonnées des avions
        logger.info("Jointure avec les métadonnées des avions")
        enriched_flight_data = cleaned_flight_data \
            .join(aircraft_metadata_df, "aircraft_msn", "left")
        
        # Calcul des statistiques par vol
        logger.info("Calcul des statistiques par vol")
        flight_stats = enriched_flight_data \
            .groupBy("aircraft_msn", "flight_id", "airline_code") \
            .agg(
                avg("engine_1_temp").alias("avg_engine_1_temp"),
                avg("engine_2_temp").alias("avg_engine_2_temp"),
                avg("engine_1_pressure").alias("avg_engine_1_pressure"),
                avg("engine_2_pressure").alias("avg_engine_2_pressure"),
                avg("engine_1_vibration").alias("avg_engine_1_vibration"),
                avg("engine_2_vibration").alias("avg_engine_2_vibration"),
                avg("fuel_flow_rate").alias("avg_fuel_flow_rate"),
                avg("altitude").alias("avg_altitude"),
                avg("speed").alias("avg_speed"),
                stddev("engine_1_temp").alias("stddev_engine_1_temp"),
                stddev("engine_2_temp").alias("stddev_engine_2_temp"),
                stddev("engine_1_vibration").alias("stddev_engine_1_vibration"),
                stddev("engine_2_vibration").alias("stddev_engine_2_vibration"),
                count("*").alias("data_points")
            )
        
        # Calcul des statistiques par avion
        logger.info("Calcul des statistiques par avion")
        aircraft_stats = enriched_flight_data \
            .groupBy("aircraft_msn", "airline_code") \
            .agg(
                avg("engine_1_temp").alias("avg_engine_1_temp"),
                avg("engine_2_temp").alias("avg_engine_2_temp"),
                avg("fuel_flow_rate").alias("avg_fuel_flow_rate"),
                count("flight_id").alias("flight_count")
            )
        
        # Calcul des statistiques par compagnie aérienne
        logger.info("Calcul des statistiques par compagnie aérienne")
        airline_stats = enriched_flight_data \
            .groupBy("airline_code") \
            .agg(
                avg("engine_1_temp").alias("avg_engine_1_temp"),
                avg("engine_2_temp").alias("avg_engine_2_temp"),
                avg("fuel_flow_rate").alias("avg_fuel_flow_rate"),
                count("flight_id").alias("flight_count"),
                count(expr("distinct aircraft_msn")).alias("aircraft_count")
            )
        
        # Calcul des tendances sur fenêtre glissante (7 jours)
        logger.info("Calcul des tendances sur fenêtre glissante")
        windowed_stats = enriched_flight_data \
            .withColumn("event_date", col("event_timestamp").cast("date")) \
            .groupBy(
                window(col("event_timestamp"), "7 days"),
                "aircraft_msn"
            ) \
            .agg(
                avg("engine_1_temp").alias("avg_engine_1_temp"),
                avg("engine_2_temp").alias("avg_engine_2_temp"),
                avg("fuel_flow_rate").alias("avg_fuel_flow_rate"),
                count("flight_id").alias("flight_count")
            )
        
        # Écriture des résultats dans TimescaleDB
        logger.info("Écriture des statistiques de vol dans TimescaleDB")
        flight_stats.write \
            .jdbc(url=jdbc_url, table="processed.flight_stats", mode="append", properties=connection_properties)
        
        logger.info("Écriture des statistiques par avion dans TimescaleDB")
        aircraft_stats.write \
            .jdbc(url=jdbc_url, table="processed.aircraft_stats", mode="append", properties=connection_properties)
        
        logger.info("Écriture des statistiques par compagnie aérienne dans TimescaleDB")
        airline_stats.write \
            .jdbc(url=jdbc_url, table="processed.airline_stats", mode="append", properties=connection_properties)
        
        logger.info("Écriture des tendances dans TimescaleDB")
        windowed_stats.select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            col("aircraft_msn"),
            col("avg_engine_1_temp"),
            col("avg_engine_2_temp"),
            col("avg_fuel_flow_rate"),
            col("flight_count")
        ).write \
            .jdbc(url=jdbc_url, table="processed.windowed_stats", mode="append", properties=connection_properties)
        
        logger.info("Traitement des données de vol terminé avec succès")
    
    except Exception as e:
        logger.error(f"Erreur lors du traitement des données de vol: {e}")
        raise
    
    finally:
        # Arrêt de la session Spark
        spark.stop()

if __name__ == "__main__":
    main()
