#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de création d'un modèle simple pour la classification rapide de toxicité
Ce modèle sera utilisé par le service fast-classifier
"""

import os
import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
import mlflow
import mlflow.tensorflow
import mlflow.sklearn
import pickle
import json
import boto3

# Créer des répertoires pour le modèle
os.makedirs("models/fast", exist_ok=True)

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
mlflow.set_experiment("toxicity-fast-classifier")

# Données d'exemple pour l'entraînement
# Dans un cas réel, ces données seraient chargées à partir d'un fichier
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
    "Tu mérites de te faire bannir, pauvre con",
    "J'emmerde tous les joueurs comme toi",
    "Tu fais chier toute l'équipe avec ton incompétence",
    "Crève et ne reviens jamais",
    "Tu es la définition même d'un joueur de merde",
    "Va pleurer chez ta mère, espèce de looser"
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

# Préparation des données
X = normal_messages + toxic_messages + friendly_banter + ambiguous_messages
y = ([0] * len(normal_messages) + 
     [1] * len(toxic_messages) + 
     [0.5] * len(friendly_banter) + 
     [0.6] * len(ambiguous_messages))  # Ajustement de la valeur des ambiguous messages

# Conversion en numpy arrays
X = np.array(X)
y = np.array(y)

# Division en ensembles d'entraînement et de test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y > 0.5)

# Vectorisation des textes avec TF-IDF
vectorizer = TfidfVectorizer(
    ngram_range=(1, 3),  # Utilise des uni-, bi- et tri-grammes
    min_df=2,            # Ignore les termes qui apparaissent dans moins de 2 documents
    max_df=0.9           # Ignore les termes qui apparaissent dans plus de 90% des documents
)
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

# Nombre réel de features après vectorisation
n_features = X_train_vec.shape[1]
print(f"Nombre réel de features générées par TF-IDF: {n_features}")

# Commence un run MLflow pour le tracking
with mlflow.start_run(run_name="fast-model-training") as run:
    # Log des paramètres
    mlflow.log_param("dataset_size", len(X))
    mlflow.log_param("normal_messages", len(normal_messages))
    mlflow.log_param("toxic_messages", len(toxic_messages))
    mlflow.log_param("features", n_features)
    
    # Entraînement d'un modèle de régression logistique avec des poids de classe équilibrés
    model = LogisticRegression(
        max_iter=1000,
        class_weight='balanced',  # Compense l'imbalance des classes
        C=0.1,                    # Régularisation plus forte
        solver='liblinear'        # Meilleur solver pour les petits datasets
    )
    model.fit(X_train_vec, y_train > 0.5)  # Binarisation pour la régression logistique
    
    # Évaluation du modèle
    y_pred = model.predict(X_test_vec)
    print("Rapport de classification:")
    report = classification_report(y_test > 0.5, y_pred, output_dict=True, zero_division=0)
    print(classification_report(y_test > 0.5, y_pred, zero_division=0))
    
    # Log des métriques
    mlflow.log_metric("precision", report["weighted avg"]["precision"])
    mlflow.log_metric("recall", report["weighted avg"]["recall"])
    mlflow.log_metric("f1_score", report["weighted avg"]["f1-score"])
    
    # Sauvegarde du modèle sklearn localement
    model_path = os.path.join(os.getcwd(), "models/fast/sklearn_model.pkl")
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    
    # Log du modèle avec un input example pour la signature
    # Créer un exemple d'entrée pour inférer la signature
    sample_input = vectorizer.transform(["Exemple de message"]).toarray()
    
    # Log du modèle avec une signature explicite
    mlflow.sklearn.log_model(
        model, 
        "logistic_regression_model",
        input_example=sample_input
    )
    
    # Création d'un modèle TensorFlow simple pour la conversion en TFLite
    def create_tf_model(input_dim):
        # Modèle séquentiel simple avec la dimension d'entrée correcte
        model = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(input_dim,)),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dropout(0.3),  # Augmentation du dropout pour réduire l'overfitting
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dropout(0.2),  # Ajout d'une couche de dropout supplémentaire
            tf.keras.layers.Dense(1, activation='sigmoid')
        ])
        
        model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy', tf.keras.metrics.Precision(), tf.keras.metrics.Recall()]  # Ajout de métriques supplémentaires
        )
        
        return model
    
    # Conversion des données pour TensorFlow
    X_train_dense = X_train_vec.toarray()
    X_test_dense = X_test_vec.toarray()
    
    # Création et entraînement du modèle TensorFlow avec la dimension correcte
    tf_model = create_tf_model(n_features)
    
    # Enable automatic logging pour TensorFlow
    mlflow.tensorflow.autolog()
    
    # Utiliser des class weights pour compenser le déséquilibre des classes
    class_weights = {0: 1.0, 1: len(y_train[y_train <= 0.5]) / len(y_train[y_train > 0.5])}
    
    # Utilisation d'un callback d'early stopping pour éviter l'overfitting
    early_stopping = tf.keras.callbacks.EarlyStopping(
        monitor='val_loss',
        patience=5,
        restore_best_weights=True
    )
    
    tf_model.fit(
        X_train_dense, 
        y_train > 0.5,  # Binarisation pour la classification binaire
        epochs=10,      # Nombre d'époques
        batch_size=16,  # Batch size plus petit
        validation_data=(X_test_dense, y_test > 0.5),
        verbose=1,
        class_weight=class_weights,
        callbacks=[early_stopping]
    )
    
    # Évaluation du modèle TensorFlow
    loss, accuracy, precision, recall = tf_model.evaluate(X_test_dense, y_test > 0.5)
    print(f"Précision du modèle TensorFlow: {accuracy:.4f}")
    print(f"Precision du modèle TensorFlow: {precision:.4f}")
    print(f"Recall du modèle TensorFlow: {recall:.4f}")
    
    # Log explicite des métriques du modèle TensorFlow
    mlflow.log_metric("tf_accuracy", accuracy)
    mlflow.log_metric("tf_loss", loss)
    mlflow.log_metric("tf_precision", precision)
    mlflow.log_metric("tf_recall", recall)
    
    # Log du modèle TensorFlow
    mlflow.tensorflow.log_model(tf_model, "tensorflow_model", input_example=X_test_dense[0:1])
    
    # Conversion en TensorFlow Lite
    converter = tf.lite.TFLiteConverter.from_keras_model(tf_model)
    tflite_model = converter.convert()
    
    # Définir le chemin correct pour la sauvegarde
    model_path = os.path.join(os.getcwd(), "models/fast/fast_toxicity_model.tflite")
    vectorizer_path = os.path.join(os.getcwd(), "models/fast/vectorizer.pkl")
    
    # Sauvegarde du modèle TFLite
    with open(model_path, 'wb') as f:
        f.write(tflite_model)
    
    print(f"Modèle TFLite sauvegardé avec succès à: {model_path}")
    
    # Log de l'artefact TFLite
    mlflow.log_artifact(model_path, "tflite_model")
    
    # Sauvegarde du vocabulaire du vectoriseur pour le prétraitement
    with open(vectorizer_path, 'wb') as f:
        pickle.dump(vectorizer, f)
    
    print(f"Vectoriseur sauvegardé avec succès à: {vectorizer_path}")
    
    # Log du vectoriseur comme artefact
    mlflow.log_artifact(vectorizer_path, "vectorizer")
    
    # Enregistrer des données d'exemple dans MinIO via MLflow
    example_data = {
        "normal_examples": normal_messages[:5],
        "toxic_examples": toxic_messages[:5],
        "ambiguous_examples": ambiguous_messages[:5]
    }
    
    example_path = os.path.join(os.getcwd(), "models/fast/example_data.json")
    with open(example_path, 'w', encoding='utf-8') as f:
        json.dump(example_data, f, indent=2, ensure_ascii=False)
    
    # Log des données d'exemple
    mlflow.log_artifact(example_path, "example_data")
    
    # Création d'un client S3 pour MinIO
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
            s3_client.put_object(Bucket=MINIO_BUCKET, Key='models/fast/')
            print("Dossier 'models/fast/' créé dans MinIO")
        except Exception as e:
            print(f"Note: {e}")
        
        # Upload des fichiers dans MinIO
        print("Upload du modèle TFLite dans MinIO...")
        s3_client.upload_file(
            model_path,
            MINIO_BUCKET,
            'models/fast/fast_toxicity_model.tflite'
        )
        
        print("Upload du vectoriseur dans MinIO...")
        s3_client.upload_file(
            vectorizer_path,
            MINIO_BUCKET,
            'models/fast/vectorizer.pkl'
        )
        
        print("Upload des données d'exemple dans MinIO...")
        s3_client.upload_file(
            example_path,
            MINIO_BUCKET,
            'models/fast/example_data.json'
        )
        
        print("Tous les fichiers ont été uploadés avec succès dans MinIO!")
        
        # Vérification des fichiers uploadés
        response = s3_client.list_objects_v2(
            Bucket=MINIO_BUCKET,
            Prefix='models/fast/'
        )
        
        if 'Contents' in response:
            print("Fichiers disponibles dans MinIO:")
            for obj in response['Contents']:
                print(f" - {obj['Key']} ({obj['Size']} bytes)")
        else:
            print("Aucun fichier trouvé dans models/fast/")
        
    except Exception as e:
        print(f"Erreur lors de l'upload dans MinIO: {e}")
        print("Les modèles ont été sauvegardés localement mais n'ont pas pu être uploadés dans MinIO.")
        print("Veuillez vérifier la configuration de MinIO et les credentials.")

print("Entraînement du modèle fast-classifier terminé et enregistré dans MLflow.")