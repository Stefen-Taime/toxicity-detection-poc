from fastapi import FastAPI, HTTPException, Query, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import json
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Création de l'application FastAPI
app = FastAPI(
    title="MCS100 Fleet Analytics API",
    description="API pour l'analyse de performance de la flotte d'avions MCS100 d'Airbus",
    version="1.0.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À ajuster en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration de la base de données
DB_CONFIG = {
    'host': os.environ.get('POSTGRES_HOST', 'timescaledb'),
    'port': int(os.environ.get('POSTGRES_PORT', 5432)),
    'dbname': os.environ.get('POSTGRES_DB', 'mcs100db'),
    'user': os.environ.get('POSTGRES_USER', 'airbus'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'airbus123')
}

# Modèles Pydantic pour la validation des données
class Aircraft(BaseModel):
    aircraft_msn: str
    airline_code: str
    aircraft_type: str = "MCS100"
    manufacturing_date: datetime
    status: str

class Component(BaseModel):
    component_id: str
    aircraft_msn: str
    component_name: str
    component_type: str
    manufacturer: str
    installation_date: datetime
    recommended_maintenance_interval: int

class MaintenanceEvent(BaseModel):
    event_id: Optional[str] = None
    aircraft_msn: str
    component_id: str
    event_timestamp: datetime
    event_type: str
    is_scheduled: bool
    duration_hours: float
    maintenance_action: str
    technician_id: str

class Alert(BaseModel):
    alert_id: Optional[str] = None
    aircraft_msn: str
    component_id: str
    event_timestamp: datetime
    alert_code: str
    severity: str
    description: str

class FlightData(BaseModel):
    aircraft_msn: str
    flight_id: str
    event_timestamp: datetime
    engine_1_temp: float
    engine_2_temp: float
    engine_1_pressure: float
    engine_2_pressure: float
    engine_1_vibration: float
    engine_2_vibration: float
    fuel_flow_rate: float
    altitude: float
    speed: float
    external_temp: float

class UsageCycle(BaseModel):
    aircraft_msn: str
    date: datetime
    flight_hours: float
    takeoffs: int
    landings: int
    apu_cycles: int
    apu_hours: float

class Anomaly(BaseModel):
    anomaly_id: Optional[str] = None
    aircraft_msn: str
    flight_id: str
    event_timestamp: datetime
    detection_timestamp: datetime
    detection_method: str
    confidence_score: float
    abnormal_parameters: List[Dict[str, Any]]
    description: str

class FailurePrediction(BaseModel):
    prediction_id: Optional[str] = None
    aircraft_msn: str
    component_id: str
    prediction_date: datetime
    calculation_timestamp: datetime
    failure_probability: float
    failure_predicted: bool
    days_since_last_maintenance: int
    component_type: str

class MaintenanceRecommendation(BaseModel):
    recommendation_id: Optional[str] = None
    aircraft_msn: str
    component_id: str
    component_type: str
    current_recommended_interval: float
    optimal_interval: float
    recommendation: str
    justification: str
    confidence_score: float
    calculation_timestamp: datetime

class ReliabilityMetric(BaseModel):
    component_id: str
    aircraft_msn: str
    total_failures: int
    unscheduled_failures: int
    total_alerts: int
    critical_alerts: int
    total_flight_hours: float
    total_cycles: int
    mtbf_hours: Optional[float] = None
    failure_rate_per_1000_hours: Optional[float] = None
    calculation_timestamp: datetime

class PerformanceMetric(BaseModel):
    aircraft_msn: str
    airline_code: str
    total_flight_hours: float
    total_takeoffs: int
    total_landings: int
    avg_daily_flight_hours: float
    total_maintenance_events: int
    unscheduled_maintenance_events: int
    total_maintenance_hours: float
    total_alerts: int
    critical_alerts: int
    warning_alerts: int
    avg_engine_1_temp: float
    avg_engine_2_temp: float
    avg_fuel_flow_rate: float
    stddev_engine_1_vibration: float
    stddev_engine_2_vibration: float
    maintenance_events_per_flight_hour: Optional[float] = None
    alerts_per_flight_hour: Optional[float] = None
    unscheduled_maintenance_ratio: Optional[float] = None
    calculation_timestamp: datetime

# Fonction pour établir une connexion à la base de données
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            dbname=DB_CONFIG['dbname'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        logger.error(f"Erreur de connexion à la base de données: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur de connexion à la base de données"
        )

# Dépendance pour obtenir une connexion à la base de données
def get_db():
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()

# Routes pour les avions
@app.get("/aircraft", response_model=List[Aircraft], tags=["Aircraft"])
def get_aircraft(
    airline_code: Optional[str] = None,
    status: Optional[str] = None,
    db: psycopg2.extensions.connection = Depends(get_db)
):
    """
    Récupère la liste des avions avec filtrage optionnel par compagnie aérienne et statut
    """
    try:
        cursor = db.cursor()
        
        query = "SELECT * FROM raw.aircraft_metadata WHERE 1=1"
        params = []
        
        if airline_code:
            query += " AND airline_code = %s"
            params.append(airline_code)
        
        if status:
            query += " AND status = %s"
            params.append(status)
        
        cursor.execute(query, params)
        result = cursor.fetchall()
        
        return result
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des avions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des avions: {str(e)}"
        )

@app.get("/aircraft/{aircraft_msn}", response_model=Aircraft, tags=["Aircraft"])
def get_aircraft_by_msn(
    aircraft_msn: str,
    db: psycopg2.extensions.connection = Depends(get_db)
):
    """
    Récupère les détails d'un avion spécifique par son numéro de série
    """
    try:
        cursor = db.cursor()
        
        query = "SELECT * FROM raw.aircraft_metadata WHERE aircraft_msn = %s"
        cursor.execute(query, (aircraft_msn,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Avion avec MSN {aircraft_msn} non trouvé"
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'avion {aircraft_msn}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération de l'avion: {str(e)}"
        )

@app.post("/aircraft", response_model=Aircraft, status_code=status.HTTP_201_CREATED, tags=["Aircraft"])
def create_aircraft(
    aircraft: Aircraft,
    db: psycopg2.extensions.connection = Depends(get_db)
):
    """
    Crée un nouvel avion
    """
    try:
        cursor = db.cursor()
        
        # Vérification si l'avion existe déjà
        cursor.execute(
            "SELECT * FROM raw.aircraft_metadata WHERE aircraft_msn = %s",
            (aircraft.aircraft_msn,)
        )
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Un avion avec MSN {aircraft.aircraft_msn} existe déjà"
            )
        
        # Insertion du nouvel avion
        query = """
        INSERT INTO raw.aircraft_metadata (
            aircraft_msn, airline_code, aircraft_type, manufacturing_date, status
        ) VALUES (%s, %s, %s, %s, %s)
        RETURNING *
        """
        cursor.execute(
            query,
            (
                aircraft.aircraft_msn,
                aircraft.airline_code,
                aircraft.aircraft_type,
                aircraft.manufacturing_date,
                aircraft.status
            )
        )
        db.commit()
        
        result = cursor.fetchone()
        return result
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erreur lors de la création de l'avion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la création de l'avion: {str(e)}"
        )

