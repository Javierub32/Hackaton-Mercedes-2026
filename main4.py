import json
import os
import sqlite3
from datetime import date
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal
import litellm

# ==========================================
# 1. CONFIGURACIÓN DE LITELLM Y PRECIOS
# ==========================================
litellm.drop_params = True 

# 🔥 TABLA DE PRECIOS FINOPS (Chargeback)
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
        "provider": "Groq (Cloud - Tarifa dinámica)"
    }
except Exception:
    print("Aviso: No se pudo cargar el precio dinámico de Groq, usando fallback.")

# Puertos de contenedores locales
API_BASES = {
    "ollama/llama3.2:3b": "http://localhost:11434", 
    "ollama/mistral:7b": "http://localhost:11435"   
}

# ==========================================
# 2. CONFIGURACIÓN DE SQLITE (Usuarios y Peticiones)
# ==========================================
DB_FILE = "finops_mercedes.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        # Tabla de usuarios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo_consumidor TEXT NOT NULL
            )
        ''')
        
        # Tabla de peticiones (Historial)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS peticiones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                tipo_consumidor TEXT,
                coste_peticion REAL,
                tokens_peticion REAL,
                dia DATE,
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
            )
        ''')
        
        # Insertar 5 usuarios de prueba si la tabla está vacía
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        if cursor.fetchone()[0] == 0:
            usuarios_demo = [
                ("marketing",),
                ("produccion",),
                ("frontend",),
                ("marketing",),
                ("backend",)
            ]
            cursor.executemany("INSERT INTO usuarios (tipo_consumidor) VALUES (?)", usuarios_demo)
            
        conn.commit()

init_db()

# ==========================================
# 3. DEFINICIÓN DE ESTRUCTURAS (PYDANTIC)
# ==========================================
app = FastAPI(title="AI FinOps Proxy - Mercedes Benz")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PeticionUsuario(BaseModel):
    prompt: str
    usuario_id: int  # Ya no pedimos el tipo de consumidor, el backend lo averigua

class ClasificacionEnrutador(BaseModel):
    complejidad: Literal["baja", "media", "alta"]
    razonamiento: str

# ==========================================
# 4. ENDPOINTS FINOPS Y USUARIOS
# ==========================================

@app.get("/usuarios")
def obtener_usuarios():
    """Devuelve la lista de todos los usuarios registrados en el sistema"""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, tipo_consumidor FROM usuarios")
            filas = cursor.fetchall()
            
            usuarios = [{"id": fila[0], "tipo_consumidor": fila[1]} for fila in filas]
            return {"total_usuarios": len(usuarios), "usuarios": usuarios}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en BD: {str(e)}")


