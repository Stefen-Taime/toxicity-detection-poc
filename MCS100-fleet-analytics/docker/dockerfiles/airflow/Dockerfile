FROM apache/airflow:2.7.1-python3.10

# Métadonnées
LABEL maintainer="Airbus MCS100 Team"
LABEL description="Image Airflow pour MCS100-fleet-analytics"
LABEL version="1.0"

USER root

# Installation des dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    wget \
    curl \
    software-properties-common \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Installation de dbt Core
RUN pip install --no-cache-dir \
    dbt-core==1.5.2 \
    dbt-postgres==1.5.2 \
    airflow-dbt==0.4.0

# Installation des connecteurs pour Spark, MongoDB, MinIO
RUN pip install --no-cache-dir \
    apache-airflow-providers-apache-spark==4.1.0 \
    apache-airflow-providers-mongo==3.2.0 \
    apache-airflow-providers-amazon==8.1.0 \
    pymongo==4.5.0 \
    minio==7.1.15 \
    psycopg2-binary==2.9.6 \
    redis==4.6.0 \
    pandas==2.0.3 \
    numpy==1.24.3 \
    scikit-learn==1.3.0 \
    matplotlib==3.7.2 \
    seaborn==0.12.2 \
    plotly==5.15.0 \
    pyspark==3.4.1 \
    faker==18.13.0

USER airflow

# Création des répertoires nécessaires
RUN mkdir -p /opt/airflow/dags /opt/airflow/plugins /opt/airflow/config /opt/airflow/dbt /opt/airflow/data /opt/airflow/scripts

# Configuration de dbt
COPY ./dbt/profiles.yml /opt/airflow/.dbt/profiles.yml

# Exposition des ports
EXPOSE 8080
