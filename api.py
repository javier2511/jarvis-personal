from __future__ import annotations

import os
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

from jarvis import Jarvis
from services.calendar_service import CalendarService
from services.spotify_service import SpotifyService
from services.tts_service import TTSService


# -----------------------------------------------------------------------------
# APLICACIÓN Y SERVICIOS
# -----------------------------------------------------------------------------

app = FastAPI(title="Jarvis API", version="2.0")

session_secret = os.getenv("SESSION_SECRET")

if not session_secret:
    raise RuntimeError("Falta SESSION_SECRET en Railway.")

app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    same_site="lax",
    https_only=True,
)

app.mount(
    "/web",
    StaticFiles(directory="web", html=True),
    name="web",
)

jarvis = Jarvis()
tts = TTSService()
openai_client = OpenAI()
spotify_service = SpotifyService()
calendar_service = CalendarService()


# -----------------------------------------------------------------------------
# ACCIONES POSTERIORES PENDIENTES
# -----------------------------------------------------------------------------
#
# La web actual muestra y envía nuevamente solo el texto de la respuesta al
# endpoint /accion-despues. Como las rutinas ahora devuelven un objeto con
# "texto" y "acciones", conservamos temporalmente las acciones asociadas al
# texto. Esto mantiene compatibilidad sin obligar a cambiar el frontend ahora.
#

_pending_actions: Dict[str, List[Dict[str, Any]]] = {}
_pending_actions_lock = threading.Lock()
_MAX_PENDING_RESPONSES = 50


def _registrar_acciones_pendientes(
    texto: str,
    acciones: List[Dict[str, Any]],
) -> None:
    if not texto or not acciones:
        return

    with _pending_actions_lock:
        _pending_actions[texto] = acciones

        while len(_pending_actions) > _MAX_PENDING_RESPONSES:
            primera_clave = next(iter(_pending_actions))
            _pending_actions.pop(primera_clave, None)


def _extraer_acciones_pendientes(texto: str) -> List[Dict[str, Any]]:
    if not texto:
        return []

    with _pending_actions_lock:
        return _pending_actions.pop(texto, [])


def _preparar_respuesta(
    texto_usuario: str,
    resultado_crudo: Any,
) -> Dict[str, Any]:
    """Convierte cualquier resultado de Jarvis a un contrato web estable."""

    texto_respuesta, acciones = jarvis._normalizar_resultado(resultado_crudo)

    if not texto_respuesta:
        texto_respuesta = (
            "La acción terminó, pero no recibí una respuesta para mostrar."
        )

    _registrar_acciones_pendientes(texto_respuesta, acciones)

    return {
        "usuario": texto_usuario,
        "resultado": texto_respuesta,
        "acciones": acciones,
        "estado": jarvis.estado,
    }


# -----------------------------------------------------------------------------
# MODELOS
# -----------------------------------------------------------------------------


class Comando(BaseModel):
    texto: str


class AccionPosterior(BaseModel):
    # Se conserva "resultado" para que el frontend actual siga funcionando.
    # También se admite una respuesta estructurada o una lista explícita de
    # acciones para futuras versiones de la interfaz.
    resultado: Any = None
    acciones: List[Dict[str, Any]] = Field(default_factory=list)


# -----------------------------------------------------------------------------
# ENDPOINTS PRINCIPALES
# -----------------------------------------------------------------------------


@app.get("/")
def home() -> Dict[str, str]:
    return {"mensaje": "Jarvis API funcionando"}


@app.post("/comando")
def ejecutar_comando(comando: Comando) -> Dict[str, Any]:
    resultado_crudo = jarvis.procesar_comando(comando.texto)
    return _preparar_respuesta(comando.texto, resultado_crudo)


@app.post("/voz")
def generar_voz(comando: Comando):
    texto = comando.texto.strip()

    if not texto:
        raise HTTPException(
            status_code=400,
            detail="No se recibió texto para generar el audio.",
        )

    archivo = f"voz_{uuid.uuid4().hex}.mp3"

    try:
        tts.generar_audio(
            texto=texto,
            archivo=archivo,
        )

        return FileResponse(
            archivo,
            media_type="audio/mpeg",
            filename="jarvis.mp3",
            background=None,
        )

    except Exception as error:
        if os.path.exists(archivo):
            os.remove(archivo)

        raise HTTPException(
            status_code=500,
            detail=f"No se pudo generar el audio: {error}",
        ) from error


