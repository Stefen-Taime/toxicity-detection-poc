"""
Configuration des tableaux de bord Grafana pour la solution MCS100 Fleet Analytics
Ce script génère les fichiers de configuration pour les tableaux de bord Grafana
"""

import os
import json
import shutil
from datetime import datetime

# Configuration
GRAFANA_DIR = "/MCS100-fleet-analytics/dashboards/grafana"
DASHBOARD_VERSION = 1
REFRESH_RATE = "5m"  # Taux de rafraîchissement des tableaux de bord

# Création du répertoire pour les tableaux de bord
os.makedirs(GRAFANA_DIR, exist_ok=True)

# Fonction pour créer un tableau de bord
def create_dashboard(title, uid, description, panels, variables=None):
    """
    Crée un tableau de bord Grafana
    
    Args:
        title (str): Titre du tableau de bord
        uid (str): UID unique du tableau de bord
        description (str): Description du tableau de bord
        panels (list): Liste des panneaux du tableau de bord
        variables (list): Liste des variables du tableau de bord
    
    Returns:
        dict: Configuration du tableau de bord
    """
    dashboard = {
        "annotations": {
            "list": [
                {
                    "builtIn": 1,
                    "datasource": "-- Grafana --",
                    "enable": True,
                    "hide": True,
                    "iconColor": "rgba(0, 211, 255, 1)",
                    "name": "Annotations & Alerts",
                    "type": "dashboard"
                }
            ]
        },
        "editable": True,
        "gnetId": None,
        "graphTooltip": 0,
        "id": None,
        "links": [],
        "panels": panels,
        "refresh": REFRESH_RATE,
        "schemaVersion": 27,
        "style": "dark",
        "tags": ["mcs100", "airbus", "fleet-analytics"],
        "templating": {
            "list": variables or []
        },
        "time": {
            "from": "now-7d",
            "to": "now"
        },
        "timepicker": {
            "refresh_intervals": [
                "5s",
                "10s",
                "30s",
                "1m",
                "5m",
                "15m",
                "30m",
                "1h",
                "2h",
                "1d"
            ]
        },
        "timezone": "browser",
        "title": title,
        "uid": uid,
        "version": DASHBOARD_VERSION,
        "description": description
    }
    
    return dashboard

# Fonction pour créer un panneau de texte
def create_text_panel(title, content, gridPos):
    """
    Crée un panneau de texte
    
    Args:
        title (str): Titre du panneau
        content (str): Contenu du panneau (Markdown)
        gridPos (dict): Position du panneau
    
    Returns:
        dict: Configuration du panneau
    """
    return {
        "type": "text",
        "title": title,
        "gridPos": gridPos,
        "id": None,
        "mode": "markdown",
        "content": content
    }

# Fonction pour créer un panneau de statistiques
def create_stat_panel(title, targets, gridPos, unit="none", colorMode="value", graphMode="area"):
    """
    Crée un panneau de statistiques
    
    Args:
        title (str): Titre du panneau
        targets (list): Liste des cibles de données
        gridPos (dict): Position du panneau
        unit (str): Unité des valeurs
        colorMode (str): Mode de coloration
        graphMode (str): Mode d'affichage du graphique
    
    Returns:
        dict: Configuration du panneau
    """
    return {
        "type": "stat",
        "title": title,
        "gridPos": gridPos,
        "id": None,
        "targets": targets,
        "options": {
            "colorMode": colorMode,
            "graphMode": graphMode,
            "justifyMode": "auto",
            "orientation": "auto",
            "reduceOptions": {
                "calcs": ["lastNotNull"],
                "fields": "",
                "values": False
            },
            "textMode": "auto"
        },
        "fieldConfig": {
            "defaults": {
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "red", "value": 80}
                    ]
                },
                "color": {"mode": "palette-classic"},
                "unit": unit
            },
            "overrides": []
        }
    }

# Fonction pour créer un panneau de graphique en courbes
def create_time_series_panel(title, targets, gridPos, unit="none"):
    """
    Crée un panneau de graphique en courbes
    
    Args:
        title (str): Titre du panneau
        targets (list): Liste des cibles de données
        gridPos (dict): Position du panneau
        unit (str): Unité des valeurs
    
    Returns:
        dict: Configuration du panneau
    """
    return {
        "type": "timeseries",
        "title": title,
        "gridPos": gridPos,
        "id": None,
        "targets": targets,
        "options": {
            "legend": {"calcs": [], "displayMode": "list", "placement": "bottom"},
            "tooltip": {"mode": "single"}
        },
        "fieldConfig": {
            "defaults": {
                "custom": {
                    "drawStyle": "line",
                    "lineInterpolation": "linear",
                    "barAlignment": 0,
                    "lineWidth": 1,
                    "fillOpacity": 10,
                    "gradientMode": "none",
                    "spanNulls": False,
                    "showPoints": "auto",
                    "pointSize": 5,
                    "stacking": {"mode": "none", "group": "A"},
                    "axisPlacement": "auto",
                    "axisLabel": "",
                    "scaleDistribution": {"type": "linear"},
                    "hideFrom": {"tooltip": False, "viz": False, "legend": False},
                    "thresholdsStyle": {"mode": "off"}
                },
                "color": {"mode": "palette-classic"},
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "red", "value": 80}
                    ]
                },
                "unit": unit
            },
            "overrides": []
        }
    }

