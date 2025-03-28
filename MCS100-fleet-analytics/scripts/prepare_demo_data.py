#!/usr/bin/env python3
"""
Script de préparation des jeux de données pour les démonstrations
Ce script prépare des jeux de données spécifiques pour démontrer les cas d'utilisation
de la solution MCS100 Fleet Analytics
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import argparse
import subprocess
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("demo-data-prep")

# Paramètres par défaut
DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DEFAULT_DEMO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demos")
DEFAULT_GENERATOR_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data/generate_test_data.py")

class DemoDataPreparer:
    """
    Classe pour préparer les jeux de données de démonstration
    """
    
    def __init__(self, data_dir, demo_dir, generator_script):
        """
        Initialise le préparateur de données de démonstration
        
        Args:
            data_dir (str): Répertoire contenant les fichiers CSV de données
            demo_dir (str): Répertoire de sortie pour les jeux de données de démonstration
            generator_script (str): Chemin vers le script de génération de données
        """
        self.data_dir = data_dir
        self.demo_dir = demo_dir
        self.generator_script = generator_script
        
        # Création des répertoires
        os.makedirs(demo_dir, exist_ok=True)
        
        logger.info(f"Préparateur configuré avec le répertoire de données: {data_dir}")
        logger.info(f"Répertoire de démonstration: {demo_dir}")
        logger.info(f"Script de génération: {generator_script}")
    
    def prepare_all_demos(self):
        """
        Prépare tous les jeux de données de démonstration
        """
        logger.info("Préparation de tous les jeux de données de démonstration...")
        
        # Cas d'utilisation 1: Analyse de la fiabilité des composants
        self.prepare_component_reliability_demo()
        
        # Cas d'utilisation 2: Prédiction des intervalles de maintenance optimaux
        self.prepare_maintenance_optimization_demo()
        
        # Cas d'utilisation 3: Détection d'anomalies dans les données de vol
        self.prepare_anomaly_detection_demo()
        
        # Cas d'utilisation 4: Analyse comparative des performances entre différentes compagnies aériennes
        self.prepare_airline_comparison_demo()
        
        # Cas d'utilisation 5: Évaluation de l'impact des modifications techniques sur la fiabilité
        self.prepare_technical_modification_impact_demo()
        
        logger.info("Préparation des jeux de données de démonstration terminée")
    
    def prepare_component_reliability_demo(self):
        """
        Prépare le jeu de données pour la démonstration de l'analyse de la fiabilité des composants
        """
        logger.info("Préparation du jeu de données pour l'analyse de la fiabilité des composants...")
        
        # Création du répertoire de démonstration
        demo_dir = os.path.join(self.demo_dir, "component_reliability")
        os.makedirs(demo_dir, exist_ok=True)
        
        # Génération des données spécifiques pour cette démonstration
        # Nous utilisons un nombre plus élevé d'avions et une période plus longue
        cmd = [
            "python3", self.generator_script,
            "--output-dir", demo_dir,
            "--num-aircraft", "30",
            "--num-airlines", "5",
            "--start-date", (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d"),
            "--end-date", datetime.now().strftime("%Y-%m-%d"),
            "--seed", "101"
        ]
        
        try:
            logger.info(f"Exécution de la commande: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
            logger.info("Génération des données terminée")
            
            # Création d'un fichier README pour cette démonstration
            readme_content = """# Démonstration: Analyse de la fiabilité des composants

## Description
Ce jeu de données est conçu pour démontrer l'analyse de la fiabilité des composants (MTBF, taux de défaillance) dans la flotte d'avions MCS100.

## Caractéristiques du jeu de données
- 30 avions
- 5 compagnies aériennes
- Période de 2 ans
- Historique complet des événements de maintenance
- Métriques de fiabilité calculées pour différentes périodes (30j, 90j, 180j, 365j)

## Cas d'utilisation
1. Analyse du MTBF (Mean Time Between Failures) par type de composant
2. Identification des composants les moins fiables
3. Analyse des tendances de fiabilité au fil du temps
4. Comparaison des taux de défaillance entre différents avions
5. Corrélation entre l'âge des composants et leur fiabilité

