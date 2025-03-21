# Architecture du système de détection de toxicité en temps réel

## Vue d'ensemble

Notre architecture remplace les solutions propriétaires (Confluent Cloud et Databricks) par des alternatives open source tout en conservant les fonctionnalités essentielles du système original.

![Architecture du système](./docs/images/architecture.png)

## Composants principaux

### 1. Ingestion des messages (Proxy d'ingestion)
- **Service**: `game-message-proxy`
- **Technologie**: FastAPI
- **Rôle**: Recevoir les messages des serveurs de jeu et les publier dans Kafka/Redpanda

### 2. Transport de messages
- **Service**: `redpanda` (alternative à Apache Kafka)
- **Technologie**: Redpanda (compatible Kafka API)
- **Rôle**: Stocker et transmettre les messages entre les composants du système
- **Topics**:
  - `raw-messages`: Messages bruts entrants
  - `classified-messages`: Messages avec classification préliminaire
  - `nlp-analysis-required`: Messages nécessitant une analyse approfondie
  - `nlp-analysis-results`: Résultats de l'analyse approfondie
  - `moderation-required`: Messages nécessitant une intervention humaine
  - `moderation-results`: Résultats de la modération humaine
  - `final-decisions`: Décisions finales sur les messages
  - `model-training-data`: Données pour l'entraînement des modèles

### 3. Classification rapide
- **Service**: `fast-classifier`
- **Technologie**: Apache Flink
- **Rôle**: Classifier rapidement les messages en trois catégories (OK, Toxique, Nécessite analyse)
- **Modèle**: Modèle léger optimisé pour la vitesse (TensorFlow Lite)

### 4. Analyse approfondie
- **Service**: `deep-analyzer`
- **Technologie**: Spark (alternative à Databricks)
- **Rôle**: Analyser en profondeur les messages ambigus avec contexte
- **Modèle**: Modèle NLP plus complexe (Transformer-based)

### 5. Stockage de données
- **Service**: `minio`
- **Technologie**: MinIO (S3 compatible)
- **Rôle**: Stocker les modèles ML, les données d'entraînement et les logs

### 6. Gestion des modèles
- **Service**: `mlflow`
- **Technologie**: MLflow
- **Rôle**: Suivre les expériences, gérer les versions des modèles et orchestrer le déploiement

### 7. Interface de modération
- **Service**: `moderation-ui`
- **Technologie**: Streamlit
- **Rôle**: Interface pour les modérateurs humains

### 8. Gestionnaire de décisions
- **Service**: `decision-manager`
- **Technologie**: Python (FastAPI)
- **Rôle**: Appliquer les règles de modération et envoyer les décisions finales

### 9. Simulateur de jeu (pour le POC)
- **Service**: `game-simulator`
- **Technologie**: Python
- **Rôle**: Simuler des conversations de jeu pour tester le système

## Flux de données

1. Les messages du jeu sont envoyés au proxy d'ingestion
2. Le proxy publie les messages dans le topic `raw-messages` de Redpanda
3. Le classificateur rapide (Flink) consomme les messages et les classe en trois catégories:
   - Messages "OK" → topic `classified-messages` (tag: OK)
   - Messages "Toxiques" → topic `classified-messages` (tag: Toxique)
   - Messages ambigus → topic `nlp-analysis-required`
4. Le service d'analyse approfondie traite les messages ambigus et publie les résultats dans `nlp-analysis-results`
5. Si l'analyse approfondie ne peut pas prendre de décision, le message est envoyé à `moderation-required`
6. Les modérateurs humains examinent ces messages via l'interface et publient leurs décisions dans `moderation-results`
7. Le gestionnaire de décisions combine toutes ces informations et publie la décision finale dans `final-decisions`
8. Les décisions et feedbacks sont utilisés pour améliorer les modèles via le topic `model-training-data`

## Avantages de cette architecture

1. **Haute disponibilité**: Tous les composants peuvent être mis à l'échelle horizontalement
2. **Faible latence**: Classification rapide pour la majorité des messages
3. **Adaptabilité**: Les modèles s'améliorent continuellement grâce aux retours
4. **Open source**: Aucune dépendance à des services propriétaires
5. **Isolation des composants**: Chaque service peut évoluer indépendamment

## Considérations de performance

- Le classificateur rapide est optimisé pour traiter des milliers de messages par seconde
- L'analyse approfondie est conçue pour gérer les cas ambigus sans affecter le flux principal
- La modération humaine est minimisée grâce à l'amélioration continue des modèles
