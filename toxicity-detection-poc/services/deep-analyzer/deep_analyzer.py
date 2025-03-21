#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module d'analyse approfondie des messages pour la détection de toxicité
Utilise PySpark et des modèles NLP avancés pour analyser le contexte des messages
"""

import os
import json
import time
import logging
import mlflow
import numpy as np
import pandas as pd
from kafka import KafkaConsumer, KafkaProducer
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from pyspark.sql import SparkSession
from pyspark.ml import Pipeline
from pyspark.ml.feature import HashingTF, IDF, Tokenizer
from pyspark.ml.classification import LogisticRegression

# Configuration du logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration Kafka
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "192.168.229.167:9092")
NLP_ANALYSIS_REQUIRED_TOPIC = os.getenv("NLP_ANALYSIS_REQUIRED_TOPIC", "nlp-analysis-required")
NLP_ANALYSIS_RESULTS_TOPIC = os.getenv("NLP_ANALYSIS_RESULTS_TOPIC", "nlp-analysis-results")
MODERATION_REQUIRED_TOPIC = os.getenv("MODERATION_REQUIRED_TOPIC", "moderation-required")

# Configuration MLflow
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://192.168.229.167:5000")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

# Configuration MinIO
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "192.168.229.167:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
os.environ["AWS_ACCESS_KEY_ID"] = MINIO_ACCESS_KEY
os.environ["AWS_SECRET_ACCESS_KEY"] = MINIO_SECRET_KEY
os.environ["MLFLOW_S3_ENDPOINT_URL"] = f"http://{MINIO_ENDPOINT}"

# Seuils de décision
TOXICITY_THRESHOLD = float(os.getenv("TOXICITY_THRESHOLD", "0.7"))
UNCERTAINTY_THRESHOLD = float(os.getenv("UNCERTAINTY_THRESHOLD", "0.1"))

class DeepAnalyzer:
    """Classe pour l'analyse approfondie des messages potentiellement toxiques"""
    
    def __init__(self):
        """Initialisation de l'analyseur"""
        self.spark = self._create_spark_session()
        self.transformer_model = self._load_transformer_model()
        self.spark_model = self._load_spark_model()
        self.consumer = self._create_kafka_consumer()
        self.producer = self._create_kafka_producer()
        logger.info("Analyseur profond initialisé avec succès")
    
    def _create_spark_session(self):
        """Crée une session Spark"""
        return SparkSession.builder \
            .appName("DeepToxicityAnalyzer") \
            .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.2") \
            .getOrCreate()
    
    def _load_transformer_model(self):
        """Charge le modèle Transformer pour l'analyse NLP"""
        try:
            # Essayer de charger le modèle depuis MLflow
            model_uri = self._get_latest_model_uri("toxicity-transformer")
            if model_uri:
                logger.info(f"Chargement du modèle Transformer depuis MLflow: {model_uri}")
                # Dans un cas réel, on utiliserait mlflow.pytorch.load_model()
                # Pour le POC, on utilise un modèle pré-entraîné de HuggingFace
                model_name = "distilbert-base-uncased-finetuned-sst-2-english"  # Exemple
                tokenizer = AutoTokenizer.from_pretrained(model_name)
                model = AutoModelForSequenceClassification.from_pretrained(model_name)
                return {"tokenizer": tokenizer, "model": model}
            else:
                # Fallback: utiliser un modèle pré-entraîné
                logger.info("Modèle non trouvé dans MLflow, utilisation d'un modèle pré-entraîné")
                model_name = "distilbert-base-uncased-finetuned-sst-2-english"  # Exemple
                tokenizer = AutoTokenizer.from_pretrained(model_name)
                model = AutoModelForSequenceClassification.from_pretrained(model_name)
                return {"tokenizer": tokenizer, "model": model}
        except Exception as e:
            logger.error(f"Erreur lors du chargement du modèle Transformer: {e}")
            return None
    
    def _load_spark_model(self):
        """Charge le modèle Spark ML pour l'analyse contextuelle"""
        try:
            # Essayer de charger le modèle depuis MLflow
            model_uri = self._get_latest_model_uri("toxicity-spark")
            if model_uri:
                logger.info(f"Chargement du modèle Spark depuis MLflow: {model_uri}")
                # Dans un cas réel, on utiliserait mlflow.spark.load_model()
                # Pour le POC, on crée un pipeline simple
                tokenizer = Tokenizer(inputCol="text", outputCol="words")
                hashingTF = HashingTF(inputCol="words", outputCol="features", numFeatures=1000)
                lr = LogisticRegression(maxIter=10, regParam=0.001)
                pipeline = Pipeline(stages=[tokenizer, hashingTF, lr])
                return pipeline
            else:
                # Fallback: créer un pipeline simple
                logger.info("Modèle non trouvé dans MLflow, création d'un pipeline simple")
                tokenizer = Tokenizer(inputCol="text", outputCol="words")
                hashingTF = HashingTF(inputCol="words", outputCol="features", numFeatures=1000)
                lr = LogisticRegression(maxIter=10, regParam=0.001)
                pipeline = Pipeline(stages=[tokenizer, hashingTF, lr])
                return pipeline
        except Exception as e:
            logger.error(f"Erreur lors du chargement du modèle Spark: {e}")
            return None
    
    def _get_latest_model_uri(self, model_name):
        """Récupère l'URI du dernier modèle enregistré dans MLflow"""
        try:
            client = mlflow.tracking.MlflowClient()
            latest_version = 1  # Simplification pour le POC
            model_uri = f"models:/{model_name}/{latest_version}"
            return model_uri
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du modèle depuis MLflow: {e}")
            return None
    
    def _create_kafka_consumer(self):
        """Crée un consommateur Kafka"""
        try:
            consumer = KafkaConsumer(
                NLP_ANALYSIS_REQUIRED_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                auto_offset_reset='latest',
                enable_auto_commit=True,
                group_id='deep-analyzer',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            logger.info(f"Consommateur Kafka connecté à {KAFKA_BOOTSTRAP_SERVERS}")
            return consumer
        except Exception as e:
            logger.error(f"Erreur lors de la création du consommateur Kafka: {e}")
            return None
    
    def _create_kafka_producer(self):
        """Crée un producteur Kafka"""
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda v: v.encode('utf-8') if v else None
            )
            logger.info(f"Producteur Kafka connecté à {KAFKA_BOOTSTRAP_SERVERS}")
            return producer
        except Exception as e:
            logger.error(f"Erreur lors de la création du producteur Kafka: {e}")
            return None
    
    def analyze_with_transformer(self, text):
        """Analyse un texte avec le modèle Transformer"""
        if not self.transformer_model:
            logger.warning("Modèle Transformer non disponible")
            return 0.5, 0.5  # Valeurs par défaut
        
        try:
            tokenizer = self.transformer_model["tokenizer"]
            model = self.transformer_model["model"]
            
            # Tokenisation et préparation des entrées
            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            
            # Prédiction
            with torch.no_grad():
                outputs = model(**inputs)
                scores = torch.nn.functional.softmax(outputs.logits, dim=1)
                
            # Pour un modèle binaire (positif/négatif), on considère le score négatif comme toxicité
            toxicity_score = float(scores[0][0].item())
            
            # Calcul de l'incertitude (simplification)
            uncertainty = 1.0 - abs(toxicity_score - 0.5) * 2
            
            return toxicity_score, uncertainty
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse avec Transformer: {e}")
            return 0.5, 0.5  # Valeurs par défaut en cas d'erreur
    
    def analyze_with_context(self, message):
        """Analyse un message en tenant compte du contexte"""
        # Extraction des informations contextuelles
        content = message.get("content", "")
        is_friends = message.get("is_friends", {})
        metadata = message.get("metadata", {})
        
        # Facteurs contextuels qui peuvent influencer la décision
        context_factors = {
            "friends_ratio": sum(1 for v in is_friends.values() if v) / max(1, len(is_friends)),
            "message_length": len(content),
            "has_game_context": 1 if metadata.get("game_context") else 0
        }
        
        # Analyse du texte avec le modèle Transformer
        toxicity_score, uncertainty = self.analyze_with_transformer(content)
        
        # Ajustement du score en fonction du contexte
        # Si ce sont des amis, on est plus tolérant
        if context_factors["friends_ratio"] > 0.5:
            toxicity_score = max(0, toxicity_score - 0.2)
            uncertainty = max(0, uncertainty - 0.1)
        
        # Si le message est très court, on augmente l'incertitude
        if context_factors["message_length"] < 5:
            uncertainty = min(1.0, uncertainty + 0.2)
        
        # Si on a du contexte de jeu, on peut mieux interpréter
        if context_factors["has_game_context"]:
            uncertainty = max(0, uncertainty - 0.1)
        
        return toxicity_score, uncertainty
    
    def process_message(self, message):
        """Traite un message et détermine s'il est toxique"""
        try:
            # Analyse du message avec contexte
            toxicity_score, uncertainty = self.analyze_with_context(message)
            
            # Ajouter les résultats d'analyse au message
            message["deep_analysis"] = {
                "toxicity_score": toxicity_score,
                "uncertainty": uncertainty,
                "timestamp": int(time.time() * 1000)
            }
            
            # Déterminer la destination du message
            if uncertainty > UNCERTAINTY_THRESHOLD:
                # Message trop ambigu, nécessite une modération humaine
                message["deep_analysis"]["decision"] = "NEEDS_MODERATION"
                return message, MODERATION_REQUIRED_TOPIC
            elif toxicity_score > TOXICITY_THRESHOLD:
                # Message toxique
                message["deep_analysis"]["decision"] = "TOXIC"
                return message, NLP_ANALYSIS_RESULTS_TOPIC
            else:
                # Message acceptable
                message["deep_analysis"]["decision"] = "OK"
                return message, NLP_ANALYSIS_RESULTS_TOPIC
                
        except Exception as e:
            logger.error(f"Erreur lors du traitement du message: {e}")
            # En cas d'erreur, envoyer pour modération humaine
            message["deep_analysis"] = {
                "error": str(e),
                "decision": "NEEDS_MODERATION",
                "timestamp": int(time.time() * 1000)
            }
            return message, MODERATION_REQUIRED_TOPIC
    
    def send_to_kafka(self, message, topic):
        """Envoie un message à un topic Kafka"""
        if not self.producer:
            logger.error("Producteur Kafka non disponible")
            return False
        
        try:
            message_id = message.get("message_id", str(time.time()))
            future = self.producer.send(
                topic=topic,
                key=message_id,
                value=message
            )
            result = future.get(timeout=10)
            logger.info(f"Message envoyé à {topic}: {message_id}, partition: {result.partition}, offset: {result.offset}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du message à Kafka: {e}")
            return False
    
    def run(self):
        """Exécute l'analyseur en continu"""
        if not self.consumer:
            logger.error("Consommateur Kafka non disponible")
            return
        
        logger.info(f"Démarrage de l'analyseur profond, écoute sur {NLP_ANALYSIS_REQUIRED_TOPIC}")
        
        try:
            for record in self.consumer:
                message = record.value
                logger.info(f"Message reçu: {message.get('message_id', 'unknown')}")
                
                # Traiter le message
                processed_message, destination_topic = self.process_message(message)
                
                # Envoyer le message traité
                self.send_to_kafka(processed_message, destination_topic)
                
        except KeyboardInterrupt:
            logger.info("Arrêt de l'analyseur profond")
        except Exception as e:
            logger.error(f"Erreur dans la boucle principale: {e}")
        finally:
            # Fermer les connexions
            if self.consumer:
                self.consumer.close()
            if self.producer:
                self.producer.close()
            if self.spark:
                self.spark.stop()

if __name__ == "__main__":
    analyzer = DeepAnalyzer()
    analyzer.run()
