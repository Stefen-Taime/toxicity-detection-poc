#!/usr/bin/env python3
"""
Simulateur d'API pour la solution MCS100 Fleet Analytics
Ce script simule les API externes pour les tests et démonstrations
"""

import os
import sys
import json
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import uuid
import logging
import argparse
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, Depends, status, BackgroundTasks, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("api-simulator")

# Paramètres par défaut
DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8080
DEFAULT_SEED = 42

# Création de l'application FastAPI
app = FastAPI(
    title="MCS100 External APIs Simulator",
    description="Simulateur d'API externes pour la solution MCS100 Fleet Analytics",
    version="1.0.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variables globales
data_dir = DEFAULT_DATA_DIR
random_seed = DEFAULT_SEED
aircraft_data = None
components_data = None
maintenance_events_data = None
alerts_data = None
flight_data_data = None
usage_cycles_data = None

# Modèles de données
class AircraftInfo(BaseModel):
    msn: str
    type: str
    airline: str
    registration: str
    manufacturing_date: str
    entry_into_service_date: Optional[str] = None
    status: str

class ComponentInfo(BaseModel):
    id: str
    name: str
    type: str
    aircraft_msn: str
    installation_date: str
    current_interval_hours: float
    total_flight_hours: float
    last_maintenance_date: Optional[str] = None

class MaintenanceEvent(BaseModel):
    id: str
    aircraft_msn: str
    component_id: str
    event_timestamp: str
    event_type: str
    description: str
    action_taken: str
    technician: str
    duration_hours: float
    is_scheduled: bool

class Alert(BaseModel):
    id: str
    aircraft_msn: str
    component_id: str
    event_timestamp: str
    alert_code: str
    severity: str
    message: str

class FlightData(BaseModel):
    aircraft_msn: str
    flight_id: str
    event_timestamp: str
    engine_1_temp: float
    engine_2_temp: float
    engine_1_pressure: float
    engine_2_pressure: float
    engine_1_vibration: float
    engine_2_vibration: float
    fuel_flow_rate: float
    altitude: float
    speed: float
    external_temp: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None

class UsageCycle(BaseModel):
    aircraft_msn: str
    date: str
    flight_hours: float
    takeoffs: int
    landings: int

class WeatherData(BaseModel):
    timestamp: str
    location: str
    temperature: float
    humidity: float
    pressure: float
    wind_speed: float
    wind_direction: float
    precipitation: float
    cloud_cover: float
    visibility: float

class MaintenanceSchedule(BaseModel):
    aircraft_msn: str
    component_id: str
    scheduled_date: str
    maintenance_type: str
    estimated_duration_hours: float
    facility: str
    technician_id: str
    priority: str
    status: str

class PartInventory(BaseModel):
    part_id: str
    part_name: str
    part_type: str
    compatible_with: List[str]
    quantity: int
    location: str
    unit_price: float
    supplier: str
    lead_time_days: int
    last_order_date: Optional[str] = None
    minimum_stock: int

class TechnicalDocument(BaseModel):
    document_id: str
    title: str
    document_type: str
    applicable_to: List[str]
    publication_date: str
    revision: str
    author: str
    summary: str
    file_path: str
    tags: List[str]

# Fonctions utilitaires
def load_data():
    """
    Charge les données depuis les fichiers CSV
    """
    global aircraft_data, components_data, maintenance_events_data, alerts_data, flight_data_data, usage_cycles_data
    
    logger.info(f"Chargement des données depuis {data_dir}...")
    
    # Vérification de l'existence du répertoire de données
    if not os.path.exists(data_dir):
        logger.error(f"Le répertoire de données {data_dir} n'existe pas")
        sys.exit(1)
    
    # Chargement des données
    try:
        aircraft_file = os.path.join(data_dir, "aircraft.csv")
        if os.path.exists(aircraft_file):
            aircraft_data = pd.read_csv(aircraft_file)
            logger.info(f"Données des avions chargées: {len(aircraft_data)} enregistrements")
        else:
            logger.warning(f"Fichier {aircraft_file} non trouvé")
            aircraft_data = pd.DataFrame()
        
        components_file = os.path.join(data_dir, "components.csv")
        if os.path.exists(components_file):
            components_data = pd.read_csv(components_file)
            logger.info(f"Données des composants chargées: {len(components_data)} enregistrements")
        else:
            logger.warning(f"Fichier {components_file} non trouvé")
            components_data = pd.DataFrame()
        
        maintenance_events_file = os.path.join(data_dir, "maintenance_events.csv")
        if os.path.exists(maintenance_events_file):
            maintenance_events_data = pd.read_csv(maintenance_events_file)
            logger.info(f"Données des événements de maintenance chargées: {len(maintenance_events_data)} enregistrements")
        else:
            logger.warning(f"Fichier {maintenance_events_file} non trouvé")
            maintenance_events_data = pd.DataFrame()
        
        alerts_file = os.path.join(data_dir, "alerts.csv")
        if os.path.exists(alerts_file):
            alerts_data = pd.read_csv(alerts_file)
            logger.info(f"Données des alertes chargées: {len(alerts_data)} enregistrements")
        else:
            logger.warning(f"Fichier {alerts_file} non trouvé")
            alerts_data = pd.DataFrame()
        
        flight_data_file = os.path.join(data_dir, "flight_data.csv")
        if os.path.exists(flight_data_file):
            flight_data_data = pd.read_csv(flight_data_file)
            logger.info(f"Données de vol chargées: {len(flight_data_data)} enregistrements")
        else:
            logger.warning(f"Fichier {flight_data_file} non trouvé")
            flight_data_data = pd.DataFrame()
        
        usage_cycles_file = os.path.join(data_dir, "usage_cycles.csv")
        if os.path.exists(usage_cycles_file):
            usage_cycles_data = pd.read_csv(usage_cycles_file)
            logger.info(f"Données des cycles d'utilisation chargées: {len(usage_cycles_data)} enregistrements")
        else:
            logger.warning(f"Fichier {usage_cycles_file} non trouvé")
            usage_cycles_data = pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Erreur lors du chargement des données: {str(e)}")
        sys.exit(1)
    
    logger.info("Chargement des données terminé")

def generate_weather_data(location, start_date, end_date):
    """
    Génère des données météorologiques synthétiques
    
    Args:
        location (str): Localisation
        start_date (str): Date de début au format YYYY-MM-DD
        end_date (str): Date de fin au format YYYY-MM-DD
    
    Returns:
        list: Liste de dictionnaires contenant les données météorologiques
    """
    random.seed(random_seed)
    np.random.seed(random_seed)
    
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    
    # Paramètres de base pour cette localisation
    base_temp = random.uniform(10, 25)
    base_humidity = random.uniform(40, 80)
    base_pressure = random.uniform(1000, 1020)
    base_wind_speed = random.uniform(5, 15)
    base_wind_direction = random.uniform(0, 360)
    base_precipitation = random.uniform(0, 5)
    base_cloud_cover = random.uniform(0, 100)
    base_visibility = random.uniform(5, 20)
    
    # Génération des données
    weather_data = []
    current_date = start_date
    
    while current_date <= end_date:
        # Variation journalière
        day_factor = np.sin(2 * np.pi * current_date.timetuple().tm_yday / 365)
        
        # Génération des données pour chaque heure
        for hour in range(24):
            # Variation horaire
            hour_factor = np.sin(2 * np.pi * hour / 24)
            
            # Calcul des valeurs
            temperature = base_temp + 5 * day_factor + 2 * hour_factor + random.uniform(-1, 1)
            humidity = base_humidity - 10 * hour_factor + random.uniform(-5, 5)
            pressure = base_pressure + random.uniform(-2, 2)
            wind_speed = base_wind_speed + 5 * abs(hour_factor) + random.uniform(-2, 2)
            wind_direction = (base_wind_direction + hour * 5) % 360
            precipitation = max(0, base_precipitation * (1 + day_factor) + random.uniform(-0.5, 0.5))
            cloud_cover = base_cloud_cover + 20 * day_factor + random.uniform(-10, 10)
            visibility = base_visibility - precipitation + random.uniform(-1, 1)
            
            # Ajustement des valeurs
            humidity = max(0, min(100, humidity))
            precipitation = max(0, precipitation)
            cloud_cover = max(0, min(100, cloud_cover))
            visibility = max(0, visibility)
            
            # Création de l'entrée
            timestamp = current_date.replace(hour=hour, minute=0, second=0)
            
            entry = {
                "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "location": location,
                "temperature": round(temperature, 1),
                "humidity": round(humidity, 1),
                "pressure": round(pressure, 1),
                "wind_speed": round(wind_speed, 1),
                "wind_direction": round(wind_direction, 1),
                "precipitation": round(precipitation, 1),
                "cloud_cover": round(cloud_cover, 1),
                "visibility": round(visibility, 1)
            }
            
            weather_data.append(entry)
        
        current_date += timedelta(days=1)
    
    return weather_data

def generate_maintenance_schedule(aircraft_msn=None, start_date=None, end_date=None):
    """
    Génère un planning de maintenance synthétique
    
    Args:
        aircraft_msn (str, optional): MSN de l'avion
        start_date (str, optional): Date de début au format YYYY-MM-DD
        end_date (str, optional): Date de fin au format YYYY-MM-DD
    
    Returns:
        list: Liste de dictionnaires contenant les plannings de maintenance
    """
    random.seed(random_seed)
    
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    if end_date is None:
        end_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
    
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    
    # Filtrage des avions
    if aircraft_msn and aircraft_data is not None and not aircraft_data.empty:
        aircraft_list = aircraft_data[aircraft_data["msn"] == aircraft_msn]["msn"].tolist()
    elif aircraft_data is not None and not aircraft_data.empty:
        aircraft_list = aircraft_data["msn"].tolist()
    else:
        aircraft_list = [f"MCS100-{10000 + i}" for i in range(5)]
    
    # Filtrage des composants
    if components_data is not None and not components_data.empty:
        if aircraft_msn:
            components_list = components_data[components_data["aircraft_msn"] == aircraft_msn]["id"].tolist()
        else:
            components_list = components_data["id"].tolist()
    else:
        components_list = [f"COMP-{i:04d}" for i in range(20)]
    
    # Types de maintenance
    maintenance_types = ["A-CHECK", "B-CHECK", "C-CHECK", "D-CHECK", "INSPECTION", "REPAIR", "REPLACEMENT", "OVERHAUL"]
    
    # Statuts
    statuses = ["SCHEDULED", "IN_PROGRESS", "COMPLETED", "DELAYED", "CANCELLED"]
    
    # Priorités
    priorities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    
    # Installations
    facilities = ["HANGAR-A", "HANGAR-B", "HANGAR-C", "WORKSHOP-1", "WORKSHOP-2", "EXTERNAL-VENDOR"]
    
    # Génération des données
    schedule_data = []
    
    for aircraft in aircraft_list:
        # Nombre d'événements de maintenance planifiés
        num_events = random.randint(2, 10)
        
        for _ in range(num_events):
            # Date planifiée entre start_date et end_date
            days_offset = random.randint(0, (end_date - start_date).days)
            scheduled_date = start_date + timedelta(days=days_offset)
            
            # Composant aléatoire
            component_id = random.choice(components_list)
            
            # Type de maintenance
            maintenance_type = random.choice(maintenance_types)
            
            # Durée estimée
            estimated_duration_hours = random.randint(1, 48)
            
            # Installation
            facility = random.choice(facilities)
            
            # Technicien
            technician_id = f"TECH-{random.randint(1000, 9999)}"
            
            # Priorité
            priority = random.choice(priorities)
            
            # Statut
            if scheduled_date < datetime.now():
                status = random.choice(["COMPLETED", "CANCELLED"])
            elif scheduled_date.date() == datetime.now().date():
                status = random.choice(["IN_PROGRESS", "SCHEDULED", "DELAYED"])
            else:
                status = "SCHEDULED"
            
            # Création de l'entrée
            entry = {
                "aircraft_msn": aircraft,
                "component_id": component_id,
                "scheduled_date": scheduled_date.strftime("%Y-%m-%d"),
                "maintenance_type": maintenance_type,
                "estimated_duration_hours": estimated_duration_hours,
                "facility": facility,
                "technician_id": technician_id,
                "priority": priority,
                "status": status
            }
            
            schedule_data.append(entry)
    
    return schedule_data

def generate_part_inventory():
    """
    Génère un inventaire de pièces synthétique
    
    Returns:
        list: Liste de dictionnaires contenant l'inventaire des pièces
    """
    random.seed(random_seed)
    
    # Types de pièces
    part_types = [
        "ENGINE_COMPONENT", "APU_COMPONENT", "LANDING_GEAR_COMPONENT", "HYDRAULIC_COMPONENT",
        "ELECTRICAL_COMPONENT", "FUEL_SYSTEM_COMPONENT", "NAVIGATION_COMPONENT", "COMMUNICATION_COMPONENT",
        "ENVIRONMENTAL_CONTROL_COMPONENT", "FLIGHT_CONTROL_COMPONENT", "AVIONICS_COMPONENT", "CABIN_COMPONENT"
    ]
    
    # Noms de pièces par type
    part_names = {
        "ENGINE_COMPONENT": ["Turbine Blade", "Fuel Injector", "Combustion Chamber", "Compressor", "Exhaust Nozzle"],
        "APU_COMPONENT": ["APU Generator", "APU Starter", "APU Controller", "APU Fuel Pump", "APU Exhaust"],
        "LANDING_GEAR_COMPONENT": ["Shock Absorber", "Wheel Assembly", "Brake Pad", "Actuator", "Steering Mechanism"],
        "HYDRAULIC_COMPONENT": ["Hydraulic Pump", "Hydraulic Reservoir", "Hydraulic Valve", "Hydraulic Filter", "Hydraulic Accumulator"],
        "ELECTRICAL_COMPONENT": ["Generator", "Battery", "Circuit Breaker", "Electrical Harness", "Power Distribution Unit"],
        "FUEL_SYSTEM_COMPONENT": ["Fuel Pump", "Fuel Filter", "Fuel Valve", "Fuel Tank Sensor", "Fuel Line"],
        "NAVIGATION_COMPONENT": ["GPS Unit", "Inertial Reference Unit", "Radio Altimeter", "VOR Receiv<response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>