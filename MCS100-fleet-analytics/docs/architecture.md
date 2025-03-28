# Architecture détaillée de la solution MCS100-fleet-analytics

## Vue d'ensemble

La solution MCS100-fleet-analytics est conçue selon une architecture microservices pour permettre l'analyse de performance et de fiabilité de la flotte d'avions MCS100 d'Airbus. Cette architecture modulaire facilite la scalabilité, la maintenance et l'évolution de la solution.

## Diagramme d'architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Sources de     │     │  Ingestion &    │     │  Stockage       │
│  données        │────▶│  Transformation │────▶│                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
       │                        │                        │
       │                        │                        │
       ▼                        ▼                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Traitement     │     │  Analyse &      │     │  Visualisation  │
│  des données    │────▶│  Prédiction     │────▶│  & API          │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │  Monitoring &   │
                                               │  Alerting       │
                                               └─────────────────┘
```

## Composants principaux

### 1. Sources de données

Les données proviennent de plusieurs sources :

- **Fichiers CSV** (dans MinIO) : Données de vol quotidiennes, cycles d'utilisation, logs de maintenance programmée, relevés de performance
- **Fichiers JSON** (dans MinIO) : Événements de maintenance non programmée, alertes et défaillances systèmes, configurations des composants, télémétrie détaillée
- **API REST** (simulées) : Mises à jour en temps réel, bulletins techniques, données météo, disponibilité des pièces
- **MongoDB** (base de référence) : Catalogue des pièces, arborescence des systèmes, historique des modifications, référentiels des normes

### 2. Ingestion et Transformation

- **Apache Airflow** : Orchestration des pipelines de données avec 5 DAGs principaux
  - `daily_data_ingestion_dag` : Extraction quotidienne des nouvelles données
  - `weekly_reliability_analysis_dag` : Analyse hebdomadaire de la fiabilité
  - `monthly_fleet_performance_dag` : Rapports mensuels de performance
  - `anomaly_detection_dag` : Détection quotidienne d'anomalies
  - `maintenance_optimization_dag` : Optimisation mensuelle des intervalles de maintenance

- **dbt Core** : Transformation des données dans TimescaleDB
  - Modèles de staging pour la préparation des données
  - Modèles intermédiaires pour les transformations complexes
  - Modèles de métriques pour le calcul des KPIs

### 3. Stockage

- **TimescaleDB** (extension PostgreSQL) : Stockage principal pour les séries temporelles
  - Tables hypertables pour les données de performance
  - Tables relationnelles pour les métadonnées et références
  - Optimisations pour les requêtes sur séries temporelles

- **Redis** : Cache et files d'attente
  - Mise en cache des requêtes fréquentes
  - Files d'attente pour les tâches asynchrones

- **MongoDB** : Stockage de données non structurées
  - Catalogue des pièces et composants
  - Configurations des avions
  - Référentiels techniques

- **MinIO** : Stockage objet S3-compatible
  - Données brutes (CSV, JSON)
  - Résultats d'analyse intermédiaires
  - Modèles ML entraînés

### 4. Traitement des données

- **Apache Spark** : Traitement distribué des données
  - Jobs de calcul de fiabilité des composants
  - Analyse statistique des performances
  - Préparation des données pour le ML

### 5. Analyse et Prédiction

- **Scikit-learn** : Modèles de machine learning
  - Détection d'anomalies (Isolation Forest, DBSCAN)
  - Prédiction de défaillances (Random Forest, Gradient Boosting)
  - Optimisation des intervalles de maintenance (Régression)

### 6. Visualisation et API

- **FastAPI** : API REST
  - Endpoints pour l'accès aux données
  - Documentation OpenAPI
  - Authentification et autorisation

- **Grafana** : Tableaux de bord de métriques temporelles
  - Dashboards de performance en temps réel
  - Visualisations des séries temporelles
  - Alertes visuelles

- **Metabase** : Exploration ad-hoc et rapports business
  - Analyses comparatives
  - Rapports de fiabilité
  - Exploration des données

### 7. Monitoring et Alerting

- **Prometheus** : Collecte de métriques
  - Métriques système
  - Métriques applicatives
  - Métriques métier

- **Alertmanager** : Gestion des alertes
  - Définition des règles d'alerte
  - Notification des équipes
  - Escalade des incidents

## Flux de données

### Flux principal

1. Les données brutes sont extraites des différentes sources par Airflow
2. Les données sont chargées dans des tables staging dans TimescaleDB
3. dbt Core transforme les données en modèles intermédiaires et calcule les métriques de base
4. Spark effectue des analyses avancées sur les données transformées
5. Les modèles ML détectent les anomalies et prédisent les défaillances
6. Les résultats sont stockés dans TimescaleDB
7. Les tableaux de bord Grafana et Metabase visualisent les résultats
8. L'API FastAPI expose les données pour l'intégration externe

### Flux de détection d'anomalies

1. Les données de vol sont extraites quotidiennement
2. Spark calcule les statistiques descriptives et les tendances
3. Les modèles ML identifient les déviations par rapport aux comportements normaux
4. Les anomalies détectées sont enregistrées dans TimescaleDB
5. Alertmanager génère des alertes en fonction des seuils configurés
6. Les tableaux de bord affichent les anomalies en temps réel

### Flux de prédiction de défaillances

1. Les données historiques de maintenance sont analysées
2. Les modèles ML sont entraînés sur les patterns de défaillance
3. Les prédictions sont générées pour chaque composant critique
4. Les recommandations de maintenance sont calculées
5. Les résultats sont exposés via l'API et les tableaux de bord

## Intégration des composants

### Intégration Airflow-Spark-dbt

- Airflow orchestre l'exécution des jobs Spark via SparkSubmitOperator
- Les résultats des jobs Spark sont stockés dans TimescaleDB
- dbt Core est exécuté depuis Airflow via DbtRunOperator
- Les modèles dbt transforment les données dans TimescaleDB

### Intégration TimescaleDB-Grafana-Metabase

- Grafana se connecte directement à TimescaleDB pour les visualisations en temps réel
- Metabase utilise TimescaleDB comme source de données pour les rapports business
- Les deux outils partagent les mêmes données mais avec des perspectives différentes

### Intégration FastAPI-Frontend

- FastAPI expose les données via des endpoints REST
- L'authentification est gérée au niveau de l'API
- Les tableaux de bord peuvent consommer les données via l'API ou directement depuis TimescaleDB

## Sécurité

- Authentification pour tous les services
- Communication sécurisée entre les composants
- Isolation des conteneurs Docker
- Gestion des secrets via variables d'environnement

## Scalabilité

- Architecture horizontalement scalable
- Possibilité d'ajouter des workers Spark pour le traitement parallèle
- Partitionnement des données dans TimescaleDB
- Réplication des services critiques

## Déploiement

- Solution entièrement conteneurisée avec Docker
- Configuration via docker-compose.yml
- Variables d'environnement pour la personnalisation
- Scripts d'initialisation pour le démarrage rapide
