FROM python:3.9-slim

WORKDIR /app

# Installation des dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source et du script d'entrée
COPY entrypoint.sh .
COPY . .

# Rendre le script d'entrée exécutable
RUN chmod +x entrypoint.sh

# Création du répertoire de stockage MLflow
RUN mkdir -p /mlflow

# Exposition du port
EXPOSE 5000

# Commande de démarrage
ENTRYPOINT ["/app/entrypoint.sh"]
