"""
DAG pour la détection d'anomalies dans les nouvelles données
Ce DAG est exécuté quotidiennement pour détecter les anomalies dans les données de vol.
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
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

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
    'anomaly_detection_dag',
    default_args=default_args,
    description='Détection quotidienne d\'anomalies dans les données de vol',
    schedule_interval='0 4 * * *',  # Tous les jours à 4h du matin
    catchup=False,
    tags=['mcs100', 'anomaly'],
)

# Fonction pour extraire les données récentes
def extract_recent_data(**kwargs):
    """Extrait les données récentes pour la détection d'anomalies"""
    logging.info("Extraction des données récentes pour la détection d'anomalies...")
    
    # Connexion à TimescaleDB
    pg_hook = BaseHook.get_connection('postgres_conn')
    conn_string = f"postgresql://{pg_hook.login}:{pg_hook.password}@{pg_hook.host}:{pg_hook.port}/{pg_hook.schema}"
    
    # Date d'exécution
    execution_date = kwargs['execution_date']
    end_date = execution_date.strftime('%Y-%m-%d')
    
    # Période d'analyse (7 derniers jours)
    start_date = (execution_date - timedelta(days=7)).strftime('%Y-%m-%d')
    
    logging.info(f"Période d'analyse: {start_date} à {end_date}")
    
    # Requêtes pour extraire les données
    queries = {
        'flight_data': f"""
        SELECT 
            fd.aircraft_msn,
            fd.flight_id,
            fd.event_timestamp,
            fd.engine_1_temp,
            fd.engine_2_temp,
            fd.engine_1_pressure,
            fd.engine_2_pressure,
            fd.engine_1_vibration,
            fd.engine_2_vibration,
            fd.fuel_flow_rate,
            fd.altitude,
            fd.speed,
            fd.external_temp
        FROM 
            raw.flight_data fd
        WHERE 
            fd.event_timestamp BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY 
            fd.aircraft_msn, fd.event_timestamp
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
        ORDER BY 
            a.aircraft_msn, a.event_timestamp
        """
    }
    
    # Création du répertoire de sortie
    output_dir = f'/opt/airflow/data/anomaly/{end_date}'
    os.makedirs(output_dir, exist_ok=True)
    
    # Extraction des données
    for name, query in queries.items():
        try:
            df = pd.read_sql(query, conn_string)
            df.to_csv(f'{output_dir}/{name}.csv', index=False)
            logging.info(f"Données extraites pour {name}: {len(df)} enregistrements")
        except Exception as e:
            logging.error(f"Erreur lors de l'extraction des données pour {name}: {e}")
    
    # Extraction des données historiques pour l'entraînement (30 derniers jours)
    historical_start_date = (execution_date - timedelta(days=30)).strftime('%Y-%m-%d')
    historical_query = f"""
    SELECT 
        fd.aircraft_msn,
        fd.flight_id,
        fd.event_timestamp,
        fd.engine_1_temp,
        fd.engine_2_temp,
        fd.engine_1_pressure,
        fd.engine_2_pressure,
        fd.engine_1_vibration,
        fd.engine_2_vibration,
        fd.fuel_flow_rate,
        fd.altitude,
        fd.speed,
        fd.external_temp
    FROM 
        raw.flight_data fd
    WHERE 
        fd.event_timestamp BETWEEN '{historical_start_date}' AND '{start_date}'
    ORDER BY 
        fd.aircraft_msn, fd.event_timestamp
    """
    
    try:
        df_historical = pd.read_sql(historical_query, conn_string)
        df_historical.to_csv(f'{output_dir}/historical_flight_data.csv', index=False)
        logging.info(f"Données historiques extraites: {len(df_historical)} enregistrements")
    except Exception as e:
        logging.error(f"Erreur lors de l'extraction des données historiques: {e}")
    
    logging.info("Extraction des données récentes terminée.")

