"""
DAG pour l'optimisation des intervalles de maintenance
Ce DAG analyse les données historiques pour recommander des intervalles de maintenance optimaux.
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
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
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
    'maintenance_optimization_dag',
    default_args=default_args,
    description='Optimisation des intervalles de maintenance',
    schedule_interval='0 5 * * 1',  # Tous les lundis à 5h du matin
    catchup=False,
    tags=['mcs100', 'maintenance'],
)

# Fonction pour extraire les données historiques de maintenance
def extract_maintenance_history(**kwargs):
    """Extrait l'historique de maintenance pour l'analyse d'optimisation"""
    logging.info("Extraction de l'historique de maintenance...")
    
    # Connexion à TimescaleDB
    pg_hook = BaseHook.get_connection('postgres_conn')
    conn_string = f"postgresql://{pg_hook.login}:{pg_hook.password}@{pg_hook.host}:{pg_hook.port}/{pg_hook.schema}"
    
    # Date d'exécution
    execution_date = kwargs['execution_date']
    end_date = execution_date.strftime('%Y-%m-%d')
    
    # Période d'analyse (180 derniers jours)
    start_date = (execution_date - timedelta(days=180)).strftime('%Y-%m-%d')
    
    logging.info(f"Période d'analyse: {start_date} à {end_date}")
    
    # Requêtes pour extraire les données
    queries = {
        'maintenance_events': f"""
        SELECT 
            me.aircraft_msn,
            me.component_id,
            me.event_timestamp,
            me.event_type,
            me.is_scheduled,
            me.duration_hours,
            me.maintenance_action,
            me.technician_id
        FROM 
            raw.maintenance_events me
        WHERE 
            me.event_timestamp BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY 
            me.aircraft_msn, me.component_id, me.event_timestamp
        """,
        
        'component_info': f"""
        SELECT 
            c.component_id,
            c.component_name,
            c.component_type,
            c.manufacturer,
            c.recommended_maintenance_interval,
            c.installation_date,
            c.aircraft_msn
        FROM 
            raw.components c
        """,
        
        'usage_cycles': f"""
        SELECT 
            uc.aircraft_msn,
            uc.date,
            uc.flight_hours,
            uc.takeoffs,
            uc.landings,
            uc.apu_cycles,
            uc.apu_hours
        FROM 
            raw.usage_cycles uc
        WHERE 
            uc.date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY 
            uc.aircraft_msn, uc.date
        """,
        
        'alerts': f"""
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
            AND a.severity IN ('WARNING', 'CRITICAL')
        ORDER BY 
            a.aircraft_msn, a.component_id, a.event_timestamp
        """
    }
    
    # Création du répertoire de sortie
    output_dir = f'/opt/airflow/data/maintenance_optimization/{end_date}'
    os.makedirs(output_dir, exist_ok=True)
    
    # Extraction des données
    for name, query in queries.items():
        try:
            df = pd.read_sql(query, conn_string)
            df.to_csv(f'{output_dir}/{name}.csv', index=False)
            logging.info(f"Données extraites pour {name}: {len(df)} enregistrements")
        except Exception as e:
            logging.error(f"Erreur lors de l'extraction des données pour {name}: {e}")
    
    logging.info("Extraction de l'historique de maintenance terminée.")

