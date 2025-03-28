#!/usr/bin/env python3
"""
Script de génération de données de test pour la solution MCS100 Fleet Analytics
Ce script génère des données synthétiques pour simuler les données de performance
d'une flotte d'avions MCS100 d'Airbus.
"""

import os
import sys
import json
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import uuid
import argparse
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("data-generator")

# Paramètres par défaut
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DEFAULT_NUM_AIRCRAFT = 20
DEFAULT_NUM_AIRLINES = 3
DEFAULT_START_DATE = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
DEFAULT_END_DATE = datetime.now().strftime("%Y-%m-%d")
DEFAULT_SEED = 42

# Constantes
AIRCRAFT_STATUS = ["active", "maintenance", "storage"]
COMPONENT_TYPES = [
    "ENGINE", "APU", "LANDING_GEAR", "HYDRAULIC_SYSTEM", "ELECTRICAL_SYSTEM",
    "FUEL_SYSTEM", "NAVIGATION_SYSTEM", "COMMUNICATION_SYSTEM", "ENVIRONMENTAL_CONTROL",
    "FLIGHT_CONTROL", "AVIONICS", "CABIN_SYSTEM"
]
MAINTENANCE_EVENT_TYPES = ["INSPECTION", "REPAIR", "REPLACEMENT", "OVERHAUL", "CHECK"]
ALERT_SEVERITIES = ["INFO", "WARNING", "CRITICAL"]
AIRLINES = [
    "Air France", "Lufthansa", "British Airways", "KLM", "Iberia",
    "Alitalia", "SAS", "Turkish Airlines", "Emirates", "Qatar Airways"
]

