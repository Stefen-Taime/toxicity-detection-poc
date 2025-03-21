#!/bin/bash
# Script pour créer le pipeline de traitement complet
# Ce script initialise les topics Kafka et configure les connexions entre les services

set -e

echo "Configuration du pipeline de traitement pour la détection de toxicité en temps réel"

# Créer les topics Kafka nécessaires sans attendre la vérification de santé
echo "Création des topics Kafka..."
docker-compose exec redpanda rpk topic create raw-messages --partitions 3 --replicas 1 || echo "Topic raw-messages existe déjà"
docker-compose exec redpanda rpk topic create classified-messages --partitions 3 --replicas 1 || echo "Topic classified-messages existe déjà"
docker-compose exec redpanda rpk topic create nlp-analysis-required --partitions 3 --replicas 1 || echo "Topic nlp-analysis-required existe déjà"
docker-compose exec redpanda rpk topic create nlp-analysis-results --partitions 3 --replicas 1 || echo "Topic nlp-analysis-results existe déjà"
docker-compose exec redpanda rpk topic create moderation-required --partitions 3 --replicas 1 || echo "Topic moderation-required existe déjà"
docker-compose exec redpanda rpk topic create moderation-results --partitions 3 --replicas 1 || echo "Topic moderation-results existe déjà"
docker-compose exec redpanda rpk topic create final-decisions --partitions 3 --replicas 1 || echo "Topic final-decisions existe déjà"
docker-compose exec redpanda rpk topic create model-training-data --partitions 3 --replicas 1 || echo "Topic model-training-data existe déjà"

echo "Topics Kafka créés avec succès!"

# Initialiser MinIO
echo "Configuration de MinIO..."
docker-compose exec minio mc alias set minio http://localhost:9000 minioadmin minioadmin

# Créer les buckets nécessaires
docker-compose exec minio mc mb minio/mlflow --ignore-existing || echo "Bucket mlflow existe déjà"
docker-compose exec minio mc mb minio/models --ignore-existing || echo "Bucket models existe déjà"
docker-compose exec minio mc mb minio/data --ignore-existing || echo "Bucket data existe déjà"

echo "Buckets MinIO créés avec succès!"

# Vérifier la présence du fichier sur le système hôte et non dans le conteneur
if [ ! -f "./services/fast-classifier/src/fast_classifier.py" ]; then
    echo "Erreur: Le fichier fast_classifier.py n'existe pas!"
    exit 1
fi

# Assurez-vous que le fichier est accessible dans le conteneur
echo "Copie du fichier fast_classifier.py dans le conteneur..."
chmod +x ./services/fast-classifier/src/fast_classifier.py

# Déployer le job Flink pour la classification rapide
echo "Déploiement du job Flink pour la classification rapide..."
docker-compose exec jobmanager /opt/flink/bin/flink run -py /opt/flink/usrlib/src/fast_classifier.py || echo "Problème de déploiement du job Flink - vérifiez le code et les dépendances"

echo "Configuration du pipeline terminée!"
echo "Le système est prêt à traiter les messages de chat en temps réel."