#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script d'initialisation des bases de données pour la solution d'analyse de performance
de la flotte d'avions MCS100 d'Airbus.

Ce script initialise les bases de données suivantes:
1. TimescaleDB: Création des schémas, tables et hypertables
2. MongoDB: Création des collections et des index
3. MinIO: Création des buckets nécessaires

Il configure également les utilisateurs, les droits d'accès et les paramètres
de performance pour chaque base de données.
"""

import os
import sys
import psycopg2
import pymongo
from minio import Minio
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv('../docker/.env')

def init_timescaledb():
    """Initialise la base de données TimescaleDB"""
    
    print("Initialisation de TimescaleDB...")
    
    # Connexion à TimescaleDB
    conn = psycopg2.connect(
        host=os.getenv('TIMESCALEDB_HOST', 'localhost'),
        port=os.getenv('TIMESCALEDB_PORT', '5432'),
        database=os.getenv('TIMESCALEDB_DB', 'mcs100_db'),
        user=os.getenv('TIMESCALEDB_USER', 'postgres'),
        password=os.getenv('TIMESCALEDB_PASSWORD', 'postgres')
    )
    
    cursor = conn.cursor()
    
    # Créer les schémas
    cursor.execute("CREATE SCHEMA IF NOT EXISTS raw;")
    cursor.execute("CREATE SCHEMA IF NOT EXISTS metrics;")
    
    # Créer les tables dans le schéma raw
    
    # Table aircraft_metadata
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS raw.aircraft_metadata (
        aircraft_msn TEXT PRIMARY KEY,
        airline_code TEXT,
        manufacture_date TIMESTAMP,
        registration TEXT,
        engine_type TEXT,
        total_flight_hours FLOAT,
        total_flight_cycles INTEGER,
        status TEXT,
        base_airport TEXT,
        last_heavy_maintenance TIMESTAMP
    );
    """)
    
    # Table components
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS raw.components (
        component_id TEXT PRIMARY KEY,
        aircraft_msn TEXT,
        component_type TEXT,
        manufacturer TEXT,
        part_number TEXT,
        serial_number TEXT,
        installation_date TIMESTAMP,
        design_life_hours INTEGER,
        design_life_cycles INTEGER,
        mtbf_hours FLOAT,
        last_overhaul_date TIMESTAMP,
        maintenance_count INTEGER
    );
    """)
    
    # Table flight_data
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS raw.flight_data (
        flight_id TEXT PRIMARY KEY,
        aircraft_msn TEXT,
        departure_time TIMESTAMP,
        arrival_time TIMESTAMP,
        departure_airport TEXT,
        arrival_airport TEXT,
        flight_hours FLOAT,
        flight_cycles INTEGER,
        fuel_consumption FLOAT,
        max_altitude INTEGER,
        avg_ground_speed FLOAT,
        flight_phase_durations JSONB
    );
    """)
    
    # Table sensor_data (hypertable)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS raw.sensor_data (
        flight_id TEXT,
        timestamp TIMESTAMP,
        flight_phase TEXT,
        altitude FLOAT,
        ground_speed FLOAT,
        engine1_temp FLOAT,
        engine2_temp FLOAT,
        engine1_vibration FLOAT,
        engine2_vibration FLOAT,
        fuel_flow FLOAT,
        cabin_pressure FLOAT,
        outside_temp FLOAT,
        wind_speed FLOAT,
        wind_direction FLOAT,
        PRIMARY KEY (flight_id, timestamp)
    );
    """)
    
    # Convertir en hypertable
    try:
        cursor.execute("SELECT create_hypertable('raw.sensor_data', 'timestamp', if_not_exists => TRUE);")
    except:
        conn.rollback()
        print("Note: Hypertable raw.sensor_data already exists or could not be created.")
    
    # Table maintenance_events
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS raw.maintenance_events (
        event_id TEXT PRIMARY KEY,
        aircraft_msn TEXT,
        component_id TEXT,
        event_type TEXT,
        event_timestamp TIMESTAMP,
        maintenance_action TEXT,
        technician_id TEXT,
        duration_hours FLOAT,
        findings TEXT,
        parts_replaced BOOLEAN,
        cost FLOAT
    );
    """)
    
    # Table alerts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS raw.alerts (
        alert_id TEXT PRIMARY KEY,
        flight_id TEXT,
        timestamp TIMESTAMP,
        parameter TEXT,
        value FLOAT,
        threshold FLOAT,
        severity TEXT,
        message TEXT,
        status TEXT,
        resolution_time TIMESTAMP,
        resolution_action TEXT
    );
    """)
    
    # Table usage_cycles
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS raw.usage_cycles (
        aircraft_msn TEXT,
        date DATE,
        flight_hours FLOAT,
        flight_cycles INTEGER,
        fuel_consumption FLOAT,
        takeoff_count INTEGER,
        landing_count INTEGER,
        max_altitude INTEGER,
        total_distance FLOAT,
        airports_visited TEXT[],
        PRIMARY KEY (aircraft_msn, date)
    );
    """)
    
    # Créer les tables dans le schéma metrics
    
    # Table reliability_metrics
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS metrics.reliability_metrics (
        calculation_timestamp TIMESTAMP,
        aircraft_msn TEXT,
        component_id TEXT,
        component_type TEXT,
        total_operating_hours FLOAT,
        total_failures INTEGER,
        unscheduled_failures INTEGER,
        mtbf_hours FLOAT,
        failure_rate_per_1000_hours FLOAT,
        PRIMARY KEY (calculation_timestamp, component_id)
    );
    """)
    
    # Table performance_metrics
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS metrics.performance_metrics (
        calculation_timestamp TIMESTAMP,
        aircraft_msn TEXT,
        airline_code TEXT,
        total_flight_hours FLOAT,
        avg_daily_flight_hours FLOAT,
        fuel_efficiency FLOAT,
        avg_engine_1_temp FLOAT,
        avg_engine_2_temp FLOAT,
        stddev_engine_1_vibration FLOAT,
        stddev_engine_2_vibration FLOAT,
        avg_fuel_flow_rate FLOAT,
        maintenance_events_per_flight_hour FLOAT,
        alerts_per_flight_hour FLOAT,
        unscheduled_maintenance_ratio FLOAT,
        PRIMARY KEY (calculation_timestamp, aircraft_msn)
    );
    """)
    
    # Table maintenance_recommendations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS metrics.maintenance_recommendations (
        calculation_timestamp TIMESTAMP,
        aircraft_msn TEXT,
        component_id TEXT,
        component_type TEXT,
        current_recommended_interval FLOAT,
        optimal_interval FLOAT,
        recommendation TEXT,
        justification TEXT,
        confidence_score FLOAT,
        PRIMARY KEY (calculation_timestamp, component_id)
    );
    """)
    
    # Table anomalies
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS metrics.anomalies (
        detection_timestamp TIMESTAMP,
        aircraft_msn TEXT,
        flight_id TEXT,
        detection_method TEXT,
        abnormal_parameters JSONB,
        confidence_score FLOAT,
        description TEXT,
        PRIMARY KEY (detection_timestamp, flight_id)
    );
    """)
    
    # Créer des index pour améliorer les performances
    
    # Index sur aircraft_msn dans plusieurs tables
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_components_aircraft_msn ON raw.components (aircraft_msn);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_flight_data_aircraft_msn ON raw.flight_data (aircraft_msn);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_maintenance_events_aircraft_msn ON raw.maintenance_events (aircraft_msn);")
    
    # Index sur component_id dans maintenance_events
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_maintenance_events_component_id ON raw.maintenance_events (component_id);")
    
    # Index sur flight_id dans sensor_data et alerts
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sensor_data_flight_id ON raw.sensor_data (flight_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_flight_id ON raw.alerts (flight_id);")
    
    # Index sur timestamp dans alerts
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON raw.alerts (timestamp);")
    
    # Index sur event_timestamp dans maintenance_events
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_maintenance_events_timestamp ON raw.maintenance_events (event_timestamp);")
    
    # Index sur component_type dans components
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_components_type ON raw.components (component_type);")
    
    # Index sur airline_code dans aircraft_metadata
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_aircraft_airline ON raw.aircraft_metadata (airline_code);")
    
    # Créer des vues pour faciliter l'accès aux données courantes
    
    # Vue des dernières métriques de fiabilité
    cursor.execute("""
    CREATE OR REPLACE VIEW metrics.latest_reliability_metrics AS
    SELECT rm.*
    FROM metrics.reliability_metrics rm
    INNER JOIN (
        SELECT component_id, MAX(calculation_timestamp) as max_timestamp
        FROM metrics.reliability_metrics
        GROUP BY component_id
    ) latest ON rm.component_id = latest.component_id AND rm.calculation_timestamp = latest.max_timestamp;
    """)
    
    # Vue des dernières métriques de performance
    cursor.execute("""
    CREATE OR REPLACE VIEW metrics.latest_performance_metrics AS
    SELECT pm.*
    FROM metrics.performance_metrics pm
    INNER JOIN (
        SELECT aircraft_msn, MAX(calculation_timestamp) as max_timestamp
        FROM metrics.performance_metrics
        GROUP BY aircraft_msn
    ) latest ON pm.aircraft_msn = latest.aircraft_msn AND pm.calculation_timestamp = latest.max_timestamp;
    """)
    
    # Vue des dernières recommandations de maintenance
    cursor.execute("""
    CREATE OR REPLACE VIEW metrics.latest_maintenance_recommendations AS
    SELECT mr.*
    FROM metrics.maintenance_recommendations mr
    INNER JOIN (
        SELECT component_id, MAX(calculation_timestamp) as max_timestamp
        FROM metrics.maintenance_recommendations
        GROUP BY component_id
    ) latest ON mr.component_id = latest.component_id AND mr.calculation_timestamp = latest.max_timestamp;
    """)
    
    # Vue des alertes non résolues
    cursor.execute("""
    CREATE OR REPLACE VIEW raw.unresolved_alerts AS
    SELECT a.*
    FROM raw.alerts a
    WHERE a.status != 'RESOLVED' OR a.status IS NULL;
    """)
    
    # Configurer les paramètres de TimescaleDB pour de meilleures performances
    cursor.execute("ALTER DATABASE mcs100_db SET timescaledb.max_background_workers = '8';")
    cursor.execute("ALTER DATABASE mcs100_db SET timescaledb.max_insert_batch_size = '10000';")
    
    # Créer un utilisateur en lecture seule pour les tableaux de bord
    try:
        cursor.execute("CREATE ROLE dashboard_user WITH LOGIN PASSWORD 'dashboard_password';")
    except:
        conn.rollback()
        print("Note: Role dashboard_user already exists.")
    
    # Accorder des droits en lecture seule sur les schémas
    cursor.execute("GRANT USAGE ON SCHEMA raw TO dashboard_user;")
    cursor.execute("GRANT USAGE ON SCHEMA metrics TO dashboard_user;")
    cursor.execute("GRANT SELECT ON ALL TABLES IN SCHEMA raw TO dashboard_user;")
    cursor.execute("GRANT SELECT ON ALL TABLES IN SCHEMA metrics TO dashboard_user;")
    
    # Configurer les droits par défaut pour les futures tables
    cursor.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT ON TABLES TO dashboard_user;")
    cursor.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA metrics GRANT SELECT ON TABLES TO dashboard_user;")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("Initialisation de TimescaleDB terminée avec succès.")

def init_mongodb():
    """Initialise la base de données MongoDB"""
    
    print("Initialisation de MongoDB...")
    
    # Connexion à MongoDB
    mongo_client = pymongo.MongoClient(
        f"mongodb://{os.getenv('MONGODB_USER', 'root')}:{os.getenv('MONGODB_PASSWORD', 'example')}@"
        f"{os.getenv('MONGODB_HOST', 'localhost')}:{os.getenv('MONGODB_PORT', '27017')}"
    )
    
    # Créer la base de données
    db_name = os.getenv('MONGODB_DB', 'mcs100_db')
    mongo_db = mongo_client[db_name]
    
    # Créer les collections
    sensor_collection = mongo_db['sensor_data']
    flight_reports_collection = mongo_db['flight_reports']
    maintenance_logs_collection = mongo_db['maintenance_logs']
    anomaly_detection_collection = mongo_db['anomaly_detection']
    
    # Créer des index pour améliorer les performances
    
    # Index sur flight_id et timestamp dans sensor_data
    sensor_collection.create_index([('flight_id', pymongo.ASCENDING), ('timestamp', pymongo.ASCENDING)])
    
    # Index sur timestamp dans sensor_data
    sensor_collection.create_index([('timestamp', pymongo.ASCENDING)])
    
    # Index sur aircraft_msn dans flight_reports
    flight_reports_collection.create_index([('aircraft_msn', pymongo.ASCENDING)])
    
    # Index sur flight_id dans flight_reports
    flight_reports_collection.create_index([('flight_id', pymongo.ASCENDING)])
    
    # Index sur aircraft_msn dans maintenance_logs
    maintenance_logs_collection.create_index([('aircraft_msn', pymongo.ASCENDING)])
    
    # Index sur component_id dans maintenance_logs
    maintenance_logs_collection.create_index([('component_id', pymongo.ASCENDING)])
    
    # Index sur detection_timestamp dans anomaly_detection
    anomaly_detection_collection.create_index([('detection_timestamp', pymongo.ASCENDING)])
    
    # Index sur aircraft_msn dans anomaly_detection
    anomaly_detection_collection.create_index([('aircraft_msn', pymongo.ASCENDING)])
    
    # Index sur flight_id dans anomaly_detection
    anomaly_detection_collection.create_index([('flight_id', pymongo.ASCENDING)])
    
    # Créer un utilisateur en lecture seule pour les tableaux de bord
    try:
        mongo_db.command(
            "createUser",
            "dashboard_user",
            pwd="dashboard_password",
            roles=[{"role": "read", "db": db_name}]
        )
    except:
        print("Note: User dashboard_user already exists in MongoDB.")
    
    print("Initialisation de MongoDB terminée avec succès.")

def init_minio():
    """Initialise le stockage MinIO"""
    
    print("Initialisation de MinIO...")
    
    # Connexion à MinIO
    minio_client = Minio(
        f"{os.getenv('MINIO_HOST', 'localhost')}:{os.getenv('MINIO_PORT', '9000')}",
        access_key=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
        secret_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
        secure=False
    )
    
    # Créer les buckets nécessaires
    buckets = [
        os.getenv('MINIO_BUCKET', 'mcs100-data'),
        'flight-reports',
        'maintenance-logs',
        'sensor-data-backups',
        'ml-models',
        'analytics-results'
    ]
    
    for bucket in buckets:
        if not minio_client.bucket_exists(bucket):
            minio_client.make_bucket(bucket)
            print(f"Bucket '{bucket}' créé.")
        else:
            print(f"Bucket '{bucket}' existe déjà.")
    
    # Configurer les politiques d'accès
    
    # Politique en lecture seule pour le bucket flight-reports
    read_only_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::flight-reports/*"]
            }
        ]
    }
    
    try:
        minio_client.set_bucket_policy('flight-reports', read_only_policy)
    except:
        print("Note: Could not set bucket policy for flight-reports.")
    
    # Créer un utilisateur en lecture seule pour les tableaux de bord
    # Note: MinIO ne supporte pas la création d'utilisateurs via l'API Python
    # Cela doit être fait via la ligne de commande ou l'interface web
    
    print("Initialisation de MinIO <response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>