class DataGenerator:
    """
    Classe pour générer des données synthétiques pour la solution MCS100 Fleet Analytics
    """
    
    def __init__(self, output_dir, num_aircraft, num_airlines, start_date, end_date, seed):
        """
        Initialise le générateur de données
        
        Args:
            output_dir (str): Répertoire de sortie pour les fichiers CSV
            num_aircraft (int): Nombre d'avions à générer
            num_airlines (int): Nombre de compagnies aériennes à utiliser
            start_date (str): Date de début au format YYYY-MM-DD
            end_date (str): Date de fin au format YYYY-MM-DD
            seed (int): Graine pour la génération aléatoire
        """
        self.output_dir = output_dir
        self.num_aircraft = num_aircraft
        self.num_airlines = min(num_airlines, len(AIRLINES))
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.seed = seed
        
        # Initialisation du générateur aléatoire
        random.seed(seed)
        np.random.seed(seed)
        
        # Création du répertoire de sortie
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialisation des données
        self.airlines = AIRLINES[:self.num_airlines]
        self.aircraft = []
        self.components = []
        self.maintenance_events = []
        self.alerts = []
        self.flight_data = []
        self.usage_cycles = []
        self.anomalies = []
        self.reliability_metrics = []
        self.failure_predictions = []
        self.maintenance_recommendations = []
        
        logger.info(f"Générateur initialisé avec {num_aircraft} avions et {num_airlines} compagnies aériennes")
        logger.info(f"Période: {start_date} à {end_date}")
        logger.info(f"Répertoire de sortie: {output_dir}")
    
    def generate_all(self):
        """
        Génère toutes les données synthétiques
        """
        logger.info("Début de la génération des données...")
        
        # Génération des données de base
        self.generate_aircraft()
        self.generate_components()
        self.generate_usage_cycles()
        self.generate_maintenance_events()
        self.generate_alerts()
        self.generate_flight_data()
        
        # Génération des données d'analyse
        self.generate_anomalies()
        self.generate_reliability_metrics()
        self.generate_failure_predictions()
        self.generate_maintenance_recommendations()
        
        # Sauvegarde des données
        self.save_all()
        
        logger.info("Génération des données terminée")
    
    def generate_aircraft(self):
        """
        Génère les données des avions
        """
        logger.info("Génération des données des avions...")
        
        for i in range(self.num_aircraft):
            msn = f"MCS100-{10000 + i}"
            airline = random.choice(self.airlines)
            registration = f"{airline[:2].upper()}-{1000 + i}"
            
            # Date de fabrication entre 1 et 10 ans avant la date de fin
            manufacturing_date = self.end_date - timedelta(days=random.randint(365, 3650))
            
            # Date de mise en service entre 1 et 3 mois après la fabrication
            entry_into_service_date = manufacturing_date + timedelta(days=random.randint(30, 90))
            
            # Statut avec une probabilité de 80% actif, 15% en maintenance, 5% en stockage
            status_rand = random.random()
            if status_rand < 0.8:
                status = "active"
            elif status_rand < 0.95:
                status = "maintenance"
            else:
                status = "storage"
            
            aircraft = {
                "msn": msn,
                "type": "MCS100",
                "airline": airline,
                "registration": registration,
                "manufacturing_date": manufacturing_date.strftime("%Y-%m-%d"),
                "entry_into_service_date": entry_into_service_date.strftime("%Y-%m-%d"),
                "status": status
            }
            
            self.aircraft.append(aircraft)
        
        logger.info(f"{len(self.aircraft)} avions générés")
    
    def generate_components(self):
        """
        Génère les données des composants
        """
        logger.info("Génération des données des composants...")
        
        for aircraft in self.aircraft:
            # Nombre de composants par avion entre 50 et 100
            num_components = random.randint(50, 100)
            
            for i in range(num_components):
                component_id = f"{aircraft['msn']}-COMP-{i+1:04d}"
                component_type = random.choice(COMPONENT_TYPES)
                
                # Date d'installation entre la date de fabrication et la date de mise en service
                manufacturing_date = datetime.strptime(aircraft["manufacturing_date"], "%Y-%m-%d")
                entry_into_service_date = datetime.strptime(aircraft["entry_into_service_date"], "%Y-%m-%d")
                installation_date = manufacturing_date + timedelta(days=random.randint(0, (entry_into_service_date - manufacturing_date).days))
                
                # Intervalle de maintenance actuel entre 500 et 5000 heures
                current_interval_hours = random.randint(500, 5000)
                
                # Heures de vol totales entre 0 et 20000
                total_flight_hours = random.randint(0, 20000)
                
                # Dernière maintenance entre 0 et l'intervalle actuel heures de vol avant la date de fin
                last_maintenance_date = None
                if random.random() < 0.8:  # 80% des composants ont une date de dernière maintenance
                    days_since_maintenance = random.randint(0, min(365, int(current_interval_hours / 10)))
                    last_maintenance_date = (self.end_date - timedelta(days=days_since_maintenance)).strftime("%Y-%m-%d")
                
                component = {
                    "id": component_id,
                    "name": f"{component_type} {i+1}",
                    "type": component_type,
                    "aircraft_msn": aircraft["msn"],
                    "installation_date": installation_date.strftime("%Y-%m-%d"),
                    "current_interval_hours": current_interval_hours,
                    "total_flight_hours": total_flight_hours,
                    "last_maintenance_date": last_maintenance_date
                }
                
                self.components.append(component)
        
        logger.info(f"{len(self.components)} composants générés")
    
    def generate_usage_cycles(self):
        """
        Génère les données d'utilisation des avions
        """
        logger.info("Génération des données d'utilisation...")
        
        # Génération des données d'utilisation pour chaque jour de la période
        current_date = self.start_date
        while current_date <= self.end_date:
            for aircraft in self.aircraft:
                # Vérification si l'avion est en service à cette date
                entry_into_service_date = datetime.strptime(aircraft["entry_into_service_date"], "%Y-%m-%d")
                if current_date < entry_into_service_date:
                    continue
                
                # Probabilité de vol ce jour-là (85%)
                if random.random() < 0.85:
                    # Heures de vol entre 2 et 14 heures
                    flight_hours = round(random.uniform(2, 14), 1)
                    
                    # Nombre de décollages et atterrissages entre 1 et 6
                    takeoffs = random.randint(1, 6)
                    landings = takeoffs
                    
                    usage = {
                        "aircraft_msn": aircraft["msn"],
                        "date": current_date.strftime("%Y-%m-%d"),
                        "flight_hours": flight_hours,
                        "takeoffs": takeoffs,
                        "landings": landings
                    }
                    
                    self.usage_cycles.append(usage)
            
            current_date += timedelta(days=1)
        
        logger.info(f"{len(self.usage_cycles)} cycles d'utilisation générés")
    
    def generate_maintenance_events(self):
        """
        Génère les événements de maintenance
        """
        logger.info("Génération des événements de maintenance...")
        
        for component in self.components:
            # Nombre d'événements de maintenance entre 0 et 10
            num_events = random.randint(0, 10)
            
            for i in range(num_events):
                event_id = str(uuid.uuid4())
                aircraft_msn = component["aircraft_msn"]
                component_id = component["id"]
                
                # Type d'événement
                event_type = random.choice(MAINTENANCE_EVENT_TYPES)
                
                # Date de l'événement entre la date d'installation et la date de fin
                installation_date = datetime.strptime(component["installation_date"], "%Y-%m-%d")
                event_date = installation_date + timedelta(days=random.randint(1, (self.end_date - installation_date).days))
                
                # Description et action
                description = f"{event_type} du composant {component['name']}"
                action_taken = f"Réalisation de {event_type.lower()}"
                
                # Technicien
                technician = f"TECH-{random.randint(1000, 9999)}"
                
                # Durée entre 1 et 48 heures
                duration_hours = round(random.uniform(1, 48), 1)
                
                # Planifié ou non (70% planifié)
                is_scheduled = random.random() < 0.7
                
                event = {
                    "id": event_id,
                    "aircraft_msn": aircraft_msn,
                    "component_id": component_id,
                    "event_timestamp": event_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "event_type": event_type,
                    "description": description,
                    "action_taken": action_taken,
                    "technician": technician,
                    "duration_hours": duration_hours,
                    "is_scheduled": is_scheduled
                }
                
                self.maintenance_events.append(event)
        
        # Tri des événements par date
        self.maintenance_events.sort(key=lambda x: x["event_timestamp"])
        
        logger.info(f"{len(self.maintenance_events)} événements de maintenance générés")
    
    def generate_alerts(self):
        """
        Génère les alertes
        """
        logger.info("Génération des alertes...")
        
        for component in self.components:
            # Nombre d'alertes entre 0 et 5
            num_alerts = random.randint(0, 5)
            
            for i in range(num_alerts):
                alert_id = str(uuid.uuid4())
                aircraft_msn = component["aircraft_msn"]
                component_id = component["id"]
                
                # Date de l'alerte entre la date d'installation et la date de fin
                installation_date = datetime.strptime(component["installation_date"], "%Y-%m-%d")
                alert_date = installation_date + timedelta(days=random.randint(1, (self.end_date - installation_date).days))
                
                # Sévérité (60% INFO, 30% WARNING, 10% CRITICAL)
                severity_rand = random.random()
                if severity_rand < 0.6:
                    severity = "INFO"
                elif severity_rand < 0.9:
                    severity = "WARNING"
                else:
                    severity = "CRITICAL"
                
                # Code d'alerte
                alert_code = f"ALT-{component['type'][:3]}-{random.randint(100, 999)}"
                
                # Message
                messages = {
                    "INFO": [
                        f"Paramètre {component['name']} hors plage normale",
                        f"Inspection recommandée pour {component['name']}",
                        f"Variation de performance détectée sur {component['name']}"
                    ],
                    "WARNING": [
                        f"Performance dégradée du composant {component['name']}",
                        f"Maintenance préventive recommandée pour {component['name']}",
                        f"Anomalie détectée sur {component['name']}"
                    ],
                    "CRITICAL": [
                        f"Défaillance imminente du composant {component['name']}",
                        f"Remplacement urgent requis pour {component['name']}",
                        f"Risque élevé de panne sur {component['name']}"
                    ]
                }
                message = random.choice(messages[severity])
                
                alert = {
                    "id": alert_id,
                    "aircraft_msn": aircraft_msn,
                    "component_id": component_id,
                    "event_timestamp": alert_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "alert_code": alert_code,
                    "severity": severity,
                    "message": message
                }
                
                self.alerts.append(alert)
        
        # Tri des alertes par date
        self.alerts.sort(key=lambda x: x["event_timestamp"])
        
        logger.info(f"{len(self.alerts)} alertes générées")
    
    def generate_flight_data(self):
        """
        Génère les données de vol
        """
        logger.info("Génération des données de vol...")
        
        # Pour chaque cycle d'utilisation, générer des données de vol
        for usage in self.usage_cycles:
            aircraft_msn = usage["aircraft_msn"]
            date = datetime.strptime(usage["date"], "%Y-%m-%d")
            flight_hours = usage["flight_hours"]
            
            # Génération d'un identifiant de vol
            flight_id = f"FLT-{aircraft_msn}-{date.strftime('%Y%m%d')}-{random.randint(1, 999):03d}"
            
            # Nombre de points de données (1 <response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>