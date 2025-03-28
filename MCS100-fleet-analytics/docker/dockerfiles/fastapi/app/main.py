from fastapi import FastAPI, HTTPException, Depends, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
import os
import json
import datetime
import random
import uuid
from pydantic import BaseModel

# Initialisation de l'application FastAPI
app = FastAPI(
    title="MCS100 Fleet Analytics API",
    description="API pour l'analyse de performance de la flotte d'avions MCS100 d'Airbus",
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

# Point d'entrée principal
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
