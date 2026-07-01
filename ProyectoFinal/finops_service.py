import os
import json
import litellm
from datetime import date
from config import (
    PRECIOS_FINOPS,
    API_BASES,
    JERARQUIA_MODELOS,
    PRESUPUESTOS_POR_EQUIPO,
    ESTIMACION_OUTPUT_TOKENS,
    SYS_PROMPT_ROUTER
)
from schemas import ClasificacionEnrutador
from helpers import contar_tokens_input
from database import obtener_coste_diario_usuario

def clasificar_complejidad(prompt: str) -> ClasificacionEnrutador:
    response_router = litellm.completion(
        model="ollama/llama3.2:3b",
        api_base=API_BASES["ollama/llama3.2:3b"],
        messages=[
            {"role": "system", "content": SYS_PROMPT_ROUTER},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    return ClasificacionEnrutador(**json.loads(response_router.choices[0].message.content))

def calcular_coste_estimado(modelo: str, prompt: str, mensajes: list, tokens_output_estimados: int) -> tuple[float, int]:
    tokens_input_est = contar_tokens_input(modelo, mensajes, prompt)
    coste_input_est = (tokens_input_est / 1_000_000) * PRECIOS_FINOPS[modelo]["input"]
    coste_output_est = (tokens_output_estimados / 1_000_000) * PRECIOS_FINOPS[modelo]["output"]
    return coste_input_est + coste_output_est, tokens_input_est

def seleccionar_modelo(
    prompt: str,
    complejidad: str,
    usuario_id: int,
    tipo_consumidor: str
) -> tuple[str, float, int, int, int, str | None]:
    """
    Selecciona el modelo óptimo según complejidad, presupuesto diario del equipo y coste acumulado.
    Retorna: (modelo_final, coste_estimado, tokens_input_est, tokens_output_est, tokens_totales_est, razon_sobreescritura)
    """
    hoy_str = date.today().isoformat()
    limite_gasto_usd = PRESUPUESTOS_POR_EQUIPO.get(tipo_consumidor, 0.0001)
    
    # Obtener el gasto acumulado hoy desde la base de datos
    coste_acumulado_hoy, _, _ = obtener_coste_diario_usuario(usuario_id, hoy_str)

    if complejidad == "alta":
        idx_deseado = 0
    elif complejidad == "media":
        idx_deseado = 1
    else:
        idx_deseado = 2

    tokens_output_estimados = ESTIMACION_OUTPUT_TOKENS[complejidad]
    mensajes_para_api = [{"role": "user", "content": prompt}]
    
    modelo_final = None
    coste_estimado = 0.0
    tokens_input_estimados = 0
    tokens_totales_estimados = 0
    razon_sobreescritura = None

    idx = idx_deseado
    while idx < len(JERARQUIA_MODELOS) and modelo_final is None:
        modelo_candidato = JERARQUIA_MODELOS[idx]
        coste_candidato, tokens_input_candidato = calcular_coste_estimado(
            modelo_candidato, prompt, mensajes_para_api, tokens_output_estimados
        )
        
        # Comprueba Coste Acumulado + Coste Estimado vs Presupuesto Diario
        if (coste_acumulado_hoy + coste_candidato) <= limite_gasto_usd:
            modelo_final = modelo_candidato
            coste_estimado = coste_candidato
            tokens_input_estimados = tokens_input_candidato
            if idx == 2: 
                tokens_input_estimados += 25
            tokens_totales_estimados = tokens_input_candidato + tokens_output_estimados
            
            if idx > idx_deseado:
                razon_sobreescritura = (
                    f"Downgrade a {modelo_final}. El gasto de hoy ({coste_acumulado_hoy:.5f}$) + "
                    f"estimación de esta petición ({coste_candidato:.5f}$) superaba el límite diario de {limite_gasto_usd}$."
                )
        idx += 1

    # Fallback de emergencia si no cabe en el presupuesto con ningún modelo
    if modelo_final is None:
        modelo_final = JERARQUIA_MODELOS[-1] # Ollama
        coste_estimado, tokens_input_estimados = calcular_coste_estimado(
            modelo_final, prompt, mensajes_para_api, tokens_output_estimados
        )
        tokens_totales_estimados = tokens_input_estimados + tokens_output_estimados
        
        if idx_deseado == (len(JERARQUIA_MODELOS) - 1):
            razon_sobreescritura = (
                f"Aviso FinOps: Presupuesto superado (Gasto: {coste_acumulado_hoy:.5f}$ / Límite: {limite_gasto_usd}$). "
                f"Como la petición era sencilla, se mantiene el modelo económico asignado ({modelo_final})."
            )
        else:
            razon_sobreescritura = (
                f"ALERTA CRÍTICA: Límite diario superado (Gasto: {coste_acumulado_hoy:.5f}$ / Límite: {limite_gasto_usd}$). "
                f"Forzando modelo económico ({modelo_final}) en lugar del solicitado."
            )

    return modelo_final, coste_estimado, tokens_input_estimados, tokens_output_estimados, tokens_totales_estimados, razon_sobreescritura

def ejecutar_peticion(modelo: str, prompt: str):
    mensajes_para_api = [{"role": "user", "content": prompt}]
    completion_kwargs = {
        "model": modelo,
        "messages": mensajes_para_api,
    }
    
    if "ollama" in modelo:
        completion_kwargs["api_base"] = API_BASES[modelo]
    elif "gemini" in modelo:
        completion_kwargs["api_key"] = os.getenv("GEMINI_API_KEY", "TU_GEMINI_API_KEY_AQUI")
    else:
        completion_kwargs["api_key"] = os.getenv("GROQ_API_KEY", "TU_GROQ_API_KEY_AQUI")

    return litellm.completion(**completion_kwargs)

def calcular_costes_reales_y_ahorros(modelo_final: str, tokens_input: int, tokens_output: int) -> tuple[float, float, float, dict, float, float]:
    precio_input = PRECIOS_FINOPS[modelo_final]["input"]
    precio_output = PRECIOS_FINOPS[modelo_final]["output"]
    
    coste_input_usd = (tokens_input / 1_000_000) * precio_input
    coste_output_usd = (tokens_output / 1_000_000) * precio_output
    coste_total_usd = coste_input_usd + coste_output_usd

    ahorro_vs_alternativas = {}
    
    # Añadimos el coste real actual a la lista de posibles costes máximos
    costes_hipoteticos = [coste_total_usd] 

    for modelo_alt, precios_alt in PRECIOS_FINOPS.items():
        if modelo_alt != modelo_final:
            coste_hipotetico = (
                ((tokens_input / 1_000_000) * precios_alt["input"]) + 
                ((tokens_output / 1_000_000) * precios_alt["output"])
            )
            costes_hipoteticos.append(coste_hipotetico)
            
            ahorro_vs_alternativas[modelo_alt] = (
                round(coste_hipotetico / coste_total_usd, 2) if coste_total_usd > 0 else 0.0
            )

    # El coste máximo es simplemente el valor más alto posible para esta petición
    coste_maximo = max(costes_hipoteticos)
    porcentaje_ahorro = 100 -(coste_total_usd*100 / coste_maximo) if coste_maximo > 0 else 0.0
    
    return coste_input_usd, coste_output_usd, coste_total_usd, ahorro_vs_alternativas, coste_maximo, porcentaje_ahorro