## Utilisation
1. Chargez les données dans TimescaleDB et MongoDB à l'aide du script d'initialisation des bases de données
2. Utilisez les tableaux de bord Grafana "Component Reliability Analysis" pour visualiser les métriques
3. Exécutez le job Spark "reliability_analysis.py" pour une analyse approfondie
"""
            
            with open(os.path.join(demo_dir, "README.md"), "w") as f:
                f.write(readme_content)
            
            logger.info(f"Jeu de données préparé dans {demo_dir}")
        
        except Exception as e:
            logger.error(f"Erreur lors de la génération des données: {str(e)}")
    
    def prepare_maintenance_optimization_demo(self):
        """
        Prépare le jeu de données pour la démonstration de la prédiction des intervalles de maintenance optimaux
        """
        logger.info("Préparation du jeu de données pour la prédiction des intervalles de maintenance optimaux...")
        
        # Création du répertoire de démonstration
        demo_dir = os.path.join(self.demo_dir, "maintenance_optimization")
        os.makedirs(demo_dir, exist_ok=True)
        
        # Génération des données spécifiques pour cette démonstration
        # Nous utilisons un nombre modéré d'avions mais avec beaucoup d'événements de maintenance
        cmd = [
            "python3", self.generator_script,
            "--output-dir", demo_dir,
            "--num-aircraft", "15",
            "--num-airlines", "3",
            "--start-date", (datetime.now() - timedelta(days=1095)).strftime("%Y-%m-%d"),
            "--end-date", datetime.now().strftime("%Y-%m-%d"),
            "--seed", "202"
        ]
        
        try:
            logger.info(f"Exécution de la commande: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
            logger.info("Génération des données terminée")
            
            # Création d'un fichier README pour cette démonstration
            readme_content = """# Démonstration: Prédiction des intervalles de maintenance optimaux

## Description
Ce jeu de données est conçu pour démontrer la prédiction des intervalles de maintenance optimaux pour les composants des avions MCS100.

## Caractéristiques du jeu de données
- 15 avions
- 3 compagnies aériennes
- Période de 3 ans
- Historique détaillé des événements de maintenance
- Données d'utilisation complètes (heures de vol, cycles)
- Recommandations d'optimisation des intervalles de maintenance

## Cas d'utilisation
1. Prédiction des intervalles de maintenance optimaux par type de composant
2. Analyse de l'impact des intervalles de maintenance sur la fiabilité
3. Optimisation des coûts de maintenance
4. Planification proactive de la maintenance
5. Évaluation des économies potentielles grâce à l'optimisation des intervalles

## Utilisation
1. Chargez les données dans TimescaleDB et MongoDB à l'aide du script d'initialisation des bases de données
2. Utilisez les tableaux de bord Grafana "Maintenance Optimization" pour visualiser les recommandations
3. Exécutez le job Spark "maintenance_optimization.py" pour générer de nouvelles recommandations
"""
            
            with open(os.path.join(demo_dir, "README.md"), "w") as f:
                f.write(readme_content)
            
            logger.info(f"Jeu de données préparé dans {demo_dir}")
        
        except Exception as e:
            logger.error(f"Erreur lors de la génération des données: {str(e)}")
    
    def prepare_anomaly_detection_demo(self):
        """
        Prépare le jeu de données pour la démonstration de la détection d'anomalies dans les données de vol
        """
        logger.info("Préparation du jeu de données pour la détection d'anomalies dans les données de vol...")
        
        # Création du répertoire de démonstration
        demo_dir = os.path.join(self.demo_dir, "anomaly_detection")
        os.makedirs(demo_dir, exist_ok=True)
        
        # Génération des données spécifiques pour cette démonstration
        # Nous utilisons un petit nombre d'avions mais avec beaucoup de données de vol
        cmd = [
            "python3", self.generator_script,
            "--output-dir", demo_dir,
            "--num-aircraft", "5",
            "--num-airlines", "2",
            "--start-date", (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
            "--end-date", datetime.now().strftime("%Y-%m-%d"),
            "--seed", "303"
        ]
        
        try:
            logger.info(f"Exécution de la commande: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
            logger.info("Génération des données terminée")
            
            # Création d'un fichier README pour cette démonstration
            readme_content = """# Démonstration: Détection d'anomalies dans les données de vol

## Description
Ce jeu de données est conçu pour démontrer la détection d'anomalies dans les données de vol des avions MCS100.

## Caractéristiques du jeu de données
- 5 avions
- 2 compagnies aériennes
- Période de 3 mois
- Données de vol détaillées (température, pression, vibrations, etc.)
- Anomalies détectées avec différents niveaux de confiance

## Cas d'utilisation
1. Détection d'anomalies en temps réel dans les données de vol
2. Identification des comportements anormaux des composants
3. Prévention des défaillances grâce à la détection précoce
4. Analyse des causes profondes des anomalies
5. Réduction des fausses alertes grâce à l'apprentissage automatique

