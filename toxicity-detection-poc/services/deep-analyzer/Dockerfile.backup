FROM python:3.9-slim

# Installation des dépendances système, y compris Java
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    default-jdk \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Définir JAVA_HOME
ENV JAVA_HOME=/usr/lib/jvm/default-java
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Définir la variable d'environnement pour Spark/MLlib
ENV PYSPARK_PYTHON=python3
ENV PYSPARK_DRIVER_PYTHON=python3

WORKDIR /app

# Copier requirements.txt, puis installer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste de votre code source
COPY . .

# Commande de démarrage
CMD ["python", "deep_analyzer.py"]