FROM bitnami/spark:3.4.1

# Métadonnées
LABEL maintainer="Airbus MCS100 Team"
LABEL description="Image Spark pour MCS100-fleet-analytics"
LABEL version="1.0"

USER root

# Installation des dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    python3-dev \
    python3-pip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Installation des bibliothèques Python pour ML et connecteurs
RUN pip3 install --no-cache-dir \
    numpy==1.24.3 \
    pandas==2.0.3 \
    scikit-learn==1.3.0 \
    matplotlib==3.7.2 \
    seaborn==0.12.2 \
    pymongo==4.5.0 \
    psycopg2-binary==2.9.6 \
    minio==7.1.15 \
    redis==4.6.0 \
    pyspark==3.4.1 \
    findspark==2.0.1

# Installation du connecteur JDBC pour PostgreSQL/TimescaleDB
RUN mkdir -p /opt/spark/jars
RUN wget https://jdbc.postgresql.org/download/postgresql-42.6.0.jar -O /opt/spark/jars/postgresql-42.6.0.jar

# Création des répertoires pour les jobs et les données
RUN mkdir -p /opt/spark/jobs /opt/spark/data

# Configuration de Spark
COPY ./config/spark-defaults.conf /opt/bitnami/spark/conf/spark-defaults.conf

# Exposition des ports
EXPOSE 7077 8080 8081

USER 1001
