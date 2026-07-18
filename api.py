from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from openai import OpenAI
from fastapi.responses import HTMLResponse

from fastapi import HTTPException
from fastapi.responses import (
    FileResponse,
    RedirectResponse,
    HTMLResponse
)

from services.spotify_service import SpotifyService

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Request
)

from fastapi.staticfiles import StaticFiles

from fastapi.responses import (
    FileResponse,
    RedirectResponse,
    HTMLResponse
)

from starlette.middleware.sessions import (
    SessionMiddleware
)

from services.calendar_service import (
    CalendarService
)
import uuid
import os

from jarvis import Jarvis
from services.tts_service import TTSService

app = FastAPI()

session_secret = os.getenv(
    "SESSION_SECRET"
)

if not session_secret:
    raise RuntimeError(
        "Falta SESSION_SECRET en Railway."
    )

app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    same_site="lax",
    https_only=True
)
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
spotify_service = SpotifyService()
calendar_service = CalendarService()


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
    
    return {
        "usuario": comando.texto,
        "resultado": resultado,
        "estado": jarvis.estado
    }
class AccionPosterior(BaseModel):
    resultado: str
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


        return {
            "usuario": texto,
            "resultado": resultado,
            "estado": jarvis.estado
        }

    finally:
        if os.path.exists(archivo_audio):
            os.remove(archivo_audio)

@app.get("/spotify/login")
def spotify_login():
    url = spotify_service.obtener_url_autorizacion()

    return RedirectResponse(url=url)


@app.get("/spotify/callback")
def spotify_callback(
    code: str | None = None,
    error: str | None = None
):
    if error:
        return HTMLResponse(
            content=f"""
            <h2>No se pudo conectar Spotify</h2>
            <p>{error}</p>
            """,
            status_code=400
        )

    if not code:
        raise HTTPException(
            status_code=400,
            detail="Spotify no devolvió un código."
        )

    spotify_service.procesar_callback(code)

    return HTMLResponse(
        content="""
        <html>
            <body style="
                background:#020711;
                color:#dffcff;
                font-family:Arial;
                text-align:center;
                padding-top:80px;
            ">
                <h1>Spotify conectado</h1>
                <p>Ya puedes regresar a Jarvis.</p>
                <a
                    href="/web/"
                    style="color:#25dfff;"
                >
                    Volver a Jarvis
                </a>
            </body>
        </html>
        """
    )

@app.get("/google/login")
def google_login(request: Request):
    (
        authorization_url,
        state,
        code_verifier
    ) = calendar_service.obtener_url_autorizacion()

    request.session["google_oauth_state"] = state
    request.session["google_code_verifier"] = code_verifier

    return RedirectResponse(
        url=authorization_url
    )

@app.get("/google/callback")
def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None
):
    if error:
        return HTMLResponse(
            content=f"""
            <html>
                <body style="
                    background:#020711;
                    color:#dffcff;
                    font-family:Arial;
                    text-align:center;
                    padding-top:80px;
                ">
                    <h1>No se pudo conectar Google</h1>
                    <p>{error}</p>
                    <a
                        href="/web/"
                        style="color:#25dfff;"
                    >
                        Volver a Jarvis
                    </a>
                </body>
            </html>
            """,
            status_code=400
        )

    if not code:
        raise HTTPException(
            status_code=400,
            detail=(
                "Google no devolvió "
                "un código."
            )
        )

    expected_state = request.session.get(
        "google_oauth_state"
    )

    if (
        not expected_state
        or state != expected_state
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "El estado OAuth de Google "
                "no coincide."
            )
        )

    
    code_verifier = request.session.get(
    "google_code_verifier"  
    )

    if not code_verifier:
        raise HTTPException(
            status_code=400,
            detail=(
                "No se encontró el code verifier "
                "de Google. Inicia nuevamente desde "
                "/google/login."
            )
        )

    calendar_service.procesar_callback(
    code=code,
    state=state,
    code_verifier=code_verifier
    )

    request.session.pop(
        "google_oauth_state",
        None
    )

    request.session.pop(
        "google_code_verifier",
        None
    )

    return HTMLResponse(
        content="""
        <html>
            <body style="
                background:#020711;
                color:#dffcff;
                font-family:Arial;
                text-align:center;
                padding-top:80px;
            ">
                <h1>Google Calendar conectado</h1>

                <p>
                    Jarvis ya puede consultar
                    y administrar tu calendario.
                </p>

                <a
                    href="/web/"
                    style="
                        color:#25dfff;
                        font-size:18px;
                    "
                >
                    Volver a Jarvis
                </a>
            </body>
        </html>
        """
    )


@app.get("/google/status")
def google_status():
    return {
        "conectado": (
            calendar_service.esta_conectado()
        )
    }
@app.get("/spotify/status")
def spotify_status():
    return {
        "conectado": spotify_service.esta_conectado(),
        "cache_path": spotify_service.cache_path
    }

@app.post("/accion-despues")
def ejecutar_accion_despues(datos: AccionPosterior):
    try:
        resultado_accion = jarvis.accion_despues_de_hablar(
            datos.resultado
        )

        return {
            "ok": True,
            "resultado": resultado_accion
        }

    except Exception as error:
        return {
            "ok": False,
            "error": str(error)
        }

@app.get("/privacy", response_class=HTMLResponse)
def privacy():

    with open(
        "web/legal/privacy.html",
        encoding="utf-8"
    ) as f:

        return f.read()


@app.get("/terms", response_class=HTMLResponse)
def terms():

    with open(
        "web/legal/terms.html",
        encoding="utf-8"
    ) as f:

        return f.read()