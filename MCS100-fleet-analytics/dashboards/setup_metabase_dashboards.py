"""
Configuration des tableaux de bord Metabase pour la solution MCS100 Fleet Analytics
Ce script génère les fichiers de configuration pour les tableaux de bord Metabase
"""

import os
import json
import shutil
from datetime import datetime

# Configuration
METABASE_DIR = "/MCS100-fleet-analytics/dashboards/metabase"
os.makedirs(METABASE_DIR, exist_ok=True)

# Structure de base pour les tableaux de bord Metabase
def create_metabase_dashboard(name, description, cards):
    """
    Crée un tableau de bord Metabase
    
    Args:
        name (str): Nom du tableau de bord
        description (str): Description du tableau de bord
        cards (list): Liste des cartes du tableau de bord
    
    Returns:
        dict: Configuration du tableau de bord
    """
    return {
        "name": name,
        "description": description,
        "cards": cards,
        "parameters": [
            {
                "name": "Aircraft MSN",
                "slug": "aircraft_msn",
                "id": "aircraft_msn",
                "type": "string/=",
                "default": None
            },
            {
                "name": "Component Type",
                "slug": "component_type",
                "id": "component_type",
                "type": "string/=",
                "default": None
            },
            {
                "name": "Airline",
                "slug": "airline",
                "id": "airline",
                "type": "string/=",
                "default": None
            },
            {
                "name": "Date Range",
                "slug": "date_range",
                "id": "date_range",
                "type": "date/range",
                "default": "past30days"
            }
        ]
    }

# Fonction pour créer une carte de question
def create_question_card(name, query, visualization_settings, position):
    """
    Crée une carte de question pour un tableau de bord Metabase
    
    Args:
        name (str): Nom de la question
        query (dict): Requête SQL
        visualization_settings (dict): Paramètres de visualisation
        position (dict): Position de la carte dans le tableau de bord
    
    Returns:
        dict: Configuration de la carte
    """
    return {
        "card": {
            "name": name,
            "dataset_query": {
                "type": "native",
                "native": {
                    "query": query,
                    "template-tags": {}
                },
                "database": 1  # ID de la base de données TimescaleDB
            },
            "display": visualization_settings.get("display", "table"),
            "visualization_settings": visualization_settings
        },
        "position": position
    }

# Fonction pour créer une carte de texte
def create_text_card(text, position):
    """
    Crée une carte de texte pour un tableau de bord Metabase
    
    Args:
        text (str): Contenu de la carte
        position (dict): Position de la carte dans le tableau de bord
    
    Returns:
        dict: Configuration de la carte
    """
    return {
        "card": {
            "name": "Text",
            "display": "text",
            "visualization_settings": {
                "text": text
            }
        },
        "position": position
    }

