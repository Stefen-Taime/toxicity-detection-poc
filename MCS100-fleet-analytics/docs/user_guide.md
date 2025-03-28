# Guide d'utilisation

Ce guide détaille l'utilisation de la solution MCS100 Fleet Analytics pour l'analyse de performance de la flotte d'avions MCS100 d'Airbus.

## Vue d'ensemble

MCS100 Fleet Analytics est une solution complète pour l'analyse de fiabilité et de performance des avions MCS100. Elle permet de :

- Collecter et stocker les données de performance des avions
- Analyser la fiabilité des composants et systèmes
- Visualiser les KPIs et métriques importantes
- Générer des alertes sur les anomalies détectées
- Prédire les défaillances potentielles

## Interfaces utilisateur

La solution propose plusieurs interfaces utilisateur :

### 1. Tableaux de bord Grafana

Grafana est l'interface principale pour visualiser les données en temps réel et les analyses historiques.

**Accès** : http://localhost:3000 (ou l'URL configurée dans votre environnement)

**Tableaux de bord disponibles** :

- **Fleet Overview** : Vue d'ensemble de la flotte avec statut des avions, métriques globales et alertes
- **Aircraft Details** : Informations détaillées sur un avion spécifique
- **Component Reliability** : Analyse de fiabilité des composants (MTBF, taux de défaillance)
- **Maintenance Optimization** : Recommandations pour l'optimisation des intervalles de maintenance
- **Anomaly Detection** : Visualisation des anomalies détectées dans les données de vol
- **Airline Comparison** : Analyse comparative des performances entre différentes compagnies aériennes
- **Technical Modifications** : Évaluation de l'impact des modifications techniques sur la fiabilité

### 2. Rapports Metabase

Metabase offre des rapports plus détaillés et des analyses ad hoc pour les utilisateurs non techniques.

**Accès** : http://localhost:3030 (ou l'URL configurée dans votre environnement)

**Rapports disponibles** :

- **Reliability Reports** : Rapports mensuels et trimestriels sur la fiabilité des composants
- **Maintenance Efficiency** : Analyse de l'efficacité des programmes de maintenance
- **Anomaly Analysis** : Analyse détaillée des anomalies détectées
- **Cost Optimization** : Rapports sur les économies potentielles grâce à l'optimisation de la maintenance

### 3. API REST

L'API REST permet d'accéder programmatiquement à toutes les fonctionnalités de la solution.

**Documentation** : http://localhost:8000/docs (ou l'URL configurée dans votre environnement)

## Cas d'utilisation

### 1. Analyse de la fiabilité des composants

Pour analyser la fiabilité des composants :

1. Accédez au tableau de bord Grafana "Component Reliability"
2. Sélectionnez la période d'analyse et le type de composant
3. Consultez les métriques de fiabilité (MTBF, taux de défaillance)
4. Identifiez les composants les moins fiables
5. Analysez les tendances de fiabilité au fil du temps

**Exemple** : Pour analyser la fiabilité des moteurs sur les 6 derniers mois :
- Sélectionnez "ENGINE" dans le filtre "Component Type"
- Définissez la période sur "Last 6 months"
- Consultez le graphique "MTBF by Component" pour identifier les moteurs les moins fiables
- Utilisez le tableau "Failure Rate Trend" pour analyser l'évolution des taux de défaillance

### 2. Prédiction des intervalles de maintenance optimaux

Pour optimiser les intervalles de maintenance :

1. Accédez au tableau de bord Grafana "Maintenance Optimization"
2. Sélectionnez le type de composant à optimiser
3. Consultez les recommandations d'intervalles de maintenance
4. Analysez les économies potentielles
5. Exportez les recommandations pour mise en œuvre

**Exemple** : Pour optimiser les intervalles de maintenance des trains d'atterrissage :
- Sélectionnez "LANDING_GEAR" dans le filtre "Component Type"
- Consultez le tableau "Recommended Maintenance Intervals"
- Analysez les économies potentielles dans le graphique "Potential Savings"
- Cliquez sur "Export Recommendations" pour télécharger un rapport détaillé

### 3. Détection d'anomalies dans les données de vol

Pour détecter et analyser les anomalies :

1. Accédez au tableau de bord Grafana "Anomaly Detection"
2. Sélectionnez l'avion et la période d'analyse
3. Consultez les anomalies détectées
4. Analysez les détails de chaque anomalie
5. Vérifiez les données de vol correspondantes

