import calendar
from datetime import date
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import litellm

# Configuración global de LiteLLM
litellm.drop_params = True

# Importaciones modulares
from config import PRESUPUESTOS_POR_EQUIPO, PRECIOS_FINOPS
from schemas import PeticionUsuario
from database import (
    init_db,
    obtener_tipo_consumidor,
    obtener_gasto_y_dias_activos,
    obtener_usuarios_lista,
    obtener_coste_diario_usuario,
    obtener_historial_usuario_lista,
    obtenerAhorrosMensuales,
    registrar_peticion,
    obtenerGatosMensuales
)
from finops_service import (
    clasificar_complejidad,
    seleccionar_modelo,
    ejecutar_peticion,
    calcular_costes_reales_y_ahorros
)

# Inicializar Base de Datos
init_db()

app = FastAPI(title="AI FinOps Proxy - Hackathon")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "AI FinOps Proxy encendido y escuchando"}

@app.get("/usuarios")
def obtener_usuarios():
    try:
        usuarios = obtener_usuarios_lista()
        return {"total_usuarios": len(usuarios), "usuarios": usuarios}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en BD: {str(e)}")
    
@app.get("/ahorro/{usuario_id}")
def obtener_ahorro(usuario_id: int):
    try:
        ahorros = obtenerAhorrosMensuales(usuario_id)
        return {"ahorros_mensuales": ahorros}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en BD: {str(e)}")

@app.get("/gasto-mensual")
def obtener_gasto_mensual():
    try:
        datos = obtenerGatosMensuales()
        return {"gasto_mensual": datos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en BD: {str(e)}")


@app.get("/prediccion/{usuario_id}")
def predecir_coste_mensual(usuario_id: int):
    try:
        hoy = date.today()
        dias_mes = calendar.monthrange(hoy.year, hoy.month)[1]
        año_mes_str = hoy.strftime("%Y-%m")
        
        gasto_actual, dias_activos = obtener_gasto_y_dias_activos(usuario_id, año_mes_str)
        
        # Cálculo de tendencia
        gasto_promedio_diario = gasto_actual / dias_activos
        gasto_proyectado_fin_de_mes = gasto_promedio_diario * dias_mes
        
        return {
            "usuario_id": usuario_id,
            "mes": año_mes_str,
            "gasto_actual_usd": round(gasto_actual, 4),
            "proyeccion_fin_de_mes_usd": round(gasto_proyectado_fin_de_mes, 4),
            "alerta": "Peligro" if gasto_proyectado_fin_de_mes > 1.0 else "Saludable"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/coste-diario/{usuario_id}")
def obtener_coste_diario(usuario_id: int):
    try:
        hoy_str = date.today().isoformat()
        coste_total, tokens_totales, num_peticiones = obtener_coste_diario_usuario(usuario_id, hoy_str)
        
        return {
            "usuario_id": usuario_id,
            "fecha": hoy_str,
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
        historial = obtener_historial_usuario_lista(usuario_id)
        return {"usuario_id": usuario_id, "total_peticiones": len(historial), "historial": historial}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en BD: {str(e)}")

@app.post("/generar")
def generar_respuesta(peticion: PeticionUsuario):
    # --- PASO 0: VERIFICAR IDENTIDAD DEL USUARIO EN BD ---
    try:
        tipo_consumidor_db = obtener_tipo_consumidor(peticion.usuario_id)
        if not tipo_consumidor_db:
            raise HTTPException(status_code=404, detail=f"El usuario con ID {peticion.usuario_id} no existe.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al verificar usuario: {str(e)}")

    try:
        # --- PASO 1: ENRUTADO ---
        decision = clasificar_complejidad(peticion.prompt)
        print(f"-> Decisión Router (User {peticion.usuario_id} - {tipo_consumidor_db}): {decision.complejidad} | Razón: {decision.razonamiento}")
        
        # --- PASO 2: MOTOR DE DECISIÓN (COMPLEJIDAD + PRESUPUESTO) ---
        modelo_final, coste_estimado, tokens_input_est, tokens_output_est, tokens_totales_est, razon_sobreescritura = seleccionar_modelo(
            prompt=peticion.prompt,
            complejidad=decision.complejidad,
            usuario_id=peticion.usuario_id,
            tipo_consumidor=tipo_consumidor_db
        )
        
        # Obtener el gasto diario acumulado previo para los metadatos finales
        hoy_str = date.today().isoformat()
        coste_acumulado_previo, _, _ = obtener_coste_diario_usuario(peticion.usuario_id, hoy_str)
        limite_gasto_usd = PRESUPUESTOS_POR_EQUIPO.get(tipo_consumidor_db, 0.0001)

        # --- PASO 3: EJECUCIÓN FINAL ---
        print(f"-> Ejecutando en modelo: {modelo_final}")
        response_final = ejecutar_peticion(modelo_final, peticion.prompt)

        # --- PASO 4: CÁLCULO MATEMÁTICO FINOPS ---
        tokens_input = response_final.usage.prompt_tokens
        tokens_output = response_final.usage.completion_tokens
        tokens_totales = response_final.usage.total_tokens
        
        coste_input_usd, coste_output_usd, coste_total_usd, ahorro_vs_alternativas, coste_maximo, porcentaje_ahorro = calcular_costes_reales_y_ahorros(
            modelo_final=modelo_final,
            tokens_input=tokens_input,
            tokens_output=tokens_output
        )

        # --- PASO 5: REGISTRO EN SQLITE ---
        estado_db = registrar_peticion(
            usuario_id=peticion.usuario_id,
            tipo_consumidor=tipo_consumidor_db,
            coste_total_usd=coste_total_usd,
            tokens_totales=tokens_totales,
            coste_maximo=coste_maximo,  
            porcentaje_ahorro=porcentaje_ahorro,
            hoy_str=hoy_str
        )

        # --- PASO 6: RETORNAR LA RESPUESTA ---
        respuesta_json = {
            "respuesta_ia": response_final.choices[0].message.content,
            "finops_metadata": {
                "usuario": {
                    "id": peticion.usuario_id,
                    "departamento": tipo_consumidor_db,
                    "gasto_diario_acumulado_previo_usd": round(coste_acumulado_previo, 8)
                },
                "estado_registro_db": estado_db,
                "limite_presupuesto_aplicado": limite_gasto_usd,
                "enrutamiento": {
                    "complejidad_detectada": decision.complejidad,
                    "razonamiento_router": decision.razonamiento
                },
                "estimacion_coste": {
                    "tokens_input_estimados": tokens_input_est,
                    "tokens_output_estimados": tokens_output_est,
                    "tokens_totales_estimados": tokens_totales_est,
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
