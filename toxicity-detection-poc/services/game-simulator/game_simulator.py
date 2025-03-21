#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simulateur de jeu pour tester le système de détection de toxicité
Génère des messages de chat simulés avec différents niveaux de toxicité
"""

import os
import json
import time
import random
import logging
import requests
import uuid
from faker import Faker
from datetime import datetime
from typing import Dict, List, Optional, Any

# Configuration du logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration du simulateur
GAME_MESSAGE_PROXY_URL = os.getenv("GAME_MESSAGE_PROXY_URL", "http://game-message-proxy:8000")
SIMULATION_INTERVAL_MS = int(os.getenv("SIMULATION_INTERVAL_MS", "2000"))
NUM_PLAYERS = int(os.getenv("NUM_PLAYERS", "20"))
NUM_GAMES = int(os.getenv("NUM_GAMES", "3"))
FRIENDS_PROBABILITY = float(os.getenv("FRIENDS_PROBABILITY", "0.3"))
TOXIC_MESSAGE_PROBABILITY = float(os.getenv("TOXIC_MESSAGE_PROBABILITY", "0.15"))
AMBIGUOUS_MESSAGE_PROBABILITY = float(os.getenv("AMBIGUOUS_MESSAGE_PROBABILITY", "0.1"))

# Initialisation de Faker pour générer des données aléatoires
fake = Faker()

class GameSimulator:
    """Simulateur de jeu pour générer des messages de chat"""
    
    def __init__(self):
        """Initialisation du simulateur"""
        self.players = self._generate_players(NUM_PLAYERS)
        self.games = self._generate_games(NUM_GAMES)
        self.channels = ["global", "team", "private"]
        self.friendships = self._generate_friendships()
        
        # Dictionnaires de messages pour la simulation
        self.normal_messages = [
            "Bien joué !",
            "On se retrouve au point B",
            "J'ai besoin de munitions",
            "Quelqu'un peut me couvrir ?",
            "Bonne partie !",
            "Merci pour l'aide",
            "Je vais à gauche",
            "Attention derrière toi",
            "Bien vu",
            "Pas mal cette stratégie",
            "On recommence ?",
            "Je dois partir, à plus tard",
            "Qui a des ressources à échanger ?",
            "Félicitations pour ta victoire",
            "Tu t'améliores vraiment",
            "Essayons une autre tactique",
            "Besoin d'aide par ici",
            "Défendez la base !",
            "Allons-y ensemble",
            "Bonne chance à tous"
        ]
        
        self.toxic_messages = [
            "T'es vraiment nul, déinstalle le jeu",
            "Va te faire foutre espèce d'idiot",
            "Mais quel noob sérieux",
            "Tu joues comme une merde",
            "Ferme ta gueule et joue",
            "Je vais te signaler, connard",
            "Putain mais t'es con ou quoi ?",
            "Retourne jouer à Fortnite, gamin",
            "T'es une honte pour l'équipe",
            "J'espère que tu vas perdre toutes tes parties"
        ]
        
        self.friendly_banter = [
            "T'es nul mec, mais je t'aime bien quand même",
            "Putain, t'as vraiment merdé sur ce coup !",
            "Espèce de noob, heureusement que je suis là",
            "Tu joues comme ma grand-mère, sérieux",
            "Arrête de faire n'importe quoi, idiot",
            "T'es con ou tu le fais exprès ?",
            "Mais quel boulet, je te jure",
            "Tu me fais honte, mais c'est pour ça que t'es mon pote",
            "Je vais te buter à la prochaine partie, prépare-toi",
            "T'es vraiment une catastrophe ambulante"
        ]
        
        self.ambiguous_messages = [
            "C'est pas terrible ce que tu fais",
            "Tu pourrais faire un effort quand même",
            "Je sais pas si tu le fais exprès",
            "Franchement, c'est pas top",
            "Tu devrais peut-être essayer un autre jeu",
            "C'est pas ton jour aujourd'hui",
            "Ça devient pénible là",
            "On dirait que tu le fais exprès",
            "Tu nous ralentis là",
            "Faudrait voir à s'améliorer"
        ]
        
        logger.info(f"Simulateur initialisé avec {NUM_PLAYERS} joueurs et {NUM_GAMES} jeux")
    
    def _generate_players(self, num_players):
        """Génère une liste de joueurs simulés"""
        players = []
        for _ in range(num_players):
            player_id = f"player_{uuid.uuid4().hex[:8]}"
            player = {
                "id": player_id,
                "name": fake.user_name(),
                "level": random.randint(1, 100),
                "created_at": fake.date_time_this_year().isoformat()
            }
            players.append(player)
        return players
    
    def _generate_games(self, num_games):
        """Génère une liste de jeux simulés"""
        game_types = ["FPS", "MOBA", "RPG", "Battle Royale", "Stratégie"]
        games = []
        for i in range(num_games):
            game_id = f"game_{i+1}"
            game = {
                "id": game_id,
                "name": f"{fake.word().capitalize()} {random.choice(['Arena', 'Legends', 'Wars', 'Heroes'])}",
                "type": random.choice(game_types),
                "max_players": random.choice([2, 4, 8, 16, 32, 64])
            }
            games.append(game)
        return games
    
    def _generate_friendships(self):
        """Génère des relations d'amitié aléatoires entre les joueurs"""
        friendships = {}
        for player in self.players:
            player_id = player["id"]
            friendships[player_id] = set()
            
            # Chaque joueur a une chance d'être ami avec chaque autre joueur
            for other_player in self.players:
                other_id = other_player["id"]
                if player_id != other_id and random.random() < FRIENDS_PROBABILITY:
                    friendships[player_id].add(other_id)
        
        return friendships
    
    def _are_friends(self, player1_id, player2_id):
        """Vérifie si deux joueurs sont amis"""
        return player2_id in self.friendships.get(player1_id, set())
    
    def _generate_message_content(self, sender_id, recipients):
        """Génère le contenu d'un message avec une probabilité de toxicité"""
        # Déterminer si tous les destinataires sont des amis
        all_friends = all(self._are_friends(sender_id, r) for r in recipients)
        
        # Probabilité de message toxique ou ambigu
        rand = random.random()
        
        if all_friends:
            # Entre amis, plus de chances d'avoir des plaisanteries qui pourraient sembler toxiques
            if rand < 0.3:
                return random.choice(self.friendly_banter)
            else:
                return random.choice(self.normal_messages)
        else:
            # Avec des inconnus, possibilité de messages toxiques ou ambigus
            if rand < TOXIC_MESSAGE_PROBABILITY:
                return random.choice(self.toxic_messages)
            elif rand < TOXIC_MESSAGE_PROBABILITY + AMBIGUOUS_MESSAGE_PROBABILITY:
                return random.choice(self.ambiguous_messages)
            else:
                return random.choice(self.normal_messages)
    
    def generate_message(self):
        """Génère un message de chat aléatoire"""
        # Sélectionner un jeu, un expéditeur et un canal aléatoires
        game = random.choice(self.games)
        sender = random.choice(self.players)
        channel = random.choice(self.channels)
        
        # Déterminer les destinataires en fonction du canal
        if channel == "global":
            # Message global: tous les joueurs du jeu
            recipients = [p["id"] for p in self.players if p["id"] != sender["id"]]
            # Limiter à un nombre raisonnable pour la simulation
            recipients = random.sample(recipients, min(len(recipients), 10))
        elif channel == "team":
            # Message d'équipe: un sous-ensemble de joueurs
            team_size = random.randint(2, 5)
            recipients = [p["id"] for p in random.sample(self.players, team_size) if p["id"] != sender["id"]]
        else:  # private
            # Message privé: un seul destinataire
            recipient = random.choice([p for p in self.players if p["id"] != sender["id"]])
            recipients = [recipient["id"]]
        
        # Déterminer si les destinataires sont des amis de l'expéditeur
        is_friends = {recipient_id: self._are_friends(sender["id"], recipient_id) for recipient_id in recipients}
        
        # Générer le contenu du message
        content = self._generate_message_content(sender["id"], recipients)
        
        # Créer le message
        message = {
            "message_id": f"msg_{uuid.uuid4().hex}",
            "sender_id": sender["id"],
            "content": content,
            "timestamp": int(time.time() * 1000),
            "game_id": game["id"],
            "channel_id": channel,
            "recipients": recipients,
            "is_friends": is_friends,
            "metadata": {
                "game_type": game["type"],
                "sender_level": sender["level"],
                "game_context": random.choice([None, "lobby", "in_game", "post_game"])
            }
        }
        
        return message
    
    def send_message(self, message):
        """Envoie un message au proxy d'ingestion"""
        try:
            response = requests.post(
                f"{GAME_MESSAGE_PROXY_URL}/api/messages",
                json=message,
                timeout=5
            )
            
            if response.status_code == 202:
                logger.info(f"Message envoyé avec succès: {message['message_id']}")
                return True
            else:
                logger.error(f"Erreur lors de l'envoi du message: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Exception lors de l'envoi du message: {e}")
            return False
    
    def run(self):
        """Exécute le simulateur en continu"""
        logger.info(f"Démarrage du simulateur, intervalle: {SIMULATION_INTERVAL_MS}ms")
        
        try:
            while True:
                # Générer et envoyer un message
                message = self.generate_message()
                success = self.send_message(message)
                
                # Afficher des informations sur le message
                if success:
                    is_friends_summary = sum(1 for v in message["is_friends"].values() if v)
                    total_recipients = len(message["is_friends"])
                    logger.info(f"Message de {message['sender_id']} à {total_recipients} destinataires "
                               f"({is_friends_summary} amis): {message['content'][:30]}...")
                
                # Attendre avant le prochain message
                time.sleep(SIMULATION_INTERVAL_MS / 1000)
                
        except KeyboardInterrupt:
            logger.info("Arrêt du simulateur")
        except Exception as e:
            logger.error(f"Erreur dans la boucle principale: {e}")

if __name__ == "__main__":
    # Attendre un peu pour s'assurer que les autres services sont prêts
    logger.info("Attente du démarrage des autres services...")
    time.sleep(10)
    
    # Démarrer le simulateur
    simulator = GameSimulator()
    simulator.run()
