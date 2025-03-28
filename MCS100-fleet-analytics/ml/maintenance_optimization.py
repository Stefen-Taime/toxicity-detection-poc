"""
Script d'optimisation des intervalles de maintenance
Ce script utilise des techniques avancées de ML pour optimiser les intervalles de maintenance
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib
import os
import json
import logging
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values
import xgboost as xgb
from lifelines import WeibullFitter, KaplanMeierFitter
from lifelines.utils import concordance_index

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("maintenance_optimization.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MaintenanceOptimizer:
    """Classe pour l'optimisation des intervalles de maintenance"""
    
    def __init__(self, db_config, model_dir='models'):
        """
        Initialisation de l'optimiseur de maintenance
        
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
            'flight_hours_total', 'takeoffs_total', 'landings_total',
            'avg_engine_1_temp', 'avg_engine_2_temp',
            'avg_engine_1_vibration', 'avg_engine_2_vibration',
            'avg_fuel_flow_rate', 'unscheduled_failures',
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
    
    def fetch_maintenance_history(self, days=365):
        """
        Récupère l'historique de maintenance depuis la base de données
        
        Args:
            days (int): Nombre de jours d'historique à récupérer
            
        Returns:
            pandas.DataFrame: Historique de maintenance
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        logger.info(f"Récupération de l'historique de maintenance du {start_date.strftime('%Y-%m-%d')} au {end_date.strftime('%Y-%m-%d')}")
        
        # Requête pour récupérer les événements de maintenance
        maintenance_query = """
        SELECT 
            me.aircraft_msn,
            me.component_id,
            me.event_timestamp,
            me.event_type,
            me.is_scheduled,
            me.duration_hours,
            c.component_type,
            c.manufacturer,
            c.recommended_maintenance_interval,
            c.installation_date,
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
            SUM(uc.flight_hours) as flight_hours_total,
            SUM(uc.takeoffs) as takeoffs_total,
            SUM(uc.landings) as landings_total,
            AVG(uc.flight_hours) as avg_daily_flight_hours
        FROM 
            raw.usage_cycles uc
        WHERE 
            uc.date BETWEEN %s AND %s
        GROUP BY 
            uc.aircraft_msn
        """
        
        # Requête pour récupérer les données de vol moyennes
        flight_query = """
        SELECT 
            fd.aircraft_msn,
            AVG(fd.engine_1_temp) as avg_engine_1_temp,
            AVG(fd.engine_2_temp) as avg_engine_2_temp,
            AVG(fd.engine_1_vibration) as avg_engine_1_vibration,
            AVG(fd.engine_2_vibration) as avg_engine_2_vibration,
            AVG(fd.fuel_flow_rate) as avg_fuel_flow_rate
        FROM 
            raw.flight_data fd
        WHERE 
            fd.event_timestamp BETWEEN %s AND %s
        GROUP BY 
            fd.aircraft_msn
        """
        
        # Requête pour récupérer les alertes par composant
        alerts_query = """
        SELECT 
            a.aircraft_msn,
            a.component_id,
            COUNT(*) as total_alerts,
            COUNT(CASE WHEN a.severity = 'CRITICAL' THEN 1 END) as critical_alerts
        FROM 
            raw.alerts a
        WHERE 
            a.event_timestamp BETWEEN %s AND %s
        GROUP BY 
            a.aircraft_msn, a.component_id
        """
        
        try:
            conn = self.connect_to_db()
            
            # Récupération des événements de maintenance
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
            
            # Récupération des données de vol moyennes
            flight_df = pd.read_sql(
                flight_query, 
                conn, 
                params=(
                    start_date.strftime('%Y-%m-%d'), 
                    end_date.strftime('%Y-%m-%d')
                )
            )
            
            # Récupération des alertes par composant
            alerts_df = pd.read_sql(
                alerts_query, 
                conn, 
                params=(
                    start_date.strftime('%Y-%m-%d'), 
                    end_date.strftime('%Y-%m-%d')
                )
            )
            
            conn.close()
            
            logger.info(f"Récupération terminée: {len(maintenance_df)} événements de maintenance, {len(usage_df)} enregistrements d'utilisation, {len(flight_df)} données de vol, {len(alerts_df)} alertes")
            
            # Préparation des données pour l'analyse
            maintenance_data = self.prepare_maintenance_data(maintenance_df, usage_df, flight_df, alerts_df)
            
            return maintenance_data
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'historique de maintenance: {e}")
            raise
    
    def prepare_maintenance_data(self, maintenance_df, usage_df, flight_df, alerts_df):
        """
        Prépare les données de maintenance pour l'analyse
        
        Args:
            maintenance_df (pandas.DataFrame): Événements de maintenance
            usage_df (pandas.DataFrame): Données d'utilisation
            flight_df (pandas.DataFrame): Données de vol moyennes
            alerts_df (pandas.DataFrame): Alertes par composant
            
        Returns:
            pandas.DataFrame: Données préparées pour l'analyse
        """
        logger.info("Préparation des données de maintenance pour l'analyse")
        
        # Conversion des timestamps en datetime
        maintenance_df['event_timestamp'] = pd.to_datetime(maintenance_df['event_timestamp'])
        maintenance_df['installation_date'] = pd.to_datetime(maintenance_df['installation_date'])
        
        # Calcul des intervalles entre les maintenances
        maintenance_intervals = []
        
        # Regroupement par composant
        for (aircraft_msn, component_id), group in maintenance_df.groupby(['aircraft_msn', 'component_id']):
            # Tri par date
            group = group.sort_values('event_timestamp')
            
            # Calcul des intervalles
            for i in range(1, len(group)):
                prev_event = group.iloc[i-1]
                curr_event = group.iloc[i]
                
                # Calcul de l'intervalle en jours
                interval_days = (curr_event['event_timestamp'] - prev_event['event_timestamp']).days
                
                # Vérification que l'intervalle est positif
                if interval_days <= 0:
                    continue
                
                # Création de l'entrée d'intervalle
                interval_entry = {
                    'aircraft_msn': aircraft_msn,
                    'component_id': component_id,
                    'component_type': curr_event['component_type'],
                    'manufacturer': curr_event['manufacturer'],
                    'airline_code': curr_event['airline_code'],
                    'recommended_interval': float(curr_event['recommended_maintenance_interval']),
                    'start_date': prev_event['event_timestamp'],
                    'end_date': curr_event['event_timestamp'],
                    'interval_days': interval_days,
                    'is_failure': curr_event['event_type'] == 'FAILURE' and not curr_event['is_scheduled']
                }
                
                maintenance_intervals.append(interval_entry)
        
        # Création du DataFrame des intervalles
        intervals_df = pd.DataFrame(maintenance_intervals)
        
        if len(intervals_df) == 0:
            logger.warning("Aucun intervalle de maintenance trouvé")
            return pd.DataFrame()
        
        # Jointure avec les données d'utilisation
        intervals_df = intervals_df.merge(
            usage_df,
            on='aircraft_msn',
            how='left'
        )
        
        # Jointure avec les données de vol moyennes
        intervals_df = intervals_df.merge(
            flight_df,
            on='aircraft_msn',
            how='left'
        )
        
        # Jointure avec les alertes
        intervals_df = intervals_df.merge(
            alerts_df,
            on=['aircraft_msn', 'component_id'],
            how='left'
        )
        
        # Remplissage des valeurs manquantes
        intervals_df['total_alerts'] = intervals_df['total_alerts'].fillna(0)
        intervals_df['critical_alerts'] = intervals_df['critical_alerts'].fillna(0)
        
        # Calcul des défaillances non programmées par composant
        unscheduled_failures = maintenance_df[
            (maintenance_df['event_type'] == 'FAILURE') & 
            (maintenance_df['is_scheduled'] == False)
        ].groupby(['aircraft_msn', 'component_id']).size().reset_index(name='unscheduled_failures')
        
        intervals_df = intervals_df.merge(
            unscheduled_failures,
            on=['aircraft_msn', 'component_id'],
            how='left'
        )
        
        intervals_df['unscheduled_failures'] = intervals_df['unscheduled_failures'].fillna(0)
        
        # Calcul du ratio d'intervalle (intervalle réel / intervalle recommandé)
        intervals_df['interval_ratio'] = intervals_df['interval_days'] / intervals_df['recommended_interval']
        
        # Calcul du risque de défaillance
        intervals_df['failure_risk'] = np.where(
            intervals_df['interval_days'] > 0,
            (intervals_df['unscheduled_failures'] * 2 + intervals_df['critical_alerts']) / intervals_df['interval_days'] * 100,
            0
        )
        
        logger.info(f"Préparation terminée: {len(intervals_df)} intervalles de maintenance")
        
        return intervals_df
    
    def analyze_maintenance_intervals(self, intervals_df):
        """
        Analyse les intervalles de maintenance pour identifier les tendances
        
        Args:
            intervals_df (pandas.DataFrame): Données des intervalles de maintenance
            
        Returns:
            dict: Résultats de l'analyse
        """
        logger.info("Analyse des intervalles de maintenance")
        
        if intervals_df.empty:
            logger.warning("Aucune donnée d'intervalle disponible pour l'analyse")
            return {}
        
        # Analyse par type de composant
        component_type_analysis = intervals_df.groupby('component_type').agg({
            'interval_days': ['mean', 'std', 'min', 'max', 'count'],
            'recommended_interval': 'mean',
            'interval_ratio': 'mean',
            'is_failure': 'sum',
            'unscheduled_failures': 'sum',
            'total_alerts': 'sum',
            'critical_alerts': 'sum'
        }).reset_index()
        
        # Renommage des colonnes
        component_type_analysis.columns = [
            'component_type', 'mean_interval', 'std_interval', 'min_interval', 'max_interval', 'count',
            'mean_recommended_interval', 'mean_interval_ratio', 'failures', 'unscheduled_failures',
            'total_alerts', 'critical_alerts'
        ]
        
        # Calcul du taux de défaillance par 1000 jours
        component_type_analysis['failure_rate_per_1000_days'] = component_type_analysis['failures'] / (component_type_analysis['mean_interval'] * component_type_analysis['count']) * 1000
        
        # Analyse par compagnie aérienne
        airline_analysis = intervals_df.groupby('airline_code').agg({
            'interval_days': ['mean', 'std', 'count'],
            'recommended_interval': 'mean',
            'interval_ratio': 'mean',
            'is_failure': 'sum',
            'unscheduled_failures': 'sum'
        }).reset_index()
        
        # Renommage des colonnes
        airline_analysis.columns = [
            'airline_code', 'mean_interval', 'std_interval', 'count',
            'mean_recommended_interval', 'mean_interval_ratio', 'failures', 'unscheduled_failures'
        ]
        
        # Analyse par fabricant
        manufacturer_analysis = intervals_df.groupby('manufacturer').agg({
            'interval_days': ['mean', 'std', 'count'],
            'recommended_interval': 'mean',
            'interval_ratio': 'mean',
            'is_failure': 'sum',
            'unscheduled_failures': 'sum'<response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>