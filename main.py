import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel  # 👈 Usaremos esto para todo
from google import genai
from google.genai import types
from typing import Literal

app = FastAPI(title="Backend Base IA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = genai.Client()

# 👈 SOLUCIÓN AQUÍ: Cambiamos typing.TypedDict por BaseModel
class AnalisisTaller(BaseModel):
    modelo_coche: str
    pieza_afectada: str
    nivel_urgencia: Literal["bajo", "medio", "alto", "extremo"]
    requiere_grua: bool
    resumen_tecnico: str

class PeticionUsuario(BaseModel):
    prompt: str

@app.post("/generar")
def generar_respuesta(peticion: PeticionUsuario):
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=f"Analiza este problema de un cliente y extrae los datos en el formato solicitado: {peticion.prompt}",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AnalisisTaller  # 👈 Gemini entiende Pydantic perfectamente
            )
        )
        
        json_estructurado = json.loads(response.text)
        return json_estructurado

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el servidor: {str(e)}")

@app.get("/")
def health_check():
    return {"status": "API encendida y escuchando"}