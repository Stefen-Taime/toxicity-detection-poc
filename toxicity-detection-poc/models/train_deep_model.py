#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de création d'un modèle simple pour l'analyse approfondie de toxicité
Ce modèle sera utilisé par le service deep-analyzer
"""

import os
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
import json
import pickle
import mlflow
import mlflow.sklearn
import mlflow.tensorflow
import boto3

# Créer un répertoire pour le modèle
current_dir = os.getcwd()
os.makedirs(os.path.join(current_dir, "models/deep"), exist_ok=True)

# Configuration des credentials pour MinIO/S3
os.environ['AWS_ACCESS_KEY_ID'] = 'minioadmin'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'minioadmin'
os.environ['MLFLOW_S3_ENDPOINT_URL'] = 'http://192.168.229.167:9000'

# Configuration MinIO
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', '192.168.229.167:9000')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'mlflow')

# Configuration MLflow
mlflow.set_tracking_uri("http://192.168.229.167:5000")
mlflow.set_experiment("toxicity-deep-analyzer")

print("Création d'un modèle pour l'analyse approfondie...")

# Données d'exemple pour l'entraînement
normal_messages = [
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

toxic_messages = [
    "T'es vraiment nul, désinstalle le jeu",
    "Va te faire foutre espèce d'idiot",
    "Mais quel noob sérieux",
    "Tu joues comme une merde",
    "Ferme ta gueule et joue",
    "Je vais te signaler, connard",
    "Putain mais t'es con ou quoi ?",
    "Retourne jouer à Fortnite, gamin",
    "T'es une honte pour l'équipe",
    "J'espère que tu vas perdre toutes tes parties",
    # Ajout de messages toxiques supplémentaires pour améliorer l'équilibre
    "Espèce de sale camper de merde",
    "Ta mère aurait dû t'avaler",
    "Désinstalle le jeu, tu es une plaie",
    "Tu dois être un enfant attardé",
    "Tu mérites de te faire bannir, pauvre con"
]

friendly_banter = [
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

ambiguous_messages = [
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

# Ajout de contexte pour l'analyse approfondie
contexts = [
    {"is_friends": True, "game_type": "FPS", "message_history": "friendly"},
    {"is_friends": False, "game_type": "MOBA", "message_history": "neutral"},
    {"is_friends": True, "game_type": "RPG", "message_history": "toxic"},
    {"is_friends": False, "game_type": "Battle Royale", "message_history": "friendly"}
]

# Préparation des données avec contexte
data = []

# Messages normaux
for msg in normal_messages:
    context = np.random.choice(contexts)
    data.append({
        "text": msg,
        "is_friends": context["is_friends"],
        "game_type": context["game_type"],
        "message_history": context["message_history"],
        "toxicity": 0.0
    })

# Messages toxiques
for msg in toxic_messages:
    context = np.random.choice(contexts)
    data.append({
        "text": msg,
        "is_friends": context["is_friends"],
        "game_type": context["game_type"],
        "message_history": context["message_history"],
        "toxicity": 1.0
    })

# Messages amicaux qui pourraient sembler toxiques
for msg in friendly_banter:
    # Pour les plaisanteries entre amis, on force le contexte d'amitié
    context = np.random.choice([c for c in contexts if c["is_friends"]])
    data.append({
        "text": msg,
        "is_friends": True,  # Toujours entre amis
        "game_type": context["game_type"],
        "message_history": context["message_history"],
        "toxicity": 0.3  # Toxicité faible car entre amis
    })

# Messages ambigus
for msg in ambiguous_messages:
    context = np.random.choice(contexts)
    # La toxicité dépend du contexte
    toxicity = 0.4 if context["is_friends"] else 0.7
    data.append({
        "text": msg,
        "is_friends": context["is_friends"],
        "game_type": context["game_type"],
        "message_history": context["message_history"],
        "toxicity": toxicity
    })

# Conversion en DataFrame
df = pd.DataFrame(data)

# Division en ensembles d'entraînement et de test
train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df["toxicity"] > 0.5)

print(f"Données d'entraînement: {len(train_df)} exemples")
print(f"Données de test: {len(test_df)} exemples")

# Commence un run MLflow pour le tracking
with mlflow.start_run(run_name="deep-model-training") as run:
    # Log des paramètres
    mlflow.log_param("dataset_size", len(df))
    mlflow.log_param("normal_messages", len(normal_messages))
    mlflow.log_param("toxic_messages", len(toxic_messages))
    mlflow.log_param("with_context", True)
    
    # Log du dataset pour référence
    dataset_path = os.path.join(current_dir, "models/deep/dataset.csv")
    df.to_csv(dataset_path, index=False)
    mlflow.log_artifact(dataset_path, "dataset")
    
    # Utilisation d'un modèle TF-IDF + Régression logistique pour l'analyse approfondie
    print("Entraînement d'un modèle TF-IDF + Régression logistique...")
    
    # Vectorisation des textes
    vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 3))
    X_train_vec = vectorizer.fit_transform(train_df["text"])
    X_test_vec = vectorizer.transform(test_df["text"])
    
    # Log des caractéristiques du vectoriseur
    mlflow.log_param("tfidf_features", X_train_vec.shape[1])
    
    # Ajout des caractéristiques contextuelles
    X_train_context = np.hstack([
        X_train_vec.toarray(),
        train_df["is_friends"].values.reshape(-1, 1)
    ])
    X_test_context = np.hstack([
        X_test_vec.toarray(),
        test_df["is_friends"].values.reshape(-1, 1)
    ])
    
    # Entraînement du modèle de régression logistique avec équilibrage des classes
    model = LogisticRegression(C=10, max_iter=1000, class_weight='balanced')
    mlflow.log_param("logistic_C", 10)
    
    model.fit(X_train_context, train_df["toxicity"] > 0.5)
    
    # Évaluation du modèle
    y_pred = model.predict(X_test_context)
    report = classification_report(test_df["toxicity"] > 0.5, y_pred, output_dict=True, zero_division=0)
    print("Rapport de classification:")
    print(classification_report(test_df["toxicity"] > 0.5, y_pred, zero_division=0))
    
    # Log des métriques
    mlflow.log_metric("precision", report["weighted avg"]["precision"])
    mlflow.log_metric("recall", report["weighted avg"]["recall"])
    mlflow.log_metric("f1_score", report["weighted avg"]["f1-score"])
    
    # Créer un exemple d'entrée pour la signature du modèle
    sample_text = "Exemple de message"
    sample_vec = vectorizer.transform([sample_text]).toarray()
    sample_input = np.hstack([sample_vec, np.array([[True]])]) 
    
    # Log du modèle de régression logistique avec signature
    mlflow.sklearn.log_model(model, "logistic_regression_model", input_example=sample_input)
    
    # Sauvegarde du modèle
    model_dir = os.path.join(current_dir, "models/deep")
    model_path = os.path.join(model_dir, "deep_model.pkl")
    vectorizer_path = os.path.join(model_dir, "deep_vectorizer.pkl")
    
    # Sauvegarde du modèle et du vectoriseur
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    
    with open(vectorizer_path, 'wb') as f:
        pickle.dump(vectorizer, f)
    
    print(f"Modèle sauvegardé à {model_path}")
    print(f"Vectoriseur sauvegardé à {vectorizer_path}")
    
    # Log des artefacts locaux
    mlflow.log_artifact(model_path, "sklearn_model")
    mlflow.log_artifact(vectorizer_path, "vectorizer")
    
    # Création d'un modèle TensorFlow simple comme alternative
    print("Création d'un modèle TensorFlow simplifié...")
    
    # Création d'un modèle Keras simple
    def create_simple_tf_model(input_dim):
        model = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(input_dim,)),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dropout(0.3),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(1, activation='sigmoid')
        ])
        
        model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy', tf.keras.metrics.Precision(), tf.keras.metrics.Recall()]
        )
        
        return model
    
    # Création et entraînement d'un modèle TensorFlow simple
    input_dim = X_train_context.shape[1]
    tf_model = create_simple_tf_model(input_dim)
    
    # Enable automatic logging pour TensorFlow
    mlflow.tensorflow.autolog()
    
    try:
        # Utiliser des class weights pour compenser le déséquilibre des classes
        class_weights = {0: 1.0, 1: len(train_df[train_df["toxicity"] <= 0.5]) / len(train_df[train_df["toxicity"] > 0.5])}
        
        # Utilisation d'un callback d'early stopping pour éviter l'overfitting
        early_stopping = tf.keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=3,
            restore_best_weights=True
        )
        
        # Entraînement du modèle
        tf_model.fit(
            X_train_context,
            train_df["toxicity"] > 0.5,
            epochs=10,
            batch_size=8,
            validation_data=(X_test_context, test_df["toxicity"] > 0.5),
            verbose=1,
            class_weight=class_weights,
            callbacks=[early_stopping]
        )
        
        # Évaluation du modèle
        loss, accuracy, precision, recall = tf_model.evaluate(X_test_context, test_df["toxicity"] > 0.5)
        print(f"Précision du modèle TensorFlow: {accuracy:.4f}")
        print(f"Precision du modèle TensorFlow: {precision:.4f}")
        print(f"Recall du modèle TensorFlow: {recall:.4f}")
        
        # Log explicite des métriques
        mlflow.log_metric("tf_accuracy", accuracy)
        mlflow.log_metric("tf_loss", loss)
        mlflow.log_metric("tf_precision", precision)
        mlflow.log_metric("tf_recall", recall)
        
        # Sauvegarde du modèle Keras avec l'extension appropriée
        tf_model_path = os.path.join(model_dir, "deep_tf_model.keras")
        tf_model.save(tf_model_path)
        print(f"Modèle TensorFlow sauvegardé à {tf_model_path}")
        
        # Log du modèle TensorFlow avec exemple d'entrée
        mlflow.tensorflow.log_model(tf_model, "tensorflow_model", input_example=X_test_context[0:1])
        
        tf_model_accuracy = accuracy
        tf_model_precision = precision
        tf_model_recall = recall
    except Exception as e:
        print(f"Erreur lors de l'entraînement du modèle TensorFlow: {e}")
        tf_model_accuracy = 0.0
        tf_model_precision = 0.0
        tf_model_recall = 0.0
        tf_model_path = None
    
    # Création d'un fichier de métadonnées pour les modèles
    metadata = {
        "logistic_model": {
            "path": model_path,
            "type": "sklearn_logistic_regression",
            "vectorizer": vectorizer_path,
            "inputs": ["text", "is_friends"],
            "description": "Modèle de régression logistique pour l'analyse de toxicité contextuelle"
        },
        "tensorflow_model": {
            "path": os.path.join(model_dir, "deep_tf_model.keras") if tf_model_path else "None",
            "type": "tensorflow",
            "accuracy": float(tf_model_accuracy),
            "precision": float(tf_model_precision),
            "recall": float(tf_model_recall),
            "description": "Modèle TensorFlow simple pour l'analyse de toxicité",
            "mlflow_run_id": run.info.run_id
        }
    }
    
    # Sauvegarde des métadonnées au format JSON
    metadata_path = os.path.join(model_dir, "models_metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"Métadonnées des modèles sauvegardées avec succès à {metadata_path}!")
    
    # Log du fichier de métadonnées
    mlflow.log_artifact(metadata_path, "metadata")
    
    # Enregistrer des exemples de cas difficiles pour l'analyse future
    difficult_cases = {
        "ambiguous_examples": list(zip(ambiguous_messages, ["True" if x["is_friends"] else "False" for x in contexts])),
        "friendly_banter": friendly_banter
    }
    
    difficult_cases_path = os.path.join(model_dir, "difficult_cases.json")
    with open(difficult_cases_path, "w", encoding="utf-8") as f:
        json.dump(difficult_cases, f, indent=2, ensure_ascii=False)
    
    # Log des cas difficiles
    mlflow.log_artifact(difficult_cases_path, "difficult_cases")

    # Upload direct des modèles dans MinIO
    try:
        print(f"Tentative de connexion à MinIO sur {MINIO_ENDPOINT}...")
        s3_client = boto3.client(
            's3',
            endpoint_url=f'http://{MINIO_ENDPOINT}',
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY,
            verify=False
        )
        
        # Vérifier si le bucket existe, sinon le créer
        try:
            s3_client.head_bucket(Bucket=MINIO_BUCKET)
            print(f"Bucket {MINIO_BUCKET} existe déjà")
        except:
            print(f"Création du bucket {MINIO_BUCKET}")
            s3_client.create_bucket(Bucket=MINIO_BUCKET)
        
        # Créer la structure de dossiers si nécessaire
        try:
            s3_client.put_object(Bucket=MINIO_BUCKET, Key='models/')
            print("Dossier 'models/' créé dans MinIO")
        except Exception as e:
            print(f"Note: {e}")
        
        try:
            s3_client.put_object(Bucket=MINIO_BUCKET, Key='models/deep/')
            print("Dossier 'models/deep/' créé dans MinIO")
        except Exception as e:
            print(f"Note: {e}")
        
        # Upload des fichiers dans MinIO
        print("Upload du modèle de régression logistique dans MinIO...")
        s3_client.upload_file(
            model_path,
            MINIO_BUCKET,
            'models/deep/deep_model.pkl'
        )
        
        print("Upload du vectoriseur dans MinIO...")
        s3_client.upload_file(
            vectorizer_path,
            MINIO_BUCKET,
            'models/deep/deep_vectorizer.pkl'
        )
        
        print("Upload des métadonnées dans MinIO...")
        s3_client.upload_file(
            metadata_path,
            MINIO_BUCKET,
            'models/deep/models_metadata.json'
        )
        
        print("Upload des cas difficiles dans MinIO...")
        s3_client.upload_file(
            difficult_cases_path,
            MINIO_BUCKET,
            'models/deep/difficult_cases.json'
        )
        
        if tf_model_path:
            print("Upload du modèle TensorFlow dans MinIO...")
            s3_client.upload_file(
                tf_model_path,
                MINIO_BUCKET,
                'models/deep/deep_tf_model.keras'
            )
        
        print("Upload du dataset dans MinIO...")
        s3_client.upload_file(
            dataset_path,
            MINIO_BUCKET,
            'models/deep/dataset.csv'
        )
        
        print("Tous les fichiers ont été uploadés avec succès dans MinIO!")
        
        # Vérification des fichiers uploadés
        response = s3_client.list_objects_v2(
            Bucket=MINIO_BUCKET,
            Prefix='models/deep/'
        )
        
        if 'Contents' in response:
            print("Fichiers disponibles dans MinIO:")
            for obj in response['Contents']:
                print(f" - {obj['Key']} ({obj['Size']} bytes)")
        else:
            print("Aucun fichier trouvé dans models/deep/")
        
    except Exception as e:
        print(f"Erreur lors de l'upload dans MinIO: {e}")
        print("Les modèles ont été sauvegardés localement mais n'ont pas pu être uploadés dans MinIO.")
        print("Veuillez vérifier la configuration de MinIO et les credentials.")

print("Formation du modèle profond terminée et enregistrée dans MLflow et MinIO.")