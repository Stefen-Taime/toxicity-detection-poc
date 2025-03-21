mkdir -p /home/ubuntu/toxicity-detection-poc/docs/images

mkdir -p /home/ubuntu/toxicity-detection-poc/services/{game-message-proxy,fast-classifier,deep-analyzer,decision-manager,moderation-ui,game-simulator,mlflow}

mkdir -p /home/ubuntu/toxicity-detection-poc/models/{fast,deep}
mkdir -p /home/ubuntu/toxicity-detection-poc/data/{raw,processed,training}
mkdir -p ~/toxicity-detection-poc/services/fast-classifier/models
touch ~/toxicity-detection-poc/services/fast-classifier/models/.gitkeep
