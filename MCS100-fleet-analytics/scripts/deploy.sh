#!/bin/bash
# Script de déploiement pour MCS100 Fleet Analytics
# Ce script déploie la solution complète en utilisant Docker Compose

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Fonction pour vérifier les prérequis
check_prerequisites() {
    log "Vérification des prérequis..."
    
    # Vérification de Docker
    if ! command -v docker &> /dev/null; then
        error "Docker n'est pas installé. Veuillez l'installer avant de continuer."
        exit 1
    fi
    
    # Vérification de Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose n'est pas installé. Veuillez l'installer avant de continuer."
        exit 1
    fi
    
    # Vérification de la version de Docker
    docker_version=$(docker --version | awk '{print $3}' | sed 's/,//')
    if [[ $(echo "$docker_version" | cut -d. -f1) -lt 20 ]]; then
        warning "Version de Docker détectée: $docker_version. Il est recommandé d'utiliser Docker 20.10.0 ou supérieur."
    else
        success "Version de Docker détectée: $docker_version"
    fi
    
    # Vérification de la version de Docker Compose
    compose_version=$(docker-compose --version | awk '{print $3}' | sed 's/,//')
    if [[ $(echo "$compose_version" | cut -d. -f1) -lt 2 ]]; then
        warning "Version de Docker Compose détectée: $compose_version. Il est recommandé d'utiliser Docker Compose 2.0.0 ou supérieur."
    else
        success "Version de Docker Compose détectée: $compose_version"
    fi
    
    # Vérification de l'espace disque
    available_space=$(df -h . | awk 'NR==2 {print $4}')
    log "Espace disque disponible: $available_space"
    
    # Vérification de la mémoire
    total_memory=$(free -h | awk '/^Mem:/ {print $2}')
    log "Mémoire totale: $total_memory"
    
    success "Vérification des prérequis terminée"
}

# Fonction pour configurer l'environnement
setup_environment() {
    log "Configuration de l'environnement..."
    
    # Vérification du fichier .env
    if [ ! -f "docker/.env" ]; then
        log "Fichier .env non trouvé, création à partir du modèle..."
        if [ -f "docker/.env.example" ]; then
            cp docker/.env.example docker/.env
            success "Fichier .env créé à partir du modèle"
        else
            error "Fichier .env.example non trouvé. Impossible de créer le fichier .env."
            exit 1
        fi
    else
        log "Fichier .env existant trouvé"
    fi
    
    # Création des répertoires nécessaires
    log "Création des répertoires nécessaires..."
    mkdir -p data/minio
    mkdir -p data/timescaledb
    mkdir -p data/mongodb
    mkdir -p logs
    mkdir -p backups
    
    success "Configuration de l'environnement terminée"
}

# Fonction pour construire les images Docker
build_images() {
    log "Construction des images Docker..."
    
    # Construction des images avec Docker Compose
    docker-compose -f docker/docker-compose.yml build
    
    if [ $? -eq 0 ]; then
        success "Construction des images Docker terminée"
    else
        error "Erreur lors de la construction des images Docker"
        exit 1
    fi
}

# Fonction pour démarrer les services
start_services() {
    log "Démarrage des services..."
    
    # Démarrage des services avec Docker Compose
    docker-compose -f docker/docker-compose.yml up -d
    
    if [ $? -eq 0 ]; then
        success "Démarrage des services terminé"
    else
        error "Erreur lors du démarrage des services"
        exit 1
    fi
}

# Fonction pour initialiser les bases de données
initialize_databases() {
    log "Initialisation des bases de données..."
    
    # Attente que les bases de données soient prêtes
    log "Attente que les bases de données soient disponibles..."
    sleep 30
    
    # Exécution du script d'initialisation
    python3 scripts/init_db.py --wait
    
    if [ $? -eq 0 ]; then
        success "Initialisation des bases de données terminée"
    else
        error "Erreur lors de l'initialisation des bases de données"
        exit 1
    fi
}

