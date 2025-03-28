"""
DAG pour l'analyse hebdomadaire de la fiabilité des composants et systèmes
Ce DAG analyse la fiabilité sur des périodes de 7 jours et 90 jours glissants.
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
    'weekly_reliability_analysis_dag',
    default_args=default_args,
    description='Analyse hebdomadaire de la fiabilité des composants et systèmes',
    schedule_interval='0 2 * * 1',  # Tous les lundis à 2h du matin
    catchup=False,
    tags=['mcs100', 'reliability'],
)

# Fonction pour préparer les données d'analyse
def prepare_reliability_data(**kwargs):
    """Prépare les données pour l'analyse de fiabilité"""
    logging.info("Préparation des données pour l'analyse de fiabilité...")
    
    # Connexion à TimescaleDB
    pg_hook = BaseHook.get_connection('postgres_conn')
    conn_string = f"postgresql://{pg_hook.login}:{pg_hook.password}@{pg_hook.host}:{pg_hook.port}/{pg_hook.schema}"
    
    # Date d'exécution
    execution_date = kwargs['execution_date']
    end_date = execution_date.strftime('%Y-%m-%d')
    
    # Périodes d'analyse
    periods = [
        {'name': '7d', 'days': 7},
        {'name': '90d', 'days': 90}
    ]
    
    for period in periods:
        days = period['days']
        period_name = period['name']
        start_date = (execution_date - timedelta(days=days)).strftime('%Y-%m-%d')
        
        logging.info(f"Préparation des données pour la période {period_name} ({start_date} à {end_date})...")
        
        # Requête pour extraire les événements de maintenance
        query_maintenance = f"""
        SELECT 
            m.aircraft_msn,
            m.component_id,
            m.event_timestamp,
            m.event_type,
            m.is_scheduled
        FROM 
            raw.maintenance_events m
        WHERE 
            m.event_timestamp BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY 
            m.event_timestamp
        """
        
        # Requête pour extraire les alertes
        query_alerts = f"""
        SELECT 
            a.aircraft_msn,
            a.component_id,
            a.event_timestamp,
            a.alert_code,
            a.severity
        FROM 
            raw.alerts a
        WHERE 
            a.event_timestamp BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY 
            a.event_timestamp
        """
        
        # Requête pour extraire les cycles d'utilisation
        query_usage = f"""
        SELECT 
            u.aircraft_msn,
            u.date,
            u.flight_hours,
            u.takeoffs,
            u.landings
        FROM 
            raw.usage_cycles u
        WHERE 
            u.date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY 
            u.date
        """
        
        try:
            # Extraction des données
            df_maintenance = pd.read_sql(query_maintenance, conn_string)
            df_alerts = pd.read_sql(query_alerts, conn_string)
            df_usage = pd.read_sql(query_usage, conn_string)
            
            # Création du répertoire de sortie
            output_dir = f'/opt/airflow/data/reliability/{period_name}'
            os.makedirs(output_dir, exist_ok=True)
            
            # Enregistrement des données
            df_maintenance.to_csv(f'{output_dir}/maintenance_events.csv', index=False)
            df_alerts.to_csv(f'{output_dir}/alerts.csv', index=False)
            df_usage.to_csv(f'{output_dir}/usage_cycles.csv', index=False)
            
            logging.info(f"Données préparées pour la période {period_name}")
        except Exception as e:
            logging.error(f"Erreur lors de la préparation des données pour la période {period_name}: {e}")
    
    logging.info("Préparation des données terminée.")

