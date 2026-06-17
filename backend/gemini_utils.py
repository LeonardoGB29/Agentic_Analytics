from __future__ import annotations

import os


DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"


def obtener_api_key_gemini() -> str | None:
    """
    Lee la API key desde variables de entorno.
    """
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


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
        import google.generativeai as genai
    except ImportError as exc:
        raise RuntimeError(
            "Falta instalar google-generativeai. Ejecute: pip install -r backend/requirements.txt"
        ) from exc

    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    model = genai.GenerativeModel(model_name)
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0,
                "top_p": 0.1,
                "max_output_tokens": 2048,
            },
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
