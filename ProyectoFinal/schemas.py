# schemas.py
from pydantic import BaseModel
from typing import Literal

class PeticionUsuario(BaseModel):
    prompt: str
    usuario_id: int  # Conectado a la DB

class ClasificacionEnrutador(BaseModel):
    complejidad: Literal["baja", "media", "alta"]
    razonamiento: str
