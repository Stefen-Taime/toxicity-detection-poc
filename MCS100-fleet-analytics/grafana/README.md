# Dashboards Grafana pour MCS100 Fleet Analytics

Ce répertoire contient les configurations des dashboards Grafana pour la solution d'analyse de performance de la flotte MCS100 d'Airbus.

## Structure des dashboards

Les dashboards sont organisés selon les cas d'utilisation principaux :

1. **Vue d'ensemble de la flotte** - Aperçu général de l'état de la flotte
2. **Analyse de fiabilité des composants** - Métriques MTBF et taux de défaillance
3. **Optimisation de la maintenance** - Intervalles de maintenance optimaux
4. **Détection d'anomalies** - Visualisation des anomalies détectées
5. **Comparaison des performances** - Analyse comparative entre compagnies aériennes
6. **Impact des modifications techniques** - Évaluation de l'impact sur la fiabilité

## Installation

Les dashboards sont automatiquement provisionnés lors du démarrage de Grafana via le volume Docker configuré dans le fichier docker-compose.yml.

## Personnalisation

Pour personnaliser les dashboards, vous pouvez :
1. Modifier les fichiers JSON directement
2. Utiliser l'interface Grafana pour modifier les dashboards et exporter les configurations
3. Ajouter de nouveaux dashboards en créant de nouveaux fichiers JSON dans ce répertoire
