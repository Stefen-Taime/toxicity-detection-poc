# Créer un répertoire pour les images d'architecture
mkdir -p /home/ubuntu/toxicity-detection-poc/docs/images

# Créer les répertoires pour chaque service
mkdir -p /home/ubuntu/toxicity-detection-poc/services/{game-message-proxy,fast-classifier,deep-analyzer,decision-manager,moderation-ui,game-simulator,mlflow}

# Créer les répertoires pour les modèles et les données
mkdir -p /home/ubuntu/toxicity-detection-poc/models/{fast,deep}
mkdir -p /home/ubuntu/toxicity-detection-poc/data/{raw,processed,training}
mkdir -p ~/toxicity-detection-poc/services/fast-classifier/models
touch ~/toxicity-detection-poc/services/fast-classifier/models/.gitkeep
