#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gestionnaire de décisions pour le système de détection de toxicité
Centralise les décisions finales sur les messages et applique les règles de modération
"""

import os
import json
import time
import logging
import threading
from kafka import KafkaConsumer, KafkaProducer
from typing import Dict, List, Optional, Any

# Configuration du logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration Kafka
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
CLASSIFIED_MESSAGES_TOPIC = os.getenv("CLASSIFIED_MESSAGES_TOPIC", "classified-messages")
NLP_ANALYSIS_RESULTS_TOPIC = os.getenv("NLP_ANALYSIS_RESULTS_TOPIC", "nlp-analysis-results")
MODERATION_RESULTS_TOPIC = os.getenv("MODERATION_RESULTS_TOPIC", "moderation-results")
FINAL_DECISIONS_TOPIC = os.getenv("FINAL_DECISIONS_TOPIC", "final-decisions")

class DecisionManager:
    """Gestionnaire de décisions pour les messages analysés"""
    
    def __init__(self):
        """Initialisation du gestionnaire de décisions"""
        self.producers = {}
        self.consumers = {}
        self.running = False
        self.consumer_threads = []
        
        # Initialiser les producteurs et consommateurs Kafka
        self._init_kafka()
        
        # Cache des messages en attente de décision finale
        # Clé: message_id, Valeur: {source: decision}
        self.pending_decisions = {}
        
        logger.info("Gestionnaire de décisions initialisé avec succès")
    
    def _init_kafka(self):
        """Initialise les connexions Kafka"""
        try:
            # Créer le producteur Kafka
            self.producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda v: v.encode('utf-8') if v else None
            )
            logger.info(f"Producteur Kafka connecté à {KAFKA_BOOTSTRAP_SERVERS}")
            
            # Créer les consommateurs Kafka pour chaque topic
            topics = [
                CLASSIFIED_MESSAGES_TOPIC,
                NLP_ANALYSIS_RESULTS_TOPIC,
                MODERATION_RESULTS_TOPIC
            ]
            
            for topic in topics:
                consumer = KafkaConsumer(
                    topic,
                    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                    auto_offset_reset='latest',
                    enable_auto_commit=True,
                    group_id='decision-manager',
                    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
                )
                self.consumers[topic] = consumer
                logger.info(f"Consommateur Kafka créé pour le topic {topic}")
                
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation Kafka: {e}")
    
    def _consume_topic(self, topic):
        """Consomme les messages d'un topic spécifique"""
        consumer = self.consumers.get(topic)
        if not consumer:
            logger.error(f"Consommateur non disponible pour le topic {topic}")
            return
        
        logger.info(f"Démarrage de la consommation du topic {topic}")
        
        try:
            for record in consumer:
                if not self.running:
                    break
                    
                message = record.value
                message_id = message.get("message_id")
                
                if not message_id:
                    logger.warning(f"Message sans ID reçu sur {topic}")
                    continue
                
                logger.info(f"Message reçu sur {topic}: {message_id}")
                
                # Traiter le message selon sa source
                if topic == CLASSIFIED_MESSAGES_TOPIC:
                    self._handle_classified_message(message)
                elif topic == NLP_ANALYSIS_RESULTS_TOPIC:
                    self._handle_nlp_analysis_result(message)
                elif topic == MODERATION_RESULTS_TOPIC:
                    self._handle_moderation_result(message)
                
        except Exception as e:
            logger.error(f"Erreur lors de la consommation du topic {topic}: {e}")
        finally:
            consumer.close()
            logger.info(f"Consommation du topic {topic} arrêtée")
    
    def _handle_classified_message(self, message):
        """Traite un message classifié par le classificateur rapide"""
        message_id = message.get("message_id")
        classification = message.get("classification", {})
        decision = classification.get("decision")
        
        if not decision:
            logger.warning(f"Message classifié sans décision: {message_id}")
            return
        
        # Si le message est déjà marqué comme nécessitant une analyse, on l'ignore
        # car il sera traité par le flux d'analyse NLP
        if decision == "NEEDS_ANALYSIS":
            return
        
        # Sinon, on prend une décision immédiate
        self._make_final_decision(message, "fast_classifier", decision)
    
    def _handle_nlp_analysis_result(self, message):
        """Traite un résultat d'analyse NLP approfondie"""
        message_id = message.get("message_id")
        deep_analysis = message.get("deep_analysis", {})
        decision = deep_analysis.get("decision")
        
        if not decision:
            logger.warning(f"Résultat d'analyse NLP sans décision: {message_id}")
            return
        
        # Si le message nécessite une modération, on l'ignore car il sera
        # traité par le flux de modération
        if decision == "NEEDS_MODERATION":
            return
        
        # Sinon, on prend une décision finale
        self._make_final_decision(message, "deep_analyzer", decision)
    
    def _handle_moderation_result(self, message):
        """Traite un résultat de modération humaine"""
        message_id = message.get("message_id")
        moderation = message.get("moderation", {})
        decision = moderation.get("decision")
        
        if not decision:
            logger.warning(f"Résultat de modération sans décision: {message_id}")
            return
        
        # La décision de modération est toujours finale
        self._make_final_decision(message, "human_moderator", decision)
    
    def _make_final_decision(self, message, source, decision):
        """Prend une décision finale sur un message et l'envoie"""
        message_id = message.get("message_id")
        
        # Ajouter la décision finale au message
        message["final_decision"] = {
            "source": source,
            "decision": decision,
            "timestamp": int(time.time() * 1000)
        }
        
        # Appliquer les actions en fonction de la décision
        if decision == "TOXIC":
            # Message toxique: bloquer et enregistrer pour formation
            message["final_decision"]["action"] = "BLOCK"
            message["final_decision"]["training_value"] = True
        elif decision == "OK":
            # Message acceptable: autoriser
            message["final_decision"]["action"] = "ALLOW"
            # Si c'est un faux positif qui a nécessité une analyse approfondie,
            # l'enregistrer pour la formation
            if source in ["deep_analyzer", "human_moderator"]:
                message["final_decision"]["training_value"] = True
        
        # Envoyer la décision finale
        self._send_final_decision(message)
    
    def _send_final_decision(self, message):
        """Envoie la décision finale à Kafka"""
        if not self.producer:
            logger.error("Producteur Kafka non disponible")
            return
        
        try:
            message_id = message.get("message_id")
            future = self.producer.send(
                topic=FINAL_DECISIONS_TOPIC,
                key=message_id,
                value=message
            )
            result = future.get(timeout=10)
            logger.info(f"Décision finale envoyée: {message_id}, décision: {message['final_decision']['decision']}")
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la décision finale: {e}")
    
    def start(self):
        """Démarre le gestionnaire de décisions"""
        if self.running:
            logger.warning("Le gestionnaire de décisions est déjà en cours d'exécution")
            return
        
        self.running = True
        
        # Démarrer un thread pour chaque consommateur
        for topic in self.consumers:
            thread = threading.Thread(target=self._consume_topic, args=(topic,))
            thread.daemon = True
            thread.start()
            self.consumer_threads.append(thread)
            logger.info(f"Thread de consommation démarré pour {topic}")
        
        logger.info("Gestionnaire de décisions démarré")
    
    def stop(self):
        """Arrête le gestionnaire de décisions"""
        self.running = False
        
        # Attendre que tous les threads se terminent
        for thread in self.consumer_threads:
            thread.join(timeout=5.0)
        
        # Fermer les connexions Kafka
        for consumer in self.consumers.values():
            consumer.close()
        
        if self.producer:
            self.producer.close()
        
        logger.info("Gestionnaire de décisions arrêté")

if __name__ == "__main__":
    manager = DecisionManager()
    try:
        manager.start()
        # Maintenir le processus en vie
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Interruption détectée, arrêt du gestionnaire de décisions")
        manager.stop()
    except Exception as e:
        logger.error(f"Erreur dans la boucle principale: {e}")
        manager.stop()
