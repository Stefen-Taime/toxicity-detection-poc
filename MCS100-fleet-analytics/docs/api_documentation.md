# Documentation de l'API

Cette documentation détaille les endpoints de l'API REST fournie par la solution MCS100 Fleet Analytics.

## Informations générales

- **Base URL** : `http://localhost:8000` (ou l'URL configurée dans votre environnement)
- **Format** : Toutes les requêtes et réponses sont au format JSON
- **Authentification** : API Key dans l'en-tête HTTP `X-API-Key`
- **Documentation interactive** : Disponible à `http://localhost:8000/docs`

## Authentification

Pour accéder à l'API, vous devez inclure une clé API valide dans l'en-tête de vos requêtes :

```
X-API-Key: votre-clé-api
```

Pour obtenir une clé API, contactez l'administrateur du système ou générez-en une via l'interface d'administration.

## Endpoints

### Avions

#### Obtenir la liste des avions

```
GET /api/v1/aircraft
```

**Paramètres de requête** :
- `airline` (optionnel) : Filtrer par compagnie aérienne
- `status` (optionnel) : Filtrer par statut (`active`, `maintenance`, `storage`)
- `limit` (optionnel) : Nombre maximum d'avions à retourner (défaut: 100)
- `offset` (optionnel) : Décalage pour la pagination (défaut: 0)

**Exemple de réponse** :
```json
{
  "items": [
    {
      "msn": "MCS100-10001",
      "type": "MCS100",
      "airline": "Air France",
      "registration": "AF-1001",
      "manufacturing_date": "2020-05-15",
      "entry_into_service_date": "2020-06-20",
      "status": "active"
    },
    {
      "msn": "MCS100-10002",
      "type": "MCS100",
      "airline": "Lufthansa",
      "registration": "LH-1002",
      "manufacturing_date": "2020-07-10",
      "entry_into_service_date": "2020-08-15",
      "status": "maintenance"
    }
  ],
  "total": 120,
  "limit": 100,
  "offset": 0
}
```

#### Obtenir les détails d'un avion

```
GET /api/v1/aircraft/{msn}
```

**Paramètres de chemin** :
- `msn` : Numéro de série de l'avion (MSN)

**Exemple de réponse** :
```json
{
  "msn": "MCS100-10001",
  "type": "MCS100",
  "airline": "Air France",
  "registration": "AF-1001",
  "manufacturing_date": "2020-05-15",
  "entry_into_service_date": "2020-06-20",
  "status": "active",
  "total_flight_hours": 5240.5,
  "total_cycles": 1245,
  "last_maintenance_date": "2023-03-10",
  "next_maintenance_date": "2023-09-15"
}
```

### Composants

#### Obtenir la liste des composants

```
GET /api/v1/components
```

**Paramètres de requête** :
- `aircraft_msn` (optionnel) : Filtrer par MSN d'avion
- `component_type` (optionnel) : Filtrer par type de composant
- `limit` (optionnel) : Nombre maximum de composants à retourner (défaut: 100)
- `offset` (optionnel) : Décalage pour la pagination (défaut: 0)

**Exemple de réponse** :
```json
{
  "items": [
    {
      "id": "MCS100-10001-COMP-0001",
      "name": "ENGINE 1",
      "type": "ENGINE",
      "aircraft_msn": "MCS100-10001",
      "installation_date": "2020-05-15",
      "current_interval_hours": 3000,
      "total_flight_hours": 5240.5,
      "last_maintenance_date": "2022-11-05"
    },
    {
      "id": "MCS100-10001-COMP-0002",
      "name": "ENGINE 2",
      "type": "ENGINE",
      "aircraft_msn": "MCS100-10001",
      "installation_date": "2020-05-15",
      "current_interval_hours": 3000,
      "total_flight_hours": 5240.5,
      "last_maintenance_date": "2022-11-05"
    }
  ],
  "total": 85,
  "limit": 100,
  "offset": 0
}
```

#### Obtenir les détails d'un composant

```
GET /api/v1/components/{component_id}
```

**Paramètres de chemin** :
- `component_id` : Identifiant du composant

**Exemple de réponse** :
```json
{
  "id": "MCS100-10001-COMP-0001",
  "name": "ENGINE 1",
  "type": "ENGINE",
  "aircraft_msn": "MCS100-10001",
  "installation_date": "2020-05-15",
  "current_interval_hours": 3000,
  "total_flight_hours": 5240.5,
  "last_maintenance_date": "2022-11-05",
  "manufacturer": "Safran",
  "part_number": "ENG-CFM-001",
  "serial_number": "SN-12345",
  "reliability_metrics": {
    "mtbf_hours": 4500.2,
    "failure_rate_per_1000h": 0.22,
    "unscheduled_removal_rate": 0.15
  }
}
```

### Événements de maintenance

#### Obtenir la liste des événements de maintenance

```
GET /api/v1/maintenance/events
```

**Paramètres de requête** :
- `aircraft_msn` (optionnel) : Filtrer par MSN d'avion
- `component_id` (optionnel) : Filtrer par identifiant de composant
- `event_type` (optionnel) : Filtrer par type d'événement
- `start_date` (optionnel) : Date de début (format: YYYY-MM-DD)
- `end_date` (optionnel) : Date de fin (format: YYYY-MM-DD)
- `is_scheduled` (optionnel) : Filtrer par événements planifiés/non planifiés
- `limit` (optionnel) : Nombre maximum d'événements à retourner (défaut: 100)
- `offset` (optionnel) : Décalage pour la pagination (défaut: 0)

**Exemple de réponse** :
```json
{
  "items": [
    {
      "id": "evt-12345",
      "aircraft_msn": "MCS100-10001",
      "component_id": "MCS100-10001-COMP-0001",
      "event_timestamp": "2022-11-05T08:30:00Z",
      "event_type": "INSPECTION",
      "description": "Inspection du moteur 1",
      "action_taken": "Inspection complète réalisée",
      "technician": "TECH-1234",
      "duration_hours": 4.5,
      "is_scheduled": true
    },
    {
      "id": "evt-12346",
      "aircraft_msn": "MCS100-10001",
      "component_id": "MCS100-10001-COMP-0002",
      "event_timestamp": "2022-11-05T13:15:00Z",
      "event_type": "REPAIR",
      "description": "Réparation du moteur 2",
      "action_taken": "Remplacement des pièces défectueuses",
      "technician": "TECH-5678",
      "duration_hours": 8.2,
      "is_scheduled": false
    }
  ],
  "total": 342,
  "limit": 100,
  "offset": 0
}
```

#### Obtenir les détails d'un événement de maintenance

```
GET /api/v1/maintenance/events/{event_id}
```

**Paramètres de chemin** :
- `event_id` : Identifiant de l'événement de maintenance

**Exemple de réponse** :
```json
{
  "id": "evt-12345",
  "aircraft_msn": "MCS100-10001",
  "component_id": "MCS100-10001-COMP-0001",
  "event_timestamp": "2022-11-05T08:30:00Z",
  "event_type": "INSPECTION",
  "description": "Inspection du moteur 1",
  "action_taken": "Inspection complète réalisée",
  "technician": "TECH-1234",
  "duration_hours": 4.5,
  "is_scheduled": true,
  "findings": [
    {
      "finding_id": "find-001",
      "description": "Usure normale des aubes de turbine",
      "severity": "LOW",
      "action_required": false
    },
    {
      "finding_id": "find-002",
      "description": "Légère corrosion sur le carter",
      "severity": "MEDIUM",
      "action_required": true,
      "recommended_action": "Traitement anti-corrosion lors de la prochaine maintenance"
    }
  ],
  "parts_replaced": [],
  "documents": [
    {
      "document_id": "doc-123",
      "title": "Rapport d'inspection du moteur 1",
      "file_path": "/documents/inspections/doc-123.pdf"
    }
  ]
}
```

### Alertes

#### Obtenir la liste des alertes

```
GET /api/v1/alerts
```

**Paramètres de requête** :
- `aircraft_msn` (optionnel) : Filtrer par MSN d'avion
- `component_id` (optionnel) : Filtrer par identifiant de composant
- `severity` (optionnel) : Filtrer par niveau de sévérité (`INFO`, `WARNING`, `CRITICAL`)
- `start_date` (optionnel) : Date de début (format: YYYY-MM-DD)
- `end_date` (optionnel) : Date de fin (format: YYYY-MM-DD)
- `limit` (optionnel) : Nombre maximum d'alertes à retourner (défaut: 100)
- `offset` (optionnel) : Décalage pour la pagination (défaut: 0)

**Exemple de réponse** :
```json
{
  "items": [
    {
      "id": "alt-12345",
      "aircraft_msn": "MCS100-10001",
      "component_id": "MCS100-10001-COMP-0001",
      "event_timestamp": "2023-03-15T14:22:30Z",
      "alert_code": "ALT-ENG-123",
      "severity": "WARNING",
      "message": "Température du moteur 1 anormalement élevée"
    },
    {
      "id": "alt-12346",
      "aircraft_msn": "MCS100-10002",
      "component_id": "MCS100-10002-COMP-0005",
      "event_timestamp": "2023-03-15T16:45:12Z",
      "alert_code": "ALT-HYD-456",
      "severity": "CRITICAL",
      "message": "Pression hydraulique basse détectée"
    }
  ],
  "total": 78,
  "limit": 100,
  "offset": 0
}
```

#### Obtenir les détails d'une alerte

```
GET /api/v1/alerts/{alert_id}
```

**Paramètres de chemin** :
- `alert_id` : Identifiant de l'alerte

**Exemple de réponse** :
```json
{
  "id": "alt-12345",
  "aircraft_msn": "MCS100-10001",
  "component_id": "MCS100-10001-COMP-0001",
  "event_timestamp": "2023-03-15T14:22:30Z",
  "alert_code": "ALT-ENG-123",
  "severity": "WARNING",
  "message": "Température du moteur 1 anormalement élevée",
  "details": {
    "measured_value": 358.5,
    "threshold": 350.0,
    "unit": "°C",
    "flight_id": "FLT-MCS100-10001-20230315-001",
    "flight_phase": "cruise",
    "altitude": 35000,
    "speed": 480
  },
  "recommended_actions": [
    "Vérifier le système de refroidissement du moteur",
    "Inspecter les capteurs de température",
    "Planifier une maintenance préventive"
  ],
  "related_alerts": [
    "alt-12340",
    "alt-12342"
  ]
}
```

### Données de vol

#### Obtenir les données de vol

```
GET /api/v1/flight-data
```

**Paramètres de requête** :
- `aircraft_msn` (optionnel) : Filtrer par MSN d'avion
- `flight_id` (optionnel) : Filtrer par identifiant de vol
- `start_date` (optionnel) : Date de début (format: YYYY-MM-DD)
- `end_date` (optionnel) : Date de fin (format: YYYY-MM-DD)
- `limit` (optionnel) : Nombre maximum de points de données à retourner (défaut: 1000)
- `offset` (optionnel) : Décalage pour la pagination (défaut: 0)

**Exemple de réponse** :
```json
{
  "items": [
    {
      "aircraft_msn": "MCS100-10001",
      "flight_id": "FLT-MCS100-10001-20230315-001",
      "event_timestamp": "2023-03-15T10:00:00Z",
      "engine_1_temp": 320.5,
      "engine_2_temp": 318.2,
      "engine_1_pressure": 35.2,
      "engine_2_pressure": 35.4,
      "engine_1_vibration": 0.8,
      "engine_2_vibration": 0.7,
      "fuel_flow_rate": 1250.0,
      "altitude": 35000.0,
      "speed": 480.0,
      "external_temp": -45.0,
      "wind_speed": 25.0,
      "wind_direction": 270.0
    },
    {
      "aircraft_msn": "MCS100-10001",
      "flight_id": "FLT-MCS100-10001-20230315-001",
      "event_timestamp": "2023-03-15T10:05:00Z",
      "engine_1_temp": 322.1,
      "engine_2_temp": 319.5,
      "engine_1_pressure": 35.1,
      "engine_2_pressure": 35.3,
      "engine_1_vibration": 0.9,
      "engine_2_vibration": 0.7,
      "fuel_flow_rate": 1248.0,
      "altitude": 35000.0,
      "speed": 482.0,
      "external_temp": -45.2,
      "wind_speed": 26.0,
      "wind_direction": 268.0
    }
  ],
  "total": 144000,
  "limit": 1000,
  "offset": 0
}
```

#### Obtenir les données de vol agrégées

```
GET /api/v1/flight-data/aggregated
```

**Paramètres de requête** :
- `aircraft_msn` (requis) : MSN de l'avion
- `start_date` (requis) : Date de début (format: YYYY-MM-DD)
- `end_date` (requis) : Date de fin (format: YYYY-MM-DD)
- `interval` (optionnel) : Intervalle d'agrégation (`hour`, `day`, `week`, `month`, défaut: `hour`)
- `metrics` (optionnel) : Liste des métriques à agréger (séparées par des virgules)

**Exemple de réponse** :
```json
{
  "items": [
    {
      "timestamp": "2023-03-15T10:00:00Z",
      "engine_1_temp_avg": 321.3,
      "engine_1_temp_min": 320.5,
      "engine_1_temp_max": 322.1,
      "engine_2_temp_avg": 318.9,
      "engine_2_temp_min": 318.2,
      "engine_2_temp_max": 319.5,
      "altitude_avg": 35000.0,
      "speed_avg": 481.0
    },
    {
      "timestamp": "2023-03-15T11:00:00Z",
      "engine_1_temp_avg": 325.7,
      "engine_1_temp_min": 323.2,
      "engine_1_temp_max": 328.4,
      "engine_2_temp_avg": 322.1,
      "engine_2_temp_min": 320.5,
      "engine_2_temp_max": 324.8,
      "altitude_avg": 35000.0,
      "speed_avg": 485.0
    }
  ],
  "total": 24,
  "interval": "hour"
}
```

### Cycles d'utilisation

#### Obtenir les cycles d'utilisation

```
GET /api/v1/usage-cycles
```

**Paramètres de requête** :
- `aircraft_msn` (optionnel) : Filtrer par MSN d'avion
- `start_date` (optionnel) : Date de début (format: YYYY-MM-DD)
- `end_date` (optionnel) : Date de fin (format: YYYY-MM-DD)
- `limit` (optionnel) : Nombre maximum de cycles à retourner (défaut: 100)
- `offset` (optionnel) : Décalage pour la pagination (défaut: 0)

**Exemple de réponse** :
```json
{
  "items": [
    {
      "aircraft_msn": "MCS100-10001",
      "date": "2023-03-15",
      "flight_hours": 12.5,
      "takeoffs": 3,
      "landings": 3
    },
    {
      "aircraft_msn": "MCS100-10001",
      "date": "2023-03-16",
      "flight_hours": 8.2,
      "takeoffs": 2,
      "landings": 2
    }
  ],
  "total": 365,
  "limit": 100,
  "offset": 0
}
```

### Anomalies

#### Obtenir les anomalies détectées

```
GET /api/v1/anomalies
```

**Paramètres de requête** :
- `aircraft_msn` (optionnel) : Filtrer par MSN d'avion
- `flight_id` (optionnel) : Filtrer par identifiant de vol
- `anomaly_type` (optionnel) : Filtrer par type d'anomalie
- `min_confidence` (optionnel) : Confiance minimale (0.0 - 1.0)
- `start_date` (optionnel) : Date de début (format: YYYY-MM-DD)
- `end_date` (optionnel) : Date de fin (format: YYYY-MM-DD)
- `limit` (optionnel) : Nombre maximum d'anomalies à retourner (défaut: 100)
- `offset` (optionnel) : Décalage pour la pagination (défaut: 0)

**Exemple de réponse** :
```json
{
  "items": [
    {
      "id": "anom-12345",
      "aircraft_msn": "MCS100-10001",
      "flight_id": "FLT-MCS100-10001-20230315-001",
      "detection_timestamp": "2023-03-15T15:30:00Z",
      "anomaly_type": "ENGINE_TEMPERATURE_ANOMALY",
      "confidence_score": 0.92,
      "description": "Température moteur anormalement élevée détectée"
    },
    {
      "id": "anom-12346",
      "aircraft_msn": "MCS100-10002",
      "flight_id": "FLT-MCS100-10002-20230316-002",
      "detection_timestamp": "2023-03-16T10:15:00Z",
      "anomaly_type": "FUEL_FLOW_ANOMALY",
      "confidence_score": 0.85,
      "description": "Débit de carburant anormal détecté"
    }
  ],
  "total": 28,
  "limit": 100,
  "offset": 0
}
```

#### Obtenir les détails d'une anomalie

```
GET /api/v1/anomalies/{anomaly_id}
```

**Paramètres de chemin** :
- `anomaly_id` : Identifiant de l'anomalie

**Exemple de réponse** :
```json
{
  "id": "anom-12345",
  "aircraft_msn": "MCS100-10001",
  "flight_id": "FLT-MCS100-10001-20230315-001",
  "detection_timestamp": "2023-03-15T15:30:00Z",
  "anomaly_type": "ENGINE_TEMPERATURE_ANOMALY",
  "confidence_score": 0.92,
  "description": "Température moteur anormalement élevée détectée",
  "details": {
    "component_id": "MCS100-10001-COMP-0001",
    "anomaly_start": "2023-03-15T14:15:00Z",
    "anomaly_end": "2023-03-15T14:35:00Z",
    "normal_range": {
      "min": 300.0,
      "max": 350.0
    },
    "observed_values": [
      {
        "timestamp": "2023-03-15T14:15:00Z",
        "value": 352.3
      },
      {
        "timestamp": "2023-03-15T14:20:00Z",
        "value": 358.7
      },
      {
        "timestamp": "2023-03-15T14:25:00Z",
        "value": 362.1
      },
      {
        "timestamp": "2023-03-15T14:30:00Z",
        "value": 359.4
      },
      {
        "timestamp": "2023-03-15T14:35:00Z",
        "value": 348.2
      }
    ],
    "detection_method": "ISOLATION_FOREST",
    "contributing_factors": [
      {
        "factor": "external_temp",
        "importance": 0.65
      },
      {
        "factor": "altitude",
        "importance": 0.25
      },
      {
        "factor": "fuel_flow_rate",
        "importance": 0.10
      }
    ]
  },
  "recommended_actions": [
    "Vérifier le système de refroidissement du moteur",
    "Inspecter les capteurs de température",
    "Planifier une maintenance préventive"
  ],
  "related_anomalies": [
    "anom-12340",
    "anom-12342"
  ]
}
```

### Métriques de fiabilité

#### Obtenir les métriques de fiabilité

```
GET /api/v1/reliability-metrics
```

**Paramètres de requête** :
- `component_id` (optionnel) : Filtrer par identifiant de composant
- `component_type` (optionnel) : Filtrer par type de composant
- `aircraf<response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>