# Fonction pour analyser les défaillances et les intervalles
def analyze_failures_and_intervals(**kwargs):
    """Analyse les défaillances et les intervalles de maintenance"""
    logging.info("Analyse des défaillances et des intervalles de maintenance...")
    
    # Date d'exécution
    execution_date = kwargs['execution_date']
    date_str = execution_date.strftime('%Y-%m-%d')
    
    # Répertoire des données
    data_dir = f'/opt/airflow/data/maintenance_optimization/{date_str}'
    
    # Répertoire de sortie pour les analyses
    analysis_dir = f'{data_dir}/analysis'
    os.makedirs(analysis_dir, exist_ok=True)
    
    try:
        # Chargement des données
        df_maintenance = pd.read_csv(f'{data_dir}/maintenance_events.csv')
        df_components = pd.read_csv(f'{data_dir}/component_info.csv')
        df_usage = pd.read_csv(f'{data_dir}/usage_cycles.csv')
        df_alerts = pd.read_csv(f'{data_dir}/alerts.csv')
        
        # Conversion des timestamps en datetime
        df_maintenance['event_timestamp'] = pd.to_datetime(df_maintenance['event_timestamp'])
        df_alerts['event_timestamp'] = pd.to_datetime(df_alerts['event_timestamp'])
        
        # Analyse des défaillances par composant
        component_failures = []
        
        for component_id in df_components['component_id'].unique():
            # Informations sur le composant
            component_info = df_components[df_components['component_id'] == component_id].iloc[0]
            component_name = component_info['component_name']
            recommended_interval = component_info['recommended_maintenance_interval']
            aircraft_msn = component_info['aircraft_msn']
            
            # Événements de maintenance pour ce composant
            component_maintenance = df_maintenance[df_maintenance['component_id'] == component_id]
            
            # Alertes pour ce composant
            component_alerts = df_alerts[df_alerts['component_id'] == component_id]
            
            # Utilisation de l'avion correspondant
            aircraft_usage = df_usage[df_usage['aircraft_msn'] == aircraft_msn]
            
            if component_maintenance.empty or aircraft_usage.empty:
                continue
            
            # Calcul des heures de vol entre les maintenances
            maintenance_events = component_maintenance.sort_values('event_timestamp')
            
            # Calcul des intervalles entre les maintenances
            if len(maintenance_events) > 1:
                intervals = []
                flight_hours_between = []
                
                for i in range(1, len(maintenance_events)):
                    prev_event = maintenance_events.iloc[i-1]
                    curr_event = maintenance_events.iloc[i]
                    
                    # Intervalle en jours
                    interval_days = (curr_event['event_timestamp'] - prev_event['event_timestamp']).days
                    
                    # Heures de vol dans cet intervalle
                    usage_in_interval = aircraft_usage[
                        (aircraft_usage['date'] >= prev_event['event_timestamp'].strftime('%Y-%m-%d')) &
                        (aircraft_usage['date'] <= curr_event['event_timestamp'].strftime('%Y-%m-%d'))
                    ]
                    
                    flight_hours = usage_in_interval['flight_hours'].sum()
                    
                    intervals.append(interval_days)
                    flight_hours_between.append(flight_hours)
                
                # Calcul des statistiques
                avg_interval_days = np.mean(intervals) if intervals else 0
                avg_flight_hours = np.mean(flight_hours_between) if flight_hours_between else 0
                
                # Nombre de défaillances non programmées
                unscheduled_count = len(maintenance_events[maintenance_events['is_scheduled'] == False])
                
                # Nombre d'alertes
                alert_count = len(component_alerts)
                
                # Ajout des statistiques
                component_failures.append({
                    'component_id': component_id,
                    'component_name': component_name,
                    'aircraft_msn': aircraft_msn,
                    'recommended_interval': float(recommended_interval),
                    'avg_actual_interval_days': float(avg_interval_days),
                    'avg_flight_hours_between_maintenance': float(avg_flight_hours),
                    'total_maintenance_events': len(maintenance_events),
                    'unscheduled_maintenance_count': int(unscheduled_count),
                    'alert_count': int(alert_count),
                    'analysis_date': date_str
                })
        
        # Création du DataFrame des analyses
        df_analysis = pd.DataFrame(component_failures)
        
        if not df_analysis.empty:
            # Enregistrement des analyses
            df_analysis.to_csv(f'{analysis_dir}/component_failure_analysis.csv', index=False)
            
            logging.info(f"Analyse des défaillances terminée pour {len(df_analysis)} composants")
        else:
            logging.warning("Aucune analyse de défaillance générée.")
    
    except Exception as e:
        logging.error(f"Erreur lors de l'analyse des défaillances: {e}")
    
    logging.info("Analyse des défaillances et des intervalles terminée.")

