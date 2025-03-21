#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de classification rapide des messages pour la détection de toxicité
Utilise Apache Flink pour le traitement en temps réel des messages
"""

import os
import json
import time
import pickle
import tempfile
import re
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment, EnvironmentSettings
from pyflink.common.typeinfo import Types
from pyflink.datastream.connectors import FlinkKafkaConsumer, FlinkKafkaProducer
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream.functions import MapFunction, RuntimeContext, FlatMapFunction

# TensorFlow warning suppression - avoid warnings about CPU instructions
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Configuration des topics Kafka
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
RAW_MESSAGES_TOPIC = os.getenv("RAW_MESSAGES_TOPIC", "raw-messages")
CLASSIFIED_MESSAGES_TOPIC = os.getenv("CLASSIFIED_MESSAGES_TOPIC", "classified-messages")
NLP_ANALYSIS_REQUIRED_TOPIC = os.getenv("NLP_ANALYSIS_REQUIRED_TOPIC", "nlp-analysis-required")

# Configuration MinIO
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "mlflow")
MINIO_MODEL_PATH = os.getenv("MINIO_MODEL_PATH", "models/fast/fast_toxicity_model.tflite")
MINIO_VECTORIZER_PATH = os.getenv("MINIO_VECTORIZER_PATH", "models/fast/vectorizer.pkl")
MINIO_SECURE = os.getenv("MINIO_SECURE", "False").lower() == "true"

# Seuils de classification
TOXICITY_THRESHOLD = float(os.getenv("TOXICITY_THRESHOLD", "0.8"))
UNCERTAINTY_THRESHOLD = float(os.getenv("UNCERTAINTY_THRESHOLD", "0.4"))

def preprocess_text(text):
    """Prétraite le texte pour la classification"""
    # Normalisation: minuscules
    text = text.lower()
    # Conserver les ponctuations significatives tout en supprimant les caractères spéciaux
    text = re.sub(r'[^\w\s!?.,]', '', text)
    return text

def fallback_classifier(message_text):
    """Classificateur de secours basé sur des règles simples"""
    # Liste de mots toxiques évidents (à enrichir dans un cas réel)
    toxic_words = ["idiot", "connard", "salope", "pute", "enculé", "merde", "putain", 
                  "con", "débile", "crétin", "nique", "fuck", "bitch", "asshole", "retard"]
    
    # Prétraiter le texte
    text = preprocess_text(message_text)
    
    # Calculer un score simple basé sur la présence de mots toxiques
    words = text.split()
    toxic_count = sum(1 for word in words if word in toxic_words)
    
    # Calculer un score entre 0 et 1
    if len(words) > 0:
        toxicity_score = min(1.0, toxic_count / len(words) * 3)  # Facteur 3 pour augmenter la sensibilité
    else:
        toxicity_score = 0.0
    
    # Ajouter un facteur d'incertitude pour les messages ambigus
    uncertainty = 0.5 if 0.3 < toxicity_score < 0.7 else 0.0
    
    return toxicity_score, uncertainty

class MessageClassifier(FlatMapFunction):
    """Classe FlatMapFunction pour la classification des messages"""
    
    def __init__(self):
        self.model_interpreter = None
        self.vectorizer = None
        self.model_initialized = False
        self.temp_dir = None
    
    def open(self, runtime_context: RuntimeContext):
        """Initialisation au démarrage de la tâche"""
        # Définir des variables d'environnement TensorFlow avant l'import
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"  # Forcer CPU
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Réduire les logs TF
        
        # Initialiser le modèle
        self.initialize_models()
    
    def load_model_from_minio(self):
        """Charge le modèle et le vectoriseur depuis MinIO"""
        try:
            print("Chargement du modèle et du vectoriseur depuis MinIO...")
            
            # Importer boto3 localement dans la méthode pour éviter les problèmes de pickle
            import boto3
            from botocore.client import Config
            
            # Configurer le client S3 pour MinIO
            s3_client = boto3.client(
                's3',
                endpoint_url=f"{'https' if MINIO_SECURE else 'http'}://{MINIO_ENDPOINT}",
                aws_access_key_id=MINIO_ACCESS_KEY,
                aws_secret_access_key=MINIO_SECRET_KEY,
                verify=False,
                config=Config(connect_timeout=10, retries={'max_attempts': 3})
            )
            
            # Créer un répertoire temporaire pour télécharger les fichiers
            self.temp_dir = tempfile.mkdtemp()
            model_path = os.path.join(self.temp_dir, "fast_toxicity_model.tflite")
            vectorizer_path = os.path.join(self.temp_dir, "vectorizer.pkl")
            
            # Télécharger le modèle et le vectoriseur
            print(f"Téléchargement du modèle depuis {MINIO_BUCKET}/{MINIO_MODEL_PATH}")
            s3_client.download_file(MINIO_BUCKET, MINIO_MODEL_PATH, model_path)
            
            print(f"Téléchargement du vectoriseur depuis {MINIO_BUCKET}/{MINIO_VECTORIZER_PATH}")
            s3_client.download_file(MINIO_BUCKET, MINIO_VECTORIZER_PATH, vectorizer_path)
            
            # Charger le modèle TensorFlow Lite - importation locale pour éviter pickle
            import tensorflow as tf
                
            # Listes des erreurs connues pour TensorFlow sous Python 3.10
            try:
                self.model_interpreter = tf.lite.Interpreter(model_path=model_path)
                self.model_interpreter.allocate_tensors()
            except Exception as tf_err:
                # En cas d'erreur avec numpy._core, essayer avec une solution de contournement
                if "numpy._core" in str(tf_err):
                    print("Erreur numpy._core détectée, tentative de contournement...")
                    import numpy
                    import importlib
                    import sys
                    
                    # Si numpy._core est manquant, essayer de corriger l'importation
                    if not hasattr(numpy, '_core'):
                        try:
                            # Tenter d'importer explicitement
                            sys.modules['numpy._core'] = importlib.import_module('numpy.core')
                            # Réessayer l'initialisation du modèle
                            self.model_interpreter = tf.lite.Interpreter(model_path=model_path)
                            self.model_interpreter.allocate_tensors()
                        except Exception as inner_err:
                            print(f"La tentative de contournement a également échoué: {inner_err}")
                            raise
                else:
                    raise
            
            # Charger le vectoriseur
            with open(vectorizer_path, 'rb') as f:
                self.vectorizer = pickle.load(f)
            
            print("Modèle et vectoriseur chargés avec succès!")
            return True
            
        except Exception as e:
            print(f"Erreur lors du chargement depuis MinIO: {e}")
            return False
    
    def initialize_models(self):
        """Initialise les modèles au démarrage du service"""
        # Essayer de charger depuis MinIO
        if self.load_model_from_minio():
            self.model_initialized = True
            return True
        
        # Si le chargement depuis MinIO échoue, vérifier si un modèle local est disponible
        local_model_path = os.getenv("MODEL_PATH", "/opt/flink/usrlib/models/fast/fast_toxicity_model.tflite")
        local_vectorizer_path = os.getenv("VECTORIZER_PATH", "/opt/flink/usrlib/models/fast/vectorizer.pkl")
        
        try:
            if os.path.exists(local_model_path) and os.path.exists(local_vectorizer_path):
                print(f"Chargement du modèle local depuis {local_model_path}")
                # Importer tensorflow localement
                import tensorflow as tf
                self.model_interpreter = tf.lite.Interpreter(model_path=local_model_path)
                self.model_interpreter.allocate_tensors()
                
                print(f"Chargement du vectoriseur local depuis {local_vectorizer_path}")
                with open(local_vectorizer_path, 'rb') as f:
                    self.vectorizer = pickle.load(f)
                
                print("Modèle et vectoriseur locaux chargés avec succès!")
                self.model_initialized = True
                return True
        except Exception as e:
            print(f"Erreur lors du chargement des modèles locaux: {e}")
        
        print("Aucun modèle disponible. Le classificateur de secours sera utilisé.")
        self.model_initialized = False
        return False
    
    def classify_message_with_model(self, text):
        """Classifie un message avec le modèle TFLite chargé"""
        try:
            # Prétraiter le texte
            processed_text = preprocess_text(text)
            
            # Importer numpy localement
            import numpy as np
            
            # Vectoriser le texte avec le même vectoriseur que lors de l'entraînement
            text_vector = self.vectorizer.transform([processed_text]).toarray().astype(np.float32)
            
            # Obtenir les détails des tenseurs d'entrée et de sortie
            input_details = self.model_interpreter.get_input_details()
            output_details = self.model_interpreter.get_output_details()
            
            # Vérifier que les dimensions correspondent à ce qu'attend le modèle
            if text_vector.shape[1] != input_details[0]['shape'][1]:
                print(f"Erreur de dimension: attendu {input_details[0]['shape'][1]}, obtenu {text_vector.shape[1]}")
                return None, 1.0  # Incertitude maximale en cas d'erreur
                
            # Définir les données d'entrée
            self.model_interpreter.set_tensor(input_details[0]['index'], text_vector)
            
            # Exécuter l'inférence
            self.model_interpreter.invoke()
            
            # Obtenir les résultats
            output_data = self.model_interpreter.get_tensor(output_details[0]['index'])
            
            # Retourner le score de toxicité (entre 0 et 1)
            toxicity_score = float(output_data[0][0])
            
            # Calculer l'incertitude: plus on est proche de 0.5, plus l'incertitude est élevée
            distance_from_threshold = abs(toxicity_score - 0.5)
            uncertainty = max(0.0, 0.5 - distance_from_threshold)
            
            return toxicity_score, uncertainty
            
        except Exception as e:
            print(f"Erreur lors de la classification avec le modèle: {e}")
            return None, 1.0  # Incertitude maximale en cas d'erreur
    
    def flat_map(self, message_json):
        """Classifie un message et détermine sa destination"""
        try:
            # Charger le message JSON
            message = json.loads(message_json)
            message_text = message.get("content", "")
            
            # Classification avec le modèle ou le fallback
            if self.model_initialized and self.model_interpreter is not None and self.vectorizer is not None:
                toxicity_score, uncertainty = self.classify_message_with_model(message_text)
                if toxicity_score is None:
                    toxicity_score, uncertainty = fallback_classifier(message_text)
            else:
                toxicity_score, uncertainty = fallback_classifier(message_text)
            
            # Ajouter les résultats de classification au message
            message["classification"] = {
                "toxicity_score": toxicity_score,
                "uncertainty": uncertainty,
                "timestamp": int(time.time() * 1000)
            }
            
            # Déterminer la destination du message
            if uncertainty > UNCERTAINTY_THRESHOLD:
                # Message ambigu nécessitant une analyse approfondie
                message["classification"]["decision"] = "NEEDS_ANALYSIS"
                yield json.dumps(message)
            elif toxicity_score > TOXICITY_THRESHOLD:
                # Message toxique
                message["classification"]["decision"] = "TOXIC"
                yield json.dumps(message)
            else:
                # Message acceptable
                message["classification"]["decision"] = "OK"
                yield json.dumps(message)
                
        except Exception as e:
            print(f"Erreur lors de la classification: {e}")
            # En cas d'erreur, envoyer pour analyse approfondie
            try:
                message = json.loads(message_json)
                message["classification"] = {
                    "error": str(e),
                    "decision": "NEEDS_ANALYSIS",
                    "timestamp": int(time.time() * 1000)
                }
                yield json.dumps(message)
            except:
                # Si on ne peut pas parser le JSON, créer un message d'erreur
                error_message = {
                    "error": "Message non parsable",
                    "raw_message": message_json[:200],  # Tronquer pour éviter les messages trop longs
                    "classification": {
                        "decision": "ERROR",
                        "timestamp": int(time.time() * 1000)
                    }
                }
                yield json.dumps(error_message)

def main():
    """Fonction principale pour le job Flink"""
    # Créer l'environnement d'exécution Flink
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)  # Ajuster selon les besoins
    
    # Mode 1: Utiliser une source de test (pour le développement)
    test_mode = os.getenv("TEST_MODE", "False").lower() == "true"
    
    if test_mode:
        # Utiliser des données de test en mode développement
        print("Exécution en mode TEST avec données simulées")
        test_data = [
            '{"id": "1", "content": "Bonjour, comment ça va?"}',
            '{"id": "2", "content": "Tu es vraiment un idiot!"}',
            '{"id": "3", "content": "Ce service est excellent, merci!"}',
        ]
        data_stream = env.from_collection(test_data)
    else:
        # Mode 2: Utiliser Kafka comme source (pour la production)
        print("Exécution en mode PRODUCTION avec connexion à Kafka")
        # Configurer le consommateur Kafka
        kafka_consumer = FlinkKafkaConsumer(
            RAW_MESSAGES_TOPIC,
            SimpleStringSchema(),
            {
                'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
                'group.id': 'fast-classifier',
                'auto.offset.reset': 'latest'
            }
        )
        
        # Créer le flux de données à partir de Kafka
        data_stream = env.add_source(kafka_consumer)
    
    # Appliquer la fonction de classification
    classified_stream = data_stream.flat_map(MessageClassifier(), output_type=Types.STRING())
    
    # Toujours activer les logs pour le debug
    classified_stream.print("DEBUG-MESSAGES:")
    
    # Mode production : ajouter les sinks Kafka
    if not test_mode:
        try:
            # Définir les routes vers des topics distincts
            def router(message, ctx):
                try:
                    # Analyser le JSON pour déterminer le topic de destination
                    msg_obj = json.loads(message)
                    decision = msg_obj.get("classification", {}).get("decision", "")
                    
                    if decision == "NEEDS_ANALYSIS":
                        return NLP_ANALYSIS_REQUIRED_TOPIC
                    else:
                        return CLASSIFIED_MESSAGES_TOPIC
                except Exception as e:
                    print(f"Erreur de routage: {e}")
                    return NLP_ANALYSIS_REQUIRED_TOPIC  # Par défaut, envoyer pour analyse
            
            # Configurer le producteur Kafka avec routage
            kafka_producer_props = {
                'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
                'transaction.timeout.ms': '5000'
            }
            
            # Créer un producteur Kafka pour chaque topic
            classified_producer = FlinkKafkaProducer(
                CLASSIFIED_MESSAGES_TOPIC,
                SimpleStringSchema(),
                kafka_producer_props
            )
            
            nlp_analysis_producer = FlinkKafkaProducer(
                NLP_ANALYSIS_REQUIRED_TOPIC,
                SimpleStringSchema(),
                kafka_producer_props
            )
            
            # Filtrer les flux par décision et les diriger vers le bon topic
            classified_msgs = classified_stream.filter(lambda msg: 
                "NEEDS_ANALYSIS" not in json.loads(msg).get("classification", {}).get("decision", ""))
            
            needs_analysis_msgs = classified_stream.filter(lambda msg: 
                "NEEDS_ANALYSIS" in json.loads(msg).get("classification", {}).get("decision", ""))
            
            # Ajouter les sinks Kafka
            classified_msgs.add_sink(classified_producer)
            needs_analysis_msgs.add_sink(nlp_analysis_producer)
            
            print("Sinks Kafka configurés et ajoutés")
        except Exception as e:
            print(f"Erreur lors de la configuration des sinks Kafka: {e}")
            print("Exécution en mode dégradé : pas d'écriture dans Kafka")
    
    # Exécuter le job Flink
    env.execute("Fast Toxicity Classifier")

if __name__ == "__main__":
    main()