# Fonction pour détecter les anomalies avec Isolation Forest
def detect_anomalies_isolation_forest(**kwargs):
    """Détecte les anomalies dans les données de vol avec Isolation Forest"""
    logging.info("Détection d'anomalies avec Isolation Forest...")
    
    # Date d'exécution
    execution_date = kwargs['execution_date']
    date_str = execution_date.strftime('%Y-%m-%d')
    
    # Répertoire des données
    data_dir = f'/opt/airflow/data/anomaly/{date_str}'
    
    # Répertoire de sortie pour les anomalies
    anomalies_dir = f'{data_dir}/anomalies'
    os.makedirs(anomalies_dir, exist_ok=True)
    
    try:
        # Chargement des données
        df_historical = pd.read_csv(f'{data_dir}/historical_flight_data.csv')
        df_recent = pd.read_csv(f'{data_dir}/flight_data.csv')
        
        # Liste des paramètres à analyser
        parameters = [
            'engine_1_temp', 'engine_2_temp', 
            'engine_1_pressure', 'engine_2_pressure', 
            'engine_1_vibration', 'engine_2_vibration', 
            'fuel_flow_rate'
        ]
        
        # Détection d'anomalies par avion
        all_anomalies = []
        
        for aircraft_msn in df_recent['aircraft_msn'].unique():
            logging.info(f"Analyse de l'avion {aircraft_msn}...")
            
            # Filtrer les données pour cet avion
            historical_data = df_historical[df_historical['aircraft_msn'] == aircraft_msn]
            recent_data = df_recent[df_recent['aircraft_msn'] == aircraft_msn]
            
            if historical_data.empty or recent_data.empty:
                logging.warning(f"Données insuffisantes pour l'avion {aircraft_msn}, passage au suivant.")
                continue
            
            # Préparation des données d'entraînement
            X_train = historical_data[parameters].fillna(0)
            
            # Normalisation des données
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            
            # Entraînement du modèle Isolation Forest
            model = IsolationForest(
                n_estimators=100,
                max_samples='auto',
                contamination=0.05,  # 5% des données sont considérées comme anormales
                random_state=42
            )
            model.fit(X_train_scaled)
            
            # Préparation des données de test
            X_test = recent_data[parameters].fillna(0)
            X_test_scaled = scaler.transform(X_test)
            
            # Prédiction des anomalies
            # -1 pour les anomalies, 1 pour les données normales
            y_pred = model.predict(X_test_scaled)
            
            # Calcul des scores d'anomalie
            scores = model.decision_function(X_test_scaled)
            
            # Identification des anomalies
            anomalies = recent_data.copy()
            anomalies['is_anomaly'] = (y_pred == -1)
            anomalies['anomaly_score'] = scores
            
            # Filtrer les anomalies
            detected_anomalies = anomalies[anomalies['is_anomaly']]
            
            if not detected_anomalies.empty:
                logging.info(f"Anomalies détectées pour l'avion {aircraft_msn}: {len(detected_anomalies)}")
                
                # Analyse des paramètres anormaux
                for idx, row in detected_anomalies.iterrows():
                    # Déterminer quels paramètres sont anormaux
                    abnormal_params = []
                    for param in parameters:
                        param_value = row[param]
                        param_mean = historical_data[param].mean()
                        param_std = historical_data[param].std()
                        
                        # Si la valeur est à plus de 3 écarts-types de la moyenne
                        if abs(param_value - param_mean) > 3 * param_std:
                            abnormal_params.append(param)
                    
                    # Créer une entrée d'anomalie
                    anomaly_entry = {
                        'aircraft_msn': row['aircraft_msn'],
                        'flight_id': row['flight_id'],
                        'event_timestamp': row['event_timestamp'],
                        'detection_timestamp': execution_date.isoformat(),
                        'anomaly_type': 'ISOLATION_FOREST',
                        'confidence_score': abs(row['anomaly_score']),
                        'abnormal_parameters': abnormal_params,
                        'description': f"Anomalie détectée dans les paramètres: {', '.join(abnormal_params)}"
                    }
                    
                    all_anomalies.append(anomaly_entry)
        
        # Enregistrement des anomalies détectées
        if all_anomalies:
            df_anomalies = pd.DataFrame(all_anomalies)
            df_anomalies.to_csv(f'{anomalies_dir}/isolation_forest_anomalies.csv', index=False)
            
            # Enregistrement au format JSON pour l'intégration avec d'autres systèmes
            with open(f'{anomalies_dir}/isolation_forest_anomalies.json', 'w') as f:
                json.dump(all_anomalies, f, indent=2)
            
            logging.info(f"Total des anomalies détectées avec Isolation Forest: {len(all_anomalies)}")
        else:
            logging.info("Aucune anomalie détectée avec Isolation Forest.")
    
    except Exception as e:
        logging.error(f"Erreur lors de la détection d'anomalies avec Isolation Forest: {e}")
    
    logging.info("Détection d'anomalies avec Isolation Forest terminée.")