# Fonction pour créer un panneau de tableau
def create_table_panel(title, targets, gridPos):
    """
    Crée un panneau de tableau
    
    Args:
        title (str): Titre du panneau
        targets (list): Liste des cibles de données
        gridPos (dict): Position du panneau
    
    Returns:
        dict: Configuration du panneau
    """
    return {
        "type": "table",
        "title": title,
        "gridPos": gridPos,
        "id": None,
        "targets": targets,
        "options": {
            "showHeader": True,
            "footer": {"show": False, "reducer": ["sum"], "countRows": False, "fields": ""},
        },
        "fieldConfig": {
            "defaults": {
                "custom": {
                    "align": "auto",
                    "displayMode": "auto",
                    "filterable": True
                },
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "red", "value": 80}
                    ]
                }
            },
            "overrides": []
        }
    }

# Fonction pour créer un panneau de jauge
def create_gauge_panel(title, targets, gridPos, min=0, max=100, unit="none"):
    """
    Crée un panneau de jauge
    
    Args:
        title (str): Titre du panneau
        targets (list): Liste des cibles de données
        gridPos (dict): Position du panneau
        min (int): Valeur minimale
        max (int): Valeur maximale
        unit (str): Unité des valeurs
    
    Returns:
        dict: Configuration du panneau
    """
    return {
        "type": "gauge",
        "title": title,
        "gridPos": gridPos,
        "id": None,
        "targets": targets,
        "options": {
            "reduceOptions": {
                "values": False,
                "calcs": ["lastNotNull"],
                "fields": ""
            },
            "orientation": "auto",
            "showThresholdLabels": False,
            "showThresholdMarkers": True
        },
        "fieldConfig": {
            "defaults": {
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "yellow", "value": 60},
                        {"color": "red", "value": 80}
                    ]
                },
                "color": {"mode": "thresholds"},
                "min": min,
                "max": max,
                "unit": unit
            },
            "overrides": []
        }
    }

# Fonction pour créer un panneau de barre
def create_bar_gauge_panel(title, targets, gridPos, min=0, max=100, unit="none"):
    """
    Crée un panneau de barre
    
    Args:
        title (str): Titre du panneau
        targets (list): Liste des cibles de données
        gridPos (dict): Position du panneau
        min (int): Valeur minimale
        max (int): Valeur maximale
        unit (str): Unité des valeurs
    
    Returns:
        dict: Configuration du panneau
    """
    return {
        "type": "bargauge",
        "title": title,
        "gridPos": gridPos,
        "id": None,
        "targets": targets,
        "options": {
            "orientation": "horizontal",
            "displayMode": "gradient",
            "reduceOptions": {
                "values": False,
                "calcs": ["lastNotNull"],
                "fields": ""
            },
            "showUnfilled": True
        },
        "fieldConfig": {
            "defaults": {
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "yellow", "value": 60},
                        {"color": "red", "value": 80}
                    ]
                },
                "color": {"mode": "thresholds"},
                "min": min,
                "max": max,
                "unit": unit
            },
            "overrides": []
        }
    }

# Création des variables communes
common_variables = [
    {
        "name": "aircraft_msn",
        "type": "query",
        "datasource": "TimescaleDB",
        "query": "SELECT DISTINCT aircraft_msn FROM aircraft ORDER BY aircraft_msn",
        "refresh": 1,
        "regex": "",
        "sort": 0,
        "allValue": ".*",
        "current": {"selected": True, "text": "All", "value": "$__all"},
        "hide": 0,
        "includeAll": True,
        "multi": True,
        "options": [],
        "label": "Aircraft MSN"
    },
    {
        "name": "component_type",
        "type": "query",
        "datasource": "TimescaleDB",
        "query": "SELECT DISTINCT type FROM components ORDER BY type",
        "refresh": 1,
        "regex": "",
        "sort": 0,
        "allValue": ".*",
        "current": {"selected": True, "text": "All", "value": "$__all"},
        "hide": 0,
        "includeAll": True,
        "multi": True,
        "options": [],
        "label": "Component Type"
    },
    {
        "name": "airline",
        "type": "query",
        "datasource": "TimescaleDB",
        "query": "SELECT DISTINCT airline FROM aircraft ORDER BY airline",
        "refresh": 1,
        "regex": "",
        "sort": 0,
        "allValue": ".*",
        "current": {"selected": True, "text": "All", "value": "$__all"},
        "hide": 0,
        "includeAll": True,
        "multi": True,
        "options": [],
        "label": "Airline"
    }
]