**Exemple** : Pour analyser les anomalies de température moteur :
- Sélectionnez l'avion dans le filtre "Aircraft"
- Filtrez par "ENGINE_TEMPERATURE_ANOMALY" dans "Anomaly Type"
- Cliquez sur une anomalie spécifique pour voir les détails
- Consultez le graphique "Flight Data" pour voir les données de vol au moment de l'anomalie

### 4. Analyse comparative des performances entre compagnies aériennes

Pour comparer les performances entre compagnies aériennes :

1. Accédez au tableau de bord Grafana "Airline Comparison"
2. Sélectionnez les compagnies aériennes à comparer
3. Choisissez les métriques de performance
4. Analysez les différences de performance
5. Identifiez les meilleures pratiques

**Exemple** : Pour comparer les taux de défaillance entre Air France et Lufthansa :
- Sélectionnez "Air France" et "Lufthansa" dans le filtre "Airlines"
- Consultez le graphique "Failure Rate Comparison"
- Analysez les différences par type de composant
- Utilisez le tableau "Maintenance Practices Comparison" pour identifier les différences dans les pratiques de maintenance

### 5. Évaluation de l'impact des modifications techniques

Pour évaluer l'impact des modifications techniques :

1. Accédez au tableau de bord Grafana "Technical Modifications"
2. Sélectionnez le type de modification
3. Analysez les métriques de fiabilité avant et après modification
4. Évaluez le retour sur investissement
5. Générez un rapport d'impact

**Exemple** : Pour évaluer l'impact d'une modification du système hydraulique :
- Sélectionnez "HYDRAULIC_SYSTEM_UPGRADE" dans le filtre "Modification Type"
- Consultez le graphique "Before vs After Reliability Metrics"
- Analysez le ROI dans le tableau "Modification ROI Analysis"
- Cliquez sur "Generate Impact Report" pour créer un rapport détaillé

## Fonctionnalités avancées

### 1. Alertes et notifications

La solution peut envoyer des alertes automatiques basées sur différents critères :

1. Accédez à la section "Alerting" de Grafana
2. Configurez les règles d'alerte selon vos besoins
3. Définissez les canaux de notification (email, Slack, etc.)
4. Activez les alertes

**Exemple de règle d'alerte** : Notification lorsque le MTBF d'un composant tombe en dessous d'un seuil critique.

### 2. Analyses personnalisées

Pour créer des analyses personnalisées :

1. Utilisez l'interface Metabase pour créer des requêtes ad hoc
2. Créez des tableaux de bord personnalisés dans Grafana
3. Utilisez l'API REST pour extraire des données spécifiques
4. Utilisez les notebooks Jupyter pour des analyses avancées

### 3. Intégration avec d'autres systèmes

La solution peut être intégrée avec d'autres systèmes via :

- **API REST** : Pour l'intégration avec des applications tierces
- **Webhooks** : Pour déclencher des actions dans d'autres systèmes
- **Exportation de données** : Pour l'analyse dans d'autres outils

## Maintenance de la solution

### 1. Sauvegarde des données

Pour sauvegarder les données :

```bash
./scripts/backup.sh
```

Les sauvegardes sont stockées dans le répertoire `backups/` par défaut.

### 2. Mise à jour des modèles

Les modèles de machine learning sont automatiquement réentraînés périodiquement. Pour forcer un réentraînement :

```bash
./scripts/retrain_models.sh
```

### 3. Surveillance des performances

Pour surveiller les performances de la solution :

1. Accédez au tableau de bord Grafana "System Monitoring"
2. Vérifiez l'utilisation des ressources (CPU, mémoire, disque)
3. Surveillez les temps de réponse des requêtes
4. Vérifiez les journaux des services

## Multilingue

La solution est disponible en français et en anglais. Pour changer la langue :

1. Cliquez sur l'icône utilisateur dans le coin supérieur droit
2. Sélectionnez "Preferences"
3. Choisissez la langue souhaitée dans le menu déroulant
4. Cliquez sur "Save"

## Support et assistance

En cas de problème ou de question :

1. Consultez la documentation détaillée dans le répertoire `docs/`
2. Vérifiez les journaux des services concernés
3. Contactez l'équipe de support à support@mcs100-fleet-analytics.com

## Glossaire

- **MTBF** : Mean Time Between Failures (Temps moyen entre pannes)
- **MTTR** : Mean Time To Repair (Temps moyen de réparation)
- **KPI** : Key Performance Indicator (Indicateur clé de performance)
- **ROI** : Return On Investment (Retour sur investissement)
- **ML** : Machine Learning (Apprentissage automatique)
