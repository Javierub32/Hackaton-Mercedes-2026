# helpers.py
import asyncio
import litellm

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
