#!/bin/bash
# Script d'arrêt pour MCS100 Fleet Analytics
# Ce script arrête tous les services et nettoie l'environnement si demandé

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

# Fonction pour arrêter les services
stop_services() {
    log "Arrêt des services..."
    
    # Arrêt des services avec Docker Compose
    docker-compose -f docker/docker-compose.yml down
    
    if [ $? -eq 0 ]; then
        success "Arrêt des services terminé"
    else
        error "Erreur lors de l'arrêt des services"
        exit 1
    fi
}

# Fonction pour nettoyer l'environnement
clean_environment() {
    log "Nettoyage de l'environnement..."
    
    # Confirmation de l'utilisateur
    read -p "Cette opération va supprimer toutes les données. Êtes-vous sûr ? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        warning "Opération annulée"
        exit 0
    fi
    
    # Arrêt des services avec suppression des volumes
    docker-compose -f docker/docker-compose.yml down -v
    
    # Suppression des répertoires de données
    log "Suppression des répertoires de données..."
    rm -rf data/minio/*
    rm -rf data/timescaledb/*
    rm -rf data/mongodb/*
    rm -rf logs/*
    
    # Suppression des images Docker
    log "Suppression des images Docker..."
    docker rmi $(docker images --filter "reference=mcs100-*" -q) 2>/dev/null || true
    
    success "Nettoyage de l'environnement terminé"
}

# Fonction principale
main() {
    log "Arrêt de MCS100 Fleet Analytics..."
    
    # Traitement des arguments
    CLEAN=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --clean)
                CLEAN=true
                shift
                ;;
            *)
                warning "Option inconnue: $1"
                shift
                ;;
        esac
    done
    
    # Arrêt des services
    stop_services
    
    # Nettoyage de l'environnement si demandé
    if [ "$CLEAN" = true ]; then
        clean_environment
    fi
    
    success "Arrêt de MCS100 Fleet Analytics terminé avec succès!"
}

# Exécution de la fonction principale
main "$@"