# Routes pour les composants
@app.get("/components", response_model=List[Component], tags=["Components"])
def get_components(
    aircraft_msn: Optional[str] = None,
    component_type: Optional[str] = None,
    manufacturer: Optional[str] = None,
    db: psycopg2.extensions.connection = Depends(get_db)
):
    """
    Récupère la liste des composants avec filtrage optionnel
    """
    try:
        cursor = db.cursor()
        
        query = "SELECT * FROM raw.components WHERE 1=1"
        params = []
        
        if aircraft_msn:
            query += " AND aircraft_msn = %s"
            params.append(aircraft_msn)
        
        if component_type:
            query += " AND component_type = %s"
            params.append(component_type)
        
        if manufacturer:
            query += " AND manufacturer = %s"
            params.append(manufacturer)
        
        cursor.execute(query, params)
        result = cursor.fetchall()
        
        return result
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des composants: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des composants: {str(e)}"
        )

@app.get("/components/{component_id}", response_model=Component, tags=["Components"])
def get_component_by_id(
    component_id: str,
    db: psycopg2.extensions.connection = Depends(get_db)
):
    """
    Récupère les détails d'un composant spécifique par son ID
    """
    try:
        cursor = db.cursor()
        
        query = "SELECT * FROM raw.components WHERE component_id = %s"
        cursor.execute(query, (component_id,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Composant avec ID {component_id} non trouvé"
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du composant {component_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération du composant: {str(e)}"
        )

# Routes pour les événements de maintenance
@app.get("/maintenance", response_model=List[MaintenanceEvent], tags=["Maintenance"])
def get_maintenance_events(
    aircraft_msn: Optional[str] = None,
    component_id: Optional[str] = None,
    event_type: Optional[str] = None,
    is_scheduled: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=1000),
    db: psycopg2.extensions.connection = Depends(get_db)
):
    """
    Récupère la liste des événements de maintenance avec filtrage optionnel
    """
    try:
        cursor = db.cursor()
        
        query = "SELECT * FROM raw.maintenance_events WHERE 1=1"
        params = []
        
        if aircraft_msn:
            query += " AND aircraft_msn = %s"
            params.append(aircraft_msn)
        
        if component_id:
            query += " AND component_id = %s"
            params.append(component_id)
        
        if event_type:
            query += " AND event_type = %s"
            params.append(event_type)
        
        if is_scheduled is not None:
            query += " AND is_scheduled = %s"
            params.append(is_scheduled)
        
        if start_date:
            query += " AND event_timestamp >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND event_timestamp <= %s"
            params.append(end_date)
        
        query += " ORDER BY event_timestamp DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        result = cursor.fetchall()
        
        return result
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des événements de maintenance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des événements de maintenance: {str(e)}"
        )

@app.post("/maintenance", response_model=MaintenanceEvent, status_code=status.HTTP_201_CREATED, tags=["Maintenance"])
def create_maintenance_event(
    event: MaintenanceEvent,
    db: psycopg2.extensions.connection = Depends(get_db)
):
    """
    Crée un nouvel événement de maintenance
    """
    try:
        cursor = db.cursor()
        
        # Vérification si le composant existe
        cursor.execute(
            "SELECT * FROM raw.components WHERE component_id = %s AND aircraft_msn = %s",
            (event.component_id, event.aircraft_msn)
        )
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Composant avec ID {event.component_id} pour l'avion {event.aircraft_msn} non trouvé"
            )
        
        # Génération d'un ID d'événement si non fourni
        if not event.event_id:
            event.event_id = f"ME-{datetime.now().strftime('%Y%m%d%H%M%S')}-{event.aircraft_msn[-4:]}"
        
        # Insertion du nouvel événement
        query = """
        INSERT INTO raw.maintenance_events (
            event_id, aircraft_msn, component_id, event_timestamp, event_type,
            is_scheduled, duration_hours, maintenance_action, technician_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
        """
        cursor.execute(
            query,
            (
                event.event_id,
                event.aircraft_msn,
                event.component_id,
                event.event_timestamp,
                event.event_type,
                event.is_scheduled,
                event.duration_hours,
                event.maintenance_action,
                event.technician_id
            )
        )
        db.commit()
        
        result = cursor.fetchone()
        return result
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erreur lors de la création de l'événement de maintenance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la création de l'événement de mainten<response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>