#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de génération de données de test pour la solution d'analyse de performance
de la flotte d'avions MCS100 d'Airbus.

Ce script génère des données synthétiques réalistes pour les scénarios suivants:
1. Analyse de la fiabilité des composants (MTBF, taux de défaillance)
2. Prédiction des intervalles de maintenance optimaux
3. Détection d'anomalies dans les données de vol
4. Analyse comparative des performances entre différentes compagnies aériennes
5. Évaluation de l'impact des modifications techniques sur la fiabilité

Les données générées sont stockées dans les bases de données appropriées:
- TimescaleDB pour les séries temporelles
- MongoDB pour les données non structurées
- MinIO pour les fichiers bruts
"""

import os
import sys
import json
import random
import datetime
import numpy as np
import pandas as pd
from faker import Faker
import psycopg2
import pymongo
from minio import Minio
from dotenv import load_dotenv
from sqlalchemy import create_engine
from scipy.stats import weibull_min, norm, expon

# Charger les variables d'environnement
load_dotenv('../docker/.env')

# Configuration
AIRCRAFT_COUNT = 100
AIRLINES = ['AFR', 'DLH', 'BAW', 'UAE', 'SIA', 'CPA', 'ANA', 'AAL', 'DAL', 'UAL']
COMPONENT_TYPES = [
    'ENGINE', 'APU', 'LANDING_GEAR', 'FLIGHT_CONTROL', 'HYDRAULIC', 'ELECTRICAL',
    'AVIONICS', 'FUEL', 'ENVIRONMENTAL', 'NAVIGATION', 'COMMUNICATION'
]
MANUFACTURERS = [
    'AIRBUS', 'SAFRAN', 'ROLLS_ROYCE', 'GE', 'HONEYWELL', 'THALES',
    'LIEBHERR', 'COLLINS', 'PARKER', 'ZODIAC'
]
START_DATE = datetime.datetime(2023, 1, 1)
END_DATE = datetime.datetime(2025, 3, 1)
DAYS = (END_DATE - START_DATE).days

# Initialisation de Faker
fake = Faker()

# Connexion aux bases de données
def connect_to_databases():
    """Établit les connexions aux différentes bases de données"""
    
    # Connexion à TimescaleDB
    timescale_conn = psycopg2.connect(
        host=os.getenv('TIMESCALEDB_HOST', 'localhost'),
        port=os.getenv('TIMESCALEDB_PORT', '5432'),
        database=os.getenv('TIMESCALEDB_DB', 'mcs100_db'),
        user=os.getenv('TIMESCALEDB_USER', 'postgres'),
        password=os.getenv('TIMESCALEDB_PASSWORD', 'postgres')
    )
    
    # Connexion à MongoDB
    mongo_client = pymongo.MongoClient(
        f"mongodb://{os.getenv('MONGODB_USER', 'root')}:{os.getenv('MONGODB_PASSWORD', 'example')}@"
        f"{os.getenv('MONGODB_HOST', 'localhost')}:{os.getenv('MONGODB_PORT', '27017')}"
    )
    mongo_db = mongo_client[os.getenv('MONGODB_DB', 'mcs100_db')]
    
    # Connexion à MinIO
    minio_client = Minio(
        f"{os.getenv('MINIO_HOST', 'localhost')}:{os.getenv('MINIO_PORT', '9000')}",
        access_key=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
        secret_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
        secure=False
    )
    
    # Créer le bucket s'il n'existe pas
    bucket_name = os.getenv('MINIO_BUCKET', 'mcs100-data')
    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)
    
    return timescale_conn, mongo_db, minio_client

def generate_aircraft_data(count=AIRCRAFT_COUNT):
    """Génère les données des avions MCS100"""
    
    aircraft_data = []
    for i in range(1, count + 1):
        msn = f"MCS100-{i:05d}"
        airline = random.choice(AIRLINES)
        manufacture_date = START_DATE - datetime.timedelta(days=random.randint(30, 365*3))
        
        aircraft = {
            'aircraft_msn': msn,
            'airline_code': airline,
            'manufacture_date': manufacture_date,
            'registration': f"{airline}-{fake.bothify(text='?###??')}",
            'engine_type': random.choice(['CFM-MCS1', 'RR-MCS1', 'PW-MCS1']),
            'total_flight_hours': random.randint(1000, 20000),
            'total_flight_cycles': random.randint(500, 10000),
            'status': random.choice(['ACTIVE', 'MAINTENANCE', 'STANDBY']),
            'base_airport': fake.airport_code(),
            'last_heavy_maintenance': START_DATE - datetime.timedelta(days=random.randint(1, 365))
        }
        aircraft_data.append(aircraft)
    
    return aircraft_data

def generate_components(aircraft_data):
    """Génère les données des composants pour chaque avion"""
    
    components = []
    component_id_counter = 1
    
    for aircraft in aircraft_data:
        # Nombre de composants par type pour cet avion
        components_per_type = {
            'ENGINE': 2,
            'APU': 1,
            'LANDING_GEAR': 3,
            'FLIGHT_CONTROL': random.randint(10, 15),
            'HYDRAULIC': random.randint(5, 8),
            'ELECTRICAL': random.randint(15, 20),
            'AVIONICS': random.randint(20, 30),
            'FUEL': random.randint(5, 8),
            'ENVIRONMENTAL': random.randint(3, 6),
            'NAVIGATION': random.randint(8, 12),
            'COMMUNICATION': random.randint(5, 10)
        }
        
        for component_type, count in components_per_type.items():
            for _ in range(count):
                component_id = f"COMP-{component_id_counter:06d}"
                component_id_counter += 1
                
                # Paramètres de fiabilité différents selon le type de composant
                if component_type in ['ENGINE', 'APU']:
                    mtbf_hours = random.randint(8000, 12000)
                elif component_type in ['LANDING_GEAR', 'FLIGHT_CONTROL']:
                    mtbf_hours = random.randint(6000, 10000)
                elif component_type in ['HYDRAULIC', 'ELECTRICAL', 'FUEL']:
                    mtbf_hours = random.randint(5000, 8000)
                else:
                    mtbf_hours = random.randint(4000, 7000)
                
                component = {
                    'component_id': component_id,
                    'aircraft_msn': aircraft['aircraft_msn'],
                    'component_type': component_type,
                    'manufacturer': random.choice(MANUFACTURERS),
                    'part_number': fake.bothify(text='P#####-##'),
                    'serial_number': fake.bothify(text='SN-??????-####'),
                    'installation_date': aircraft['manufacture_date'] + datetime.timedelta(days=random.randint(0, 30)),
                    'design_life_hours': random.randint(20000, 50000),
                    'design_life_cycles': random.randint(10000, 25000),
                    'mtbf_hours': mtbf_hours,
                    'last_overhaul_date': START_DATE - datetime.timedelta(days=random.randint(1, 730)),
                    'maintenance_count': random.randint(0, 10)
                }
                components.append(component)
    
    return components

def generate_flight_data(aircraft_data):
    """Génère les données de vol pour chaque avion"""
    
    flight_data = []
    flight_id_counter = 1
    
    for aircraft in aircraft_data:
        # Nombre de vols par jour en moyenne pour cet avion
        flights_per_day = random.uniform(2.5, 5.5)
        
        # Générer les vols sur la période
        current_date = START_DATE
        while current_date < END_DATE:
            # Nombre de vols ce jour
            daily_flights = int(np.random.poisson(flights_per_day))
            
            # Si l'avion est en maintenance, pas de vols
            if random.random() < 0.05:  # 5% de chance d'être en maintenance
                current_date += datetime.timedelta(days=1)
                continue
            
            for _ in range(daily_flights):
                flight_id = f"FLT-{flight_id_counter:07d}"
                flight_id_counter += 1
                
                # Durée du vol entre 1 et 8 heures
                flight_hours = random.uniform(1.0, 8.0)
                
                # Heure de départ aléatoire dans la journée
                departure_time = current_date + datetime.timedelta(hours=random.uniform(0, 24-flight_hours))
                arrival_time = departure_time + datetime.timedelta(hours=flight_hours)
                
                # Aéroports de départ et d'arrivée
                departure_airport = fake.airport_code()
                while True:
                    arrival_airport = fake.airport_code()
                    if arrival_airport != departure_airport:
                        break
                
                flight = {
                    'flight_id': flight_id,
                    'aircraft_msn': aircraft['aircraft_msn'],
                    'departure_time': departure_time,
                    'arrival_time': arrival_time,
                    'departure_airport': departure_airport,
                    'arrival_airport': arrival_airport,
                    'flight_hours': flight_hours,
                    'flight_cycles': 1,
                    'fuel_consumption': flight_hours * random.uniform(2000, 3000),  # kg/h
                    'max_altitude': random.randint(30000, 41000),  # pieds
                    'avg_ground_speed': random.uniform(400, 500),  # nœuds
                    'flight_phase_durations': json.dumps({
                        'taxi_out': random.uniform(10, 30),
                        'takeoff': random.uniform(1, 3),
                        'climb': random.uniform(20, 40),
                        'cruise': flight_hours * 60 - random.uniform(60, 120),
                        'descent': random.uniform(20, 40),
                        'approach': random.uniform(10, 20),
                        'landing': random.uniform(1, 3),
                        'taxi_in': random.uniform(5, 20)
                    })
                }
                flight_data.append(flight)
            
            current_date += datetime.timedelta(days=1)
    
    return flight_data

def generate_sensor_data(flight_data):
    """Génère les données de capteurs pour chaque vol"""
    
    sensor_data = []
    
    for flight in flight_data:
        # Nombre d'enregistrements de capteurs pour ce vol (1 par minute en moyenne)
        flight_minutes = int(flight['flight_hours'] * 60)
        
        # Paramètres de base pour ce vol
        base_engine1_temp = random.uniform(300, 350)
        base_engine2_temp = random.uniform(300, 350)
        base_engine1_vibration = random.uniform(0.1, 0.3)
        base_engine2_vibration = random.uniform(0.1, 0.3)
        base_fuel_flow = random.uniform(1000, 1500)
        
        # Générer des données pour chaque minute du vol
        departure_time = flight['departure_time']
        
        for minute in range(flight_minutes):
            timestamp = departure_time + datetime.timedelta(minutes=minute)
            
            # Calculer la phase de vol
            flight_phase = 'cruise'
            if minute < 30:
                flight_phase = 'climb'
            elif minute > flight_minutes - 30:
                flight_phase = 'descent'
            
            # Ajouter des variations selon la phase de vol
            if flight_phase == 'climb':
                phase_factor = min(1.0, minute / 30.0) * 1.2
            elif flight_phase == 'descent':
                phase_factor = min(1.0, (flight_minutes - minute) / 30.0) * 0.8
            else:
                phase_factor = 1.0
            
            # Ajouter du bruit aléatoire
            noise_factor = random.uniform(0.95, 1.05)
            
            # Calculer les valeurs des capteurs
            engine1_temp = base_engine1_temp * phase_factor * noise_factor
            engine2_temp = base_engine2_temp * phase_factor * noise_factor
            engine1_vibration = base_engine1_vibration * noise_factor
            engine2_vibration = base_engine2_vibration * noise_factor
            fuel_flow = base_fuel_flow * phase_factor * noise_factor
            
            # Ajouter des anomalies occasionnelles (0.1% de chance)
            if random.random() < 0.001:
                anomaly_type = random.choice(['temp', 'vibration', 'fuel'])
                if anomaly_type == 'temp':
                    engine1_temp *= random.uniform(1.1, 1.3)
                elif anomaly_type == 'vibration':
                    engine1_vibration *= random.uniform(1.5, 3.0)
                else:
                    fuel_flow *= random.uniform(0.7, 0.9)
            
            record = {
                'flight_id': flight['flight_id'],
                'timestamp': timestamp,
                'flight_phase': flight_phase,
                'altitude': random.uniform(30000, 40000) if flight_phase == 'cruise' else random.uniform(10000, 30000),
                'ground_speed': random.uniform(400, 500) if flight_phase == 'cruise' else random.uniform(200, 400),
                'engine1_temp': engine1_temp,
                'engine2_temp': engine2_temp,
                'engine1_vibration': engine1_vibration,
                'engine2_vibration': engine2_vibration,
                'fuel_flow': fuel_flow,
                'cabin_pressure': random.uniform(11.5, 12.5),
                'outside_temp': random.uniform(-50, -40),
                'wind_speed': random.uniform(0, 100),
                'wind_direction': random.uniform(0, 360)
            }
            sensor_data.append(record)
    
    return sensor_data

def generate_maintenance_events(aircraft_data, components):
    """Génère les événements de maintenance pour les avions et composants"""
    
    maintenance_events = []
    event_id_counter = 1
    
    # Créer un dictionnaire pour accéder facilement aux composants par avion
    components_by_aircraft = {}
    for component in components:
        aircraft_msn = component['aircraft_msn']
        if aircraft_msn not in components_by_aircraft:
            components_by_aircraft[aircraft_msn] = []
        components_by_aircraft[aircraft_msn].append(component)
    
    # Générer des événements de maintenance programmée pour chaque avion
    for aircraft in aircraft_data:
        # Maintenance légère tous les 500-700 heures de vol
        light_maintenance_interval = random.randint(500, 700)
        
        # Maintenance lourde tous les 2500-3500 heures de vol
        heavy_maintenance_interval = random.randint(2500, 3500)
        
        # Heures de vol initiales
        initial_hours = random.randint(0, light_maintenance_interval - 100)
        
        # Générer les maintenances sur la période
        current_date = START_DATE
        current_hours = initial_hours
        
        while current_date < END_DATE:
            # Ajouter des heures de vol quotidiennes
            daily_hours = random.uniform(5, 12)
            current_hours += daily_hours
            
            # Vérifier si une maintenance légère est nécessaire
            if current_hours >= light_maintenance_interval:
                event_id = f"MAINT-{event_id_counter:07d}"
                event_id_counter += 1
                
                # Sélectionner quelques composants pour la maintenance
                selected_components = random.sample(
                    components_by_aircraft.get(aircraft['aircraft_msn'], []),
                    min(5, len(components_by_aircraft.get(aircraft['aircraft_msn'], [])))
                )
                
                for component in selected_components:
                    maintenance_event = {
                        'event_id': event_id,
                        'aircraft_msn': aircraft['aircraft_msn'],
                        'component_id': component['component_id'],
                        'event_type': 'SCHEDULED_MAINTENANCE',
                        'event_timestamp': current_date,
                        'maintenance_action': random.choice(['INSPECTION', 'SERVICE', 'ADJUSTMENT']),
                        'technician_id': fake.bothify(text='TECH-###'),
                        'duration_hours': random.uniform(1, 4),
                        'findings': random.choice([
                            'No issues found', 'Minor wear observed', 'Within acceptable limits',
                            'Adjusted to specifications', 'Serviced as<response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>