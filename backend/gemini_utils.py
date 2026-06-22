from __future__ import annotations

import os
from functools import lru_cache


DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"
DEFAULT_GEMINI_MODELS = [
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]


def obtener_api_key_gemini() -> str | None:
    """
    Lee la API key desde variables de entorno.
    """
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


@lru_cache(maxsize=128)
def generar_texto_gemini(prompt: str) -> str:
    """
    Ejecuta un prompt contra Gemini y devuelve texto plano.
    """
    api_key = obtener_api_key_gemini()
    if not api_key:
        raise RuntimeError(
            "No se encontro GEMINI_API_KEY ni GOOGLE_API_KEY en variables de entorno."
        )

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "Falta instalar google-genai. Ejecute: pip install -r backend/requirements.txt"
        ) from exc

    client = genai.Client(api_key=api_key)
    model_names = obtener_modelos_gemini()

    errores = []
    for model_name in model_names:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0,
                    top_p=0.1,
                    max_output_tokens=2048,
                ),
            )
            text = getattr(response, "text", "") or ""
            return text.strip()
        except Exception as exc:
            errores.append(f"{model_name}: {exc}")

    detalle = " | ".join(errores)
    raise RuntimeError(f"Error al llamar a Gemini con todos los modelos configurados: {detalle}")


def obtener_modelos_gemini() -> list[str]:
    """
    Devuelve la lista ordenada de modelos a probar.
    """
    modelos = os.getenv("GEMINI_MODELS")
    if modelos:
        return [modelo.strip() for modelo in modelos.split(",") if modelo.strip()]

    modelo = os.getenv("GEMINI_MODEL")
    if modelo:
        return [modelo.strip()]

    return DEFAULT_GEMINI_MODELS.copy()


def generar_texto_gemini_con_modelo_unico(prompt: str) -> str:
    """
    Ejecuta Gemini usando solo GEMINI_MODEL o el modelo por defecto.
    Se conserva para depuracion manual.
    """
    api_key = obtener_api_key_gemini()
    if not api_key:
        raise RuntimeError(
            "No se encontro GEMINI_API_KEY ni GOOGLE_API_KEY en variables de entorno."
        )

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "Falta instalar google-genai. Ejecute: pip install -r backend/requirements.txt"
        ) from exc

    client = genai.Client(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                top_p=0.1,
                max_output_tokens=2048,
            ),
        )
    except Exception as exc:
        raise RuntimeError(f"Error al llamar a Gemini: {exc}") from exc

    text = getattr(response, "text", "") or ""
    return text.strip()


def limpiar_respuesta_llm(texto: str) -> str:
    """
    Elimina fences de Markdown y espacios sobrantes de una respuesta del LLM.
    """
    texto = texto.strip()
    if texto.startswith("```"):
        lineas = texto.splitlines()
        if lineas and lineas[0].startswith("```"):
            lineas = lineas[1:]
        if lineas and lineas[-1].startswith("```"):
            lineas = lineas[:-1]
        texto = "\n".join(lineas)
    return texto.strip().rstrip(";").strip()
