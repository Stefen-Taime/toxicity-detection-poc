"""
Job Spark pour l'analyse de fiabilité des composants
Ce script analyse la fiabilité des composants et systèmes de la flotte MCS100
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, sum, count, when, lit, expr, datediff, to_date
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType, IntegerType
import os
import logging
from datetime import datetime, timedelta

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Fonction principale pour l'analyse de fiabilité"""
    logger.info("Démarrage de l'analyse de fiabilité")
    
    # Création de la session Spark
    spark = SparkSession.builder \
        .appName("MCS100 Reliability Analysis") \
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
        
        # Périodes d'analyse
        periods = [
            {"name": "7d", "days": 7},
            {"name": "30d", "days": 30},
            {"name": "90d", "days": 90}
        ]
        
        for period in periods:
            days = period["days"]
            period_name = period["name"]
            start_date = (execution_date - timedelta(days=days)).strftime('%Y-%m-%d')
            
            logger.info(f"Analyse de fiabilité pour la période {period_name} ({start_date} à {end_date})")
            
            # Lecture des événements de maintenance
            logger.info("Lecture des événements de maintenance")
            maintenance_df = spark.read \
                .jdbc(url=jdbc_url, table="raw.maintenance_events", properties=connection_properties) \
                .filter(col("event_timestamp").between(start_date, end_date))
            
            # Lecture des alertes
            logger.info("Lecture des alertes")
            alerts_df = spark.read \
                .jdbc(url=jdbc_url, table="raw.alerts", properties=connection_properties) \
                .filter(col("event_timestamp").between(start_date, end_date))
            
            # Lecture des cycles d'utilisation
            logger.info("Lecture des cycles d'utilisation")
            usage_df = spark.read \
                .jdbc(url=jdbc_url, table="raw.usage_cycles", properties=connection_properties) \
                .filter(col("date").between(start_date, end_date))
            
            # Lecture des informations sur les composants
            logger.info("Lecture des informations sur les composants")
            components_df = spark.read \
                .jdbc(url=jdbc_url, table="raw.components", properties=connection_properties)
            
            # Analyse de fiabilité par composant
            logger.info("Analyse de fiabilité par composant")
            
            # Calcul des défaillances par composant
            component_failures = maintenance_df \
                .filter(col("event_type") == "FAILURE") \
                .groupBy("component_id") \
                .agg(
                    count("*").alias("total_failures"),
                    count(when(col("is_scheduled") == False, 1)).alias("unscheduled_failures")
                )
            
            # Calcul des alertes par composant
            component_alerts = alerts_df \
                .groupBy("component_id") \
                .agg(
                    count("*").alias("total_alerts"),
                    count(when(col("severity") == "CRITICAL", 1)).alias("critical_alerts")
                )
            
            # Jointure des composants avec les avions
            component_aircraft = components_df \
                .select("component_id", "aircraft_msn")
            
            # Calcul des heures de vol par avion
            aircraft_usage = usage_df \
                .groupBy("aircraft_msn") \
                .agg(
                    sum("flight_hours").alias("total_flight_hours"),
                    sum("takeoffs").alias("total_cycles")
                )
            
            # Jointure pour obtenir les heures de vol par composant
            component_usage = component_aircraft \
                .join(aircraft_usage, "aircraft_msn", "left") \
                .groupBy("component_id") \
                .agg(
                    sum("total_flight_hours").alias("total_flight_hours"),
                    sum("total_cycles").alias("total_cycles")
                )
            
            # Calcul des métriques de fiabilité
            reliability_metrics = component_usage \
                .join(component_failures, "component_id", "left") \
                .join(component_alerts, "component_id", "left") \
                .join(components_df.select("component_id", "component_name", "component_type"), "component_id", "left") \
                .withColumn("total_failures", when(col("total_failures").isNull(), 0).otherwise(col("total_failures"))) \
                .withColumn("unscheduled_failures", when(col("unscheduled_failures").isNull(), 0).otherwise(col("unscheduled_failures"))) \
                .withColumn("total_alerts", when(col("total_alerts").isNull(), 0).otherwise(col("total_alerts"))) \
                .withColumn("critical_alerts", when(col("critical_alerts").isNull(), 0).otherwise(col("critical_alerts"))) \
                .withColumn("mtbf_hours", when(col("total_failures") > 0, col("total_flight_hours") / col("total_failures")).otherwise(None)) \
                .withColumn("failure_rate_per_1000_hours", when(col("total_flight_hours") > 0, col("total_failures") * 1000 / col("total_flight_hours")).otherwise(None)) \
                .withColumn("period", lit(period_name)) \
                .withColumn("start_date", lit(start_date)) \
                .withColumn("end_date", lit(end_date)) \
                .withColumn("calculation_timestamp", lit(execution_date.isoformat()))
            
            # Écriture des métriques de fiabilité dans TimescaleDB
            logger.info(f"Écriture des métriques de fiabilité pour la période {period_name}")
            reliability_metrics.write \
                .jdbc(url=jdbc_url, table="metrics.component_reliability", mode="append", properties=connection_properties)
            
            # Analyse de fiabilité par système
            logger.info("Analyse de fiabilité par système")
            
            # Jointure pour obtenir le système de chaque composant
            component_system = components_df \
                .select("component_id", "component_type")
            
            # Calcul des métriques par système
            system_reliability = component_failures \
                .join(component_system, "component_id", "left") \
                .groupBy("component_type") \
                .agg(
                    count("component_id").alias("component_count"),
                    sum("total_failures").alias("total_failures"),
                    sum("unscheduled_failures").alias("unscheduled_failures")
                ) \
                .join(
                    component_alerts \
                    .join(component_system, "component_id", "left") \
                    .groupBy("component_type") \
                    .agg(
                        sum("total_alerts").alias("total_alerts"),
                        sum("critical_alerts").alias("critical_alerts")
                    ),
                    "component_type",
                    "left"
                ) \
                .withColumn("total_alerts", when(col("total_alerts").isNull(), 0).otherwise(col("total_alerts"))) \
                .withColumn("critical_alerts", when(col("critical_alerts").isNull(), 0).otherwise(col("critical_alerts"))) \
                .withColumn("period", lit(period_name)) \
                .withColumn("start_date", lit(start_date)) \
                .withColumn("end_date", lit(end_date)) \
                .withColumn("calculation_timestamp", lit(execution_date.isoformat()))
            
            # Écriture des métriques de fiabilité par système dans TimescaleDB
            logger.info(f"Écriture des métriques de fiabilité par système pour la période {period_name}")
            system_reliability.write \
                .jdbc(url=jdbc_url, table="metrics.system_reliability", mode="append", properties=connection_properties)
        
        logger.info("Analyse de fiabilité terminée avec succès")
    
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse de fiabilité: {e}")
        raise
    
    finally:
        # Arrêt de la session Spark
        spark.stop()

if __name__ == "__main__":
    main()
