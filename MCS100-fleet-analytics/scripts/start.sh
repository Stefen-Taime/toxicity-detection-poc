#!/bin/bash

# Script de démarrage pour MCS100-fleet-analytics
# Ce script démarre tous les services Docker et initialise les bases de données

# Couleurs pour les messages
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Démarrage de MCS100-fleet-analytics...${NC}"

# Vérification de la présence de Docker et Docker Compose
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker n'est pas installé. Veuillez l'installer avant de continuer.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose n'est pas installé. Veuillez l'installer avant de continuer.${NC}"
    exit 1
fi

# Vérification de la présence du fichier .env
if [ ! -f "docker/.env" ]; then
    echo -e "${YELLOW}Fichier .env non trouvé. Création à partir du modèle...${NC}"
    cp docker/.env.example docker/.env
    echo -e "${GREEN}Fichier .env créé avec succès.${NC}"
fi

# Démarrage des services Docker
echo -e "${YELLOW}Démarrage des services Docker...${NC}"
docker-compose -f docker/docker-compose.yml up -d

# Vérification du démarrage des services
echo -e "${YELLOW}Vérification du démarrage des services...${NC}"
sleep 10

# Vérification de TimescaleDB
if docker ps | grep -q "timescaledb"; then
    echo -e "${GREEN}TimescaleDB démarré avec succès.${NC}"
else
    echo -e "${RED}Erreur lors du démarrage de TimescaleDB.${NC}"
    exit 1
fi

# Vérification de MongoDB
if docker ps | grep -q "mongodb"; then
    echo -e "${GREEN}MongoDB démarré avec succès.${NC}"
else
    echo -e "${RED}Erreur lors du démarrage de MongoDB.${NC}"
    exit 1
fi

# Vérification de MinIO
if docker ps | grep -q "minio"; then
    echo -e "${GREEN}MinIO démarré avec succès.${NC}"
else
    echo -e "${RED}Erreur lors du démarrage de MinIO.${NC}"
    exit 1
fi

# Vérification d'Airflow
if docker ps | grep -q "airflow-webserver"; then
    echo -e "${GREEN}Airflow démarré avec succès.${NC}"
else
    echo -e "${RED}Erreur lors du démarrage d'Airflow.${NC}"
    exit 1
fi

# Initialisation des bases de données
echo -e "${YELLOW}Initialisation des bases de données...${NC}"
docker exec -it mcs100-fleet-analytics-airflow-worker python /opt/airflow/scripts/init_db.py

# Génération des données de test
echo -e "${YELLOW}Génération des données de test...${NC}"
docker exec -it mcs100-fleet-analytics-airflow-worker python /opt/airflow/scripts/generate_test_data.py

echo -e "${GREEN}MCS100-fleet-analytics démarré avec succès.${NC}"
echo -e "${YELLOW}Interfaces disponibles:${NC}"
echo -e "  - Airflow: http://localhost:8080"
echo -e "  - Grafana: http://localhost:3000"
echo -e "  - Metabase: http://localhost:3001"
echo -e "  - FastAPI: http://localhost:8000/docs"
echo -e "  - MinIO: http://localhost:9001"
echo -e "  - PgAdmin: http://localhost:5050"
echo -e "  - MongoDB Express: http://localhost:8081"
echo -e "  - Redis Commander: http://localhost:8082"
echo -e "  - Prometheus: http://localhost:9090"
echo -e "  - Alertmanager: http://localhost:9093"