# 1. Tableau de bord de vue d'ensemble de la flotte
fleet_overview_cards = [
    # Carte de texte d'en-tête
    create_text_card(
        "# Vue d'ensemble de la flotte MCS100\n\nCe tableau de bord présente une vue d'ensemble de la flotte d'avions MCS100, incluant les statistiques clés, l'état des avions et les alertes récentes.",
        {"col": 0, "row": 0, "sizeX": 18, "sizeY": 1}
    ),
    
    # Statistiques clés
    create_question_card(
        "Nombre total d'avions",
        "SELECT COUNT(*) AS \"Total d'avions\" FROM aircraft WHERE airline = {{airline}}",
        {"display": "scalar", "scalar.field": "Total d'avions"},
        {"col": 0, "row": 1, "sizeX": 4, "sizeY": 2}
    ),
    create_question_card(
        "Avions actifs",
        "SELECT COUNT(*) AS \"Avions actifs\" FROM aircraft WHERE status = 'active' AND airline = {{airline}}",
        {"display": "scalar", "scalar.field": "Avions actifs"},
        {"col": 4, "row": 1, "sizeX": 4, "sizeY": 2}
    ),
    create_question_card(
        "Avions en maintenance",
        "SELECT COUNT(*) AS \"Avions en maintenance\" FROM aircraft WHERE status = 'maintenance' AND airline = {{airline}}",
        {"display": "scalar", "scalar.field": "Avions en maintenance"},
        {"col": 8, "row": 1, "sizeX": 4, "sizeY": 2}
    ),
    create_question_card(
        "Heures de vol totales (30 derniers jours)",
        "SELECT SUM(flight_hours) AS \"Heures de vol\" FROM usage_cycles WHERE date >= NOW() - INTERVAL '30 days' AND aircraft_msn IN (SELECT msn FROM aircraft WHERE airline = {{airline}})",
        {"display": "scalar", "scalar.field": "Heures de vol"},
        {"col": 12, "row": 1, "sizeX": 6, "sizeY": 2}
    ),
    
    # Graphique des heures de vol par jour
    create_question_card(
        "Heures de vol quotidiennes",
        "SELECT date AS \"Date\", SUM(flight_hours) AS \"Heures de vol\" FROM usage_cycles WHERE date >= {{date_range.start}} AND date <= {{date_range.end}} AND aircraft_msn IN (SELECT msn FROM aircraft WHERE airline = {{airline}}) GROUP BY date ORDER BY date",
        {"display": "line", "graph.dimensions": ["Date"], "graph.metrics": ["Heures de vol"]},
        {"col": 0, "row": 3, "sizeX": 9, "sizeY": 4}
    ),
    
    # Graphique des décollages par jour
    create_question_card(
        "Décollages quotidiens",
        "SELECT date AS \"Date\", SUM(takeoffs) AS \"Décollages\" FROM usage_cycles WHERE date >= {{date_range.start}} AND date <= {{date_range.end}} AND aircraft_msn IN (SELECT msn FROM aircraft WHERE airline = {{airline}}) GROUP BY date ORDER BY date",
        {"display": "line", "graph.dimensions": ["Date"], "graph.metrics": ["Décollages"]},
        {"col": 9, "row": 3, "sizeX": 9, "sizeY": 4}
    ),
    
    # Tableau des alertes récentes
    create_question_card(
        "Alertes récentes",
        "SELECT event_timestamp AS \"Date\", aircraft_msn AS \"MSN\", component_id AS \"Composant\", severity AS \"Sévérité\", alert_code AS \"Code\", message AS \"Message\" FROM alerts WHERE event_timestamp >= NOW() - INTERVAL '7 days' AND aircraft_msn IN (SELECT msn FROM aircraft WHERE airline = {{airline}}) ORDER BY event_timestamp DESC LIMIT 10",
        {"display": "table"},
        {"col": 0, "row": 7, "sizeX": 18, "sizeY": 4}
    ),
    
    # Tableau des événements de maintenance récents
    create_question_card(
        "Événements de maintenance récents",
        "SELECT event_timestamp AS \"Date\", aircraft_msn AS \"MSN\", component_id AS \"Composant\", event_type AS \"Type\", description AS \"Description\", action_taken AS \"Action\", duration_hours AS \"Durée (h)\" FROM maintenance_events WHERE event_timestamp >= NOW() - INTERVAL '7 days' AND aircraft_msn IN (SELECT msn FROM aircraft WHERE airline = {{airline}}) ORDER BY event_timestamp DESC LIMIT 10",
        {"display": "table"},
        {"col": 0, "row": 11, "sizeX": 18, "sizeY": 4}
    )
]

fleet_overview_dashboard = create_metabase_dashboard(
    "Vue d'ensemble de la flotte MCS100",
    "Tableau de bord présentant une vue d'ensemble de la flotte d'avions MCS100",
    fleet_overview_cards
)

