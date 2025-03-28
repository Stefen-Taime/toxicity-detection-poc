from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional, Any
import random
import datetime
import json
import os
from pydantic import BaseModel

app = FastAPI(
    title="MCS100 API Simulator",
    description="Simulateur d'API pour les données de la flotte MCS100",
    version="1.0.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modèles de données
class FlightData(BaseModel):
    timestamp: str
    aircraft_msn: str
    flight_id: str
    altitude: float
    speed: float
    engine_1_temp: float
    engine_2_temp: float
    engine_1_pressure: float
    engine_2_pressure: float
    engine_1_vibration: float
    engine_2_vibration: float
    fuel_flow: float
    external_temp: float
    position: Dict[str, float]

class WeatherData(BaseModel):
    timestamp: str
    location: Dict[str, float]
    temperature: float
    pressure: float
    humidity: float
    wind_speed: float
    wind_direction: float
    precipitation: float
    visibility: float

class MaintenanceRecord(BaseModel):
    record_id: str
    aircraft_msn: str
    component_id: str
    timestamp: str
    maintenance_type: str
    description: str
    technician: str
    duration_hours: float
    parts_replaced: List[Dict[str, Any]]
    findings: List[Dict[str, Any]]

class PartInventory(BaseModel):
    part_id: str
    part_number: str
    description: str
    manufacturer: str
    quantity_available: int
    unit_price: float
    lead_time_days: int
    last_order_date: Optional[str] = None
    location: str
    compatible_aircraft: List[str]

class TechnicalDocument(BaseModel):
    document_id: str
    title: str
    document_type: str
    publication_date: str
    revision: str
    applicable_aircraft: List[str]
    applicable_components: List[str]
    file_path: str
    file_size: int
    file_format: str
    keywords: List[str]

# Données simulées
flight_data_cache = {}
weather_data_cache = {}
maintenance_records_cache = {}
parts_inventory_cache = {}
technical_documents_cache = {}

# Génération de données simulées
def generate_sample_data():
    # Générer des données de vol
    for i in range(1, 1001):
        flight_id = f"FLT-{i:05d}"
        msn = f"MCS100-{random.randint(1, 100):05d}"
        timestamp = datetime.datetime(2023, random.randint(1, 12), random.randint(1, 28), 
                                     random.randint(0, 23), random.randint(0, 59)).isoformat()
        
        flight_data_cache[flight_id] = FlightData(
            timestamp=timestamp,
            aircraft_msn=msn,
            flight_id=flight_id,
            altitude=random.uniform(0, 40000),
            speed=random.uniform(0, 500),
            engine_1_temp=random.uniform(300, 400),
            engine_2_temp=random.uniform(300, 400),
            engine_1_pressure=random.uniform(30, 40),
            engine_2_pressure=random.uniform(30, 40),
            engine_1_vibration=random.uniform(0.1, 1.0),
            engine_2_vibration=random.uniform(0.1, 1.0),
            fuel_flow=random.uniform(1000, 2000),
            external_temp=random.uniform(-50, 30),
            position={
                "latitude": random.uniform(-90, 90),
                "longitude": random.uniform(-180, 180)
            }
        )
    
    # Générer des données météo
    locations = [
        {"name": "Paris", "latitude": 48.8566, "longitude": 2.3522},
        {"name": "New York", "latitude": 40.7128, "longitude": -74.0060},
        {"name": "Tokyo", "latitude": 35.6762, "longitude": 139.6503},
        {"name": "Sydney", "latitude": -33.8688, "longitude": 151.2093},
        {"name": "Dubai", "latitude": 25.2048, "longitude": 55.2708}
    ]
    
    for i in range(1, 501):
        weather_id = f"WTHR-{i:05d}"
        location = random.choice(locations)
        timestamp = datetime.datetime(2023, random.randint(1, 12), random.randint(1, 28), 
                                     random.randint(0, 23), random.randint(0, 59)).isoformat()
        
        weather_data_cache[weather_id] = WeatherData(
            timestamp=timestamp,
            location={
                "name": location["name"],
                "latitude": location["latitude"],
                "longitude": location["longitude"]
            },
            temperature=random.uniform(-20, 40),
            pressure=random.uniform(980, 1030),
            humidity=random.uniform(0, 100),
            wind_speed=random.uniform(0, 100),
            wind_direction=random.uniform(0, 360),
            precipitation=random.uniform(0, 50),
            visibility=random.uniform(0, 10)
        )
    
    # Générer des enregistrements de maintenance
    maintenance_types = ["SCHEDULED", "UNSCHEDULED", "INSPECTION", "REPAIR", "OVERHAUL"]
    
    for i in range(1, 301):
        record_id = f"MAINT-{i:05d}"
        msn = f"MCS100-{random.randint(1, 100):05d}"
        component_id = f"{msn}-COMP-{random.randint(1, 10):04d}"
        timestamp = datetime.datetime(2023, random.randint(1, 12), random.randint(1, 28), 
                                     random.randint(0, 23), random.randint(0, 59)).isoformat()
        
        maintenance_records_cache[record_id] = MaintenanceRecord(
            record_id=record_id,
            aircraft_msn=msn,
            component_id=component_id,
            timestamp=timestamp,
            maintenance_type=random.choice(maintenance_types),
            description=f"Maintenance record {i}",
            technician=f"TECH-{random.randint(1000, 9999)}",
            duration_hours=random.uniform(1, 24),
            parts_replaced=[
                {
                    "part_id": f"PART-{random.randint(1000, 9999)}",
                    "part_number": f"PN-{random.randint(10000, 99999)}",
                    "quantity": random.randint(1, 5),
                    "cost": random.uniform(100, 10000)
                } for _ in range(random.randint(0, 3))
            ],
            findings=[
                {
                    "finding_id": f"FIND-{random.randint(1000, 9999)}",
                    "description": f"Finding {j}",
                    "severity": random.choice(["LOW", "MEDIUM", "HIGH"]),
                    "action_required": random.choice([True, False])
                } for j in range(random.randint(0, 3))
            ]
        )
    
    # Générer des données d'inventaire de pièces
    manufacturers = ["AIRBUS", "SAFRAN", "ROLLS_ROYCE", "GE", "HONEYWELL", "THALES", "ZODIAC"]
    locations = ["WAREHOUSE_A", "WAREHOUSE_B", "WAREHOUSE_C", "EXTERNAL_SUPPLIER"]
    
    for i in range(1, 201):
        part_id = f"PART-{i:05d}"
        
        parts_inventory_cache[part_id] = PartInventory(
            part_id=part_id,
            part_number=f"PN-{random.randint(10000, 99999)}",
            description=f"Part description {i}",
            manufacturer=random.choice(manufacturers),
            quantity_available=random.randint(0, 100),
            unit_price=random.uniform(100, 50000),
            lead_time_days=random.randint(1, 90),
            last_order_date=datetime.date(2023, random.randint(1, 12), random.randint(1, 28)).isoformat() if random.random() > 0.3 else None,
            location=random.choice(locations),
            compatible_aircraft=[f"MCS100-{random.randint(1, 100):05d}" for _ in range(random.randint(1, 5))]
        )
    
    # Générer des documents techniques
    document_types = ["MANUAL", "PROCEDURE", "BULLETIN", "REPORT", "CERTIFICATION"]
    file_formats = ["PDF", "DOC", "XLS", "DWG", "XML"]
    
    for i in range(1, 151):
        document_id = f"DOC-{i:05d}"
        
        technical_documents_cache[document_id] = TechnicalDocument(
            document_id=document_id,
            title=f"Technical document {i}",
            document_type=random.choice(document_types),
            publication_date=datetime.date(2023, random.randint(1, 12), random.randint(1, 28)).isoformat(),
            revision=f"{random.choice('ABCDEFG')}.{random.randint(1, 9)}",
            applicable_aircraft=[f"MCS100-{random.randint(1, 100):05d}" for _ in range(random.randint(1, 5))],
            applicable_components=[f"MCS100-{random.randint(1, 100):05d}-COMP-{random.randint(1, 10):04d}" for _ in range(random.randint(1, 5))],
            file_path=f"/documents/{document_id}.{random.choice(file_formats).lower()}",
            file_size=random.randint(100000, 10000000),
            file_format=random.choice(file_formats),
            keywords=[f"keyword_{j}" for j in range(random.randint(3, 8))]
        )

# Générer les données au démarrage
generate_sample_data()

# Routes API

# Routes pour les données de vol
@app.get("/api/v1/flight-data", response_model=Dict[str, Any], tags=["Flight Data"])
def get_flight_data(
    aircraft_msn: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Récupère les données de vol avec filtrage optionnel.
    """
    filtered_data = list(flight_data_cache.values())
    
    if aircraft_msn:
        filtered_data = [d for d in filtered_data if d.aircraft_msn == aircraft_msn]
    
    if start_date:
        filtered_data = [d for d in filtered_data if d.timestamp >= start_date]
    
    if end_date:
        filtered_data = [d for d in filtered_data if d.timestamp <= end_date]
    
    total = len(filtered_data)
    paginated = filtered_data[offset:offset+limit]
    
    return {
        "items": paginated,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@app.get("/api/v1/flight-data/{flight_id}", response_model=FlightData, tags=["Flight Data"])
def get_flight_data_by_id(flight_id: str):
    """
    Récupère les données d'un vol spécifique.
    """
    if flight_id not in flight_data_cache:
        raise HTTPException(status_code=404, detail=f"Vol {flight_id} non trouvé")
    
    return flight_data_cache[flight_id]

# Routes pour les données météo
@app.get("/api/v1/weather-data", response_model=Dict[str, Any], tags=["Weather Data"])
def get_weather_data(
    location_name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Récupère les données météo avec filtrage optionnel.
    """
    filtered_data = list(weather_data_cache.values())
    
    if location_name:
        filtered_data = [d for d in filtered_data if d.location.get("name") == location_name]
    
    if start_date:
        filtered_data = [d for d in filtered_data if d.timestamp >= start_date]
    
    if end_date:
        filtered_data = [d for d in filtered_data if d.timestamp <= end_date]
    
    total = len(filtered_data)
    paginated = filtered_data[offset:offset+limit]
    
    return {
        "items": paginated,
        "total": total,
        "limit": limit,
        "offset": offset
    }

# Routes pour les enregistrements de maintenance
@app.get("/api/v1/maintenance-records", response_model=Dict[str, Any], tags=["Maintenance Records"])
def get_maintenance_records(
    aircraft_msn: Optional[str] = None,
    component_id: Optional[str] = None,
    maintenance_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Récupère les enregistrements de maintenance avec filtrage optionnel.
    """
    filtered_data = list(maintenance_records_cache.values())
    
    if aircraft_msn:
        filtered_data = [d for d in filtered_data if d.aircraft_msn == aircraft_msn]
    
    if component_id:
        filtered_data = [d for d in filtered_data if d.component_id == component_id]
    
    if maintenance_type:
        filtered_data = [d for d in filtered_data if d.maintenance_type == maintenance_type]
    
    if start_date:
        filtered_data = [d for d in filtered_data if d.timestamp >= start_date]
    
    if end_date:
        filtered_data = [d for d in filtered_data if d.timestamp <= end_date]
    
    total = len(filtered_data)
    paginated = filtered_data[offset:offset+limit]
    
    return {
        "items": paginated,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@app.get("/api/v1/maintenance-records/{record_id}", response_model=MaintenanceRecord, tags=["Maintenance Records"])
def get_maintenance_record_by_id(record_id: str):
    """
    Récupère un enregistrement de maintenance spécifique.
    """
    if record_id not in maintenance_records_cache:
        raise HTTPException(status_code=404, detail=f"Enregistrement de maintenance {record_id} non trouvé")
    
    return maintenance_records_cache[record_id]

# Routes pour l'inventaire des pièces
@app.get("/api/v1/parts-inventory", response_model=Dict[str, Any], tags=["Parts Inventory"])
def get_parts_inventory(
    part_number: Optional[str] = None,
    manufacturer: Optional[str] = None,
    location: Optional[str] = None,
    min_quantity: Optional[int] = None,
    compatible_aircraft: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Récupère l'inventaire des pièces avec filtrage optionnel.
    """
    filtered_data = list(parts_inventory_cache.values())
    
    if part_number:
        filtered_data = [d for d in filtered_data if d.part_number == part_number]
    
    if manufacturer:
        filtered_data = [d for d in filtered_data if d.manufacturer == manufacturer]
    
    if location:
        filtered_data = [d for d in filtered_data if d.location == location]
    
    if min_quantity is not None:
        filtered_data = [d for d in filtered_data if d.quantity_available >= min_quantity]
    
    if compatible_aircraft:
        filtered_data = [d for d in filtered_data if compatible_aircraft in d.compatible_aircraft]
    
    total = len(filtered_data)
    paginated = filtered_data[offset:offset+limit]
    
    return {
        "items": paginated,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@app.get("/api/v1/parts-inventory/{part_id}", response_model=PartInventory, tags=["Parts Inventory"])
def get_part_by_id(part_id: str):
    """
    Récupère les informations d'une pièce spécifique.
    """
    if part_id not in parts_inventory_cache:
        raise HTTPException(status_code=404, detail=f"Pièce {part_id} non trouvée")
    
    return parts_inventory_cache[part_id]

# Routes pour les documents techniques
@app.get("/api/v1/technical-documents", response_model=Dict[str, Any], tags=["Technical Documents"])
def get_technical_documents(
    document_type: Optional[str] = None,
    applicable_aircraft: Optional[str] = None,
    applicable_component: Optional[str] = None,
    keyword: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Récupère les documents techniques avec filtrage optionnel.
    """
    filtered_data = list(technical_documents_cache.values())
    
    if document_type:
        filtered_data = [d for d in filtered_data if d.document_type == document_type]
    
    if applicable_aircraft:
        filtered_data = [d for d in filtered_data if applicable_aircraft in d.applicable_aircraft]
    
    if applicable_component:
        filtered_data = [d for d in filtered_data if applicable_component in d.applicable_components]
    
    if keyword:
        filtered_data = [d for d in filtered_data if keyword in d.keywords]
    
    if start_date:
        filtered_data = [d for d in filtered_data if d.publication_date >= start_date]
    
    if end_date:
        filtered_data = [d for d in filtered_data if d.publication_date <= end_date]
    
    total = len(filtered_data)
    paginated = filtered_data[offset:offset+limit]
    
    return {
        "items": paginated,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@app.get("/api/v1/technical-documents/{document_id}", response_model=TechnicalDocument, tags=["Technical Documents"])
def get_document_by_id(document_id: str):
    """
    Récupère un document technique spécifique.
    """
    if document_id not in technical_documents_cache:
        raise HTTPException(status_code=404, detail=f"Document {document_id} non trouvé")
    
    return technical_documents_cache[document_id]

# Point d'entrée principal
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
