# MCS100-fleet-analytics

## Solution opérationnelle d'analyse de performance pour la flotte d'avions MCS100 d'Airbus

Cette solution complète permet l'analyse de fiabilité et de performance des avions MCS100 d'Airbus. Elle est entièrement conteneurisée avec Docker et utilise exclusivement des technologies open source.

## Fonctionnalités principales

- Collecte et stockage des données de performance des avions MCS100
- Analyse de la fiabilité des composants et systèmes
- Visualisation des KPIs et métriques importantes
- Génération d'alertes sur les anomalies détectées
- Prédiction des défaillances potentielles

## Architecture

La solution est basée sur une architecture microservices avec les composants suivants :

- **Base de données** : TimescaleDB (extension PostgreSQL) pour le stockage principal des séries temporelles
- **ETL/Ingestion** : Apache Airflow pour l'orchestration et dbt Core pour la transformation
- **Traitement des données** : Apache Spark pour le traitement parallèle des données
- **API** : FastAPI pour exposer les données via REST
- **Visualisation** : Grafana pour les tableaux de bord de métriques temporelles et Metabase pour l'exploration ad-hoc
- **Machine Learning** : Scikit-learn pour la détection d'anomalies et la prédiction des défaillances
- **Monitoring** : Prometheus + Alertmanager pour la surveillance en temps réel

## Cas d'utilisation

1. Analyse de la fiabilité des composants (MTBF, taux de défaillance)
2. Prédiction des intervalles de maintenance optimaux
3. Détection d'anomalies dans les données de vol
4. Analyse comparative des performances entre différentes compagnies aériennes
5. Évaluation de l'impact des modifications techniques sur la fiabilité

## Démarrage rapide

```bash
# Cloner le dépôt
git clone https://github.com/airbus/MCS100-fleet-analytics.git
cd MCS100-fleet-analytics

# Lancer la solution
make up
```

Pour plus de détails, consultez le [Guide d'installation](docs/installation.md) et le [Guide d'utilisation](docs/user_guide.md).
