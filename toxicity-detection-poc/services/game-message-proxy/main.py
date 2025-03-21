from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from kafka import KafkaProducer
import json
import os
import logging
from typing import Dict, List, Optional, Any

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration Kafka
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "192.168.229.167:9092")
RAW_MESSAGES_TOPIC = os.getenv("RAW_MESSAGES_TOPIC", "raw-messages")

# Initialisation de l'application FastAPI
app = FastAPI(title="Game Message Proxy", 
              description="Proxy d'ingestion pour les messages de chat des jeux vidéo")

# Modèle de données pour les messages
class GameMessage(BaseModel):
    message_id: str
    sender_id: str
    content: str
    timestamp: int
    game_id: str
    channel_id: str
    recipients: List[str]
    is_friends: Dict[str, bool] = {}  # Indique si le destinataire est ami avec l'expéditeur
    metadata: Optional[Dict[str, Any]] = None

# Initialisation du producteur Kafka
try:
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        key_serializer=lambda v: v.encode('utf-8') if v else None
    )
    logger.info(f"Connexion établie avec Kafka sur {KAFKA_BOOTSTRAP_SERVERS}")
except Exception as e:
    logger.error(f"Erreur lors de la connexion à Kafka: {e}")
    producer = None

# Fonction pour envoyer un message à Kafka
def send_to_kafka(message: dict, message_id: str):
    if producer:
        try:
            future = producer.send(
                topic=RAW_MESSAGES_TOPIC,
                key=message_id,
                value=message
            )
            result = future.get(timeout=10)
            logger.info(f"Message envoyé à Kafka: {message_id}, partition: {result.partition}, offset: {result.offset}")
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du message à Kafka: {e}")
    else:
        logger.error("Producteur Kafka non disponible")

@app.post("/api/messages", status_code=202)
async def receive_message(message: GameMessage, background_tasks: BackgroundTasks):
    """
    Reçoit un message de chat de jeu et l'envoie à Kafka pour traitement
    """
    logger.info(f"Message reçu: {message.message_id} de {message.sender_id}")
    
    # Conversion du modèle Pydantic en dictionnaire
    message_dict = message.dict()
    
    # Envoi du message à Kafka en arrière-plan
    background_tasks.add_task(send_to_kafka, message_dict, message.message_id)
    
    return {"status": "accepted", "message_id": message.message_id}

@app.get("/health")
async def health_check():
    """
    Vérifie l'état de santé du service
    """
    if producer:
        return {"status": "healthy", "kafka_connected": True}
    else:
        return {"status": "degraded", "kafka_connected": False}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
