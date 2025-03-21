#!/bin/bash

set -e

echo "Configuration de MLflow avec MinIO..."

if [ -z "$MLFLOW_S3_ENDPOINT_URL" ]; then
  echo "MLFLOW_S3_ENDPOINT_URL n'est pas défini, utilisation de la valeur par défaut http://minio:9000"
  export MLFLOW_S3_ENDPOINT_URL="http://minio:9000"
fi

if [ -z "$AWS_ACCESS_KEY_ID" ]; then
  echo "AWS_ACCESS_KEY_ID n'est pas défini, utilisation de la valeur par défaut minioadmin"
  export AWS_ACCESS_KEY_ID="minioadmin"
fi

if [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
  echo "AWS_SECRET_ACCESS_KEY n'est pas défini, utilisation de la valeur par défaut minioadmin"
  export AWS_SECRET_ACCESS_KEY="minioadmin"
fi

echo "Vérification du bucket MLflow dans MinIO..."
python3 - << EOF
import boto3
import os
from botocore.client import Config

s3_client = boto3.client(
    's3',
    endpoint_url=os.environ.get('MLFLOW_S3_ENDPOINT_URL', 'http://minio:9000'),
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID', 'minioadmin'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY', 'minioadmin'),
    config=Config(signature_version='s3v4'),
    region_name='us-east-1'
)

# Liste des buckets
response = s3_client.list_buckets()
buckets = [bucket['Name'] for bucket in response['Buckets']]

# Création du bucket mlflow s'il n'existe pas
if 'mlflow' not in buckets:
    print("Création du bucket 'mlflow'...")
    s3_client.create_bucket(Bucket='mlflow')
    print("Bucket 'mlflow' créé avec succès")
else:
    print("Le bucket 'mlflow' existe déjà")
EOF

echo "Démarrage du serveur MLflow..."
mlflow server --host 0.0.0.0 --port 5000 --backend-store-uri /mlflow --default-artifact-root s3://mlflow/
