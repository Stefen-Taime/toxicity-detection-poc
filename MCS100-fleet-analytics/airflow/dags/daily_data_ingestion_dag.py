"""
DAG pour l'ingestion quotidienne des données des avions MCS100
Ce DAG extrait les nouvelles données depuis MinIO, les APIs et MongoDB,
puis les charge dans TimescaleDB.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.mongo.hooks.mongo import MongoHook
from airflow.hooks.base import BaseHook
from airflow_dbt.operators.dbt_operator import DbtRunOperator
import requests
import json
import pandas as pd
import os
import logging

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
    'daily_data_ingestion_dag',
    default_args=default_args,
    description='Extraction quotidienne des nouvelles données des avions MCS100',
    schedule_interval='0 1 * * *',  # Tous les jours à 1h du matin
    catchup=False,
    tags=['mcs100', 'ingestion'],
)

# Fonction pour extraire les données CSV depuis MinIO
def extract_csv_from_minio(**kwargs):
    """Extrait les fichiers CSV depuis MinIO"""
    logging.info("Extraction des fichiers CSV depuis MinIO...")
    
    # Connexion à MinIO via le hook S3
    s3_hook = S3Hook(aws_conn_id='minio_conn')
    
    # Date d'exécution
    execution_date = kwargs['execution_date']
    date_str = execution_date.strftime('%Y-%m-%d')
    
    # Liste des buckets et préfixes à extraire
    extractions = [
        {'bucket': 'raw-data', 'prefix': f'airline=AIR/date={date_str}', 'local_dir': '/opt/airflow/data/minio-init/csv/airline=AIR'},
        {'bucket': 'raw-data', 'prefix': f'airline=FLY/date={date_str}', 'local_dir': '/opt/airflow/data/minio-init/csv/airline=FLY'},
        {'bucket': 'raw-data', 'prefix': f'airline=SKY/date={date_str}', 'local_dir': '/opt/airflow/data/minio-init/csv/airline=SKY'},
    ]
    
    # Extraction des fichiers
    for extraction in extractions:
        bucket = extraction['bucket']
        prefix = extraction['prefix']
        local_dir = extraction['local_dir']
        
        # Création du répertoire local si nécessaire
        os.makedirs(local_dir, exist_ok=True)
        
        # Liste des fichiers dans le bucket avec le préfixe spécifié
        files = s3_hook.list_keys(bucket_name=bucket, prefix=prefix)
        
        if not files:
            logging.info(f"Aucun fichier trouvé dans {bucket}/{prefix}")
            continue
        
        # Téléchargement des fichiers
        for file_key in files:
            local_path = os.path.join(local_dir, os.path.basename(file_key))
            s3_hook.download_file(key=file_key, bucket_name=bucket, local_path=local_path)
            logging.info(f"Fichier téléchargé: {local_path}")
    
    logging.info("Extraction des fichiers CSV terminée.")

# Fonction pour extraire les données JSON depuis MinIO
def extract_json_from_minio(**kwargs):
    """Extrait les fichiers JSON depuis MinIO"""
    logging.info("Extraction des fichiers JSON depuis MinIO...")
    
    # Connexion à MinIO via le hook S3
    s3_hook = S3Hook(aws_conn_id='minio_conn')
    
    # Date d'exécution
    execution_date = kwargs['execution_date']
    date_str = execution_date.strftime('%Y-%m-%d')
    
    # Liste des buckets et préfixes à extraire
    extractions = [
        {'bucket': 'raw-data', 'prefix': 'alerts', 'local_dir': '/opt/airflow/data/minio-init/json'},
        {'bucket': 'raw-data', 'prefix': 'maintenance', 'local_dir': '/opt/airflow/data/minio-init/json'},
        {'bucket': 'raw-data', 'prefix': 'configurations', 'local_dir': '/opt/airflow/data/minio-init/json'},
    ]
    
    # Extraction des fichiers
    for extraction in extractions:
        bucket = extraction['bucket']
        prefix = extraction['prefix']
        local_dir = extraction['local_dir']
        
        # Création du répertoire local si nécessaire
        os.makedirs(local_dir, exist_ok=True)
        
        # Liste des fichiers dans le bucket avec le préfixe spécifié
        files = s3_hook.list_keys(bucket_name=bucket, prefix=prefix)
        
        if not files:
            logging.info(f"Aucun fichier trouvé dans {bucket}/{prefix}")
            continue
        
        # Téléchargement des fichiers
        for file_key in files:
            # Vérifier si le fichier contient la date d'exécution
            if date_str in file_key:
                local_path = os.path.join(local_dir, os.path.basename(file_key))
                s3_hook.download_file(key=file_key, bucket_name=bucket, local_path=local_path)
                logging.info(f"Fichier téléchargé: {local_path}")
    
    logging.info("Extraction des fichiers JSON terminée.")

# Fonction pour extraire les données depuis les APIs
def extract_from_apis(**kwargs):
    """Extrait les données depuis les APIs simulées"""
    logging.info("Extraction des données depuis les APIs...")
    
    # Date d'exécution
    execution_date = kwargs['execution_date']
    date_str = execution_date.strftime('%Y-%m-%d')
    
    # Liste des endpoints à appeler
    endpoints = [
        {'url': 'http://api-simulator:8000/airline-data', 'params': {'date': date_str}, 'output_file': f'/opt/airflow/data/api/airline_data_{date_str}.json'},
        {'url': 'http://api-simulator:8000/technical-bulletins', 'params': {'date': date_str}, 'output_file': f'/opt/airflow/data/api/technical_bulletins_{date_str}.json'},
        {'url': 'http://api-simulator:8000/weather-data', 'params': {'date': date_str}, 'output_file': f'/opt/airflow/data/api/weather_data_{date_str}.json'},
    ]
    
    # Création du répertoire de sortie
    os.makedirs('/opt/airflow/data/api', exist_ok=True)
    
    # Appel des endpoints
    for endpoint in endpoints:
        url = endpoint['url']
        params = endpoint['params']
        output_file = endpoint['output_file']
        
        try:
            # Appel de l'API
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            # Écriture des données dans un fichier
            with open(output_file, 'w') as f:
                json.dump(response.json(), f)
            
            logging.info(f"Données extraites depuis {url} et enregistrées dans {output_file}")
        except Exception as e:
            logging.error(f"Erreur lors de l'extraction depuis {url}: {e}")
    
    logging.info("Extraction des données depuis les APIs terminée.")

# Fonction pour extraire les données depuis MongoDB
def extract_from_mongodb(**kwargs):
    """Extrait les données depuis MongoDB"""
    logging.info("Extraction des données depuis MongoDB...")
    
    # Connexion à MongoDB
    mongo_hook = MongoHook(conn_id='mongo_conn')
    
    # Liste des collections à extraire
    collections = [
        {'db': 'mcs100_reference', 'collection': 'components', 'output_file': '/opt/airflow/data/mongodb/components.json'},
        {'db': 'mcs100_reference', 'collection': 'systems', 'output_file': '/opt/airflow/data/mongodb/systems.json'},
        {'db': 'mcs100_reference', 'collection': 'configurations', 'output_file': '/opt/airflow/data/mongodb/configurations.json'},
        {'db': 'mcs100_reference', 'collection': 'maintenance_standards', 'output_file': '/opt/airflow/data/mongodb/maintenance_standards.json'},
    ]
    
    # Création du répertoire de sortie
    os.makedirs('/opt/airflow/data/mongodb', exist_ok=True)
    
    # Extraction des collections
    for collection_info in collections:
        db = collection_info['db']
        collection = collection_info['collection']
        output_file = collection_info['output_file']
        
        # Extraction des données
        data = list(mongo_hook.find(mongo_collection=collection, query={}, mongo_db=db))
        
        # Conversion des ObjectId en str pour la sérialisation JSON
        for item in data:
            if '_id' in item:
                item['_id'] = str(item['_id'])
        
        # Écriture des données dans un fichier
        with open(output_file, 'w') as f:
            json.dump(data, f)
        
        logging.info(f"Données extraites depuis {db}.{collection} et enregistrées dans {output_file}")
    
    logging.info("Extraction des données depuis MongoDB terminée.")

# Fonction pour charger les données CSV dans TimescaleDB
def load_csv_to_timescaledb(**kwargs):
    """Charge les données CSV dans TimescaleDB"""
    logging.info("Chargement des données CSV dans TimescaleDB...")
    
    # Connexion à TimescaleDB
    pg_hook = BaseHook.get_connection('postgres_conn')
    
    # Date d'exécution
    execution_date = kwargs['execution_date']
    date_str = execution_date.strftime('%Y-%m-%d')
    
    # Liste des répertoires à traiter
    airlines = ['AIR', 'FLY', 'SKY']
    
    for airline in airlines:
        # Chemin du répertoire
        dir_path = f'/opt/airflow/data/minio-init/csv/airline={airline}/date={date_str}'
        
        if not os.path.exists(dir_path):
            logging.info(f"Répertoire {dir_path} non trouvé, passage au suivant.")
            continue
        
        # Liste des fichiers dans le répertoire
        files = [f for f in os.listdir(dir_path) if f.endswith('.csv')]
        
        for file in files:
            file_path = os.path.join(dir_path, file)
            
            try:
                # Lecture du fichier CSV
                df = pd.read_csv(file_path)
                
                # Détermination de la table cible en fonction du contenu du fichier
                if 'engine_1_temp' in df.columns:
                    table_name = 'raw.flight_data'
                elif 'takeoffs' in df.columns:
                    table_name = 'raw.usage_cycles'
                else:
                    logging.warning(f"Type de fichier inconnu: {file_path}")
                    continue
                
                # Connexion à la base de données
                conn_string = f"postgresql://{pg_hook.login}:{pg_hook.password}@{pg_hook.host}:{pg_hook.port}/{pg_hook.schema}"
                
                # Chargement des données dans TimescaleDB
                df.to_sql(name=table_name.split('.')[1], schema=table_name.split('.')[0], con=conn_string, if_exists='append', index=False)
                
                logging.info(f"Données chargées depuis {file_path} vers {table_name}")
            except Exception as e:
                logging.error(f"Erreur lors du chargement de {file_path}: {e}")
    
    logging.info("Chargement des données CSV dans TimescaleDB terminé.")

# Fonction pour charger les données JSON dans TimescaleDB
def load_json_to_timescaledb(**kwargs):
    """Charge les données JSON dans TimescaleDB"""
    logging.info("Chargement des données JSON dans TimescaleDB...")
    
    # Connexion à TimescaleDB
    pg_hook = BaseHook.get_connection('postgres_conn')
    
    # Date d'exécution
    execution_date = kwargs['execution_date']
    date_str = execution_date.strftime('%Y-%m-%d')
    
    # Répertoire des fichiers JSON
    json_dir = '/opt/airflow/data/minio-init/json'
    
    if not os.path.exists(json_dir):
        logging.info(f"Répertoire {json_dir} non trouvé.")
        return
    
    # Liste des fichiers dans le répertoire
    files = [f for f in os.listdir(json_dir) if f.endswith('.json') and date_str in f]
    
    for file in files:
        file_path = os.path.join(json_dir, file)
        
        try:
            # Lecture du fichier JSON
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Conversion en DataFrame
            df = pd.DataFrame(data if isinstance(data, list) else [data])
            
            # Détermination de la table cible en fonction du contenu du fichier
            if 'alert_code' in df.columns:
                table_name = 'raw.alerts'
            elif 'event_type' in df.columns and 'maintenance' in file:
                table_name = 'raw.maintenance_events'
            else:
                logging.warning(f"Type de fichier inconnu: {file_path}")
                continue
            
            # Connexion à la base de données
            conn_string = f"postgresql://{pg_hook.login}:{pg_hook.password}@{pg_hook.host}:{pg_hook.port}/{pg_hook.schema}"
            
            # Chargement des données dans TimescaleDB
            df.to_sql(name=table_name.split('.')[1], schema=table_name.split('.')[0], con=conn_string, if_exists='append', index=False)
            
            logging.info(f"Données chargées depuis {file_path} vers {table_name}")
        except Exception as e:
            logging.error(f"Erreur lors du chargement de {file_path}: {e}")
    
    logging.info("Chargement des données JSON dans TimescaleDB terminé.")

# Fonction pour charger les données API dans TimescaleDB
def load_api_to_timescaledb(**kwargs):
    """Charge les données API dans TimescaleDB"""
    logging.info("Chargement des données API dans TimescaleDB...")
    
    # Connexion à TimescaleDB
    pg_hook = BaseHook.get_connection('postgres_conn')
    
    # Date d'exécution
    execution_date = kwargs['execution_date']
    date_str = execution_date.strftime('%Y-%m-%d')
    
    # Répertoire des fichiers API
    api_dir = '/opt/airflow/data/api'
    
    if not os.path.exists(api_dir):
        logging.info(f"Répertoire {api_dir} non trouvé.")
        return
    
    # Liste des fichiers dans le répertoire
    files = [f for f in os.listdir(api_dir) if f.endswith('.json') and date_str in f]
    
    for file in files:
        file_path = os.path.join(api_dir, file)
        
        try:
            # Lecture du fichier JSON
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Conversion en DataFrame
            df = pd.DataFrame(data if isinstance(data, list) else [data])
            
            # Détermination de la table cible en fonction du nom du fichier
            if 'airline_data' in file:
                table_name = 'raw.airline_metadata'
            elif 'technical_bulletins' in file:
                table_name = 'raw.technical_bulletins'
            elif 'weather_data' in file:
                table_name = 'raw.weather_data'
            else:
                logging.warning(f"Type de fichier inconnu: {file_path}")
                continue
            
            # Connexion à la base de données
            conn_string = f"postgresql://{pg_hook.login}:{pg_hook.password}@{pg_hook.host}:{pg_hook.port}/{pg_hook.schema}"
            
            # Chargement des données dans TimescaleDB
            df.to_sql(name=table_name.split('.')[1], schema=table_name.split('.')[0], con=conn_string, if_exists='append', index=False)
            
            logging.info(f"Données chargées depuis {file_path} vers {table_name}")
        except Exception as e:
            logging.error(f"Erreur lors du chargement de {file_path}: {e}")
    
    logging.info("Chargement des données API dans TimescaleDB terminé.")

# Définition des tâches
extract_csv_task = PythonOperator(
    task_id='extract_csv_from_minio',
    python_callable=extract_csv_from_minio,
    provide_context=True,
    dag=dag,
)

extract_json_task = PythonOperator(
    task_id='extract_json_from_minio',
    python_callable=extract_json_from_minio,
    provide_context=True,
    dag=dag,
)

extract_api_task = PythonOperator(
    task_id='extract_from_apis',
    python_callable=extract_from_apis,
    provide_context=True,
    dag=dag,
)

extract_mongodb_task = PythonOperator(
    task_id='extract_from_mongodb',
    python_callable=extract_from_mongodb,
    provide_context=True,
    dag=dag,
)

load_csv_task = PythonOperator(
    task_id='load_csv_to_timescaledb',
    python_callable=lo<response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>