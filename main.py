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
# Precios base (Chargeback local) por cada 1,000,000 de tokens
PRECIOS_FINOPS = {
    "ollama/llama3.2:3b": {"input": 0.06, "output": 0.06, "provider": "Ollama A (Local)"},
    "ollama/mistral:7b": {"input": 0.24, "output": 0.24, "provider": "Ollama B (Local)"},
    "groq/llama-3.1-8b-instant": {"input": 0.05, "output": 0.08, "provider": "Groq (Cloud)"}
}

# ¡NUEVO! Obtenemos el precio de la nube dinámicamente desde LiteLLM para Groq
try:
    groq_info = litellm.get_model_info("groq/llama-3.1-8b-instant")
    PRECIOS_FINOPS["groq/llama-3.1-8b-instant"] = {
        "input": groq_info["input_cost_per_token"] * 1_000_000,
        "output": groq_info["output_cost_per_token"] * 1_000_000,
        "provider": "Groq (Cloud - Tarifa dinámica LiteLLM)"
    }
except Exception as e:
    print("Aviso: No se pudo cargar el precio dinámico de Groq, usando fallback.")

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
        
        # --- PASO 2: SELECCIÓN DE MODELO Y ESTIMACIÓN PRE-VUELO ---
        # Mapeo original del compañero
        model_map = {
            "baja": "ollama/llama3.2:3b",
            "media": "ollama/mistral:7b",
            "alta": "groq/llama-3.1-8b-instant"
        }
        modelo_final = model_map[decision.complejidad]

        # Estimación de tokens y coste dinámico del modelo elegido por el enrutador
        tokens_estimados = litellm.token_counter(model="gpt-3.5-turbo", text=peticion.prompt)
        precio_input_estimado = PRECIOS_FINOPS[modelo_final]["input"]
        coste_estimado = (tokens_estimados / 1_000_000) * precio_input_estimado
        
        LIMITE_COSTE_PROMPT = 0.0001
        razon_sobreescritura = None

        # REGLA FINOPS: Si el router elige un modelo de pago (Groq - alta complejidad) pero es muy caro, forzamos downgrade a local
        if modelo_final == "groq/llama-3.1-8b-instant" and coste_estimado > LIMITE_COSTE_PROMPT:
            print(f"ALERTA FINOPS: Prompt muy costoso ({coste_estimado:.6f}$). Desviando a Local (Mistral).")
            modelo_final = "ollama/mistral:7b"
            razon_sobreescritura = "Downgrade a modelo Local por exceso de presupuesto estimado en prompt."
            
            # Recalculamos la estimación para que el JSON muestre la estimación del nuevo modelo asignado
            coste_estimado = (tokens_estimados / 1_000_000) * PRECIOS_FINOPS[modelo_final]["input"]

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
        
        # Fórmula coste real: (Tokens / 1M) * Precio
        coste_input_usd = (tokens_input / 1_000_000) * precio_input
        coste_output_usd = (tokens_output / 1_000_000) * precio_output
        coste_total_usd = coste_input_usd + coste_output_usd

        # Cálculo de ahorro frente a otros modelos (Cost Avoidance)
        ahorro_vs_alternativas = {}
        for modelo_alt, precios_alt in PRECIOS_FINOPS.items():
            if modelo_alt != modelo_final:
                coste_hipotetico = ((tokens_input / 1_000_000) * precios_alt["input"]) + \
                                   ((tokens_output / 1_000_000) * precios_alt["output"])
                ahorro = coste_hipotetico - coste_total_usd
                ahorro_vs_alternativas[modelo_alt] = round(ahorro, 10)

        # --- PASO 5: RETORNAR LA RESPUESTA CON METADATOS FINOPS ---
        respuesta_json = {
            "respuesta_ia": response_final.choices[0].message.content,
            "finops_metadata": {
                "consumidor": peticion.consumidor,
                "enrutamiento": {
                    "complejidad_detectada": decision.complejidad,
                    "razonamiento_router": decision.razonamiento
                },
                "estimacion_coste": {
                    "tokens_input_estimados": tokens_estimados,
                    "coste_estimado_usd": round(coste_estimado, 10)
                },
                "coste_real_usd": {
                    "coste_input": round(coste_input_usd, 10),
                    "coste_output": round(coste_output_usd, 10),
                    "coste_total": round(coste_total_usd, 10)
                },
                "ahorro_usd": ahorro_vs_alternativas,
                "ejecucion": {
                    "modelo_usado": modelo_final,
                    "proveedor": PRECIOS_FINOPS[modelo_final]["provider"],
                    "tokens_input": tokens_input,
                    "tokens_output": tokens_output,
                    "tokens_totales": tokens_totales
                }
            }
        }

        # Si el escudo FinOps actuó, lo añadimos al JSON para la demo
        if razon_sobreescritura:
            respuesta_json["finops_metadata"]["enrutamiento"]["intervencion_finops"] = razon_sobreescritura

        return respuesta_json

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el servidor: {str(e)}")

@app.get("/")
def health_check():
    return {"status": "AI FinOps Proxy encendido y escuchando"}