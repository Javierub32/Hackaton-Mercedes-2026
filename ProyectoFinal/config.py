PRECIOS_FINOPS = {
    "groq/llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79, "provider": "Groq (Cloud)"}, # Nivel 0 (Caro/Complejo)
    "groq/llama-3.1-8b-instant": {"input": 0.15, "output": 0.15, "provider": "Groq (Cloud)"},    # Nivel 1 (Medio)
    "ollama/llama3.2:3b": {"input": 0.05, "output": 0.05, "provider": "Ollama A (Local)"}        # Nivel 2 (Barato)
}

API_BASES = {
    "ollama/llama3.2:3b": "http://localhost:11434"
}

DB_FILE = "finops_mercedes.db"

JERARQUIA_MODELOS = [
    "groq/llama-3.3-70b-versatile", # Nivel 0: Alta
    "groq/llama-3.1-8b-instant",    # Nivel 1: Media
    "ollama/llama3.2:3b"            # Nivel 2: Baja
]

PRESUPUESTOS_POR_EQUIPO = {
    "equipo-vip": 0.005,
    "backend": 0.01151402,
    "frontend": 0.0082243,
    "marketing": 0.00164486,
    "produccion": 0.00328972,
}

ESTIMACION_OUTPUT_TOKENS = {"baja": 150, "media": 600, "alta": 1500}

SYS_PROMPT_ROUTER = """
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
