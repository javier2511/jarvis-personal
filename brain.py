import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from openai import OpenAI
from session import obtener_contexto


load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("JARVIS_MODEL", "gpt-5.5")
USER_NAME = os.getenv("JARVIS_USER_NAME", "Javier").strip()

if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY no encontrada")

client = OpenAI(api_key=API_KEY)


INSTRUCCIONES_BASE = """
Eres el cerebro de Jarvis.

Convierte el mensaje del usuario en un único objeto JSON válido.
No ejecutes acciones.
No agregues markdown, explicaciones ni texto adicional.

Formato obligatorio:
{
  "modulo": "",
  "accion": "",
  "parametros": {}
}

Usa el contexto de sesión y la memoria personal únicamente para interpretar
referencias incompletas. Nunca inventes recuerdos.

MÓDULOS Y ACCIONES

system:
- abrir_programa
Parámetros:
- programa

memory:
- guardar
  Parámetros:
  - contenido: recuerdo completo y autosuficiente
  - categoria: personal, trabajo, preferencias, relaciones, planes u otro
  - importancia: entero de 1 a 5
  - etiquetas: lista de palabras

- consultar
  Parámetros:
  - consulta

- listar
  Parámetros:
  - opcionales

- eliminar
  Parámetros:
  - consulta

spotify:
- abrir
- pausa
- siguiente
- anterior
- cancion_actual
- reproducir_busqueda

Parámetros de reproducir_busqueda:
- busqueda

calendar:
- eventos_hoy
- proximo_evento
- crear_evento
- buscar_eventos
- mover_evento
- eliminar_evento

routine:
- buenos_dias

sports:
- proximo_evento
- ultimo_resultado
- noticias_equipo

Parámetros:
- equipo

none:
- none

EJEMPLOS

Usuario: recuerda que mi jefe se llama Andrés
{
  "modulo": "memory",
  "accion": "guardar",
  "parametros": {
    "contenido": "El jefe de Javier se llama Andrés.",
    "categoria": "trabajo",
    "importancia": 4,
    "etiquetas": ["jefe", "Andrés", "trabajo"]
  }
}

Usuario: qué recuerdas de mi novia
{
  "modulo": "memory",
  "accion": "consultar",
  "parametros": {
    "consulta": "novia"
  }
}

Usuario: qué recuerdas de mí
{
  "modulo": "memory",
  "accion": "listar",
  "parametros": {}
}

Usuario: olvida que entreno los martes
{
  "modulo": "memory",
  "accion": "eliminar",
  "parametros": {
    "consulta": "entreno los martes"
  }
}

Usuario: reproduce Eminem
{
  "modulo": "spotify",
  "accion": "reproducir_busqueda",
  "parametros": {
    "busqueda": "Eminem"
  }
}

Usuario: cuándo juegan los Giants
{
  "modulo": "sports",
  "accion": "proximo_evento",
  "parametros": {
    "equipo": "New York Giants"
  }
}

Cuando no corresponda ninguna acción:
{
  "modulo": "none",
  "accion": "none",
  "parametros": {}
}
""".strip()


def _construir_instrucciones():
    return (
        INSTRUCCIONES_BASE
        + f"""

DATOS DEL USUARIO

El nombre del usuario es {USER_NAME}.

Cuando redactes recuerdos:
- Usa siempre "{USER_NAME}".
- Nunca escribas "el usuario", "la persona" ni expresiones impersonales.
- Redacta el recuerdo como una frase completa y autosuficiente.

Ejemplo incorrecto:
"El usuario le va a los Giants."

Ejemplo correcto:
"{USER_NAME} le va a los New York Giants."
"""
    ).strip()


def _extraer_json(texto):
    texto = (texto or "").strip()

    if texto.startswith("```"):
        lineas = texto.splitlines()

        if lineas and lineas[0].startswith("```"):
            lineas = lineas[1:]

        if lineas and lineas[-1].strip() == "```":
            lineas = lineas[:-1]

        texto = "\n".join(lineas).strip()

    inicio = texto.find("{")
    fin = texto.rfind("}")

    if inicio == -1 or fin == -1 or fin < inicio:
        raise ValueError("La IA no devolvió un JSON válido.")

    datos = json.loads(texto[inicio:fin + 1])

    if not isinstance(datos, dict):
        raise ValueError("La interpretación debe ser un objeto JSON.")

    datos.setdefault("modulo", "none")
    datos.setdefault("accion", "none")
    datos.setdefault("parametros", {})

    if not isinstance(datos["parametros"], dict):
        datos["parametros"] = {}

    return datos


def interpretar_comando(texto_usuario, memoria_contexto=""):
    contexto_sesion = obtener_contexto()

    zona = ZoneInfo("America/Mexico_City")
    fecha_actual = datetime.now(zona).isoformat()
    instrucciones = _construir_instrucciones()

    respuesta = client.responses.create(
        model=MODEL,
        instructions=instrucciones,
        input=f"""
Fecha actual:
{fecha_actual}

Nombre del usuario:
{USER_NAME}

Contexto de sesión:
{contexto_sesion}

Memoria personal disponible:
{memoria_contexto or "Sin recuerdos relevantes."}

Mensaje del usuario:
{texto_usuario}
""".strip(),
    )

    return _extraer_json(respuesta.output_text)
