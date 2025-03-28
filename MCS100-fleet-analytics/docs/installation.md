# Guide d'installation

Ce guide détaille les étapes nécessaires pour installer et configurer la solution MCS100 Fleet Analytics.

## Prérequis

Avant de commencer l'installation, assurez-vous que votre système répond aux exigences suivantes :

### Configuration matérielle recommandée
- **CPU** : 8 cœurs ou plus
- **RAM** : 16 Go minimum, 32 Go recommandé
- **Stockage** : 100 Go minimum d'espace disque disponible (SSD recommandé)
- **Réseau** : Connexion Internet stable

### Logiciels requis
- **Docker** : version 20.10.0 ou supérieure
- **Docker Compose** : version 2.0.0 ou supérieure
- **Git** : pour cloner le dépôt
- **Python 3.8+** : pour les scripts utilitaires (généralement préinstallé sur les systèmes Linux modernes)

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/airbus/mcs100-fleet-analytics.git
cd mcs100-fleet-analytics
```

### 2. Configuration de l'environnement

Copiez le fichier d'exemple de variables d'environnement et ajustez les paramètres selon vos besoins :

```bash
cp docker/.env.example docker/.env
```

Ouvrez le fichier `docker/.env` avec votre éditeur préféré et modifiez les paramètres selon votre environnement. Les paramètres les plus importants à vérifier sont :

- `POSTGRES_PASSWORD` : mot de passe pour la base de données TimescaleDB
- `MONGO_PASSWORD` : mot de passe pour la base de données MongoDB
- `MINIO_ROOT_USER` et `MINIO_ROOT_PASSWORD` : identifiants pour MinIO
- `GRAFANA_ADMIN_PASSWORD` : mot de passe pour l'administrateur Grafana
- `METABASE_PASSWORD` : mot de passe pour Metabase

### 3. Lancement de la solution

Utilisez le script de démarrage pour lancer tous les services :

```bash
./scripts/start.sh
```

Ce script effectue les opérations suivantes :
1. Vérifie les prérequis (Docker, Docker Compose)
2. Construit les images Docker personnalisées
3. Démarre tous les services définis dans le fichier docker-compose.yml
4. Initialise les bases de données avec les schémas nécessaires
5. Configure les connecteurs entre les différents services
6. Vérifie que tous les services sont opérationnels

Le démarrage complet peut prendre plusieurs minutes, en fonction de la puissance de votre machine.

### 4. Vérification de l'installation

Une fois le démarrage terminé, vous pouvez vérifier que tous les services sont opérationnels en exécutant :

```bash
docker ps
```

Vous devriez voir tous les conteneurs en cours d'exécution.

Vous pouvez également accéder aux interfaces web des différents services :

- **API FastAPI** : http://localhost:8000/docs
- **Grafana** : http://localhost:3000 (identifiants par défaut : admin / mot de passe défini dans .env)
- **Metabase** : http://localhost:3030 (identifiants par défaut : admin@mcs100.com / mot de passe défini dans .env)
- **Airflow** : http://localhost:8080 (identifiants par défaut : airflow / airflow)
- **MinIO** : http://localhost:9001 (identifiants définis dans .env)
- **Spark Master UI** : http://localhost:8181

### 5. Génération de données de test

Pour générer des données de test, utilisez le script fourni :

```bash
python3 data/generate_test_data.py
```

Pour initialiser les bases de données avec ces données de test :

```bash
python3 scripts/init_db.py --wait
```

Pour préparer des jeux de données spécifiques pour les démonstrations :

```bash
python3 scripts/prepare_demo_data.py
```

## Configuration avancée

### Personnalisation des ports

Si vous souhaitez modifier les ports utilisés par les différents services, éditez le fichier `docker/.env` et modifiez les variables correspondantes.

### Configuration de la haute disponibilité

Pour une configuration en haute disponibilité, vous devez :

1. Modifier le fichier `docker/docker-compose.ha.yml` pour ajuster le nombre de répliques
2. Lancer la solution avec la commande :

```bash
./scripts/start.sh --ha
```

### Configuration pour le cloud

La solution peut être déployée sur différentes plateformes cloud :

#### AWS
1. Configurez les variables d'environnement AWS dans `docker/.env`
2. Utilisez le script de déploiement AWS :

```bash
./scripts/deploy_aws.sh
```

#### Azure
1. Configurez les variables d'environnement Azure dans `docker/.env`
2. Utilisez le script de déploiement Azure :

```bash
./scripts/deploy_azure.sh
```

#### Google Cloud
1. Configurez les variables d'environnement GCP dans `docker/.env`
2. Utilisez le script de déploiement GCP :

```bash
./scripts/deploy_gcp.sh
```

## Dépannage

### Problèmes courants

#### Les conteneurs ne démarrent pas

Vérifiez les journaux des conteneurs :

```bash
docker-compose -f docker/docker-compose.yml logs
```

#### Problèmes de connexion aux bases de données

Vérifiez que les services de base de données sont en cours d'exécution :

```bash
docker ps | grep -E "timescaledb|mongodb"
```

Vérifiez les journaux des bases de données :

```bash
docker-compose -f docker/docker-compose.yml logs timescaledb
docker-compose -f docker/docker-compose.yml logs mongodb
```

#### Problèmes de mémoire

Si vous rencontrez des problèmes de mémoire, augmentez la mémoire allouée à Docker dans les paramètres de Docker Desktop (pour Windows et macOS) ou ajustez les limites de mémoire dans le fichier docker-compose.yml.

### Obtenir de l'aide

Si vous rencontrez des problèmes non résolus par ce guide, vous pouvez :

1. Consulter la documentation détaillée dans le répertoire `docs/`
2. Ouvrir une issue sur le dépôt GitHub
3. Contacter l'équipe de support à support@mcs100-fleet-analytics.com

## Mise à jour

Pour mettre à jour la solution vers une nouvelle version :

1. Arrêtez les services en cours d'exécution :

```bash
./scripts/stop.sh
```

2. Mettez à jour le dépôt :

```bash
git pull
```

3. Redémarrez les services :

```bash
./scripts/start.sh
```

## Désinstallation

Pour désinstaller complètement la solution :

```bash
./scripts/stop.sh --clean
```

Cette commande arrête tous les services et supprime les volumes Docker, effaçant ainsi toutes les données. Utilisez cette commande avec précaution.