# Fonction pour configurer les connecteurs
configure_connectors() {
    log "Configuration des connecteurs..."
    
    # Attente que tous les services soient prêts
    log "Attente que tous les services soient disponibles..."
    sleep 30
    
    # Configuration des connecteurs Spark-TimescaleDB
    log "Configuration du connecteur Spark-TimescaleDB..."
    docker exec mcs100-spark-master bash -c "cp /opt/spark-connector/postgresql-42.5.1.jar /opt/spark/jars/"
    
    # Configuration des connecteurs Airflow
    log "Configuration des connecteurs Airflow..."
    docker exec mcs100-airflow bash -c "pip install apache-airflow-providers-postgres apache-airflow-providers-mongo"
    
    success "Configuration des connecteurs terminée"
}

# Fonction pour vérifier l'état des services
check_services() {
    log "Vérification de l'état des services..."
    
    # Liste des services à vérifier
    services=(
        "mcs100-timescaledb"
        "mcs100-mongodb"
        "mcs100-redis"
        "mcs100-minio"
        "mcs100-spark-master"
        "mcs100-spark-worker"
        "mcs100-airflow"
        "mcs100-fastapi"
        "mcs100-grafana"
        "mcs100-metabase"
        "mcs100-prometheus"
        "mcs100-alertmanager"
    )
    
    # Vérification de chaque service
    for service in "${services[@]}"; do
        if docker ps | grep -q "$service"; then
            success "Service $service en cours d'exécution"
        else
            warning "Service $service non trouvé ou non démarré"
        fi
    done
    
    log "Vérification de l'état des services terminée"
}

# Fonction pour afficher les URLs d'accès
display_access_urls() {
    log "URLs d'accès aux services:"
    echo -e "${GREEN}API FastAPI:${NC} http://localhost:8000/docs"
    echo -e "${GREEN}Grafana:${NC} http://localhost:3000 (admin / mot de passe défini dans .env)"
    echo -e "${GREEN}Metabase:${NC} http://localhost:3030 (admin@mcs100.com / mot de passe défini dans .env)"
    echo -e "${GREEN}Airflow:${NC} http://localhost:8080 (airflow / airflow)"
    echo -e "${GREEN}MinIO:${NC} http://localhost:9001 (identifiants définis dans .env)"
    echo -e "${GREEN}Spark Master UI:${NC} http://localhost:8181"
    echo -e "${GREEN}Prometheus:${NC} http://localhost:9090"
    echo -e "${GREEN}Alertmanager:${NC} http://localhost:9093"
}

# Fonction pour générer des données de test
generate_test_data() {
    log "Génération des données de test..."
    
    # Exécution du script de génération de données
    python3 data/generate_test_data.py
    
    if [ $? -eq 0 ]; then
        success "Génération des données de test terminée"
    else
        error "Erreur lors de la génération des données de test"
        exit 1
    fi
}

# Fonction pour préparer les jeux de données de démonstration
prepare_demo_data() {
    log "Préparation des jeux de données de démonstration..."
    
    # Exécution du script de préparation des données de démonstration
    python3 scripts/prepare_demo_data.py
    
    if [ $? -eq 0 ]; then
        success "Préparation des jeux de données de démonstration terminée"
    else
        error "Erreur lors de la préparation des jeux de données de démonstration"
        exit 1
    fi
}

# Fonction principale
main() {
    log "Démarrage du déploiement de MCS100 Fleet Analytics..."
    
    # Traitement des arguments
    GENERATE_DATA=false
    PREPARE_DEMO=false
    HIGH_AVAILABILITY=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --generate-data)
                GENERATE_DATA=true
                shift
                ;;
            --prepare-demo)
                PREPARE_DEMO=true
                shift
                ;;
            --ha)
                HIGH_AVAILABILITY=true
                shift
                ;;
            *)
                warning "Option inconnue: $1"
                shift
                ;;
        esac
    done
    
    # Exécution des étapes de déploiement
    check_prerequisites
    setup_environment
    build_images
    start_services
    initialize_databases
    configure_connectors
    check_services
    
    # Génération de données si demandé
    if [ "$GENERATE_DATA" = true ]; then
        generate_test_data
    fi
    
    # Préparation des données de démonstration si demandé
    if [ "$PREPARE_DEMO" = true ]; then
        prepare_demo_data
    fi
    
    # Affichage des URLs d'accès
    display_access_urls
    
    success "Déploiement de MCS100 Fleet Analytics terminé avec succès!"
}

# Exécution de la fonction principale
main "$@"
