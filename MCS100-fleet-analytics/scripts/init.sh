#!/bin/bash
# Script d'initialisation pour MCS100-fleet-analytics
# Ce script initialise l'environnement de développement et les données de test

# Couleurs pour les messages
YELLOW='\033[1;33m'
GREEN='\033[1;32m'
RED='\033[1;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Initialisation de l'environnement MCS100-fleet-analytics...${NC}"

# Vérification des prérequis
echo -e "${YELLOW}Vérification des prérequis...${NC}"

# Vérifier si Docker est installé
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker n'est pas installé. Veuillez l'installer avant de continuer.${NC}"
    exit 1
fi

# Vérifier si Docker Compose est installé
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose n'est pas installé. Veuillez l'installer avant de continuer.${NC}"
    exit 1
fi

echo -e "${GREEN}Tous les prérequis sont satisfaits.${NC}"

# Création des répertoires nécessaires
echo -e "${YELLOW}Création des répertoires nécessaires...${NC}"
mkdir -p data/timescaledb
mkdir -p data/mongodb
mkdir -p data/redis
mkdir -p data/minio
mkdir -p data/grafana
mkdir -p data/metabase
mkdir -p data/prometheus
mkdir -p logs/airflow
mkdir -p logs/spark
mkdir -p logs/fastapi

echo -e "${GREEN}Répertoires créés avec succès.${NC}"

# Configuration des permissions
echo -e "${YELLOW}Configuration des permissions...${NC}"
chmod -R 777 data
chmod -R 777 logs

echo -e "${GREEN}Permissions configurées avec succès.${NC}"

# Construction des images Docker
echo -e "${YELLOW}Construction des images Docker...${NC}"
cd docker && docker-compose build

if [ $? -ne 0 ]; then
    echo -e "${RED}Erreur lors de la construction des images Docker.${NC}"
    exit 1
fi

echo -e "${GREEN}Images Docker construites avec succès.${NC}"

# Initialisation des données de test
echo -e "${YELLOW}Initialisation des données de test...${NC}"
echo -e "${YELLOW}Cette étape sera effectuée après le démarrage des services.${NC}"
echo -e "${YELLOW}Utilisez 'make init-data' après avoir démarré les services avec 'make up'.${NC}"

# Instructions finales
echo -e "${GREEN}Initialisation terminée avec succès.${NC}"
echo -e "${YELLOW}Pour démarrer les services, exécutez:${NC}"
echo -e "${YELLOW}  make up${NC}"
echo -e "${YELLOW}Pour initialiser les données de test, exécutez:${NC}"
echo -e "${YELLOW}  make init-data${NC}"
echo -e "${YELLOW}Pour plus d'informations, consultez la documentation dans le répertoire docs/${NC}"
