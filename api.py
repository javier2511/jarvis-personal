from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from openai import OpenAI

import uuid
import os

from jarvis import Jarvis
from services.tts_service import TTSService

app = FastAPI()
app.mount(
    "/web",
    StaticFiles(
        directory="web",
        html=True
    ),
    name="web"
)
jarvis = Jarvis()
tts = TTSService()
openai_client = OpenAI()


class Comando(BaseModel):
    texto: str


@app.get("/")
def home():
    return {
        "mensaje": "Jarvis API funcionando"
    }


@app.post("/comando")
def ejecutar_comando(comando: Comando):
    resultado = jarvis.procesar_comando(comando.texto)
    jarvis.accion_despues_de_hablar(resultado)
    return {
        "usuario": comando.texto,
        "resultado": resultado,
        "estado": jarvis.estado
    }

@app.post("/voz")
def generar_voz(comando: Comando):
    archivo = f"voz_{uuid.uuid4().hex}.mp3"

    tts.generar_audio(
        texto=comando.texto,
        archivo=archivo
    )

    return FileResponse(
        archivo,
        media_type="audio/mpeg",
        filename="jarvis.mp3"
    )

@app.post("/audio")
async def procesar_audio(audio: UploadFile = File(...)):
    extension = Path(audio.filename or "").suffix

    if not extension:
        tipos = {
            "audio/mp4": ".m4a",
            "audio/x-m4a": ".m4a",
            "audio/webm": ".webm",
            "audio/ogg": ".ogg",
            "audio/wav": ".wav"
        }

        extension = tipos.get(
            audio.content_type,
            ".webm"
        )

    archivo_audio = (
        f"audio_{uuid.uuid4().hex}{extension}"
    )

    try:
        contenido = await audio.read()

        with open(archivo_audio, "wb") as archivo:
            archivo.write(contenido)

        with open(archivo_audio, "rb") as archivo:
            transcripcion = (
                openai_client.audio.transcriptions.create(
                    model="gpt-4o-mini-transcribe",
                    file=archivo,
                    language="es"
                )
            )

        texto = transcripcion.text.strip()

        resultado = jarvis.procesar_comando(texto)

        jarvis.accion_despues_de_hablar(resultado)

        return {
            "usuario": texto,
            "resultado": resultado,
            "estado": jarvis.estado
        }

    finally:
        if os.path.exists(archivo_audio):
            os.remove(archivo_audio)