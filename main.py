import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal
from openai import OpenAI

# ==========================================
# 1. CONFIGURACIÓN DE PROVEEDORES Y FINOPS
# ==========================================
# Precios por cada 1,000,000 de tokens (Extraídos de tu README)
PRECIOS_MODELOS = {
    "llama3.2:3b": {"input": 0.06, "output": 0.06, "provider": "Ollama A (Local)"},
    "mistral:7b": {"input": 0.24, "output": 0.24, "provider": "Ollama B (Local)"},
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08, "provider": "Groq (Cloud)"}
}

# Clientes OpenAI-compatibles para cada proveedor
client_ollama_a = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
client_ollama_b = OpenAI(base_url="http://localhost:11435/v1", api_key="ollama")
client_groq = OpenAI(
    base_url="https://api.groq.com/openai/v1", 
    api_key=os.getenv("GROQ_API_KEY", "TU_CLAVE_GROQ_AQUI") # Asegúrate de poner tu clave o usar variables de entorno
)

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
    consumidor: str = "equipo-default"  # Útil para el Pilar 1 de tu hackathon (Tracking por equipo)

class ClasificacionEnrutador(BaseModel):
    # Aquí usamos Literal como pediste para forzar la salida
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
User: "Escribe una función en Python para calcular el número de Fibonacci usando recursividad." -> {"complejidad": "alta", "razonamiento": "Tarea de programación"}
User: "Explica la teoría de la relatividad" -> {"complejidad": "media", "razonamiento": "Explicación conceptual"}

Analiza el prompt del usuario y responde estrictamente en formato JSON según el esquema proporcionado.
"""

        response_router = client_ollama_a.beta.chat.completions.parse(
            model="llama3.2:3b",
            messages=[
                {"role": "system", "content": sys_prompt_router},
                {"role": "user", "content": peticion.prompt}
            ],
            response_format=ClasificacionEnrutador,
        )

        
        decision = response_router.choices[0].message.parsed

        print(f"Decisión tomada: {decision.complejidad}")
        print(f"Por qué: {decision.razonamiento}")
        return decision

        # --- PASO 2: SELECCIÓN DEL MODELO ---
        # Aplicamos criterios de coste según la complejidad (Pilar 3 del Hackathon)
        if decision.complejidad == "baja":
            modelo_elegido = "llama3.2:3b"
            cliente_elegido = client_ollama_a
        elif decision.complejidad == "media":
            modelo_elegido = "llama-3.1-8b-instant"
            cliente_elegido = client_groq
        else: # "alta"
            modelo_elegido = "mistral:7b"
            cliente_elegido = client_ollama_b

        # --- PASO 3: EJECUCIÓN DEL PROMPT FINAL ---
        response_final = cliente_elegido.chat.completions.create(
            model=modelo_elegido,
            messages=[
                {"role": "user", "content": peticion.prompt}
            ]
        )

        # --- PASO 4: CÁLCULO FINOPS (Costes y Tokens) ---
        usage = response_final.usage
        tokens_input = usage.prompt_tokens
        tokens_output = usage.completion_tokens
        
        precio_input = PRECIOS_MODELOS[modelo_elegido]["input"]
        precio_output = PRECIOS_MODELOS[modelo_elegido]["output"]
        
        # Fórmula: (Tokens / 1,000,000) * Precio
        coste_input_usd = (tokens_input / 1_000_000) * precio_input
        coste_output_usd = (tokens_output / 1_000_000) * precio_output
        coste_total_usd = coste_input_usd + coste_output_usd

        # --- PASO 5: CONSTRUIR LA RESPUESTA ---
        return {
            "respuesta_ia": response_final.choices[0].message.content,
            "finops_metadata": {
                "consumidor": peticion.consumidor,
                "enrutamiento": {
                    "complejidad_detectada": decision.complejidad,
                    "razonamiento_router": decision.razonamiento
                },
                "ejecucion": {
                    "modelo_usado": modelo_elegido,
                    "proveedor": PRECIOS_MODELOS[modelo_elegido]["provider"],
                    "tokens_input": tokens_input,
                    "tokens_output": tokens_output
                },
                "costes_usd": {
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