# Fonction pour calculer les métriques de fiabilité
def calculate_reliability_metrics(**kwargs):
    """Calcule les métriques de fiabilité à partir des données préparées"""
    logging.info("Calcul des métriques de fiabilité...")
    
    # Connexion à TimescaleDB
    pg_hook = BaseHook.get_connection('postgres_conn')
    conn_string = f"postgresql://{pg_hook.login}:{pg_hook.password}@{pg_hook.host}:{pg_hook.port}/{pg_hook.schema}"
    
    # Date d'exécution
    execution_date = kwargs['execution_date']
    calculation_timestamp = execution_date.isoformat()
    
    # Périodes d'analyse
    periods = [
        {'name': '7d', 'days': 7},
        {'name': '90d', 'days': 90}
    ]
    
    for period in periods:
        period_name = period['name']
        days = period['days']
        
        logging.info(f"Calcul des métriques pour la période {period_name}...")
        
        # Chargement des données préparées
        input_dir = f'/opt/airflow/data/reliability/{period_name}'
        
        try:
            df_maintenance = pd.read_csv(f'{input_dir}/maintenance_events.csv')
            df_alerts = pd.read_csv(f'{input_dir}/alerts.csv')
            df_usage = pd.read_csv(f'{input_dir}/usage_cycles.csv')
            
            # Calcul des métriques par composant
            component_metrics = []
            
            # Regroupement des données par composant
            if not df_maintenance.empty and 'component_id' in df_maintenance.columns:
                component_failures = df_maintenance[df_maintenance['is_scheduled'] == False].groupby('component_id').size().reset_index(name='failures')
                
                for _, row in component_failures.iterrows():
                    component_id = row['component_id']
                    failures = row['failures']
                    
                    # Calcul du MTBF (Mean Time Between Failures)
                    # Filtrer les données d'utilisation pour les avions ayant ce composant
                    aircraft_with_component = df_maintenance[df_maintenance['component_id'] == component_id]['aircraft_msn'].unique()
                    
                    if len(aircraft_with_component) > 0:
                        # Calculer les heures de vol totales pour ces avions
                        total_flight_hours = df_usage[df_usage['aircraft_msn'].isin(aircraft_with_component)]['flight_hours'].sum()
                        
                        # Calculer le MTBF
                        mtbf = total_flight_hours / max(1, failures)  # Éviter la division par zéro
                        
                        # Calculer le taux de défaillance (failures per 1000 flight hours)
                        failure_rate = (failures * 1000) / max(1, total_flight_hours)
                        
                        # Ajouter les métriques à la liste
                        component_metrics.append({
                            'component_id': component_id,
                            'period': period_name,
                            'start_date': (execution_date - timedelta(days=days)).strftime('%Y-%m-%d'),
                            'end_date': execution_date.strftime('%Y-%m-%d'),
                            'failures': int(failures),
                            'flight_hours': float(total_flight_hours),
                            'mtbf': float(mtbf),
                            'failure_rate': float(failure_rate),
                            'calculation_timestamp': calculation_timestamp
                        })
            
            # Création du DataFrame des métriques
            df_metrics = pd.DataFrame(component_metrics)
            
            if not df_metrics.empty:
                # Enregistrement des métriques dans TimescaleDB
                df_metrics.to_sql('reliability', schema='metrics', con=conn_string, if_exists='append', index=False)
                
                # Enregistrement des métriques dans un fichier CSV
                output_dir = f'/opt/airflow/data/reliability/metrics'
                os.makedirs(output_dir, exist_ok=True)
                df_metrics.to_csv(f'{output_dir}/reliability_metrics_{period_name}.csv', index=False)
                
                logging.info(f"Métriques calculées pour la période {period_name}: {len(df_metrics)} composants analysés")
            else:
                logging.warning(f"Aucune métrique calculée pour la période {period_name}")
        
        except Exception as e:
            logging.error(f"Erreur lors du calcul des métriques pour la période {period_name}: {e}")
    
    logging.info("Calcul des métriques de fiabilité terminé.")