# Fonction pour détecter les anomalies avec DBSCAN
def detect_anomalies_dbscan(**kwargs):
    """Détecte les anomalies dans les données de vol avec DBSCAN"""
    logging.info("Détection d'anomalies avec DBSCAN...")
    
    # Date d'exécution
    execution_date = kwargs['execution_date']
    date_str = execution_date.strftime('%Y-%m-%d')
    
    # Répertoire des données
    data_dir = f'/opt/airflow/data/anomaly/{date_str}'
    
    # Répertoire de sortie pour les anomalies
    anomalies_dir = f'{data_dir}/anomalies'
    os.makedirs(anomalies_dir, exist_ok=True)
    
    try:
        # Chargement des données
        df_recent = pd.read_csv(f'{data_dir}/flight_data.csv')
        
        # Liste des paramètres à analyser
        parameters = [
            'engine_1_temp', 'engine_2_temp', 
            'engine_1_pressure', 'engine_2_pressure', 
            'engine_1_vibration', 'engine_2_vibration', 
            'fuel_flow_rate'
        ]
        
        # Détection d'anomalies par avion
        all_anomalies = []
        
        for aircraft_msn in df_recent['aircraft_msn'].unique():
            logging.info(f"Analyse de l'avion {aircraft_msn} avec DBSCAN...")
            
            # Filtrer les données pour cet avion
            aircraft_data = df_recent[df_recent['aircraft_msn'] == aircraft_msn]
            
            if len(aircraft_data) < 10:
                logging.warning(f"Données insuffisantes pour l'avion {aircraft_msn}, passage au suivant.")
                continue
            
            # Préparation des données
            X = aircraft_data[parameters].fillna(0)
            
            # Normalisation des données
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Application de DBSCAN
            dbscan = DBSCAN(eps=0.5, min_samples=5)
            clusters = dbscan.fit_predict(X_scaled)
            
            # Les points avec cluster -1 sont des anomalies
            aircraft_data['cluster'] = clusters
            aircraft_data['is_anomaly'] = (clusters == -1)
            
            # Filtrer les anomalies
            detected_anomalies = aircraft_data[aircraft_data['is_anomaly']]
            
            if not detected_anomalies.empty:
                logging.info(f"Anomalies DBSCAN détectées pour l'avion {aircraft_msn}: {len(detected_anomalies)}")
                
                # Analyse des paramètres anormaux
                for idx, row in detected_anomalies.iterrows():
                    # Déterminer quels paramètres sont anormaux
                    abnormal_params = []
                    for param in parameters:
                        param_value = row[param]
                        param_mean = aircraft_data[param].mean()
                        param_std = aircraft_data[param].std()
                        
                        # Si la valeur est à plus de 3 écarts-types de la moyenne
                        if abs(param_value - param_mean) > 3 * param_std:
                            abnormal_params.append(param)
                    
                    # Créer une entrée d'anomalie
                    anomaly_entry = {
                        'aircraft_msn': row['aircraft_msn'],
                        'flight_id': row['flight_id'],
                        'event_timestamp': row['event_timestamp'],
                        'detection_timestamp': execution_date.isoformat(),
                        'anomaly_type': 'DBSCAN',
                        'confidence_score': 0.8,  # Score fixe pour DBSCAN
                        'abnormal_parameters': abnormal_params,
                        'description': f"Anomalie de cluster détectée dans les paramètres: {', '.join(abnormal_params)}"
                    }
                    
                    all_anomalies.append(anomaly_entry)
        
        # Enregistrement des anomalies détectées
        if all_anomalies:
            df_anomalies = pd.DataFrame(all_anomalies)
            df_anomalies.to_csv(f'{anomalies_dir}/dbscan_anomalies.csv', index=False)
            
            # Enregistrement au format JSON pour l'intégration avec d'autres systèmes
            with open(f'{anomalies_dir}/dbscan_anomalies.json', 'w') as f:
                json.dump(all_anomalies, f, indent=2)
            
            logging.info(f"Total des anomalies détectées avec DBSCAN: {len(all_anomalies)}")
        else:
            logging.info("Aucune anomalie détectée avec DBSCAN.")
    
    except Exception as e:
        logging.error(f"Erreur lors de la détection d'anomalies avec DBSCAN: {e}")
    
    logging.info("Détection d'anomalies avec DBSCAN terminée.")

# Fonction pour fusionner et enregistrer les anomalies
def merge_and_store_anomalies(**kwargs):
    """Fusionne et enregistre les anomalies détectées dans TimescaleDB"""
    logging.info("Fusion et enregistrement des anomalies...")
    
    # Connexion à TimescaleDB
    pg_hook = BaseHook.get_connection('postgres_conn')
    conn_string = f"postgresql://{pg_hook.login}:{pg_hook.password}@{pg_hook.host}:{pg_hook.port}/{pg_hook.schema}"
    
    # Date d'exécution
    execution_date = kwargs['execution_date']
    date_str = execution_date.strftime('%Y-%m-%d')
    
    # Répertoire des anomalies
    anomalies_dir = f'/opt/airflow/data/anomaly/{date_str}/anomalies'
    
    try:
        # Chargement des anomalies détectées
        anomalies = []
        
        # Isolation Forest
        if os.path.exists(f'{anomalies_dir}/isolation_forest_anomalies.csv'):
            df_if =<response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>