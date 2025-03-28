"""
Script de prédiction de défaillances pour la maintenance prédictive
Ce script utilise des techniques avancées de ML pour prédire les défaillances des composants
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.metrics import classification_report, confusion_matrix, roc_curve, auc, precision_recall_curve
from sklearn.utils import resample
import joblib
import os
import json
import logging
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values
import xgboost as xgb
from imblearn.over_sampling import SMOTE

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("failure_prediction.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FailurePredictor:
    """Classe pour la prédiction des défaillances des composants"""
    
    def __init__(self, db_config, model_dir='models'):
        """
        Initialisation du prédicteur de défaillances
        
        Args:
            db_config (dict): Configuration de la base de données
            model_dir (str): Répertoire pour sauvegarder les modèles
        """
        self.db_config = db_config
        self.model_dir = model_dir
        
        # Création du répertoire des modèles s'il n'existe pas
        os.makedirs(model_dir, exist_ok=True)
        
        # Paramètres des modèles
        self.rf_params = {
            'n_estimators': [50, 100, 200],
            'max_depth': [5, 10, 20, None],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4]
        }
        
        self.gb_params = {
            'n_estimators': [50, 100, 200],
            'learning_rate': [0.01, 0.1, 0.2],
            'max_depth': [3, 5, 10],
            'subsample': [0.8, 1.0]
        }
        
        self.xgb_params = {
            'n_estimators': [50, 100, 200],
            'learning_rate': [0.01, 0.1, 0.2],
            'max_depth': [3, 5, 10],
            'subsample': [0.8, 1.0],
            'colsample_bytree': [0.8, 1.0]
        }
        
        # Colonnes numériques et catégorielles
        self.numeric_features = [
            'flight_hours', 'takeoffs', 'landings',
            'avg_engine_1_temp', 'avg_engine_2_temp',
            'avg_engine_1_pressure', 'avg_engine_2_pressure',
            'avg_engine_1_vibration', 'avg_engine_2_vibration',
            'avg_fuel_flow_rate', 'days_since_last_maintenance',
            'total_alerts', 'critical_alerts'
        ]
        
        self.categorical_features = [
            'component_type', 'manufacturer', 'airline_code'
        ]
    
    def connect_to_db(self):
        """Établit une connexion à la base de données"""
        try:
            conn = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                dbname=self.db_config['dbname'],
                user=self.db_config['user'],
                password=self.db_config['password']
            )
            return conn
        except Exception as e:
            logger.error(f"Erreur de connexion à la base de données: {e}")
            raise
    
    def fetch_training_data(self, days=365):
        """
        Récupère les données d'entraînement depuis la base de données
        
        Args:
            days (int): Nombre de jours d'historique à récupérer
            
        Returns:
            pandas.DataFrame: Données d'entraînement
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        logger.info(f"Récupération des données d'entraînement du {start_date.strftime('%Y-%m-%d')} au {end_date.strftime('%Y-%m-%d')}")
        
        # Requête pour récupérer les données de maintenance
        maintenance_query = """
        SELECT 
            me.aircraft_msn,
            me.component_id,
            me.event_timestamp,
            me.event_type,
            me.is_scheduled,
            c.component_type,
            c.manufacturer,
            am.airline_code
        FROM 
            raw.maintenance_events me
        JOIN 
            raw.components c ON me.component_id = c.component_id
        JOIN 
            raw.aircraft_metadata am ON me.aircraft_msn = am.aircraft_msn
        WHERE 
            me.event_timestamp BETWEEN %s AND %s
        ORDER BY 
            me.aircraft_msn, me.component_id, me.event_timestamp
        """
        
        # Requête pour récupérer les données d'utilisation
        usage_query = """
        SELECT 
            uc.aircraft_msn,
            uc.date,
            uc.flight_hours,
            uc.takeoffs,
            uc.landings
        FROM 
            raw.usage_cycles uc
        WHERE 
            uc.date BETWEEN %s AND %s
        ORDER BY 
            uc.aircraft_msn, uc.date
        """
        
        # Requête pour récupérer les données de vol
        flight_query = """
        SELECT 
            fd.aircraft_msn,
            fd.flight_id,
            DATE(fd.event_timestamp) as date,
            AVG(fd.engine_1_temp) as avg_engine_1_temp,
            AVG(fd.engine_2_temp) as avg_engine_2_temp,
            AVG(fd.engine_1_pressure) as avg_engine_1_pressure,
            AVG(fd.engine_2_pressure) as avg_engine_2_pressure,
            AVG(fd.engine_1_vibration) as avg_engine_1_vibration,
            AVG(fd.engine_2_vibration) as avg_engine_2_vibration,
            AVG(fd.fuel_flow_rate) as avg_fuel_flow_rate
        FROM 
            raw.flight_data fd
        WHERE 
            fd.event_timestamp BETWEEN %s AND %s
        GROUP BY 
            fd.aircraft_msn, fd.flight_id, DATE(fd.event_timestamp)
        ORDER BY 
            fd.aircraft_msn, DATE(fd.event_timestamp)
        """
        
        # Requête pour récupérer les alertes
        alerts_query = """
        SELECT 
            a.aircraft_msn,
            a.component_id,
            DATE(a.event_timestamp) as date,
            COUNT(*) as total_alerts,
            COUNT(CASE WHEN a.severity = 'CRITICAL' THEN 1 END) as critical_alerts
        FROM 
            raw.alerts a
        WHERE 
            a.event_timestamp BETWEEN %s AND %s
        GROUP BY 
            a.aircraft_msn, a.component_id, DATE(a.event_timestamp)
        ORDER BY 
            a.aircraft_msn, a.component_id, DATE(a.event_timestamp)
        """
        
        try:
            conn = self.connect_to_db()
            
            # Récupération des données de maintenance
            maintenance_df = pd.read_sql(
                maintenance_query, 
                conn, 
                params=(
                    start_date.strftime('%Y-%m-%d'), 
                    end_date.strftime('%Y-%m-%d')
                )
            )
            
            # Récupération des données d'utilisation
            usage_df = pd.read_sql(
                usage_query, 
                conn, 
                params=(
                    start_date.strftime('%Y-%m-%d'), 
                    end_date.strftime('%Y-%m-%d')
                )
            )
            
            # Récupération des données de vol
            flight_df = pd.read_sql(
                flight_query, 
                conn, 
                params=(
                    start_date.strftime('%Y-%m-%d'), 
                    end_date.strftime('%Y-%m-%d')
                )
            )
            
            # Récupération des alertes
            alerts_df = pd.read_sql(
                alerts_query, 
                conn, 
                params=(
                    start_date.strftime('%Y-%m-%d'), 
                    end_date.strftime('%Y-%m-%d')
                )
            )
            
            conn.close()
            
            logger.info(f"Récupération terminée: {len(maintenance_df)} événements de maintenance, {len(usage_df)} cycles d'utilisation, {len(flight_df)} données de vol, {len(alerts_df)} alertes")
            
            # Préparation des données pour l'entraînement
            training_data = self.prepare_training_data(maintenance_df, usage_df, flight_df, alerts_df)
            
            return training_data
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des données d'entraînement: {e}")
            raise
    
    def prepare_training_data(self, maintenance_df, usage_df, flight_df, alerts_df):
        """
        Prépare les données pour l'entraînement des modèles
        
        Args:
            maintenance_df (pandas.DataFrame): Données de maintenance
            usage_df (pandas.DataFrame): Données d'utilisation
            flight_df (pandas.DataFrame): Données de vol
            alerts_df (pandas.DataFrame): Données d'alertes
            
        Returns:
            pandas.DataFrame: Données préparées pour l'entraînement
        """
        logger.info("Préparation des données d'entraînement")
        
        # Conversion des timestamps en datetime
        maintenance_df['event_timestamp'] = pd.to_datetime(maintenance_df['event_timestamp'])
        maintenance_df['event_date'] = maintenance_df['event_timestamp'].dt.date
        
        # Identification des défaillances (événements de maintenance non programmés)
        failures = maintenance_df[
            (maintenance_df['event_type'] == 'FAILURE') & 
            (maintenance_df['is_scheduled'] == False)
        ].copy()
        
        # Création d'un DataFrame pour tous les composants et toutes les dates
        # Pour chaque composant, nous voulons une ligne par jour avec des informations sur son état
        
        # Obtention de la liste des composants uniques
        components = maintenance_df[['aircraft_msn', 'component_id', 'component_type', 'manufacturer']].drop_duplicates()
        
        # Obtention de la liste des dates uniques
        min_date = min(usage_df['date'].min(), flight_df['date'].min())
        max_date = max(usage_df['date'].max(), flight_df['date'].max())
        date_range = pd.date_range(start=min_date, end=max_date)
        
        # Création d'un DataFrame avec toutes les combinaisons composant-date
        component_dates = []
        for _, component in components.iterrows():
            for date in date_range:
                component_dates.append({
                    'aircraft_msn': component['aircraft_msn'],
                    'component_id': component['component_id'],
                    'component_type': component['component_type'],
                    'manufacturer': component['manufacturer'],
                    'date': date.date()
                })
        
        component_date_df = pd.DataFrame(component_dates)
        
        # Ajout des informations sur les compagnies aériennes
        aircraft_airlines = maintenance_df[['aircraft_msn', 'airline_code']].drop_duplicates()
        component_date_df = component_date_df.merge(
            aircraft_airlines, 
            on='aircraft_msn', 
            how='left'
        )
        
        # Ajout des données d'utilisation
        # Pour chaque composant et date, nous voulons connaître l'utilisation de l'avion
        component_date_df = component_date_df.merge(
            usage_df[['aircraft_msn', 'date', 'flight_hours', 'takeoffs', 'landings']],
            on=['aircraft_msn', 'date'],
            how='left'
        )
        
        # Remplissage des valeurs manquantes pour l'utilisation
        component_date_df[['flight_hours', 'takeoffs', 'landings']] = component_date_df[['flight_hours', 'takeoffs', 'landings']].fillna(0)
        
        # Ajout des données de vol moyennes par jour et par avion
        flight_daily_avg = flight_df.groupby(['aircraft_msn', 'date']).agg({
            'avg_engine_1_temp': 'mean',
            'avg_engine_2_temp': 'mean',
            'avg_engine_1_pressure': 'mean',
            'avg_engine_2_pressure': 'mean',
            'avg_engine_1_vibration': 'mean',
            'avg_engine_2_vibration': 'mean',
            'avg_fuel_flow_rate': 'mean'
        }).reset_index()
        
        component_date_df = component_date_df.merge(
            flight_daily_avg,
            on=['aircraft_msn', 'date'],
            how='left'
        )
        
        # Remplissage des valeurs manquantes pour les données de vol
        for col in flight_daily_avg.columns:
            if col not in ['aircraft_msn', 'date']:
                component_date_df[col] = component_date_df[col].fillna(method='ffill')
                component_date_df[col] = component_date_df[col].fillna(method='bfill')
                component_date_df[col] = component_date_df[col].fillna(0)
        
        # Ajout des alertes
        component_date_df = component_date_df.merge(
            alerts_df[['aircraft_msn', 'component_id', 'date', 'total_alerts', 'critical_alerts']],
            on=['aircraft_msn', 'component_id', 'date'],
            how='left'
        )
        
        # Remplissage des valeurs manquantes pour les alertes
        component_date_df[['total_alerts', 'critical_alerts']] = component_date_df[['total_alerts', 'critical_alerts']].fillna(0)
        
        # Calcul du temps écoulé depuis la dernière maintenance
        maintenance_dates = maintenance_df.groupby(['aircraft_msn', 'component_id'])['event_date'].apply(list).reset_index()
        
        def days_since_last_maintenance(row, maintenance_dates_dict):
            key = (row['aircraft_msn'], row['component_id'])
            if key in maintenance_dates_dict:
                maintenance_list = maintenance_dates_dict[key]
                maintenance_list = [date for date in maintenance_list if date < row['date']]
                if maintenance_list:
                    last_maintenance = max(maintenance_list)
                    return (row['date'] - last_maintenance).days
            return 365  # Valeur par défaut si aucune maintenance antérieure
        
        # Création d'un dictionnaire pour un accès plus rapide
        maintenance_dates_dict = {}
        for _, row in maintenance_dates.iterrows():
            maintenance_dates_dict[(row['aircraft_msn'], row['component_id'])] = row['event_date']
        
        # Calcul des jours depuis la dernière maintenance
        component_date_df['days_since_last_maintenance'] = component_date_df.apply(
            lambda row: days_since_last_maintenance(row, maintenance_dates_dict), 
            axis=1
        )
        
        # Création de la variable cible: défaillance dans les 7 prochains jours
        def failure_in_next_days(row, failures_df, days=7):
            future_date = row['date'] + timedelta(days=days)
            return failures_df[
                (failures_df['aircraft_msn'] == row['aircraft_msn']) &
                (failures_df['component_id'] == row['component_id']) &
                (failures_df['event_date'] > row['date']) &
                (failures_df['event_date'] <= future_date)
            ].shape[0] > 0
        
        # Création d'un DataFrame des défaillances pour un accès plus rapide
        failures_df = failures.copy()
        failures_df['event_date'] = failures_df['event_timestamp'].dt.date
        
        # Calcul de la variable cible
        component_date_df['failure_next_7d'] = component_date_df.apply(
            lambda row: failure_in_next_days(row, failures_df, 7), 
            axis=1
        )
        
        logger.info(f"Préparation terminée: {len(component_date_df)} lignes, {component_date_df['failure_next_7d'].sum()} défaillances")
    <response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>