@app.post("/audio")
async def procesar_audio(audio: UploadFile = File(...)) -> Dict[str, Any]:
    extension = Path(audio.filename or "").suffix

    if not extension:
        tipos = {
            "audio/mp4": ".m4a",
            "audio/x-m4a": ".m4a",
            "audio/webm": ".webm",
            "audio/ogg": ".ogg",
            "audio/wav": ".wav",
        }

        extension = tipos.get(audio.content_type, ".webm")

    archivo_audio = f"audio_{uuid.uuid4().hex}{extension}"

    try:
        contenido = await audio.read()

        if not contenido:
            raise HTTPException(
                status_code=400,
                detail="El archivo de audio está vacío.",
            )

        with open(archivo_audio, "wb") as archivo:
            archivo.write(contenido)

        with open(archivo_audio, "rb") as archivo:
            transcripcion = openai_client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=archivo,
                language="es",
            )

        texto_usuario = (transcripcion.text or "").strip()

        if not texto_usuario:
            raise HTTPException(
                status_code=422,
                detail="No se pudo obtener texto del audio.",
            )

        resultado_crudo = jarvis.procesar_comando(texto_usuario)
        return _preparar_respuesta(texto_usuario, resultado_crudo)

    finally:
        if os.path.exists(archivo_audio):
            os.remove(archivo_audio)


@app.post("/accion-despues")
def ejecutar_accion_despues(datos: AccionPosterior) -> Dict[str, Any]:
    try:
        acciones = list(datos.acciones)

        # Formato futuro: {resultado: {texto: ..., acciones: [...]}}
        if not acciones and isinstance(datos.resultado, dict):
            _, acciones = jarvis._normalizar_resultado(datos.resultado)

        # Compatibilidad con la web actual: vuelve a mandar solo el texto.
        if not acciones and isinstance(datos.resultado, str):
            acciones = _extraer_acciones_pendientes(datos.resultado.strip())

        if not acciones:
            return {
                "ok": True,
                "resultado": [],
                "mensaje": "No había acciones posteriores pendientes.",
            }

        resultados = jarvis.ejecutar_acciones_posteriores(acciones)

        return {
            "ok": True,
            "resultado": resultados,
        }

    except Exception as error:
        return {
            "ok": False,
            "error": str(error),
        }


# -----------------------------------------------------------------------------
# SPOTIFY
# -----------------------------------------------------------------------------


@app.get("/spotify/login")
def spotify_login():
    url = spotify_service.obtener_url_autorizacion()
    return RedirectResponse(url=url)


@app.get("/spotify/callback")
def spotify_callback(
    code: str | None = None,
    error: str | None = None,
):
    if error:
        return HTMLResponse(
            content=f"""
            <h2>No se pudo conectar Spotify</h2>
            <p>{error}</p>
            """,
            status_code=400,
        )

    if not code:
        raise HTTPException(
            status_code=400,
            detail="Spotify no devolvió un código.",
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
                <a href="/web/" style="color:#25dfff;">
                    Volver a Jarvis
                </a>
            </body>
        </html>
        """
    )


@app.get("/spotify/status")
def spotify_status() -> Dict[str, Any]:
    return {
        "conectado": spotify_service.esta_conectado(),
        "cache_path": spotify_service.cache_path,
    }


# -----------------------------------------------------------------------------
# GOOGLE CALENDAR
# -----------------------------------------------------------------------------


@app.get("/google/login")
def google_login(request: Request):
    authorization_url, state, code_verifier = (
        calendar_service.obtener_url_autorizacion()
    )

    request.session["google_oauth_state"] = state
    request.session["google_code_verifier"] = code_verifier

    return RedirectResponse(url=authorization_url)


@app.get("/google/callback")
def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
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
                    <a href="/web/" style="color:#25dfff;">
                        Volver a Jarvis
                    </a>
                </body>
            </html>
            """,
            status_code=400,
        )

    if not code:
        raise HTTPException(
            status_code=400,
            detail="Google no devolvió un código.",
        )

    expected_state = request.session.get("google_oauth_state")

    if not expected_state or state != expected_state:
        raise HTTPException(
            status_code=400,
            detail="El estado OAuth de Google no coincide.",
        )

    code_verifier = request.session.get("google_code_verifier")

    if not code_verifier:
        raise HTTPException(
            status_code=400,
            detail=(
                "No se encontró el code verifier de Google. "
                "Inicia nuevamente desde /google/login."
            ),
        )

    calendar_service.procesar_callback(
        code=code,
        state=state,
        code_verifier=code_verifier,
    )

    request.session.pop("google_oauth_state", None)
    request.session.pop("google_code_verifier", None)

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
                    Jarvis ya puede consultar y administrar tu calendario.
                </p>
                <a
                    href="/web/"
                    style="color:#25dfff;font-size:18px;"
                >
                    Volver a Jarvis
                </a>
            </body>
        </html>
        """
    )


@app.get("/google/status")
def google_status() -> Dict[str, bool]:
    return {
        "conectado": calendar_service.esta_conectado(),
    }


# -----------------------------------------------------------------------------
# LEGALES
# -----------------------------------------------------------------------------


@app.get("/privacy", response_class=HTMLResponse)
def privacy():
    with open("web/legal/privacy.html", encoding="utf-8") as archivo:
        return archivo.read()


@app.get("/terms", response_class=HTMLResponse)
def terms():
    with open("web/legal/terms.html", encoding="utf-8") as archivo:
        return archivo.read()
