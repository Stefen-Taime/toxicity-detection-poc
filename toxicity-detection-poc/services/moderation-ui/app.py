"""
Interface de modération pour le système de détection de toxicité
Version Web (HTML/CSS/JS + Flask) pour remplacer Streamlit
"""

import os
import json
import time
import logging
import threading
from flask import Flask, render_template, jsonify, request
from kafka import KafkaConsumer, KafkaProducer
from datetime import datetime
from collections import deque

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
MODERATION_REQUIRED_TOPIC = os.getenv("MODERATION_REQUIRED_TOPIC", "moderation-required")
MODERATION_RESULTS_TOPIC = os.getenv("MODERATION_RESULTS_TOPIC", "moderation-results")

global_moderation_queue = deque(maxlen=100)
moderation_history = []
consumer_running = False
last_consumer_activity = time.time()

queue_lock = threading.Lock()

app = Flask(__name__)

def setup_kafka_consumer():
    """Configure et retourne un consommateur Kafka"""
    try:
        logger.info(f"Tentative de connexion au serveur Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
        
        group_id = 'moderation-ui-' + str(int(time.time()))
        
        consumer = KafkaConsumer(
            MODERATION_REQUIRED_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            auto_offset_reset='earliest',  
            enable_auto_commit=True,
            group_id=group_id,
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        )
        logger.info(f"Consommateur Kafka connecté à {KAFKA_BOOTSTRAP_SERVERS} avec group_id={group_id}")
        return consumer
    except Exception as e:
        logger.error(f"Erreur lors de la création du consommateur Kafka: {e}")
        return None

def setup_kafka_producer():
    """Configure et retourne un producteur Kafka"""
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

def consume_messages():
    """Consomme les messages du topic de modération et les ajoute à la file d'attente"""
    global consumer_running, last_consumer_activity, global_moderation_queue
    
    logger.info("Thread de consommation démarré")
    consumer_running = True
    last_consumer_activity = time.time()
    
    consumer = setup_kafka_consumer()
    if not consumer:
        logger.error("Impossible de créer le consommateur Kafka")
        consumer_running = False
        return
    
    logger.info(f"Consumer configuré: {consumer}")
    logger.info(f"Début de la boucle de consommation sur le topic: {MODERATION_REQUIRED_TOPIC}")
    
    try:
        for record in consumer:
            try:
                message = record.value
                logger.info(f"Message reçu: {message}")
                last_consumer_activity = time.time()
                
                message_id = message.get('message_id', '')
                with queue_lock:
                    existing_ids = [msg.get('message_id', '') for msg in global_moderation_queue]
                    if message_id not in existing_ids:
                        global_moderation_queue.append(message)
                        logger.info(f"Message ajouté à la file d'attente: {message_id}")
                
                time.sleep(0.1)  
            except Exception as msg_error:
                logger.error(f"Erreur lors du traitement d'un message: {msg_error}")
    except Exception as e:
        logger.error(f"Erreur lors de la consommation des messages: {e}")
    finally:
        try:
            consumer.close()
            logger.info("Consommateur Kafka fermé")
        except:
            pass
        consumer_running = False

def load_messages_directly():
    """Charge directement les messages depuis Kafka sans utiliser le thread consumer"""
    global global_moderation_queue
    
    try:
        temp_group_id = 'temp-loader-' + str(int(time.time()))
        logger.info(f"Chargement direct des messages avec group_id={temp_group_id}")
        
        temp_consumer = KafkaConsumer(
            MODERATION_REQUIRED_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            auto_offset_reset='earliest',
            enable_auto_commit=False,  
            group_id=temp_group_id,
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            consumer_timeout_ms=10000  
        )
        
        messages = []
        for record in temp_consumer:
            message = record.value
            messages.append(message)
            logger.info(f"Message chargé directement: {message.get('message_id', 'unknown')}")
        
        count = 0
        with queue_lock:
            existing_ids = [msg.get('message_id', '') for msg in global_moderation_queue]
            for msg in messages:
                msg_id = msg.get('message_id', '')
                if msg_id not in existing_ids:
                    global_moderation_queue.append(msg)
                    count += 1
        
        temp_consumer.close()
        logger.info(f"{count} messages chargés directement depuis Kafka")
        
        return count
    except Exception as e:
        logger.error(f"Erreur lors du chargement direct des messages: {e}")
        return 0

def send_moderation_decision(message, decision, reason=None):
    """Envoie une décision de modération à Kafka"""
    producer = setup_kafka_producer()
    if not producer:
        logger.error("Impossible d'envoyer la décision. Vérifiez la configuration Kafka.")
        return False
    
    try:
        message["moderation"] = {
            "decision": decision,
            "reason": reason,
            "moderator_id": "human_moderator",
            "timestamp": int(time.time() * 1000)
        }
        
        message_id = message.get("message_id", str(time.time()))
        future = producer.send(
            topic=MODERATION_RESULTS_TOPIC,
            key=message_id,
            value=message
        )
        result = future.get(timeout=10)
        logger.info(f"Décision envoyée: {message_id}, décision: {decision}")
        
        global moderation_history
        moderation_history.append({
            "timestamp": datetime.now().isoformat(),
            "message_id": message_id,
            "decision": decision,
            "reason": reason
        })
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de la décision: {e}")
        return False
    finally:
        producer.close()

@app.route('/')
def index():
    """Page principale de l'interface"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Retourne l'état actuel du système"""
    global consumer_running, last_consumer_activity
    
    with queue_lock:
        queue_size = len(global_moderation_queue)
    
    consumer_inactive_seconds = time.time() - last_consumer_activity
    
    return jsonify({
        "consumer_running": consumer_running,
        "last_activity": last_consumer_activity,
        "inactive_seconds": consumer_inactive_seconds,
        "queue_size": queue_size,
        "kafka_server": KAFKA_BOOTSTRAP_SERVERS,
        "input_topic": MODERATION_REQUIRED_TOPIC,
        "output_topic": MODERATION_RESULTS_TOPIC
    })

@app.route('/api/messages/current')
def get_current_message():
    """Retourne le premier message de la file d'attente"""
    with queue_lock:
        if global_moderation_queue:
            current_message = dict(global_moderation_queue[0])
            return jsonify({
                "status": "success",
                "message": current_message
            })
        else:
            return jsonify({
                "status": "empty",
                "message": None
            })

@app.route('/api/messages/all')
def get_all_messages():
    """Retourne tous les messages de la file d'attente"""
    with queue_lock:
        return jsonify({
            "status": "success",
            "queue_size": len(global_moderation_queue),
            "messages": list(global_moderation_queue)
        })

@app.route('/api/decision', methods=['POST'])
def post_decision():
    """Traite une décision de modération"""
    data = request.json
    
    if not data or 'decision' not in data:
        return jsonify({"status": "error", "message": "Données manquantes"}), 400
    
    with queue_lock:
        if not global_moderation_queue:
            return jsonify({"status": "error", "message": "Aucun message à modérer"}), 404
        
        current_message = dict(global_moderation_queue[0])  
    
    decision = data['decision']
    reason = data.get('reason', '')
    
    if decision == "TOXIC" and not reason:
        return jsonify({"status": "error", "message": "Une raison est requise pour bloquer un message"}), 400
    
    # Envoyer la décision
    if decision in ["OK", "TOXIC"]:
        success = send_moderation_decision(current_message, decision, reason)
        
        if success:
            with queue_lock:
                if global_moderation_queue:
                    global_moderation_queue.popleft()
                    logger.info(f"Message {current_message.get('message_id')} supprimé de la file après décision: {decision}")
            
            return jsonify({"status": "success", "message": "Décision traitée avec succès"})
        else:
            return jsonify({"status": "error", "message": "Erreur lors de l'envoi de la décision"}), 500
    
    elif decision == "SKIP":
        with queue_lock:
            if global_moderation_queue:
                message = global_moderation_queue.popleft()
                global_moderation_queue.append(message)
                logger.info(f"Message {message.get('message_id')} déplacé à la fin de la file")
        
        return jsonify({"status": "success", "message": "Message ignoré et déplacé à la fin de la file"})
    
    else:
        return jsonify({"status": "error", "message": "Décision non reconnue"}), 400
    
@app.route('/api/actions/restart-consumer', methods=['POST'])
def restart_consumer():
    """Redémarre le consommateur Kafka"""
    global consumer_running
    
    consumer_running = False
    
    with queue_lock:
        global_moderation_queue.clear()
    
    kafka_thread = threading.Thread(target=consume_messages, daemon=True)
    kafka_thread.start()
    
    return jsonify({"status": "success", "message": "Consommateur redémarré"})

@app.route('/api/actions/load-messages', methods=['POST'])
def load_messages():
    """Charge des messages directement depuis Kafka"""
    count = load_messages_directly()
    
    if count > 0:
        return jsonify({"status": "success", "message": f"{count} messages chargés depuis Kafka"})
    else:
        return jsonify({"status": "warning", "message": "Aucun message trouvé dans le topic Kafka"})

@app.route('/api/actions/clear-queue', methods=['POST'])
def clear_queue():
    """Vide la file d'attente"""
    with queue_lock:
        global_moderation_queue.clear()
    
    return jsonify({"status": "success", "message": "File d'attente vidée"})

@app.route('/api/actions/add-test-message', methods=['POST'])
def add_test_message():
    """Ajoute un message de test à la file d'attente"""
    test_message = {
        "message_id": "test-" + str(int(time.time())),
        "sender_id": "test-user",
        "content": "Ceci est un message de test pour vérifier l'interface de modération",
        "game_id": "game-test",
        "channel_id": "general",
        "is_friends": {"user1": True, "user2": False},
        "classification": {
            "toxicity_score": 0.6, 
            "uncertainty": 0.4,
            "decision": "NEEDS_ANALYSIS",
            "timestamp": int(time.time() * 1000)
        },
        "deep_analysis": {
            "toxicity_score": 0.55, 
            "uncertainty": 0.45,
            "decision": "NEEDS_MODERATION",
            "timestamp": int(time.time() * 1000)
        },
        "metadata": {
            "game_context": "casual",
            "message_type": "chat"
        }
    }
    
    with queue_lock:
        global_moderation_queue.append(test_message)
    
    return jsonify({"status": "success", "message": "Message de test ajouté"})

@app.route('/api/history')
def get_moderation_history():
    """Retourne l'historique des décisions de modération"""
    global moderation_history
    
    return jsonify({
        "status": "success",
        "history": moderation_history
    })

if __name__ == "__main__":
    kafka_thread = threading.Thread(target=consume_messages, daemon=True)
    kafka_thread.start()
    
    app.run(host='0.0.0.0', port=8501, debug=True, use_reloader=False)