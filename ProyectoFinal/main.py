import asyncio
import calendar
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

# 🔥 TABLA DE PRECIOS CORREGIDA (Alta -> Media -> Baja)
PRECIOS_FINOPS = {
    "groq/llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79, "provider": "Groq (Cloud)"}, # Nivel 0 (Caro/Complejo)
    "groq/llama-3.1-8b-instant": {"input": 0.15, "output": 0.15, "provider": "Groq (Cloud)"},    # Nivel 1 (Medio)
    "ollama/llama3.2:3b": {"input": 0.05, "output": 0.05, "provider": "Ollama A (Local)"}        # Nivel 2 (Barato)
}

API_BASES = {
    "ollama/llama3.2:3b": "http://localhost:11434"
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
        
        # Insertar usuarios de prueba si la tabla está vacía
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        if cursor.fetchone()[0] == 0:
            usuarios_demo = [
                ("marketing",),
                ("produccion",),
                ("frontend",),
                ("backend",),
                ("equipo-vip",) # Agregado para probar presupuestos altos
            ]
            cursor.executemany("INSERT INTO usuarios (tipo_consumidor) VALUES (?)", usuarios_demo)
            
        conn.commit()

init_db()

# ==========================================
# 3. DEFINICIÓN DE ESTRUCTURAS (PYDANTIC) Y HELPERS
# ==========================================

def contar_tokens_input(modelo: str, messages: list, prompt: str) -> int:
    """
    Intenta obtener el conteo EXACTO de tokens de entrada llamando a la
    API de conteo real del proveedor (litellm.acount_tokens -> Gemini/OpenAI/Anthropic).
    Si el proveedor no está soportado (p.ej. Groq) o falla la llamada,
    cae en litellm.token_counter (tokenizador local, aproximado) y por
    último en una heurística por nº de palabras.
    """
    try:
        resultado = asyncio.run(litellm.acount_tokens(model=modelo, messages=messages))
        if not resultado.error and resultado.total_tokens:
            return resultado.total_tokens
    except Exception:
        pass

    try:
        return litellm.token_counter(model=modelo, messages=messages)
    except Exception:
        return int(len(prompt.split()) * 1.3) + 30


app = FastAPI(title="AI FinOps Proxy - Hackathon")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PeticionUsuario(BaseModel):
    prompt: str
    usuario_id: int  # Conectado a la DB

class ClasificacionEnrutador(BaseModel):
    complejidad: Literal["baja", "media", "alta"]
    razonamiento: str

# ==========================================
# 4. ENDPOINTS FINOPS Y USUARIOS (Base de Datos)
# ==========================================

@app.get("/prediccion/{usuario_id}")
def predecir_coste_mensual(usuario_id: int):
    try:
        hoy = date.today()
        dias_mes = calendar.monthrange(hoy.year, hoy.month)[1]
        
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # Obtener el gasto total y el número de días distintos en los que ha usado la IA
            cursor.execute('''
                SELECT SUM(coste_peticion), COUNT(DISTINCT dia) 
                FROM peticiones 
                WHERE usuario_id = ? AND substr(dia, 1, 7) = ?
            ''', (usuario_id, hoy.strftime("%Y-%m")))
            
            resultado = cursor.fetchone()
            gasto_actual = resultado[0] or 0.0
            dias_activos = resultado[1] or 1 # Evitar división por cero
            
            # Cálculo de tendencia
            gasto_promedio_diario = gasto_actual / dias_activos
            gasto_proyectado_fin_de_mes = gasto_promedio_diario * dias_mes
            
            return {
                "usuario_id": usuario_id,
                "mes": hoy.strftime("%Y-%m"),
                "gasto_actual_usd": round(gasto_actual, 4),
                "proyeccion_fin_de_mes_usd": round(gasto_proyectado_fin_de_mes, 4),
                "alerta": "Peligro" if gasto_proyectado_fin_de_mes > 1.0 else "Saludable" # Límite inventado para la demo
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/usuarios")
def obtener_usuarios():
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
            
            historial = [{"identificador": f"Petición {i}", "id_bd": f[0], "tokens": f[1], "coste_usd": round(f[2], 10), "dia": f[3]} for i, f in enumerate(filas, start=1)]
            
            return {"usuario_id": usuario_id, "total_peticiones": len(historial), "historial": historial}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en BD: {str(e)}")

# ==========================================
# 5. LÓGICA PRINCIPAL (PROXY, ENRUTADO Y DB)
# ==========================================

@app.post("/generar")
def generar_respuesta(peticion: PeticionUsuario):
    # --- PASO 0: VERIFICAR IDENTIDAD DEL USUARIO EN BD ---
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT tipo_consumidor FROM usuarios WHERE id = ?", (peticion.usuario_id,))
            resultado_usuario = cursor.fetchone()
            
            if not resultado_usuario:
                raise HTTPException(status_code=404, detail=f"El usuario con ID {peticion.usuario_id} no existe.")
            
            tipo_consumidor_db = resultado_usuario[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al verificar usuario: {str(e)}")

    try:
        sys_prompt_router = """
Eres un clasificador de IA de alta precisión. Tu trabajo es analizar la intención del usuario y clasificar la complejidad del prompt para optimizar costes.
Reglas estrictas:
"baja": Preguntas directas, saludos, datos simples, cultura general, opiniones breves, tiempo, o tareas de una sola oración.
"media": Redacción de textos, resúmenes, extracción de datos estructurados, emails, o explicaciones de nivel intermedio.
"alta": Programación, matemáticas avanzadas, lógica compleja, análisis de grandes documentos, o razonamiento multi-paso.
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
        
        decision = ClasificacionEnrutador(**json.loads(response_router.choices[0].message.content))
        print(f"-> Decisión Router (User {peticion.usuario_id} - {tipo_consumidor_db}): {decision.complejidad} | Razón: {decision.razonamiento}")
        
        # --- PASO 2: MOTOR DE DECISIÓN (COMPLEJIDAD + PRESUPUESTO) ---
        presupuestos_por_equipo = {
            "equipo-vip": 0.05,        
            "backend": 0.01,           
            "frontend": 0.01,
            "marketing": 0.005,
            "produccion": 0.0001,      
        }
        # Limite de gasto DIARIO por departamento
        limite_gasto_usd = presupuestos_por_equipo.get(tipo_consumidor_db, 0.0001)

        # OBTENER EL GASTO ACUMULADO HOY DESDE LA BD
        hoy_str = date.today().isoformat()
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT SUM(coste_peticion) FROM peticiones WHERE usuario_id = ? AND dia = ?', (peticion.usuario_id, hoy_str))
            resultado_suma = cursor.fetchone()
            coste_acumulado_hoy = resultado_suma[0] if resultado_suma[0] is not None else 0.0

        jerarquia_modelos = [
            "groq/llama-3.3-70b-versatile", # Nivel 0: Alta
            "groq/llama-3.1-8b-instant",    # Nivel 1: Media
            "ollama/llama3.2:3b"            # Nivel 2: Baja
        ]

        if decision.complejidad == "alta": idx_deseado = 0
        elif decision.complejidad == "media": idx_deseado = 1
        else: idx_deseado = 2

        ESTIMACION_OUTPUT_TOKENS = {"baja": 150, "media": 600, "alta": 1500}
        tokens_output_estimados = ESTIMACION_OUTPUT_TOKENS[decision.complejidad]
        
        modelo_final = None
        coste_estimado = 0
        tokens_input_estimados = 0
        tokens_totales_estimados = 0
        razon_sobreescritura = None

        mensajes_para_api = [{"role": "user", "content": peticion.prompt}]

        idx = idx_deseado
        while idx < len(jerarquia_modelos) and modelo_final is None:
            modelo_candidato = jerarquia_modelos[idx]
            
            tokens_input_candidato = contar_tokens_input(modelo_candidato, mensajes_para_api, peticion.prompt)
                
            coste_input_est = (tokens_input_candidato / 1_000_000) * PRECIOS_FINOPS[modelo_candidato]["input"]
            coste_output_est = (tokens_output_estimados / 1_000_000) * PRECIOS_FINOPS[modelo_candidato]["output"]
            coste_candidato = coste_input_est + coste_output_est
            
            # Comprueba Coste Acumulado + Coste Estimado vs Presupuesto Diario
            if (coste_acumulado_hoy + coste_candidato) <= limite_gasto_usd:
                modelo_final = modelo_candidato
                coste_estimado = coste_candidato
                tokens_input_estimados = tokens_input_candidato
                if (idx == 2): 
                    tokens_input_estimados += 25
                tokens_totales_estimados = tokens_input_candidato + tokens_output_estimados
                
                if idx > idx_deseado:
                    razon_sobreescritura = f"Downgrade a {modelo_final}. El gasto de hoy ({coste_acumulado_hoy:.5f}$) + estimación de esta petición ({coste_candidato:.5f}$) superaba el límite diario de {limite_gasto_usd}$."
            idx += 1
        
        # --- FALLBACK DE EMERGENCIA (Si superas el presupuesto con cualquier modelo) ---
        if modelo_final is None:
            modelo_final = jerarquia_modelos[-1] # Obligamos a usar el más barato (Ollama)
            tokens_input_estimados = contar_tokens_input(modelo_final, mensajes_para_api, peticion.prompt)

            tokens_totales_estimados = tokens_input_estimados + tokens_output_estimados
            coste_input_est = (tokens_input_estimados / 1_000_000) * PRECIOS_FINOPS[modelo_final]["input"]
            coste_output_est = (tokens_output_estimados / 1_000_000) * PRECIOS_FINOPS[modelo_final]["output"]
            coste_estimado = coste_input_est + coste_output_est
            
            # Si ya se iba a usar el modelo barato, cambiamos el mensaje para que no parezca un downgrade
            if idx_deseado == (len(jerarquia_modelos) - 1):
                razon_sobreescritura = f"Aviso FinOps: Presupuesto superado (Gasto: {coste_acumulado_hoy:.5f}$ / Límite: {limite_gasto_usd}$). Como la petición era sencilla, se mantiene el modelo económico asignado ({modelo_final})."
            else:
                razon_sobreescritura = f"ALERTA CRÍTICA: Límite diario superado (Gasto: {coste_acumulado_hoy:.5f}$ / Límite: {limite_gasto_usd}$). Forzando modelo económico ({modelo_final}) en lugar del solicitado."
                
        # --- PASO 3: EJECUCIÓN FINAL ---
        completion_kwargs = {
            "model": modelo_final,
            "messages": mensajes_para_api,
            "max_tokens": tokens_output_estimados
        }
        
        if "ollama" in modelo_final:
            completion_kwargs["api_base"] = API_BASES[modelo_final]
        elif "gemini" in modelo_final:
            completion_kwargs["api_key"] = os.getenv("GEMINI_API_KEY", "TU_API_KEY_DE_GEMINI_AQUI")
        else:
            completion_kwargs["api_key"] = os.getenv("GROQ_API_KEY", "TU_API_KEY_AQUI")

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
                coste_hipotetico = ((tokens_input / 1_000_000) * precios_alt["input"]) + ((tokens_output / 1_000_000) * precios_alt["output"])
                ahorro_vs_alternativas[modelo_alt] = round(coste_hipotetico/coste_total_usd, 2) if coste_total_usd > 0 else None

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

        # --- PASO 6: RETORNAR LA RESPUESTA ---
        respuesta_json = {
            "respuesta_ia": response_final.choices[0].message.content,
            "finops_metadata": {
                "usuario": {
                    "id": peticion.usuario_id,
                    "departamento": tipo_consumidor_db,
                    "gasto_diario_acumulado_previo_usd": round(coste_acumulado_hoy, 8)
                },
                "estado_registro_db": estado_db,
                "limite_presupuesto_aplicado": limite_gasto_usd,
                "enrutamiento": {
                    "complejidad_detectada": decision.complejidad,
                    "razonamiento_router": decision.razonamiento
                },
                "estimacion_coste": {
                    "tokens_input_estimados": tokens_input_estimados,
                    "tokens_output_estimados": tokens_output_estimados,
                    "tokens_totales_estimados": tokens_totales_estimados,
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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el servidor: {str(e)}")


@app.get("/")
def health_check():
    return {"status": "AI FinOps Proxy encendido y escuchando"}