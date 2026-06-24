from __future__ import annotations

import os
import json
from functools import lru_cache
from typing import List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"
DEFAULT_GEMINI_MODELS = [
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]


def obtener_api_key_gemini() -> Optional[str]:
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

    model_names = obtener_modelos_gemini()

    errores = []
    for model_name in model_names:
        try:
            return _generar_texto_gemini_rest(api_key, model_name, prompt)
        except Exception as exc:
            errores.append(f"{model_name}: {exc}")

    detalle = " | ".join(errores)
    raise RuntimeError(f"Error al llamar a Gemini con todos los modelos configurados: {detalle}")


def obtener_modelos_gemini() -> List[str]:
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

    model_name = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    try:
        return _generar_texto_gemini_rest(api_key, model_name, prompt)
    except Exception as exc:
        raise RuntimeError(f"Error al llamar a Gemini: {exc}") from exc


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


def _generar_texto_gemini_rest(api_key: str, model_name: str, prompt: str) -> str:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_name}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0,
            "topP": 0.1,
            "maxOutputTokens": 2048,
        },
    }
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"No se pudo conectar a Gemini: {exc}") from exc

    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"Gemini no devolvio candidatos: {data}")

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts)
    if not text.strip():
        raise RuntimeError(f"Gemini devolvio una respuesta vacia: {data}")
    return text.strip()
