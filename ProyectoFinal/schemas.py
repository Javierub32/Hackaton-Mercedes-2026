from pydantic import BaseModel
from typing import Literal

class PeticionUsuario(BaseModel):
    prompt: str
    usuario_id: int

class ClasificacionEnrutador(BaseModel):
    complejidad: Literal["baja", "media", "alta"]
    razonamiento: str
