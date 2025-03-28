# Makefile pour MCS100-fleet-analytics

# Variables
DOCKER_COMPOSE = docker-compose
PROJECT_NAME = mcs100-fleet-analytics

# Couleurs pour les messages
GREEN = \033[0;32m
YELLOW = \033[0;33m
RED = \033[0;31m
NC = \033[0m # No Color

.PHONY: help up down build init logs clean test generate-data deploy-local deploy-prod

# Aide
help:
	@echo "${YELLOW}MCS100-fleet-analytics - Solution d'analyse de performance pour la flotte d'avions MCS100${NC}"
	@echo ""
	@echo "${GREEN}Commandes disponibles:${NC}"
	@echo "  ${YELLOW}make help${NC}          - Affiche cette aide"
	@echo "  ${YELLOW}make up${NC}            - Démarre tous les services"
	@echo "  ${YELLOW}make down${NC}          - Arrête tous les services"
	@echo "  ${YELLOW}make build${NC}         - Construit les images Docker"
	@echo "  ${YELLOW}make init${NC}          - Initialise les bases de données et charge les données de test"
	@echo "  ${YELLOW}make logs${NC}          - Affiche les logs de tous les services"
	@echo "  ${YELLOW}make clean${NC}         - Nettoie les volumes et les images Docker"
	@echo "  ${YELLOW}make test${NC}          - Exécute les tests"
	@echo "  ${YELLOW}make generate-data${NC} - Génère des données de test"
	@echo "  ${YELLOW}make deploy-local${NC}  - Déploie la solution en local"
	@echo "  ${YELLOW}make deploy-prod${NC}   - Déploie la solution en production"
	@echo ""
	@echo "${GREEN}Ordre d'exécution recommandé:${NC}"
	@echo "  1. ${YELLOW}make build${NC}         - Construction des images Docker"
	@echo "  2. ${YELLOW}make up${NC}            - Démarrage des services"
	@echo "  3. ${YELLOW}make init${NC}          - Initialisation des bases de données"
	@echo "  4. ${YELLOW}make generate-data${NC} - Génération des données de test"
	@echo ""
	@echo "${GREEN}Pour un démarrage rapide:${NC}"
	@echo "  ${YELLOW}make deploy-local${NC}     - Exécute build, up, init et generate-data en séquence"

# Démarrer tous les services
up:
	@echo "${GREEN}Démarrage des services...${NC}"
	@$(DOCKER_COMPOSE) -p $(PROJECT_NAME) -f docker/docker-compose.yml up -d
	@echo "${GREEN}Services démarrés avec succès.${NC}"
	@echo "${YELLOW}Interfaces disponibles:${NC}"
	@echo "  - Airflow: http://localhost:8080"
	@echo "  - Grafana: http://localhost:3000"
	@echo "  - Metabase: http://localhost:3001"
	@echo "  - FastAPI: http://localhost:8000/docs"
	@echo "  - MinIO: http://localhost:9001"
	@echo "  - PgAdmin: http://localhost:5050"
	@echo "  - MongoDB Express: http://localhost:8081"
	@echo "  - Redis Commander: http://localhost:8082"
	@echo "  - Prometheus: http://localhost:9090"
	@echo "  - Alertmanager: http://localhost:9093"

# Arrêter tous les services
down:
	@echo "${YELLOW}Arrêt des services...${NC}"
	@$(DOCKER_COMPOSE) -p $(PROJECT_NAME) -f docker/docker-compose.yml down
	@echo "${GREEN}Services arrêtés avec succès.${NC}"

# Construire les images Docker
build:
	@echo "${YELLOW}Construction des images Docker...${NC}"
	@$(DOCKER_COMPOSE) -p $(PROJECT_NAME) -f docker/docker-compose.yml build
	@echo "${GREEN}Images Docker construites avec succès.${NC}"

# Initialiser les bases de données et charger les données de test
init:
	@echo "${YELLOW}Initialisation des bases de données...${NC}"
	@docker exec -it $(PROJECT_NAME)-airflow-worker python /opt/airflow/scripts/init_db.py
	@echo "${GREEN}Bases de données initialisées avec succès.${NC}"

# Afficher les logs de tous les services
logs:
	@$(DOCKER_COMPOSE) -p $(PROJECT_NAME) -f docker/docker-compose.yml logs -f

# Nettoyer les volumes et les images Docker
clean:
	@echo "${RED}Attention: Cette opération va supprimer tous les volumes et les données.${NC}"
	@read -p "Êtes-vous sûr de vouloir continuer? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo ""; \
		echo "${YELLOW}Nettoyage des volumes et des images Docker...${NC}"; \
		$(DOCKER_COMPOSE) -p $(PROJECT_NAME) -f docker/docker-compose.yml down -v --rmi all; \
		echo "${GREEN}Nettoyage terminé avec succès.${NC}"; \
	else \
		echo ""; \
		echo "${YELLOW}Opération annulée.${NC}"; \
	fi

# Exécuter les tests
test:
	@echo "${YELLOW}Exécution des tests...${NC}"
	@docker exec -it $(PROJECT_NAME)-airflow-worker pytest /opt/airflow/tests
	@echo "${GREEN}Tests exécutés avec succès.${NC}"

# Générer des données de test
generate-data:
	@echo "${YELLOW}Génération des données de test...${NC}"
	@docker exec -it $(PROJECT_NAME)-airflow-worker python /opt/airflow/scripts/generate_test_data.py
	@echo "${GREEN}Données de test générées avec succès.${NC}"

# Déployer la solution en local (build + up + init + generate-data)
deploy-local:
	@echo "${YELLOW}Déploiement de la solution en local...${NC}"
	@$(MAKE) build
	@$(MAKE) up
	@echo "${YELLOW}Attente du démarrage complet des services...${NC}"
	@sleep 30
	@$(MAKE) init
	@$(MAKE) generate-data
	@echo "${GREEN}Solution déployée avec succès en local.${NC}"

# Déployer la solution en production
deploy-prod:
	@echo "${RED}Attention: Cette opération va déployer la solution en production.${NC}"
	@read -p "Êtes-vous sûr de vouloir continuer? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo ""; \
		echo "${YELLOW}Déploiement de la solution en production...${NC}"; \
		$(DOCKER_COMPOSE) -p $(PROJECT_NAME) -f docker/docker-compose.prod.yml up -d; \
		echo "${GREEN}Solution déployée avec succès en production.${NC}"; \
	else \
		echo ""; \
		echo "${YELLOW}Opération annulée.${NC}"; \
	fi
