"""
DAG pour l'analyse mensuelle de la performance de la flotte
Ce DAG génère des rapports complets de performance par compagnie aérienne et par flotte.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.hooks.base import BaseHook
from airflow_dbt.operators.dbt_operator import DbtRunOperator
import pandas as pd
import numpy as np
import logging
import os
import json
import matplotlib.pyplot as plt
import seaborn as sns

# Configuration par défaut
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2024, 1, 1),
}

# Création du DAG
dag = DAG(
    'monthly_fleet_performance_dag',
    default_args=default_args,
    description='Génération mensuelle des rapports de performance de la flotte',
    schedule_interval='0 3 1 * *',  # Le 1er de chaque mois à 3h du matin
    catchup=False,
    tags=['mcs100', 'performance'],
)

# Fonction pour extraire les données de performance
def extract_performance_data(**kwargs):
    """Extrait les données de performance pour l'analyse mensuelle"""
    logging.info("Extraction des données de performance...")
    
    # Connexion à TimescaleDB
    pg_hook = BaseHook.get_connection('postgres_conn')
    conn_string = f"postgresql://{pg_hook.login}:{pg_hook.password}@{pg_hook.host}:{pg_hook.port}/{pg_hook.schema}"
    
    # Date d'exécution
    execution_date = kwargs['execution_date']
    year = execution_date.year
    month = execution_date.month
    
    # Calcul du premier et dernier jour du mois précédent
    if month == 1:
        previous_month = 12
        previous_year = year - 1
    else:
        previous_month = month - 1
        previous_year = year
    
    start_date = datetime(previous_year, previous_month, 1)
    if previous_month == 12:
        end_date = datetime(previous_year, previous_month, 31)
    else:
        end_date = datetime(previous_year, previous_month + 1, 1) - timedelta(days=1)
    
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    logging.info(f"Période d'analyse: {start_date_str} à {end_date_str}")
    
    # Requêtes pour extraire les données
    queries = {
        'flight_data': f"""
        SELECT 
            fd.aircraft_msn,
            am.airline_code,
            DATE(fd.event_timestamp) as date,
            AVG(fd.engine_1_temp) as avg_engine_1_temp,
            AVG(fd.engine_2_temp) as avg_engine_2_temp,
            AVG(fd.engine_1_vibration) as avg_engine_1_vibration,
            AVG(fd.engine_2_vibration) as avg_engine_2_vibration,
            AVG(fd.fuel_flow_rate) as avg_fuel_flow_rate
        FROM 
            raw.flight_data fd
        JOIN 
            raw.aircraft_metadata am ON fd.aircraft_msn = am.aircraft_msn
        WHERE 
            fd.event_timestamp BETWEEN '{start_date_str}' AND '{end_date_str}'
        GROUP BY 
            fd.aircraft_msn, am.airline_code, DATE(fd.event_timestamp)
        ORDER BY 
            am.airline_code, fd.aircraft_msn, DATE(fd.event_timestamp)
        """,
        
        'usage_cycles': f"""
        SELECT 
            uc.aircraft_msn,
            am.airline_code,
            uc.date,
            uc.flight_hours,
            uc.takeoffs,
            uc.landings,
            uc.apu_cycles,
            uc.apu_hours
        FROM 
            raw.usage_cycles uc
        JOIN 
            raw.aircraft_metadata am ON uc.aircraft_msn = am.aircraft_msn
        WHERE 
            uc.date BETWEEN '{start_date_str}' AND '{end_date_str}'
        ORDER BY 
            am.airline_code, uc.aircraft_msn, uc.date
        """,
        
        'maintenance_events': f"""
        SELECT 
            me.aircraft_msn,
            am.airline_code,
            me.component_id,
            me.event_timestamp,
            me.event_type,
            me.is_scheduled,
            me.duration_hours
        FROM 
            raw.maintenance_events me
        JOIN 
            raw.aircraft_metadata am ON me.aircraft_msn = am.aircraft_msn
        WHERE 
            me.event_timestamp BETWEEN '{start_date_str}' AND '{end_date_str}'
        ORDER BY 
            am.airline_code, me.aircraft_msn, me.event_timestamp
        """,
        
        'alerts': f"""
        SELECT 
            a.aircraft_msn,
            am.airline_code,
            a.component_id,
            a.event_timestamp,
            a.alert_code,
            a.severity
        FROM 
            raw.alerts a
        JOIN 
            raw.aircraft_metadata am ON a.aircraft_msn = am.aircraft_msn
        WHERE 
            a.event_timestamp BETWEEN '{start_date_str}' AND '{end_date_str}'
        ORDER BY 
            am.airline_code, a.aircraft_msn, a.event_timestamp
        """
    }
    
    # Création du répertoire de sortie
    output_dir = f'/opt/airflow/data/performance/{previous_year}_{previous_month:02d}'
    os.makedirs(output_dir, exist_ok=True)
    
    # Extraction des données
    for name, query in queries.items():
        try:
            df = pd.read_sql(query, conn_string)
            df.to_csv(f'{output_dir}/{name}.csv', index=False)
            logging.info(f"Données extraites pour {name}: {len(df)} enregistrements")
        except Exception as e:
            logging.error(f"Erreur lors de l'extraction des données pour {name}: {e}")
    
    logging.info("Extraction des données de performance terminée.")