# 2. Tableau de bord d'analyse de fiabilité
reliability_analysis_cards = [
    # Carte de texte d'en-tête
    create_text_card(
        "# Analyse de fiabilité des composants\n\nCe tableau de bord présente une analyse détaillée de la fiabilité des composants des avions MCS100, incluant les métriques MTBF, les taux de défaillance et les tendances.",
        {"col": 0, "row": 0, "sizeX": 18, "sizeY": 1}
    ),
    
    # Statistiques clés
    create_question_card(
        "MTBF moyen (heures)",
        "SELECT AVG(mtbf_hours) AS \"MTBF moyen\" FROM reliability_metrics WHERE component_type = {{component_type}} AND aircraft_msn = {{aircraft_msn}}",
        {"display": "scalar", "scalar.field": "MTBF moyen"},
        {"col": 0, "row": 1, "sizeX": 6, "sizeY": 2}
    ),
    create_question_card(
        "Taux de défaillance moyen (pour 1000h)",
        "SELECT AVG(failure_rate_per_1000h) AS \"Taux de défaillance\" FROM reliability_metrics WHERE component_type = {{component_type}} AND aircraft_msn = {{aircraft_msn}}",
        {"display": "scalar", "scalar.field": "Taux de défaillance"},
        {"col": 6, "row": 1, "sizeX": 6, "sizeY": 2}
    ),
    create_question_card(
        "Taux de retrait non planifié moyen",
        "SELECT AVG(unscheduled_removal_rate) AS \"Taux de retrait\" FROM reliability_metrics WHERE component_type = {{component_type}} AND aircraft_msn = {{aircraft_msn}}",
        {"display": "scalar", "scalar.field": "Taux de retrait"},
        {"col": 12, "row": 1, "sizeX": 6, "sizeY": 2}
    ),
    
    # Graphique des taux de défaillance par type de composant
    create_question_card(
        "Taux de défaillance par type de composant (pour 1000h)",
        "SELECT component_type AS \"Type de composant\", AVG(failure_rate_per_1000h) AS \"Taux de défaillance\" FROM reliability_metrics WHERE component_type = {{component_type}} GROUP BY component_type ORDER BY AVG(failure_rate_per_1000h) DESC LIMIT 10",
        {"display": "bar", "graph.dimensions": ["Type de composant"], "graph.metrics": ["Taux de défaillance"]},
        {"col": 0, "row": 3, "sizeX": 9, "sizeY": 5}
    ),
    
    # Graphique des MTBF par type de composant
    create_question_card(
        "MTBF par type de composant (heures)",
        "SELECT component_type AS \"Type de composant\", AVG(mtbf_hours) AS \"MTBF\" FROM reliability_metrics WHERE component_type = {{component_type}} GROUP BY component_type ORDER BY AVG(mtbf_hours) ASC LIMIT 10",
        {"display": "bar", "graph.dimensions": ["Type de composant"], "graph.metrics": ["MTBF"]},
        {"col": 9, "row": 3, "sizeX": 9, "sizeY": 5}
    ),
    
    # Graphique de l'évolution des taux de défaillance
    create_question_card(
        "Évolution des taux de défaillance (pour 1000h)",
        "SELECT period_end AS \"Période\", AVG(failure_rate_per_1000h) AS \"Taux de défaillance\" FROM reliability_metrics WHERE component_type = {{component_type}} AND aircraft_msn = {{aircraft_msn}} GROUP BY period_end ORDER BY period_end",
        {"display": "line", "graph.dimensions": ["Période"], "graph.metrics": ["Taux de défaillance"]},
        {"col": 0, "row": 8, "sizeX": 18, "sizeY": 4}
    ),
    
    # Tableau des composants les moins fiables
    create_question_card(
        "Top 10 des composants les moins fiables",
        "SELECT component_id AS \"Composant\", component_type AS \"Type\", aircraft_msn AS \"MSN\", mtbf_hours AS \"MTBF (h)\", failure_rate_per_1000h AS \"Taux de défaillance\", unscheduled_removal_rate AS \"Taux de retrait\" FROM reliability_metrics WHERE component_type = {{component_type}} AND aircraft_msn = {{aircraft_msn}} ORDER BY failure_rate_per_1000h DESC LIMIT 10",
        {"display": "table"},
        {"col": 0, "row": 12, "sizeX": 18, "sizeY": 5}
    )
]

reliability_analysis_dashboard = create_metabase_dashboard(
    "Analyse de fiabilité des composants",
    "Tableau de bord présentant une analyse détaillée de la fiabilité des composants des avions MCS100",
    reliability_analysis_cards
)