# 1. Tableau de bord de vue d'ensemble de la flotte
fleet_overview_panels = [
    # Panneau d'en-tête
    create_text_panel(
        "Vue d'ensemble de la flotte MCS100",
        "Ce tableau de bord présente une vue d'ensemble de la flotte d'avions MCS100, incluant les statistiques clés, l'état des avions et les alertes récentes.",
        {"h": 3, "w": 24, "x": 0, "y": 0}
    ),
    
    # Statistiques clés
    create_stat_panel(
        "Nombre total d'avions",
        [{"refId": "A", "datasource": "TimescaleDB", "rawSql": "SELECT COUNT(*) FROM aircraft WHERE airline IN ($airline)", "format": "time_series"}],
        {"h": 5, "w": 6, "x": 0, "y": 3}
    ),
    create_stat_panel(
        "Avions actifs",
        [{"refId": "A", "datasource": "TimescaleDB", "rawSql": "SELECT COUNT(*) FROM aircraft WHERE status = 'active' AND airline IN ($airline)", "format": "time_series"}],
        {"h": 5, "w": 6, "x": 6, "y": 3}
    ),
    create_stat_panel(
        "Avions en maintenance",
        [{"refId": "A", "datasource": "TimescaleDB", "rawSql": "SELECT COUNT(*) FROM aircraft WHERE status = 'maintenance' AND airline IN ($airline)", "format": "time_series"}],
        {"h": 5, "w": 6, "x": 12, "y": 3}
    ),
    create_stat_panel(
        "Heures de vol totales (30 derniers jours)",
        [{"refId": "A", "datasource": "TimescaleDB", "rawSql": "SELECT SUM(flight_hours) FROM usage_cycles WHERE date >= NOW() - INTERVAL '30 days' AND aircraft_msn IN (SELECT msn FROM aircraft WHERE airline IN ($airline))", "format": "time_series"}],
        {"h": 5, "w": 6, "x": 18, "y": 3},
        unit="h"
    ),
    
    # Graphique des heures de vol par jour
    create_time_series_panel(
        "Heures de vol quotidiennes",
        [{"refId": "A", "datasource": "TimescaleDB", "rawSql": "SELECT date, SUM(flight_hours) FROM usage_cycles WHERE date >= NOW() - INTERVAL '30 days' AND aircraft_msn IN (SELECT msn FROM aircraft WHERE airline IN ($airline)) GROUP BY date ORDER BY date", "format": "time_series"}],
        {"h": 8, "w": 12, "x": 0, "y": 8},
        unit="h"
    ),
    
    # Graphique des décollages par jour
    create_time_series_panel(
        "Décollages quotidiens",
        [{"refId": "A", "datasource": "TimescaleDB", "rawSql": "SELECT date, SUM(takeoffs) FROM usage_cycles WHERE date >= NOW() - INTERVAL '30 days' AND aircraft_msn IN (SELECT msn FROM aircraft WHERE airline IN ($airline)) GROUP BY date ORDER BY date", "format": "time_series"}],
        {"h": 8, "w": 12, "x": 12, "y": 8}
    ),
    
    # Tableau des alertes récentes
    create_table_panel(
        "Alertes récentes",
        [{"refId": "A", "datasource": "TimescaleDB", "rawSql": "SELECT event_timestamp, aircraft_msn, component_id, severity, alert_code, message FROM alerts WHERE event_timestamp >= NOW() - INTERVAL '7 days' AND aircraft_msn IN (SELECT msn FROM aircraft WHERE airline IN ($airline)) ORDER BY event_timestamp DESC LIMIT 10", "format": "table"}],
        {"h": 8, "w": 24, "x": 0, "y": 16}
    ),
    
    # Tableau des événements de maintenance récents
    create_table_panel(
        "Événements de maintenance récents",
        [{"refId": "A", "datasource": "TimescaleDB", "rawSql": "SELECT event_timestamp, aircraft_msn, component_id, event_type, description, action_taken, duration_hours FROM maintenance_events WHERE event_timestamp >= NOW() - INTERVAL '7 days' AND aircraft_msn IN (SELECT msn FROM aircraft WHERE airline IN ($airline)) ORDER BY event_timestamp DESC LIMIT 10", "format": "table"}],
        {"h": 8, "w": 24, "x": 0, "y": 24}
    )
]

fleet_overview_dashboard = create_dashboard(
    "Vue d'ensemble de la flotte MCS100",
    "fleet-overview",
    "Tableau de bord présentant une vue d'ensemble de la flotte d'avions MCS100",
    fleet_overview_panels,
    common_variables
)

# 2. Tableau de bord d'analyse de fiabilité
reliability_analysis_panels = [
    # Panneau d'en-tête
    <response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>