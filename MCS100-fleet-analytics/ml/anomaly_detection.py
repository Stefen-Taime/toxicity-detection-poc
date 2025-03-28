"""
Script de détection d'anomalies avancé pour les données de vol
Ce script utilise des techniques avancées de ML pour détecter les anomalies dans les données de vol
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
import joblib
import os
import json
import logging
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("anomaly_detection.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AnomalyDetector:
    """Classe pour la détection d'anomalies dans les données de vol"""
    
    def __init__(self, db_config, model_dir='models'):
        """
        Initialisation du détecteur d'anomalies
        
        Args:
            db_config (dict): Configuration de la base de données
            model_dir (str): Répertoire pour sauvegarder les modèles
        """
        self.db_config = db_config
        self.model_dir = model_dir
        
        # Création du répertoire des modèles s'il n'existe pas
        os.makedirs(model_dir, exist_ok=True)
        
        # Paramètres des modèles
        self.isolation_forest_params = {
            'n_estimators': 100,
            'max_samples': 'auto',
            'contamination': 0.05,
            'random_state': 42
        }
        
        self.dbscan_params = {
            'eps': 0.5,
            'min_samples': 5
        }
        
        # Colonnes pour l'analyse
        self.feature_columns = [
            'engine_1_temp', 'engine_2_temp',
            'engine_1_pressure', 'engine_2_pressure',
            'engine_1_vibration', 'engine_2_vibration',
            'fuel_flow_rate', 'altitude', 'speed'
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
    
    def fetch_flight_data(self, start_date, end_date):
        """
        Récupère les données de vol depuis la base de données
        
        Args:
            start_date (str): Date de début au format YYYY-MM-DD
            end_date (str): Date de fin au format YYYY-MM-DD
            
        Returns:
            pandas.DataFrame: Données de vol
        """
        logger.info(f"Récupération des données de vol du {start_date} au {end_date}")
        
        query = f"""
        SELECT 
            aircraft_msn,
            flight_id,
            event_timestamp,
            engine_1_temp,
            engine_2_temp,
            engine_1_pressure,
            engine_2_pressure,
            engine_1_vibration,
            engine_2_vibration,
            fuel_flow_rate,
            altitude,
            speed,
            external_temp
        FROM 
            raw.flight_data
        WHERE 
            event_timestamp BETWEEN %s AND %s
        ORDER BY 
            aircraft_msn, event_timestamp
        """
        
        try:
            conn = self.connect_to_db()
            df = pd.read_sql(query, conn, params=(start_date, end_date))
            conn.close()
            
            logger.info(f"Récupération de {len(df)} enregistrements de données de vol")
            return df
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des données de vol: {e}")
            raise
    
    def fetch_historical_data(self, aircraft_msn, days=30):
        """
        Récupère les données historiques pour un avion spécifique
        
        Args:
            aircraft_msn (str): Numéro de série de l'avion
            days (int): Nombre de jours d'historique à récupérer
            
        Returns:
            pandas.DataFrame: Données historiques
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        logger.info(f"Récupération des données historiques pour l'avion {aircraft_msn} sur {days} jours")
        
        query = f"""
        SELECT 
            aircraft_msn,
            flight_id,
            event_timestamp,
            engine_1_temp,
            engine_2_temp,
            engine_1_pressure,
            engine_2_pressure,
            engine_1_vibration,
            engine_2_vibration,
            fuel_flow_rate,
            altitude,
            speed,
            external_temp
        FROM 
            raw.flight_data
        WHERE 
            aircraft_msn = %s AND
            event_timestamp BETWEEN %s AND %s
        ORDER BY 
            event_timestamp
        """
        
        try:
            conn = self.connect_to_db()
            df = pd.read_sql(
                query, 
                conn, 
                params=(
                    aircraft_msn, 
                    start_date.strftime('%Y-%m-%d'), 
                    end_date.strftime('%Y-%m-%d')
                )
            )
            conn.close()
            
            logger.info(f"Récupération de {len(df)} enregistrements historiques pour l'avion {aircraft_msn}")
            return df
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des données historiques: {e}")
            raise
    
    def preprocess_data(self, df):
        """
        Prétraite les données pour la détection d'anomalies
        
        Args:
            df (pandas.DataFrame): Données brutes
            
        Returns:
            pandas.DataFrame: Données prétraitées
        """
        logger.info("Prétraitement des données")
        
        # Suppression des lignes avec des valeurs manquantes
        df_clean = df.dropna(subset=self.feature_columns)
        
        # Filtrage des valeurs aberrantes évidentes
        df_clean = df_clean[
            (df_clean['engine_1_temp'] > 0) & 
            (df_clean['engine_2_temp'] > 0) & 
            (df_clean['fuel_flow_rate'] > 0)
        ]
        
        # Normalisation des données
        scaler = StandardScaler()
        df_clean[self.feature_columns] = scaler.fit_transform(df_clean[self.feature_columns])
        
        logger.info(f"Prétraitement terminé, {len(df_clean)} enregistrements conservés")
        return df_clean, scaler
    
    def train_isolation_forest(self, df, aircraft_msn):
        """
        Entraîne un modèle Isolation Forest pour un avion spécifique
        
        Args:
            df (pandas.DataFrame): Données prétraitées
            aircraft_msn (str): Numéro de série de l'avion
            
        Returns:
            sklearn.ensemble.IsolationForest: Modèle entraîné
        """
        logger.info(f"Entraînement du modèle Isolation Forest pour l'avion {aircraft_msn}")
        
        # Création et entraînement du modèle
        model = IsolationForest(**self.isolation_forest_params)
        model.fit(df[self.feature_columns])
        
        # Sauvegarde du modèle
        model_path = os.path.join(self.model_dir, f"isolation_forest_{aircraft_msn}.joblib")
        joblib.dump(model, model_path)
        
        logger.info(f"Modèle Isolation Forest entraîné et sauvegardé: {model_path}")
        return model
    
    def train_dbscan(self, df, aircraft_msn):
        """
        Entraîne un modèle DBSCAN pour un avion spécifique
        
        Args:
            df (pandas.DataFrame): Données prétraitées
            aircraft_msn (str): Numéro de série de l'avion
            
        Returns:
            sklearn.cluster.DBSCAN: Modèle entraîné
        """
        logger.info(f"Entraînement du modèle DBSCAN pour l'avion {aircraft_msn}")
        
        # Réduction de dimensionnalité avec PCA
        pca = PCA(n_components=3)
        pca_result = pca.fit_transform(df[self.feature_columns])
        
        # Création et entraînement du modèle
        model = DBSCAN(**self.dbscan_params)
        clusters = model.fit_predict(pca_result)
        
        # Évaluation de la qualité du clustering
        if len(set(clusters)) > 1:  # Plus d'un cluster
            silhouette_avg = silhouette_score(pca_result, clusters)
            logger.info(f"Score de silhouette pour DBSCAN: {silhouette_avg}")
        
        # Sauvegarde du modèle et du PCA
        model_path = os.path.join(self.model_dir, f"dbscan_{aircraft_msn}.joblib")
        pca_path = os.path.join(self.model_dir, f"pca_{aircraft_msn}.joblib")
        
        joblib.dump(model, model_path)
        joblib.dump(pca, pca_path)
        
        logger.info(f"Modèle DBSCAN entraîné et sauvegardé: {model_path}")
        return model, pca
    
    def detect_anomalies(self, df, aircraft_msn):
        """
        Détecte les anomalies dans les données de vol
        
        Args:
            df (pandas.DataFrame): Données à analyser
            aircraft_msn (str): Numéro de série de l'avion
            
        Returns:
            pandas.DataFrame: Anomalies détectées
        """
        logger.info(f"Détection d'anomalies pour l'avion {aircraft_msn}")
        
        # Récupération des données historiques pour l'entraînement
        historical_data = self.fetch_historical_data(aircraft_msn)
        
        if len(historical_data) < 100:
            logger.warning(f"Données historiques insuffisantes pour l'avion {aircraft_msn}")
            return pd.DataFrame()  # Retourne un DataFrame vide
        
        # Prétraitement des données
        historical_clean, scaler = self.preprocess_data(historical_data)
        
        # Prétraitement des données à analyser
        df_scaled = pd.DataFrame(
            scaler.transform(df[self.feature_columns]),
            columns=self.feature_columns
        )
        df_scaled['aircraft_msn'] = df['aircraft_msn']
        df_scaled['flight_id'] = df['flight_id']
        df_scaled['event_timestamp'] = df['event_timestamp']
        
        # Entraînement des modèles
        iso_forest = self.train_isolation_forest(historical_clean, aircraft_msn)
        dbscan, pca = self.train_dbscan(historical_clean, aircraft_msn)
        
        # Détection avec Isolation Forest
        iso_predictions = iso_forest.predict(df_scaled[self.feature_columns])
        iso_scores = iso_forest.decision_function(df_scaled[self.feature_columns])
        
        # Détection avec DBSCAN
        pca_result = pca.transform(df_scaled[self.feature_columns])
        dbscan_clusters = dbscan.fit_predict(pca_result)
        
        # Création du DataFrame des résultats
        results = df.copy()
        results['iso_forest_anomaly'] = iso_predictions == -1
        results['iso_forest_score'] = iso_scores
        results['dbscan_cluster'] = dbscan_clusters
        results['dbscan_anomaly'] = dbscan_clusters == -1
        
        # Identification des anomalies (combinaison des deux méthodes)
        results['is_anomaly'] = results['iso_forest_anomaly'] | results['dbscan_anomaly']
        
        # Filtrage des anomalies
        anomalies = results[results['is_anomaly']]
        
        logger.info(f"Détection terminée: {len(anomalies)} anomalies trouvées sur {len(df)} enregistrements")
        return anomalies
    
    def analyze_anomalies(self, anomalies, original_data):
        """
        Analyse les anomalies détectées pour identifier les paramètres anormaux
        
        Args:
            anomalies (pandas.DataFrame): Anomalies détectées
            original_data (pandas.DataFrame): Données originales pour référence
            
        Returns:
            list: Liste des anomalies analysées
        """
        logger.info(f"Analyse de {len(anomalies)} anomalies")
        
        analyzed_anomalies = []
        
        for _, anomaly in anomalies.iterrows():
            aircraft_msn = anomaly['aircraft_msn']
            flight_id = anomaly['flight_id']
            event_timestamp = anomaly['event_timestamp']
            
            # Calcul des statistiques de référence pour cet avion
            aircraft_data = original_data[original_data['aircraft_msn'] == aircraft_msn]
            
            if len(aircraft_data) < 10:
                continue
            
            # Calcul des moyennes et écarts-types
            means = aircraft_data[self.feature_columns].mean()
            stds = aircraft_data[self.feature_columns].std()
            
            # Identification des paramètres anormaux (> 3 écarts-types)
            abnormal_params = []
            for param in self.feature_columns:
                param_value = anomaly[param]
                param_mean = means[param]
                param_std = stds[param]
                
                if param_std > 0 and abs(param_value - param_mean) > 3 * param_std:
                    abnormal_params.append({
                        'parameter': param,
                        'value': float(param_value),
                        'mean': float(param_mean),
                        'std': float(param_std),
                        'deviation': float(abs(param_value - param_mean) / param_std)
                    })
            
            # Détermination de la méthode de détection
            if anomaly['iso_forest_anomaly'] and anomaly['dbscan_anomaly']:
                detection_method = "BOTH"
                confidence = 0.95
            elif anomaly['iso_forest_anomaly']:
                detection_method = "ISOLATION_FOREST"
                confidence = 0.85
            else:
                detection_method = "DBSCAN"
                confidence = 0.75
            
            # Création de l'entrée d'anomalie
            anomaly_entry = {
                'aircraft_msn': aircraft_msn,
                'flight_id': flight_id,
                'event_timestamp': event_timestamp.isoformat() if isinstance(event_timestamp, datetime) else event_timestamp,
                'detection_timestamp': datetime.now().isoformat(),
                'detection_method': detection_method,
                'confidence_score': confidence,
                'abnormal_parameters': abnormal_params,
                'description': f"Anomalie détectée par {detection_method} dans {len(abnormal_params)} paramètres"
            }
            
            analyzed_anomalies.append(anomaly_entry)
        
        logger.info(f"Analyse terminée: {len(analyzed_anomalies)} anomalies analysées")
        return analyzed_anomalies
    
    def save_anomalies_to_db(self, anomalies):
        """
        Sauvegarde les anomalies dans la base de données
        
        Args:
            anomalies (list): Liste des anomalies analysées
            
        Returns:
            int: Nombre d'anomalies sauvegardées
        """
        if not anomalies:
            logger.info("Aucune anomalie à sauvegarder")
            return 0
        
        logger.info(f"Sauvegarde de {len(anomalies)} anomalies dans la base de données")
        
        # Préparation des données pour l'insertion
        values = []
        for anomaly in anomalies:
            values.append((
                anomaly['aircraft_msn'],
                anomaly['flight_id'],
                anomaly['event_timestamp'],
                anomaly['detection_timestamp'],
                anomaly['detection_method'],
                anomaly['confidence_score'],
                json.dumps(anomaly['abnormal_parameters']),
                anomaly['description']
            ))
       <response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>