# Fonction pour calculer les métriques de performance
def calculate_performance_metrics(**kwargs):
    """Calcule les métriques de performance à partir des données extraites"""
    logging.info("Calcul des métriques de performance...")
    
    # Date d'exécution
    execution_date = kwargs['execution_date']
    year = execution_date.year
    month = execution_date.month
    
    # Calcul du mois précédent
    if month == 1:
        previous_month = 12
        previous_year = year - 1
    else:
        previous_month = month - 1
        previous_year = year
    
    # Répertoire des données
    data_dir = f'/opt/airflow/data/performance/{previous_year}_{previous_month:02d}'
    
    # Répertoire de sortie pour les métriques
    metrics_dir = f'{data_dir}/metrics'
    os.makedirs(metrics_dir, exist_ok=True)
    
    try:
        # Chargement des données
        df_flight = pd.read_csv(f'{data_dir}/flight_data.csv')
        df_usage = pd.read_csv(f'{data_dir}/usage_cycles.csv')
        df_maintenance = pd.read_csv(f'{data_dir}/maintenance_events.csv')
        df_alerts = pd.read_csv(f'{data_dir}/alerts.csv')
        
        # 1. Métriques par compagnie aérienne
        airline_metrics = []
        
        for airline_code in df_usage['airline_code'].unique():
            # Filtrer les données pour cette compagnie
            airline_usage = df_usage[df_usage['airline_code'] == airline_code]
            airline_maintenance = df_maintenance[df_maintenance['airline_code'] == airline_code]
            airline_alerts = df_alerts[df_alerts['airline_code'] == airline_code]
            
            # Calcul des métriques
            total_flight_hours = airline_usage['flight_hours'].sum()
            total_cycles = airline_usage['takeoffs'].sum()
            total_maintenance_events = len(airline_maintenance)
            total_unscheduled_maintenance = len(airline_maintenance[airline_maintenance['is_scheduled'] == False])
            total_alerts = len(airline_alerts)
            critical_alerts = len(airline_alerts[airline_alerts['severity'] == 'CRITICAL'])
            
            # Calcul des ratios
            maintenance_per_flight_hour = total_maintenance_events / max(1, total_flight_hours)
            unscheduled_ratio = total_unscheduled_maintenance / max(1, total_maintenance_events)
            alerts_per_flight_hour = total_alerts / max(1, total_flight_hours)
            
            # Ajout des métriques
            airline_metrics.append({
                'airline_code': airline_code,
                'year': previous_year,
                'month': previous_month,
                'total_flight_hours': float(total_flight_hours),
                'total_cycles': int(total_cycles),
                'total_maintenance_events': int(total_maintenance_events),
                'total_unscheduled_maintenance': int(total_unscheduled_maintenance),
                'total_alerts': int(total_alerts),
                'critical_alerts': int(critical_alerts),
                'maintenance_per_flight_hour': float(maintenance_per_flight_hour),
                'unscheduled_ratio': float(unscheduled_ratio),
                'alerts_per_flight_hour': float(alerts_per_flight_hour)
            })
        
        # Enregistrement des métriques par compagnie
        df_airline_metrics = pd.DataFrame(airline_metrics)
        df_airline_metrics.to_csv(f'{metrics_dir}/airline_metrics.csv', index=False)
        
        # 2. Métriques par avion
        aircraft_metrics = []
        
        for aircraft_msn in df_usage['aircraft_msn'].unique():
            # Filtrer les données pour cet avion
            aircraft_usage = df_usage[df_usage['aircraft_msn'] == aircraft_msn]
            aircraft_flight = df_flight[df_flight['aircraft_msn'] == aircraft_msn]
            aircraft_maintenance = df_maintenance[df_maintenance['aircraft_msn'] == aircraft_msn]
            aircraft_alerts = df_alerts[df_alerts['aircraft_msn'] == aircraft_msn]
            
            # Récupérer la compagnie aérienne
            airline_code = aircraft_usage['airline_code'].iloc[0] if not aircraft_usage.empty else 'UNKNOWN'
            
            # Calcul des métriques
            total_flight_hours = aircraft_usage['flight_hours'].sum()
            total_cycles = aircraft_usage['takeoffs'].sum()
            avg_fuel_flow = aircraft_flight['avg_fuel_flow_rate'].mean() if not aircraft_flight.empty else 0
            avg_engine_1_temp = aircraft_flight['avg_engine_1_temp'].mean() if not aircraft_flight.empty else 0
            avg_engine_2_temp = aircraft_flight['avg_engine_2_temp'].mean() if not aircraft_flight.empty else 0
            total_maintenance_events = len(aircraft_maintenance)
            total_unscheduled_maintenance = len(aircraft_maintenance[aircraft_maintenance['is_scheduled'] == False])
            total_alerts = len(aircraft_alerts)
            
            # Calcul des ratios
            fuel_efficiency = avg_fuel_flow / max(1, total_flight_hours)
            maintenance_per_flight_hour = total_maintenance_events / max(1, total_flight_hours)
            
            # Ajout des métriques
            aircraft_metrics.append({
                'aircraft_msn': aircraft_msn,
                'airline_code': airline_code,
                'year': previous_year,
                'month': previous_month,
                'total_flight_hours': float(total_flight_hours),
                'total_cycles': int(total_cycles),
                'avg_fuel_flow': float(avg_fuel_flow),
                'avg_engine_1_temp': float(avg_engine_1_temp),
                'avg_engine_2_temp': float(avg_engine_2_temp),
                'total_maintenance_events': int(total_maintenance_events),
                'total_unscheduled_maintenance': int(total_unscheduled_maintenance),
                'total_alerts': int(total_alerts),
                'fuel_efficiency': float(fuel_efficiency),
                'maintenance_per_flight_hour': float(maintenance_per_flight_hour)
            })
        
        # Enregistrement des métriques par avion
        df_aircraft_metrics = pd.DataFrame(aircraft_metrics)
        df_aircraft_metrics.to_csv(f'{metrics_dir}/aircraft_metrics.csv', index=False)
        
        logging.info(f"Métriques calculées: {len(df_airline_metrics)} compagnies, {len(df_aircraft_metrics)} avions")
    
    except Exception as e:
        logging.error(f"Erreur lors du calcul des métriques de performance: {e}")
    
    logging.info("Calcul des métriques de performance terminé.")

