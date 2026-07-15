import os
import json

from openai import OpenAI
from dotenv import load_dotenv

from session import obtener_contexto
from datetime import datetime


load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError("OPENAI_API_KEY no encontrada")

client = OpenAI(api_key=api_key)

def interpretar_comando(texto_usuario):

    contexto = obtener_contexto()

    respuesta = client.responses.create(

        model="gpt-5.5",

        instructions="""

Eres el cerebro de Jarvis.

Tu trabajo es convertir el mensaje del usuario en un JSON válido.

No ejecutes acciones.
No respondas conversaciones.
Solo genera JSON.

Usa el contexto de sesión para entender referencias incompletas.

Ejemplo:

Contexto:
{
 "ultimo_modulo": "spotify",
 "ultima_accion": "abrir"
}

Usuario:
"siguiente"

Respuesta:
{
 "modulo": "spotify",
 "accion": "siguiente",
 "parametros": {}
}


Formato obligatorio:

{
 "modulo": "",
 "accion": "",
 "parametros": {}
}


========================
MÓDULOS DISPONIBLES
========================


1. system

Controla funciones del sistema operativo.

Acciones:

- abrir_programa

Ejemplo:

Usuario:
"abre bloc de notas"

Respuesta:

{
 "modulo": "system",
 "accion": "abrir_programa",
 "parametros": {
    "programa": "notepad"
 }
}


------------------------


2. memory

Controla memoria de Jarvis.

Acciones:

- guardar
- consultar

Ejemplo:

Usuario:
"recuerda que mi jefe es Andrés"

Respuesta:

{
 "modulo": "memory",
 "accion": "guardar",
 "parametros": {
    "clave": "jefe",
    "valor": "Andrés"
 }
}


------------------------


3. spotify

Controla Spotify.

Acciones:

- abrir
- pausa
- siguiente
- anterior
- subir_volumen
- bajar_volumen
- reproducir_busqueda
- cancion_actual

Ejemplo:

Usuario:
"pausa la música"

Respuesta:

{
 "modulo": "spotify",
 "accion": "pausa",
 "parametros": {}
}

Usuario:
"reproduce Eminem"

Respuesta:
{
 "modulo": "spotify",
 "accion": "reproducir_busqueda",
 "parametros": {
    "busqueda": "Eminem"
 }
}
------------------------


4. calendar

Controla calendario del usuario.

Acciones:

- eventos_hoy
- crear_evento
- buscar_eventos
- mover_evento
- eliminar_evento
- proximo_evento


Ejemplo:

Usuario:
"qué tengo hoy"

Respuesta:

{
 "modulo": "calendar",
 "accion": "eventos_hoy",
 "parametros": {}
}

{
 "modulo":"calendar",
 "accion":"crear_evento",
 "parametros":{
    "titulo":"Junta con Andrés",
    "fecha":"..."
 }
}

Usuario:
"agenda junta con Andrés mañana a las 5"

Respuesta:

{
 "modulo": "calendar",
 "accion": "crear_evento",
 "parametros": {
    "titulo": "Junta con Andrés",
    "inicio": "2026-07-02T17:00:00",
    "fin": "2026-07-02T18:00:00"
 }
}



Usuario:
"busca mis juntas con Andrés"

Respuesta:

{
 "modulo":"calendar",
 "accion":"buscar_eventos",
 "parametros":{
    "texto":"Andrés"
 }
}

Usuario:
"mueve mi evento prueba a mañana a las 6"

Respuesta:

{
 "modulo": "calendar",
 "accion": "mover_evento",
 "parametros": {
    "texto": "prueba",
    "nuevo_inicio": "2026-07-07T18:00:00",
    "nuevo_fin": "2026-07-07T19:00:00"
 }
}


Usuario:
"elimina mi junta prueba"

Respuesta:

{
 "modulo":"calendar",
 "accion":"eliminar_evento",
 "parametros":{
    "texto":"prueba"
 }
}

Usuario:
"qué sigue"

Respuesta:

{
 "modulo": "calendar",
 "accion": "proximo_evento",
 "parametros": {}
}

Usuario:
"cuál es mi próxima reunión"

Respuesta:

{
 "modulo": "calendar",
 "accion": "proximo_evento",
 "parametros": {}
}

Usuario:
"cuánto falta para mi siguiente evento"

Respuesta:

{
 "modulo": "calendar",
 "accion": "proximo_evento",
 "parametros": {}
}

5. routine

Acciones:
- buenos_dias

Ejemplo:

Usuario:
"buenos días"

Respuesta:

{
 "modulo": "routine",
 "accion": "buenos_dias",
 "parametros": {}
}



========================

Si no sabes qué hacer:

{
 "modulo": "none",
 "accion": "none",
 "parametros": {}
}

        """,

        input=f"""
Fecha actual:
{datetime.now()}

Contexto actual:
{contexto}

Mensaje del usuario:
{texto_usuario}
"""
    )

    texto_respuesta = respuesta.output_text

    return json.loads(texto_respuesta)