## Utilisation
1. Chargez les données dans TimescaleDB et MongoDB à l'aide du script d'initialisation des bases de données
2. Utilisez les tableaux de bord Grafana "Anomaly Detection" pour visualiser les anomalies
3. Exécutez le job Spark "anomaly_detection.py" pour détecter de nouvelles anomalies
"""
            
            with open(os.path.join(demo_dir, "README.md"), "w") as f:
                f.write(readme_content)
            
            logger.info(f"Jeu de données préparé dans {demo_dir}")
        
        except Exception as e:
            logger.error(f"Erreur lors de la génération des données: {str(e)}")
    
    def prepare_airline_comparison_demo(self):
        """
        Prépare le jeu de données pour la démonstration de l'analyse comparative des performances entre différentes compagnies aériennes
        """
        logger.info("Préparation du jeu de données pour l'analyse comparative des performances entre différentes compagnies aériennes...")
        
        # Création du répertoire de démonstration
        demo_dir = os.path.join(self.demo_dir, "airline_comparison")
        os.makedirs(demo_dir, exist_ok=True)
        
        # Génération des données spécifiques pour cette démonstration
        # Nous utilisons un grand nombre d'avions répartis entre plusieurs compagnies aériennes
        cmd = [
            "python3", self.generator_script,
            "--output-dir", demo_dir,
            "--num-aircraft", "50",
            "--num-airlines", "8",
            "--start-date", (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
            "--end-date", datetime.now().strftime("%Y-%m-%d"),
            "--seed", "404"
        ]
        
        try:
            logger.info(f"Exécution de la commande: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
            logger.info("Génération des données terminée")
            
            # Création d'un fichier README pour cette démonstration
            readme_content = """# Démonstration: Analyse comparative des performances entre différentes compagnies aériennes

## Description
Ce jeu de données est conçu pour démontrer l'analyse comparative des performances des avions MCS100 entre différentes compagnies aériennes.

## Caractéristiques du jeu de données
- 50 avions
- 8 compagnies aériennes
- Période d'un an
- Données complètes d'utilisation et de maintenance
- Métriques de performance par compagnie aérienne

## Cas d'utilisation
1. Comparaison des taux de défaillance entre compagnies aériennes
2. Analyse des pratiques de maintenance par compagnie
3. Évaluation de l'impact des conditions d'exploitation sur la fiabilité
4. Benchmarking des performances opérationnelles
5. Identification des meilleures pratiques

## Utilisation
1. Chargez les données dans TimescaleDB et MongoDB à l'aide du script d'initialisation des bases de données
2. Utilisez les tableaux de bord Grafana "Airline Performance Comparison" pour visualiser les comparaisons
3. Exécutez le notebook Jupyter "airline_comparison_analysis.ipynb" pour une analyse approfondie
"""
            
            with open(os.path.join(demo_dir, "README.md"), "w") as f:
                f.write(readme_content)
            
            logger.info(f"Jeu de données préparé dans {demo_dir}")
        
        except Exception as e:
            logger.error(f"Erreur lors de la génération des données: {str(e)}")
    
    def prepare_technical_modification_impact_demo(self):
        """
        Prépare le jeu de données pour la démonstration de l'évaluation de l'impact des modifications techniques sur la fiabilité
        """
        logger.info("Préparation du jeu de données pour l'évaluation de l'impact des modifications techniques sur la fiabilité...")
        
        # Création du répertoire de démonstration
        demo_dir = os.path.join(self.demo_dir, "technical_modification_impact")
        os.makedirs(demo_dir, exist_ok=True)
        
        # Génération des données spécifiques pour cette démonstration
        # Nous utilisons un nombre modéré d'avions sur une longue période
        cmd = [
            "python3", self.generator_script,
            "--output-dir", demo_dir,
            "--num-aircraft", "20",
            "--num-airlines", "4",
            "--start-date", (datetime.now() - timedelta(days=1460)).strftime("%Y-%m-%d"),
            "--end-date", datetime.now().strftime("%Y-%m-%d"),
            "--seed", "505"
        ]
        
        try:
            logger.info(f"Exécution de la commande: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
            logger.info("Génération des données terminée")
            
            # Création d'un fichier README pour cette démonstration
            readme_content = """# Démonstration: Évaluation de l'impact des modifications techniques sur la fiabilité

## Description
Ce jeu de données est conçu pour démontrer l'évaluation de l'impact des modifications techniques sur la fiabilité des avions MCS100.

## Caractéristiques du jeu de données
- 20 avions
- 4 compagnies aériennes
- Période de 4 ans
- Historique complet des modifications techniques
- Données de fiabilité avant et après modifications

## Cas d'utilisation
1. Analyse de l'impact des modifications techniques sur la fiabilité
2. Évaluation du retour sur investissement des modifications
3. Comparaison des performances avant et après modification
4. Priorisation des modifications techniques futures
5. Validation d<response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>