# Fonction pour optimiser les intervalles de maintenance
def optimize_maintenance_intervals(**kwargs):
    """Optimise les intervalles de maintenance en fonction des analyses"""
    logging.info("Optimisation des intervalles de maintenance...")
    
    # Date d'exécution
    execution_date = kwargs['execution_date']
    date_str = execution_date.strftime('%Y-%m-%d')
    
    # Répertoire des données
    data_dir = f'/opt/airflow/data/maintenance_optimization/{date_str}'
    analysis_dir = f'{data_dir}/analysis'
    
    # Répertoire de sortie pour les recommandations
    recommendations_dir = f'{data_dir}/recommendations'
    os.makedirs(recommendations_dir, exist_ok=True)
    
    try:
        # Chargement des analyses
        df_analysis = pd.read_csv(f'{analysis_dir}/component_failure_analysis.csv')
        
        if df_analysis.empty:
            logging.warning("Aucune donnée d'analyse disponible pour l'optimisation.")
            return
        
        # Optimisation des intervalles
        optimized_intervals = []
        
        for _, component in df_analysis.iterrows():
            component_id = component['component_id']
            component_name = component['component_name']
            recommended_interval = component['recommended_interval']
            avg_actual_interval = component['avg_actual_interval_days']
            avg_flight_hours = component['avg_flight_hours_between_maintenance']
            unscheduled_count = component['unscheduled_maintenance_count']
            alert_count = component['alert_count']
            
            # Calcul du score de risque
            risk_score = (unscheduled_count * 2 + alert_count) / max(1, component['total_maintenance_events'])
            
            # Détermination de l'intervalle optimal
            if risk_score > 0.5:
                # Risque élevé: réduire l'intervalle
                optimal_interval = recommended_interval * 0.8
                recommendation = "REDUCE_INTERVAL"
                justification = "Taux élevé de défaillances non programmées et d'alertes"
            elif risk_score > 0.2:
                # Risque modéré: maintenir l'intervalle recommandé
                optimal_interval = recommended_interval
                recommendation = "MAINTAIN_INTERVAL"
                justification = "Taux modéré de défaillances non programmées"
            else:
                # Risque faible: augmenter légèrement l'intervalle
                optimal_interval = recommended_interval * 1.1
                recommendation = "EXTEND_INTERVAL"
                justification = "Faible taux de défaillances non programmées"
            
            # Ajustement basé sur l'utilisation réelle
            if avg_flight_hours > 0:
                flight_hours_per_day = avg_flight_hours / max(1, avg_actual_interval)
                optimal_flight_hours = optimal_interval * flight_hours_per_day
            else:
                optimal_flight_hours = None
            
            # Ajout des recommandations
            optimized_intervals.append({
                'component_id': component_id,
                'component_name': component_name,
                'current_recommended_interval_days': float(recommended_interval),
                'optimal_interval_days': float(optimal_interval),
                'optimal_flight_hours': float(optimal_flight_hours) if optimal_flight_hours else None,
                'risk_score': float(risk_score),
                'recommendation': recommendation,
                'justification': justification,
                'analysis_date': date_str
            })
        
        # Création du DataFrame des recommandations
        df_recommendations = pd.DataFrame(optimized_intervals)
        
        # Enregistrement des recommandations
        df_recommendations.to_csv(f'{recommendations_dir}/optimized_maintenance_intervals.csv', index=False)
        
        # Enregistrement au format JSON pour l'intégration avec d'autres systèmes
        with open(f'{recommendations_dir}/optimized_maintenance_intervals.json', 'w') as f:
            json.dump(optimized_intervals, f, indent=2)
        
        logging.info(f"Intervalles de maintenance optimisés pour {len(df_recommendations)} composants")
        
        # Génération de visualisations
        generate_optimization_visualizations(df_recommendations, recommendations_dir)
    
    except Exception as e:
        logging.error(f"Erreur lors de l'optimisation des intervalles de maintenance: {e}")
    
    logging.info("Optimisation des intervalles de maintenance terminée.")

# Fonction pour générer des visualisations
def generate_optimization_visualizations(df_recommendations, output_dir):
    """Génère des visualisations pour les recommandations d'optimisation"""
    logging.info("Génération des visualisations d'optimisation...")
    
    try:
        # Configuration des visualisations
        plt.figure(figsize=(12, 8))
        sns.set(style="whitegrid")
        
        # 1. Comparaison des intervalles actuels et optimaux
        plt.figure(figsize=(12, 8))
        df_plot = df_recommendations.sort_values('risk_score', ascending=False).head(15)
        
        x = np.arange(len(df_plot))
        width = 0.35
        
        fig, ax = plt.subplots(figsize=(14, 8))
        rects1 = ax.bar(x - width/2, df_plot['current_recommended_interval_days'], width, label='Intervalle actuel')
        rects2 = ax.bar(x + width/2, df_plot['optimal_interval_days'], width, label='Intervalle optimal')
        
        ax.set_xlabel('Composants')
        ax.set_ylabel('Intervalle (jours)')
        ax.set_title('Comparaison des intervalles de maintenance actuels et optimaux')
        ax.set_xticks(x)
        ax.set_xticklabels(df_plot['component_name'], rotation=45, ha='right')
        ax.legend()
        
        fig.tight_layout()
        plt.savefig(f'{output_dir}/interval_comparison.png')
        plt.close()
        
        # 2. Distribution des scores de risque
        plt.figure(figsize=(10, 6))<response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>