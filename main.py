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
litellm.drop_params = True 

# TABLA DE PRECIOS SEGÚN LA DOCUMENTACIÓN
PRECIOS_FINOPS = {
    "ollama/llama3.2:3b": {"input": 0.06, "output": 0.06, "provider": "Ollama A (Local)"},
    "ollama/mistral:7b": {"input": 0.24, "output": 0.24, "provider": "Ollama B (Local)"},
    "groq/llama-3.1-8b-instant": {"input": 0.05, "output": 0.08, "provider": "Groq (Cloud)"}
}

try:
    groq_info = litellm.get_model_info("groq/llama-3.1-8b-instant")
    PRECIOS_FINOPS["groq/llama-3.1-8b-instant"] = {
        "input": groq_info["input_cost_per_token"] * 1_000_000,
        "output": groq_info["output_cost_per_token"] * 1_000_000,
        "provider": "Groq (Cloud - Tarifa dinámica LiteLLM)"
    }
except Exception as e:
    print("Aviso: No se pudo cargar el precio dinámico de Groq, usando fallback.")

API_BASES = {
    "ollama/llama3.2:3b": "http://localhost:11434", 
    "ollama/mistral:7b": "http://localhost:11435"   
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
        
        contenido_router = response_router.choices[0].message.content
        decision_dict = json.loads(contenido_router)
        decision = ClasificacionEnrutador(**decision_dict)
        print(f"-> Decisión del Router: {decision.complejidad} | Razón: {decision.razonamiento}")
        
        # --- PASO 2: MOTOR DE DECISIÓN (COMPLEJIDAD + PRESUPUESTO) ---
        
        # --- PRESUPUESTOS POR EQUIPO (CONECTAR A BBDD) ---
        presupuestos_por_equipo = {
            "equipo-vip": 0.05,        # Presupuesto alto
            "equipo-default": 0.0001,  # Presupuesto normal
            "equipo-lowcost": 0.00002  # Presupuesto muy estricto
        }
        # LIMITE DE GASTO SEGÚN EL EQUIPO DEL USUARIO (DEFAULT: 0.0001 USD)
        limite_gasto_usd = presupuestos_por_equipo.get(peticion.consumidor, 0.0001)

        # JERARQUÍA DE MODELOS (DE ALTO A BAJO COSTE)
        jerarquia_modelos = [
            "groq/llama-3.1-8b-instant",  # Nivel 0: Alta
            "ollama/mistral:7b",          # Nivel 1: Media
            "ollama/llama3.2:3b"          # Nivel 2: Baja
        ]

        # MODELO IDEAL SEGÚN LA COMPLEJIDAD DETECTADA
        if decision.complejidad == "alta":
            idx_deseado = 0
        elif decision.complejidad == "media":
            idx_deseado = 1
        else:
            idx_deseado = 2

        tokens_estimados = litellm.token_counter(model="gpt-3.5-turbo", text=peticion.prompt)
        
        modelo_final = None
        coste_estimado = 0
        razon_sobreescritura = None

        idx = idx_deseado
        while idx < len(jerarquia_modelos) and modelo_final is None:
            modelo_candidato = jerarquia_modelos[idx]
            coste_candidato = (tokens_estimados / 1_000_000) * PRECIOS_FINOPS[modelo_candidato]["input"]
            
            # Si entra en presupuesto, lo asignamos (lo que también hará que la condición del while falle en el siguiente ciclo)
            if coste_candidato <= limite_gasto_usd:
                modelo_final = modelo_candidato
                coste_estimado = coste_candidato
                
                # Si tuvimos que bajar de nivel, guardamos el motivo
                if idx > idx_deseado:
                    razon_sobreescritura = f"Downgrade a {modelo_final}. El modelo ideal ({jerarquia_modelos[idx_deseado]}) superaba el límite de {limite_gasto_usd}$ del {peticion.consumidor}."
            
            idx += 1
        
        # E) Failsafe: Si el prompt es tan gigantesco que supera el presupuesto incluso en el modelo más barato
        if modelo_final is None:
            modelo_final = jerarquia_modelos[-1] # Forzamos el nivel más bajo (Llama 3.2 3B)
            coste_estimado = (tokens_estimados / 1_000_000) * PRECIOS_FINOPS[modelo_final]["input"]
            razon_sobreescritura = f"ALERTA CRÍTICA: Presupuesto excedido en todos los modelos. Forzando ejecución en el modelo más económico ({modelo_final})."

        # --- PASO 3: EJECUCIÓN FINAL ---
        completion_kwargs = {
            "model": modelo_final,
            "messages": [{"role": "user", "content": peticion.prompt}]
        }
        
        if "ollama" in modelo_final:
            completion_kwargs["api_base"] = API_BASES[modelo_final]
        else:
            completion_kwargs["api_key"] = os.getenv("GROQ_API_KEY", "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")

        print(f"-> Ejecutando en modelo: {modelo_final}")
        response_final = litellm.completion(**completion_kwargs)

        # --- PASO 4: CÁLCULO MATEMÁTICO FINOPS ---
        tokens_input = response_final.usage.prompt_tokens
        tokens_output = response_final.usage.completion_tokens
        tokens_totales = response_final.usage.total_tokens
        
        precio_input = PRECIOS_FINOPS[modelo_final]["input"]
        precio_output = PRECIOS_FINOPS[modelo_final]["output"]
        
        coste_input_usd = (tokens_input / 1_000_000) * precio_input
        coste_output_usd = (tokens_output / 1_000_000) * precio_output
        coste_total_usd = coste_input_usd + coste_output_usd

        ahorro_vs_alternativas = {}
        for modelo_alt, precios_alt in PRECIOS_FINOPS.items():
            if modelo_alt != modelo_final:
                coste_hipotetico = ((tokens_input / 1_000_000) * precios_alt["input"]) + \
                                   ((tokens_output / 1_000_000) * precios_alt["output"])
                ahorro = coste_hipotetico - coste_total_usd
                ahorro_vs_alternativas[modelo_alt] = round(ahorro, 8)

        # --- PASO 5: RETORNAR LA RESPUESTA ---
        respuesta_json = {
            "respuesta_ia": response_final.choices[0].message.content,
            "finops_metadata": {
                "consumidor": peticion.consumidor,
                "limite_presupuesto_aplicado": limite_gasto_usd,
                "enrutamiento": {
                    "complejidad_detectada": decision.complejidad,
                    "razonamiento_router": decision.razonamiento
                },
                "estimacion_coste": {
                    "tokens_input_estimados": tokens_estimados,
                    "coste_estimado_usd": round(coste_estimado, 8)
                },
                "coste_real_usd": {
                    "coste_input": round(coste_input_usd, 8),
                    "coste_output": round(coste_output_usd, 8),
                    "coste_total": round(coste_total_usd, 8)
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

        if razon_sobreescritura:
            respuesta_json["finops_metadata"]["enrutamiento"]["intervencion_finops"] = razon_sobreescritura

        return respuesta_json

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el servidor: {str(e)}")

@app.get("/")
def health_check():
    return {"status": "AI FinOps Proxy encendido y escuchando"}