# 3. Tableau de bord de détection d'anomalies
anomaly_detection_cards = [
    # Carte de texte d'en-tête
    create_text_card(
        "# Détection d'anomalies\n\nCe tableau de bord présente les résultats de la détection d'anomalies dans les données de vol des avions MCS100, permettant d'identifier les comportements anormaux et les problèmes potentiels.",
        {"col": 0, "row": 0, "sizeX": 18, "sizeY": 1}
    ),
    
    # Statistiques clés
    create_question_card(
        "Nombre total d'anomalies (7 derniers jours)",
        "SELECT COUNT(*) AS \"Anomalies\" FROM anomalies WHERE detection_timestamp >= NOW() - INTERVAL '7 days' AND aircraft_msn = {{aircraft_msn}}",
        {"display": "scalar", "scalar.field": "Anomalies"},
        {"col": 0, "row": 1, "sizeX": 6, "sizeY": 2}
    ),
    create_question_card(
        "Anomalies critiques (7 derniers jours)",
        "SELECT COUNT(*) AS \"Anomalies critiques\" FROM anomalies WHERE detection_timestamp >= NOW() - INTERVAL '7 days' AND confidence_score >= 0.8 AND aircraft_msn = {{aircraft_msn}}",
        {"display": "scalar", "scalar.field": "Anomalies critiques"},
        {"col": 6, "row": 1, "sizeX": 6, "sizeY": 2}
    ),
    create_question_card(
        "Taux d'anomalies (%)",
        "SELECT 100.0 * COUNT(DISTINCT a.id) / COUNT(DISTINCT f.id) AS \"Taux d'anomalies\" FROM anomalies a RIGHT JOIN flight_data f ON a.flight_id = f.flight_id WHERE f.event_timestamp >= NOW() - INTERVAL '7 days' AND f.aircraft_msn = {{aircraft_msn}}",
        {"display": "scalar", "scalar.field": "Taux d'anomalies"},
        {"col": 12, "row": 1, "sizeX": 6, "sizeY": 2}
    ),
    
    # Graphique des anomalies par jour
    create_question_card(
        "Anomalies détectées par jour",
        "SELECT DATE(detection_timestamp) AS \"Jour\", COUNT(*) AS \"Anomalies\" FROM anomalies WHERE detection_timestamp >= {{date_range.start}} AND detection_timestamp <= {{date_range.end}} AND aircraft_msn = {{aircraft_msn}} GROUP BY \"Jour\" ORDER BY \"Jour\"",
        {"display": "line", "graph.dimensions": ["Jour"], "graph.metrics": ["Anomalies"]},
        {"col": 0, "row": 3, "sizeX": 9, "sizeY": 4}
    ),
    
    # Graphique des anomalies par type
    create_question_card(
        "Anomalies par type",
        "SELECT anomaly_type AS \"Type\", COUNT(*) AS \"Nombre\" FROM anomalies WHERE detection_timestamp >= NOW() - INTERVAL '7 days' AND aircraft_msn = {{aircraft_msn}} GROUP BY anomaly_type ORDER BY COUNT(*) DESC",
        {"display": "bar", "graph.dimensions": ["Type"], "graph.metrics": ["Nombre"]},
        {"col": 9, "row": 3, "sizeX": 9, "sizeY": 4}
    ),
    
    # Tableau des anomalies récentes
    create_question_card(
        "Anomalies récentes",
        "SELECT detection_timestamp AS \"Date\", aircraft_msn AS \"MSN\", flight_id AS \"Vol\", anomaly_type AS \"Type\", confidence_score AS \"Score\", description AS \"Description\" FROM anomalies WHERE detection_timestamp >= NOW() - INTERVAL '7 days' AND aircraft_msn = {{aircraft_msn}} ORDER BY detection_timestamp DESC, confidence_score DESC LIMIT 20",
        {"display": "table"},
        {"col": 0, "row": 7, "sizeX": 18, "sizeY": 5}
    ),
    
    # Graphique des paramètres de vol anormaux
    create_question_card(
        "Paramètres de vol anormaux (exemple)",
        "SELECT event_timestamp AS \"Temps\", engine_1_temp AS \"Température moteur 1\", engine_2_temp AS \"Température moteur 2\" FROM flight_data WHERE aircraft_msn = {{aircraft_msn}} AND flight_id IN (SELECT DISTINCT flight_id FROM anomalies WHERE detection_timestamp >= NOW() - INTERVAL '1 day' AND aircraft_msn = {{aircraft_msn}} LIMIT 1) ORDER BY event_timestamp",
        {"display": "line", "graph.dimensions": ["Temps"], "graph.metrics": ["Température moteur 1", "Température moteur 2"]},
        {"col": 0, "row": 12, "sizeX": 18, "sizeY": 4}
    )
]

anomaly_detection_dashboard = create_metabase_dashboard(
    "Détection d'anomalies",
    "Tableau de bord présentant les résultats de la détection d'anomalies dans les données de vol des avions MCS100",
    anomaly_detection_cards
)

# 4. Tableau de bord de prédiction de défaillances
failure_prediction_cards = [
    # Carte de texte d'en-tête
    create_text_card(
        "# Prédiction de défaillances\n\nCe tableau de bord présente les prédictions de défaillances pour les composants des avions MCS100, permettant d'anticiper les problèmes et d'optimiser la maintenance.",
        {"col": 0, "row": 0, "sizeX": 18, "sizeY": 1}
    ),
    
    # Statistiques clés
    create_question_card(
        <response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>