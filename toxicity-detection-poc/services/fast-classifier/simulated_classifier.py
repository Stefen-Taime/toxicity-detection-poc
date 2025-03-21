#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
import random
import sys

def generate_random_message():
    messages = [
        {"id": "1", "content": "Bonjour, comment ça va?"},
        {"id": "2", "content": "Tu es vraiment un idiot!"},
        {"id": "3", "content": "Ce service est excellent, merci!"},
    ]
    return random.choice(messages)

def fallback_classifier(message_text):
    """Classificateur de secours basé sur des règles simples"""
    toxic_words = ["idiot", "merde"]
    text = message_text.lower()
    words = text.split()
    toxic_count = sum(1 for word in words if word in toxic_words)
    
    if len(words) > 0:
        toxicity_score = min(1.0, toxic_count / len(words) * 3)
    else:
        toxicity_score = 0.0
    
    uncertainty = 0.5 if 0.3 < toxicity_score < 0.7 else 0.0
    return toxicity_score, uncertainty

def main():
    print("Démarrage du service de classification")
    
    try:
        # Boucle infinie pour simuler un service continu
        while True:
            # Générer un message aléatoire
            message = generate_random_message()
            message_text = message["content"]
            
            # Classifier le message
            toxicity_score, uncertainty = fallback_classifier(message_text)
            
            # Décider de la classification
            if uncertainty > 0.4:
                decision = "NEEDS_ANALYSIS"
            elif toxicity_score > 0.7:
                decision = "TOXIC"
            else:
                decision = "OK"
            
            # Formater le résultat
            result = {
                "original": message,
                "classification": {
                    "toxicity_score": toxicity_score,
                    "uncertainty": uncertainty,
                    "decision": decision,
                    "timestamp": int(time.time() * 1000)
                }
            }
            
            # Afficher le résultat
            print(json.dumps(result, indent=2))
            
            # Attendre avant de traiter le prochain message
            time.sleep(5)
            
    except KeyboardInterrupt:
