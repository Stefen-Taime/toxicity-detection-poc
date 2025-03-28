"""
Job Spark pour le traitement quotidien des données de vol
Ce script traite les données brutes et calcule des métriques agrégées
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, max, min, count, sum, stddev, date_format, to_date
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType, IntegerType
import os
import sys
import json
from datetime import datetime, timedelta

# Initialisation de la session Spark
spark = SparkSession.builder \
    .appName("MCS100 Daily Data Processing") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

# Fonction principale
def process_daily_data(date_str):
    """
    Traite les données de vol pour une date spécifique
    """
    print(f"Traitement des données pour la date: {date_str}")
    
    # Conversion de la date
    process_date = datetime.strptime(date_str, "%Y-%m-%d")
    yesterday = process_date - timedelta(days=1)
    yesterday_str = yesterday.strftime("%Y-%m-%d")
    
    # Chemins des données
    input_dir = f"/opt/airflow/data/tmp/{yesterday_str}"
    output_dir = f"/opt/airflow/data/processed/{yesterday_str}"
    
    # Création du répertoire de sortie s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)
    
    # Traitement des données de vol
    process_flight_data(input_dir, output_dir, yesterday_str)
    
    # Traitement des données d'utilisation
    process_usage_data(input_dir, output_dir, yesterday_str)
    
    # Traitement des événements de maintenance
    process_maintenance_events(input_dir, output_dir, yesterday_str)
    
    # Traitement des alertes
    process_alerts(input_dir, output_dir, yesterday_str)
    
    print(f"Traitement terminé. Résultats sauvegardés dans: {output_dir}")
    return output_dir

def process_flight_data(input_dir, output_dir, date_str):
    """
    Traite les données de vol
    """
    # Vérification de l'existence des fichiers CSV
    csv_dir = f"{input_dir}/csv"
    if not os.path.exists(csv_dir):
        print(f"Répertoire {csv_dir} non trouvé. Aucune donnée de vol à traiter.")
        return
    
    # Schéma des données de vol
    flight_schema = StructType([
        StructField("aircraft_msn", StringType(), True),
        StructField("flight_id", StringType(), True),
        StructField("event_timestamp", TimestampType(), True),
        StructField("engine_1_temp", DoubleType(), True),
        StructField("engine_2_temp", DoubleType(), True),
        StructField("engine_1_pressure", DoubleType(), True),
        StructField("engine_2_pressure", DoubleType(), True),
        StructField("engine_1_vibration", DoubleType(), True),
        StructField("engine_2_vibration", DoubleType(), True),
        StructField("fuel_flow_rate", DoubleType(), True),
        StructField("altitude", DoubleType(), True),
        StructField("speed", DoubleType(), True),
        StructField("external_temp", DoubleType(), True),
        StructField("wind_speed", DoubleType(), True),
        StructField("wind_direction", DoubleType(), True)
    ])
    
    # Lecture des fichiers CSV
    flight_data = spark.read.csv(f"{csv_dir}/*.csv", header=True, schema=flight_schema)
    
    # Filtrage des données pour la date spécifiée
    flight_data = flight_data.filter(
        date_format(col("event_timestamp"), "yyyy-MM-dd") == date_str
    )
    
    # Calcul des métriques agrégées par avion et par vol
    flight_metrics = flight_data.groupBy("aircraft_msn", "flight_id") \
        .agg(
            min("event_timestamp").alias("start_time"),
            max("event_timestamp").alias("end_time"),
            avg("engine_1_temp").alias("avg_engine_1_temp"),
            avg("engine_2_temp").alias("avg_engine_2_temp"),
            avg("engine_1_pressure").alias("avg_engine_1_pressure"),
            avg("engine_2_pressure").alias("avg_engine_2_pressure"),
            avg("engine_1_vibration").alias("avg_engine_1_vibration"),
            avg("engine_2_vibration").alias("avg_engine_2_vibration"),
            avg("fuel_flow_rate").alias("avg_fuel_flow_rate"),
            avg("altitude").alias("avg_altitude"),
            avg("speed").alias("avg_speed"),
            max("altitude").alias("max_altitude"),
            max("speed").alias("max_speed"),
            stddev("engine_1_temp").alias("stddev_engine_1_temp"),
            stddev("engine_2_temp").alias("stddev_engine_2_temp")
        )
    
    # Calcul des métriques agrégées par avion pour la journée
    daily_metrics = flight_data.groupBy("aircraft_msn") \
        .agg(
            count("flight_id").alias("flight_count"),
            avg("engine_1_temp").alias("daily_avg_engine_1_temp"),
            avg("engine_2_temp").alias("daily_avg_engine_2_temp"),
            avg("engine_1_pressure").alias("daily_avg_engine_1_pressure"),
            avg("engine_2_pressure").alias("daily_avg_engine_2_pressure"),
            avg("engine_1_vibration").alias("daily_avg_engine_1_vibration"),
            avg("engine_2_vibration").alias("daily_avg_engine_2_vibration"),
            avg("fuel_flow_rate").alias("daily_avg_fuel_flow_rate"),
            avg("altitude").alias("daily_avg_altitude"),
            avg("speed").alias("daily_avg_speed"),
            max("altitude").alias("daily_max_altitude"),
            max("speed").alias("daily_max_speed")
        )
    
    # Sauvegarde des résultats
    flight_metrics.write.mode("overwrite").parquet(f"{output_dir}/flight_metrics")
    daily_metrics.write.mode("overwrite").parquet(f"{output_dir}/daily_metrics")
    
    # Sauvegarde au format CSV pour faciliter la lecture
    flight_metrics.write.mode("overwrite").option("header", "true").csv(f"{output_dir}/flight_metrics_csv")
    daily_metrics.write.mode("overwrite").option("header", "true").csv(f"{output_dir}/daily_metrics_csv")
    
    print(f"Traitement des données de vol terminé: {flight_data.count()} enregistrements traités")

def process_usage_data(input_dir, output_dir, date_str):
    """
    Traite les données d'utilisation
    """
    # Vérification de l'existence des fichiers CSV
    csv_dir = f"{input_dir}/csv"
    if not os.path.exists(csv_dir):
        print(f"Répertoire {csv_dir} non trouvé. Aucune donnée d'utilisation à traiter.")
        return
    
    # Schéma des données d'utilisation
    usage_schema = StructType([
        StructField("aircraft_msn", StringType(), True),
        StructField("date", StringType(), True),
        StructField("takeoffs", IntegerType(), True),
        StructField("landings", IntegerType(), True),
        StructField("flight_hours", DoubleType(), True),
        StructField("apu_cycles", IntegerType(), True),
        StructField("apu_hours", DoubleType(), True)
    ])
    
    # Lecture des fichiers CSV
    usage_data = spark.read.csv(f"{csv_dir}/*.csv", header=True, schema=usage_schema)
    
    # Filtrage des données pour la date spécifiée
    usage_data = usage_data.filter(col("date") == date_str)
    
    # Calcul des métriques cumulatives
    cumulative_usage = usage_data.groupBy("aircraft_msn") \
        .agg(
            sum("takeoffs").alias("total_takeoffs"),
            sum("landings").alias("total_landings"),
            sum("flight_hours").alias("total_flight_hours"),
            sum("apu_cycles").alias("total_apu_cycles"),
            sum("apu_hours").alias("total_apu_hours")
        )
    
    # Sauvegarde des résultats
    usage_data.write.mode("overwrite").parquet(f"{output_dir}/usage_data")
    cumulative_usage.write.mode("overwrite").parquet(f"{output_dir}/cumulative_usage")
    
    # Sauvegarde au format CSV pour faciliter la lecture
    usage_data.write.mode("overwrite").option("header", "true").csv(f"{output_dir}/usage_data_csv")
    cumulative_usage.write.mode("overwrite").option("header", "true").csv(f"{output_dir}/cumulative_usage_csv")
    
    print(f"Traitement des données d'utilisation terminé: {usage_data.count()} enregistrements traités")

def process_maintenance_events(input_dir, output_dir, date_str):
    """
    Traite les événements de maintenance
    """
    # Vérification de l'existence des fichiers JSON
    json_dir = f"{input_dir}/json"
    if not os.path.exists(json_dir):
        print(f"Répertoire {json_dir} non trouvé. Aucun événement de maintenance à traiter.")
        return
    
    # Schéma des événements de maintenance
    maintenance_schema = StructType([
        StructField("aircraft_msn", StringType(), True),
        StructField("component_id", StringType(), True),
        StructField("event_timestamp", TimestampType(), True),
        StructField("event_type", StringType(), True),
        StructField("description", StringType(), True),
        StructField("action_taken", StringType(), True),
        StructField("technician", StringType(), True),
        StructField("duration_hours", DoubleType(), True),
        StructField("is_scheduled", StringType(), True)
    ])
    
    # Lecture des fichiers JSON
    maintenance_events = spark.read.json(f"{json_dir}/*.json", schema=maintenance_schema)
    
    # Filtrage des données pour la date spécifiée
    maintenance_events = maintenance_events.filter(
        date_format(col("event_timestamp"), "yyyy-MM-dd") == date_str
    )
    
    # Calcul des métriques par avion et par composant
    maintenance_metrics = maintenance_events.groupBy("aircraft_msn", "component_id") \
        .agg(
            count("*").alias("event_count"),
            sum(col("duration_hours")).alias("total_maintenance_hours"),
            sum(col("is_scheduled") == "true").alias("scheduled_events"),
            sum(col("is_scheduled") == "false").alias("unscheduled_events"),
            sum(col("event_type") == "REPAIR").alias("repair_events"),
            sum(col("event_type") == "INSPECTION").alias("inspection_events")
        )
    
    # Sauvegarde des résultats
    maintenance_events.write.mode("overwrite").parquet(f"{output_dir}/maintenance_events")
    maintenance_metrics.write.mode("overwrite").parquet(f"{output_dir}/maintenance_metrics")
    
    # Sauvegarde au format CSV pour faciliter la lecture
    maintenance_events.write.mode("overwrite").option("header", "true").csv(f"{output_dir}/maintenance_events_csv")
    maintenance_metrics.write.mode("overwrite").option("header", "true").csv(f"{output_dir}/maintenance_metrics_csv")
    
    print(f"Traitement des événements de maintenance terminé: {maintenance_events.count()} enregistrements traités")

def process_alerts(input_dir, output_dir, date_str):
    """
    Traite les alertes
    """
    # Vérification de l'existence des fichiers JSON
    json_dir = f"{input_dir}/json"
    if not os.path.exists(json_dir):
        print(f"Répertoire {json_dir} non trouvé. Aucune alerte à traiter.")
        return
    
    # Schéma des alertes
    alerts_schema = StructType([
        StructField("aircraft_msn", StringType(), True),
        StructField("component_id", StringType(), True),
        StructField("event_timestamp", TimestampType(), True),
        StructField("alert_code", StringType(), True),
        StructField("severity", StringType(), True),
        StructField("message", StringType(), True)
    ])
    
    # Lecture des fichiers JSON
    alerts = spark.read.json(f"{json_dir}/*.json", schema=alerts_schema)
    
    # Filtrage des données pour la date spécifiée
    alerts = alerts.filter(
        date_format(col("event_timestamp"), "yyyy-MM-dd") == date_str
    )
    
    # Calcul des métriques par avion et par composant
    alerts_metrics = alerts.groupBy("aircraft_msn", "component_id") \
        .agg(
            count("*").alias("alert_count"),
            sum(col("severity") == "CRITICAL").alias("critical_alerts"),
            sum(col("severity") == "WARNING").alias("warning_alerts"),
            sum(col("severity") == "INFO").alias("info_alerts")
        )
    
    # Sauvegarde des résultats
    alerts.write.mode("overwrite").parquet(f"{output_dir}/alerts")
    alerts_metrics.write.mode("overwrite").parquet(f"{output_dir}/alerts_metrics")
    
    # Sauvegarde au format CSV pour faciliter la lecture
    alerts.write.mode("overwrite").option("header", "true").csv(f"{output_dir}/alerts_csv")
    alerts_metrics.write.mode("overwrite").option("header", "true").csv(f"{output_dir}/alerts_metrics_csv")
    
    print(f"Traitement des alertes terminé: {alerts.count()} enregistrements traités")

# Point d'entrée du script
if __name__ == "__main__":
    # Vérification des arguments
    if len(sys.argv) != 2:
        print("Usage: process_daily_data.py <date>")
        sys.exit(1)
    
    # Récupération de la date
    date_str = sys.argv[1]
    
    # Traitement des données
    output_dir = process_daily_data(date_str)
    
    # Écriture du chemin de sortie dans un fichier pour récupération par Airflow
    with open("/tmp/output_dir.txt", "w") as f:
        f.write(output_dir)
    
    # Arrêt de la session Spark
    spark.stop()
