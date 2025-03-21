# Détection de toxicité en temps réel dans les jeux vidéo

Ce POC (Proof of Concept) implémente un système de détection de toxicité en temps réel pour les jeux vidéo, en utilisant des technologies open source.

## Objectif

Créer un système capable de détecter et de filtrer les messages toxiques dans les chats de jeux vidéo en temps réel, tout en préservant l'expérience utilisateur et en distinguant les plaisanteries amicales des comportements réellement toxiques.

## Architecture

Notre solution remplace les composants propriétaires mentionnés dans l'article original par des alternatives open source :

- **Apache Kafka** (remplaçant Confluent Cloud) pour le transport des messages
- **Apache Flink** pour le traitement en temps réel
- **MLflow + Spark** (remplaçant Databricks) pour l'analyse approfondie et l'entraînement des modèles
- **MinIO** (remplaçant le stockage cloud) pour le stockage des données et modèles
- **FastAPI** pour les API de service
- **Streamlit** pour l'interface de modération humaine

## Fonctionnalités

1. Ingestion de messages en temps réel
2. Classification rapide des messages (OK, Toxique, Nécessite analyse)
3. Analyse approfondie des cas ambigus
4. Intervention humaine pour les cas complexes
5. Apprentissage continu des modèles
6. Interface de modération et de supervision

## Prérequis

- Docker et Docker Compose
- Git (pour cloner ce dépôt)

## Démarrage rapide

```bash
git clone [ce-repo]
cd toxicity-detection-poc
docker-compose up -d
```

Accédez à l'interface de démonstration : http://localhost:8501

## Structure du projet

Consultez le document [ARCHITECTURE.md](ARCHITECTURE.md) pour plus de détails sur la conception du système.