# Fonction pour générer des visualisations
def generate_performance_visualizations(**kwargs):
    """Génère des visualisations à partir des métriques de performance"""
    logging.info("Génération des visualisations de performance...")
    
    # Date d'exécution
    execution_date = kwargs['execution_date']
    year = execution_date.year
    month = execution_date.month
    
    # Calcul du mois précédent
    if month == 1:
        previous_month = 12
        previous_year = year - 1
    else:
        previous_month = month - 1
        previous_year = year
    
    # Répertoire des métriques
    metrics_dir = f'/opt/airflow/data/performance/{previous_year}_{previous_month:02d}/metrics'
    
    # Répertoire de sortie pour les visualisations
    viz_dir = f'/opt/airflow/data/performance/{previous_year}_{previous_month:02d}/visualizations'
    os.makedirs(viz_dir, exist_ok=True)
    
    try:
        # Chargement des métriques
        df_airline = pd.read_csv(f'{metrics_dir}/airline_metrics.csv')
        df_aircraft = pd.read_csv(f'{metrics_dir}/aircraft_metrics.csv')
        
        # Configuration des visualisations
        plt.figure(figsize=(12, 8))
        sns.set(style="whitegrid")
        
        # 1. Comparaison des heures de vol par compagnie
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(x='airline_code', y='total_flight_hours', data=df_airline)
        plt.title(f'Total Flight Hours by Airline - {previous_year}/{previous_month:02d}')
        plt.xlabel('Airline')
        plt.ylabel('Flight Hours')
        plt.tight_layout()
        plt.savefig(f'{viz_dir}/flight_hours_by_airline.png')
        plt.close()
        
        # 2. Comparaison des ratios de maintenance non programmée
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(x='airline_code', y='unscheduled_ratio', data=df_airline)
        plt.title(f'Unscheduled Maintenance Ratio by Airline - {previous_year}/{previous_month:02d}')
        plt.xlabel('Airline')
        plt.ylabel('Unscheduled Maintenance Ratio')
        plt.tight_layout()
        plt.savefig(f'{viz_dir}/unscheduled_ratio_by_airline.png')
        plt.close()
        
        # 3. Comparaison de l'efficacité énergétique par avion
        plt.figure(figsize=(12, 8))
        ax = sns.barplot(x='aircraft_msn', y='fuel_efficiency', hue='airline_code', data=df_aircraft)
        plt.title(f'Fuel Efficiency by Aircraft - {previous_year}/{previous_month:02d}')
        plt.xlabel('Aircraft MSN')
        plt.ylabel('Fuel Efficiency (Flow Rate / Flight Hour)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(f'{viz_dir}/fuel_efficiency_by_aircraft.png')
        plt.close()
        
        # 4. Comparaison des événements de maintenance par avion
        plt.figure(figsize=(12, 8))
        ax = sns.barplot(x='aircraft_msn', y='maintenance_per_flight_hour', hue='airline_code', data=df_aircraft)
        plt.title(f'Maintenance Events per Flight Hour by Aircraft - {previous_year}/{previous_month:02d}')
        plt.xlabel('Aircraft MSN')
        plt.ylabel('Maintenance Events per Flight Hour')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(f'{viz_dir}/maintenance_by_aircraft.png')
        plt.close()
        
        logging.info(f"Visualisations générées dans {viz_dir}")
    
    except Exception as e:
        logging.error(f"Erreur lors de la génération des visualisations: {e}")
    
    logging.info("Génération des visualisations terminée.")

# Fonction pour générer le rapport mensuel
def generate_monthly_report(**kwargs):
    """Génère un rapport mensuel de performance de la flotte"""
    logging.info("Génération du rapport mensuel de performance...")
    
    # Date d'exécution
    execution_date = kwargs['execution_date']
    year <response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>