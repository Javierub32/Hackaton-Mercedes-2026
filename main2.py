import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal
import litellm

# ==========================================
# 1. CONFIGURACIÓN DE LITELLM Y PRECIOS
# ==========================================
# Elimina parámetros que no entienda un proveedor específico para evitar errores
litellm.drop_params = True 

# 🔥 TABLA DE PRECIOS FINOPS (Visible y auditable para los jueces)
# Precios por cada 1,000,000 de tokens
PRECIOS_FINOPS = {
    "ollama/llama3.2:3b": {"input": 0.06, "output": 0.06, "provider": "Ollama A (Local)"},
    "ollama/mistral:7b": {"input": 0.24, "output": 0.24, "provider": "Ollama B (Local)"},
    "groq/llama-3.1-8b-instant": {"input": 0.05, "output": 0.08, "provider": "Groq (Cloud)"}
}

# Diccionario para saber a qué puerto de Docker llamar localmente
API_BASES = {
    "ollama/llama3.2:3b": "http://localhost:11434", # Proveedor A
    "ollama/mistral:7b": "http://localhost:11435"   # Proveedor B
}

# ==========================================
# 2. DEFINICIÓN DE ESTRUCTURAS (PYDANTIC)
# ==========================================
app = FastAPI(title="AI FinOps Proxy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PeticionUsuario(BaseModel):
    prompt: str
    consumidor: str = "equipo-default"

class ClasificacionEnrutador(BaseModel):
    complejidad: Literal["baja", "media", "alta"]
    razonamiento: str

# ==========================================
# 3. LÓGICA PRINCIPAL (PROXY Y ENRUTADO)
# ==========================================
@app.post("/generar")
def generar_respuesta(peticion: PeticionUsuario):
    try:
        sys_prompt_router = """
Eres un clasificador de IA de alta precisión. Tu trabajo es analizar la intención del usuario y clasificar la complejidad del prompt para optimizar costes.

Reglas estrictas:
- "baja": Preguntas directas, saludos, datos simples, cultura general, opiniones breves, tiempo, o tareas de una sola oración.
- "media": Redacción de textos, resúmenes, extracción de datos estructurados, emails, o explicaciones de nivel intermedio.
- "alta": Programación, matemáticas avanzadas, lógica compleja, análisis de grandes documentos, o razonamiento multi-paso.

Ejemplos:
User: "Hola, ¿qué tal?" -> {"complejidad": "baja", "razonamiento": "Saludo simple"}
User: "¿Qué tiempo hace en Madrid?" -> {"complejidad": "baja", "razonamiento": "Consulta de información puntual"}
User: "Escribe un correo electrónico para mi jefe pidiendo vacaciones." -> {"complejidad": "media", "razonamiento": "Generación de texto estructurado"}
User: "Escribe una función en Python para calcular el número de Fibonacci." -> {"complejidad": "alta", "razonamiento": "Tarea de programación"}

Analiza el prompt del usuario y responde estrictamente en formato JSON según el esquema proporcionado.
"""
        # --- PASO 1: ENRUTADO ---
        response_router = litellm.completion(
            model="ollama/llama3.2:3b",
            api_base=API_BASES["ollama/llama3.2:3b"],
            messages=[
                {"role": "system", "content": sys_prompt_router}, 
                {"role": "user", "content": peticion.prompt}
            ],
            response_format={"type": "json_object"} 
        )
        
        # Parseamos el JSON manualmente y lo validamos con Pydantic
        contenido_router = response_router.choices[0].message.content
        decision_dict = json.loads(contenido_router)
        decision = ClasificacionEnrutador(**decision_dict)
        print(f"-> Decisión del Router: {decision.complejidad} | Razón: {decision.razonamiento}")
        
        # --- PASO 2: SELECCIÓN DE MODELO ---
        model_map = {
            "baja": "ollama/llama3.2:3b",
            "alta": "groq/llama-3.1-8b-instant",
            "media": "ollama/mistral:7b"
        }
        modelo_final = model_map[decision.complejidad]

        # Preparamos la llamada a LiteLLM
        completion_kwargs = {
            "model": modelo_final,
            "messages": [{"role": "user", "content": peticion.prompt}]
        }
        
        # Inyectamos configuración según el proveedor
        if "ollama" in modelo_final:
            completion_kwargs["api_base"] = API_BASES[modelo_final]
        else:
            completion_kwargs["api_key"] = os.getenv("GROQ_API_KEY", "API_KEY") # <-- PON TU CLAVE AQUÍ

        # --- PASO 3: EJECUCIÓN FINAL ---
        print(f"-> Ejecutando en modelo: {modelo_final}")
        response_final = litellm.completion(**completion_kwargs)

        # --- PASO 4: CÁLCULO MATEMÁTICO FINOPS ---
        tokens_input = response_final.usage.prompt_tokens
        tokens_output = response_final.usage.completion_tokens
        tokens_totales = response_final.usage.total_tokens
        
        precio_input = PRECIOS_FINOPS[modelo_final]["input"]
        precio_output = PRECIOS_FINOPS[modelo_final]["output"]
        
        # Fórmula: (Tokens / 1M) * Precio
        coste_input_usd = (tokens_input / 1_000_000) * precio_input
        coste_output_usd = (tokens_output / 1_000_000) * precio_output
        coste_total_usd = coste_input_usd + coste_output_usd

        # --- PASO 5: RETORNAR LA RESPUESTA CON METADATOS FINOPS ---
        return {
            "respuesta_ia": response_final.choices[0].message.content,
            "finops_metadata": {
                "consumidor": peticion.consumidor,
                "enrutamiento": {
                    "complejidad_detectada": decision.complejidad,
                    "razonamiento_router": decision.razonamiento
                },
                "ejecucion": {
                    "modelo_usado": modelo_final,
                    "proveedor": PRECIOS_FINOPS[modelo_final]["provider"],
                    "tokens_input": tokens_input,
                    "tokens_output": tokens_output,
                    "tokens_totales": tokens_totales
                },
                "coste_usd": {
                    "coste_input": round(coste_input_usd, 8),
                    "coste_output": round(coste_output_usd, 8),
                    "coste_total": round(coste_total_usd, 8)
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el servidor: {str(e)}")

@app.get("/")
def health_check():
    return {"status": "AI FinOps Proxy encendido y escuchando"}