@app.get("/coste-diario/{usuario_id}")
def obtener_coste_diario(usuario_id: int):
    """Obtiene el gasto total de un usuario en el día actual"""
    try:
        hoy = date.today().isoformat()
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT SUM(coste_peticion), SUM(tokens_peticion), COUNT(id)
                FROM peticiones 
                WHERE usuario_id = ? AND dia = ?
            ''', (usuario_id, hoy))
            
            resultado = cursor.fetchone()
            coste_total = resultado[0] or 0.0
            tokens_totales = resultado[1] or 0.0
            num_peticiones = resultado[2] or 0

        return {
            "usuario_id": usuario_id,
            "fecha": hoy,
            "metricas_hoy": {
                "peticiones_realizadas": num_peticiones,
                "tokens_consumidos": tokens_totales,
                "coste_total_usd": round(coste_total, 10)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en BD: {str(e)}")


@app.get("/historial/{usuario_id}")
def obtener_historial_usuario(usuario_id: int):
    """Obtiene el historial detallado de todas las peticiones de un usuario"""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, tokens_peticion, coste_peticion, dia 
                FROM peticiones 
                WHERE usuario_id = ?
                ORDER BY id ASC
            ''', (usuario_id,))
            filas = cursor.fetchall()
            
        historial = []
        for indice, fila in enumerate(filas, start=1):
            id_bd, tokens, coste, dia = fila
            historial.append({
                "identificador": f"Petición {indice}",
                "id_bd": id_bd,
                "tokens": tokens,
                "coste_usd": round(coste, 10),
                "dia": dia
            })
            
        return {
            "usuario_id": usuario_id,
            "total_peticiones": len(historial),
            "historial": historial
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en BD: {str(e)}")


@app.post("/generar")
def generar_respuesta(peticion: PeticionUsuario):
    # --- PASO 0: VERIFICAR IDENTIDAD DEL USUARIO ---
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT tipo_consumidor FROM usuarios WHERE id = ?", (peticion.usuario_id,))
            resultado_usuario = cursor.fetchone()
            
            if not resultado_usuario:
                raise HTTPException(status_code=404, detail=f"El usuario con ID {peticion.usuario_id} no existe en la base de datos.")
            
            tipo_consumidor_db = resultado_usuario[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al verificar usuario: {str(e)}")

    try:
        sys_prompt_router = """
Eres un clasificador de IA de alta precisión. Analiza la intención y clasifica la complejidad.
- "baja": Saludos, datos simples, cultura general, tiempo, tareas de una oración.
- "media": Redacción de textos, emails, resúmenes, extracción de datos.
- "alta": Programación, matemáticas, lógica, razonamiento complejo.
Responde estrictamente en JSON: {"complejidad": "baja|media|alta", "razonamiento": "..."}.
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
        
        decision = ClasificacionEnrutador(**json.loads(response_router.choices[0].message.content))
        print(f"-> Decisión Router (Usuario {peticion.usuario_id} - {tipo_consumidor_db}): {decision.complejidad}")

        # --- PASO 2: SELECCIÓN Y ESTIMACIÓN (ESCUDO FINOPS) ---
        model_map = {
            "baja": "ollama/llama3.2:3b",
            "media": "ollama/mistral:7b",
            "alta": "groq/llama-3.1-8b-instant"
        }
        modelo_final = model_map[decision.complejidad]

        tokens_estimados = litellm.token_counter(model="gpt-3.5-turbo", text=peticion.prompt)
        precio_input_estimado = PRECIOS_FINOPS[modelo_final]["input"]
        coste_estimado = (tokens_estimados / 1_000_000) * precio_input_estimado
        
        LIMITE_COSTE_PROMPT = 0.0001
        razon_sobreescritura = None

        if modelo_final == "groq/llama-3.1-8b-instant" and coste_estimado > LIMITE_COSTE_PROMPT:
            print(f"ALERTA FINOPS: Prompt muy costoso. Desviando a Local.")
            modelo_final = "ollama/mistral:7b"
            razon_sobreescritura = "Downgrade a modelo Local por exceso de presupuesto estimado en prompt."
            coste_estimado = (tokens_estimados / 1_000_000) * PRECIOS_FINOPS[modelo_final]["input"]

        # --- PASO 3: EJECUCIÓN FINAL ---
        completion_kwargs = {
            "model": modelo_final,
            "messages": [{"role": "user", "content": peticion.prompt}]
        }
        if "ollama" in modelo_final:
            completion_kwargs["api_base"] = API_BASES[modelo_final]
        else:
            completion_kwargs["api_key"] = os.getenv("GROQ_API_KEY", "TU_CLAVE_GROQ")

        response_final = litellm.completion(**completion_kwargs)

        # --- PASO 4: CÁLCULOS MATEMÁTICOS EXACTOS ---
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
                ahorro_vs_alternativas[modelo_alt] = round(ahorro, 10)

        # --- PASO 5: REGISTRO EN SQLITE ---
        hoy = date.today().isoformat()
        try:
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO peticiones (usuario_id, tipo_consumidor, coste_peticion, tokens_peticion, dia)
                    VALUES (?, ?, ?, ?, ?)
                ''', (peticion.usuario_id, tipo_consumidor_db, coste_total_usd, tokens_totales, hoy))
                conn.commit()
            estado_db = "registrado_ok"
        except Exception as e:
            estado_db = f"error_db: {e}"

        # --- PASO 6: RESPUESTA FINAL HIPER-DETALLADA ---
        respuesta_json = {
            "respuesta_ia": response_final.choices[0].message.content,
            "finops_metadata": {
                "usuario": {
                    "id": peticion.usuario_id,
                    "departamento": tipo_consumidor_db
                },
                "estado_registro_db": estado_db,
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

        if razon_sobreescritura:
            respuesta_json["finops_metadata"]["enrutamiento"]["intervencion_finops"] = razon_sobreescritura

        return respuesta_json

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el servidor: {str(e)}")

@app.get("/")
def health_check():
    return {"status": "AI FinOps Proxy encendido y escuchando"}