# Fonction pour générer le rapport de fiabilité
def generate_reliability_report(**kwargs):
    """Génère un rapport de fiabilité à partir des métriques calculées"""
    logging.info("Génération du rapport de fiabilité...")
    
    # Date d'exécution
    execution_date = kwargs['execution_date']
    report_date = execution_date.strftime('%Y-%m-%d')
    
    # Chargement des métriques
    metrics_dir = f'/opt/airflow/data/reliability/metrics'
    
    try:
        # Métriques sur 7 jours
        df_7d = pd.read_csv(f'{metrics_dir}/reliability_metrics_7d.csv')
        
        # Métriques sur 90 jours
        df_90d = pd.read_csv(f'{metrics_dir}/reliability_metrics_90d.csv')
        
        # Création du rapport
        report = {
            'report_date': report_date,
            'report_type': 'reliability',
            'periods': {
                '7d': {
                    'start_date': df_7d['start_date'].iloc[0] if not df_7d.empty else None,
                    'end_date': df_7d['end_date'].iloc[0] if not df_7d.empty else None,
                    'total_components_analyzed': len(df_7d),
                    'total_failures': int(df_7d['failures'].sum()) if not df_7d.empty else 0,
                    'total_flight_hours': float(df_7d['flight_hours'].sum()) if not df_7d.empty else 0,
                    'average_mtbf': float(df_7d['mtbf'].mean()) if not df_7d.empty else 0,
                    'average_failure_rate': float(df_7d['failure_rate'].mean()) if not df_7d.empty else 0,
                    'top_reliable_components': df_7d.nlargest(5, 'mtbf')[['component_id', 'mtbf']].to_dict('records') if not df_7d.empty else [],
                    'top_unreliable_components': df_7d.nlargest(5, 'failure_rate')[['component_id', 'failure_rate']].to_dict('records') if not df_7d.empty else []
                },
                '90d': {
                    'start_date': df_90d['start_date'].iloc[0] if not df_90d.empty else None,
                    'end_date': df_90d['end_date'].iloc[0] if not df_90d.empty else None,
                    'total_components_analyzed': len(df_90d),
                    'total_failures': int(df_90d['failures'].sum()) if not df_90d.empty else 0,
                    'total_flight_hours': float(df_90d['flight_hours'].sum()) if not df_90d.empty else 0,
                    'average_mtbf': float(df_90d['mtbf'].mean()) if not df_90d.empty else 0,
                    'average_failure_rate': float(df_90d['failure_rate'].mean()) if not df_90d.empty else 0,
                    'top_reliable_components': df_90d.nlargest(5, 'mtbf')[['component_id', 'mtbf']].to_dict('records') if not df_90d.empty else [],
                    'top_unreliable_components': df_90d.nlargest(5, 'failure_rate')[['component_id', 'failure_rate']].to_dict('records') if not df_90d.empty else []
                }
            }
        }
        
        # Enregistrement du rapport
        reports_dir = f'/opt/airflow/data/reports'
        os.makedirs(reports_dir, exist_ok=True)
        
        with open(f'{reports_dir}/reliability_report_{report_date}.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        logging.info(f"Rapport de fiabilité généré: {reports_dir}/reliability_report_{report_date}.json")
    
    except Exception as e:
        logging.error(f"Erreur lors de la génération du rapport de fiabilité: {e}")
    
    logging.info("Génération du rapport de fiabilité terminée.")

# Définition des tâches
prepare_data_task = PythonOperator(
    task_id='prepare_reliability_data',
    python_callable=prepare_reliability_data,
    provide_context=True,
    dag=dag,
)

calculate_metrics_task = PythonOperator(
    task_id='calculate_reliability_metrics',
    python_callable=calculate_reliability_metrics,
    provide_context=True,
    dag=dag,
)

generate_report_task = PythonOperator(
    task_id='generate_reliability_report',
    python_callable=generate_reliability_report,
    provide_context=True,
    dag=dag,
)

# Tâche Spark pour l'analyse avancée de fiabilité
spark_reliability_task = SparkSubmitOperator(
    task_id='spark_reliability_analysis',
    application='/opt/airflow/spark/jobs/reliability_analysis.py',
    conn_id='spark_conn',
    verbose=True,
    dag=dag,
)

# Tâche dbt pour la transformation des données de fiabilité
dbt_run_task = DbtRunOperator(
    task_id='dbt_run_reliability',
    profiles_dir='/opt/airflow/dbt/profiles',
    target='dev',
    models=['metrics.reliability'],
    dir='/opt/airflow/dbt',
    dag=dag,
)

# Définition des dépendances
prepare_data_task >> calculate_metrics_task >> spark_reliability_task >> dbt_run_task >> generate_report_task
