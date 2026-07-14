import json
import os
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/calendar"
]


class CalendarService:
    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

        self.token_path = Path(
            os.getenv(
                "GOOGLE_TOKEN_PATH",
                "token.json"
            )
        )

    def _validar_configuracion(self):
        faltantes = []

        if not self.client_id:
            faltantes.append("GOOGLE_CLIENT_ID")

        if not self.client_secret:
            faltantes.append("GOOGLE_CLIENT_SECRET")

        if not self.redirect_uri:
            faltantes.append("GOOGLE_REDIRECT_URI")

        if faltantes:
            raise RuntimeError(
                "Faltan variables de Google: "
                + ", ".join(faltantes)
            )

    def _client_config(self):
        self._validar_configuracion()

        return {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": (
                    "https://accounts.google.com/o/oauth2/auth"
                ),
                "token_uri": (
                    "https://oauth2.googleapis.com/token"
                ),
                "redirect_uris": [
                    self.redirect_uri
                ]
            }
        }

    def crear_flujo_oauth(self, state=None):
    return Flow.from_client_config(
        client_config=self._client_config(),
        scopes=SCOPES,
        state=state,
        redirect_uri=self.redirect_uri,
        autogenerate_code_verifier=True
    )


def obtener_url_autorizacion(self):
    flow = self.crear_flujo_oauth()

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )

    return authorization_url, state, flow.code_verifier


def procesar_callback(
    self,
    code,
    state=None,
    code_verifier=None
):
    flow = Flow.from_client_config(
        client_config=self._client_config(),
        scopes=SCOPES,
        state=state,
        redirect_uri=self.redirect_uri,
        code_verifier=code_verifier,
        autogenerate_code_verifier=False
    )

    flow.fetch_token(code=code)

    self.guardar_credenciales(
        flow.credentials
    )
    def guardar_credenciales(self, credentials):
        self.token_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.token_path.write_text(
            credentials.to_json(),
            encoding="utf-8"
        )

    def cargar_credenciales(self):
        if not self.token_path.exists():
            return None

        try:
            credentials = (
                Credentials.from_authorized_user_file(
                    str(self.token_path),
                    SCOPES
                )
            )
        except (ValueError, json.JSONDecodeError):
            return None

        if (
            credentials.expired
            and credentials.refresh_token
        ):
            credentials.refresh(
                GoogleRequest()
            )

            self.guardar_credenciales(
                credentials
            )

        if not credentials.valid:
            return None

        return credentials

    def esta_conectado(self):
        try:
            return (
                self.cargar_credenciales()
                is not None
            )
        except Exception:
            return False

    def obtener_servicio(self):
        credentials = (
            self.cargar_credenciales()
        )

        if not credentials:
            raise RuntimeError(
                "Google Calendar no está conectado. "
                "Abre /google/login para autorizarlo."
            )

        return build(
            "calendar",
            "v3",
            credentials=credentials,
            cache_discovery=False
        )

    def eventos_hoy(self):
        service = self.obtener_servicio()

        zona = ZoneInfo(
            "America/Mexico_City"
        )

        hoy = datetime.now(zona).date()

        inicio_dia = datetime.combine(
            hoy,
            time.min,
            tzinfo=zona
        )

        fin_dia = datetime.combine(
            hoy,
            time.max,
            tzinfo=zona
        )

        resultado = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=inicio_dia.isoformat(),
                timeMax=fin_dia.isoformat(),
                maxResults=20,
                singleEvents=True,
                orderBy="startTime"
            )
            .execute()
        )

        eventos = resultado.get(
            "items",
            []
        )

        if not eventos:
            return "No tienes eventos hoy."

        respuesta = [
            "Tus eventos de hoy son:"
        ]

        for evento in eventos:
            inicio = evento["start"].get(
                "dateTime",
                evento["start"].get("date")
            )

            titulo = evento.get(
                "summary",
                "Sin título"
            )

            if inicio and "T" in inicio:
                fecha = datetime.fromisoformat(
                    inicio.replace(
                        "Z",
                        "+00:00"
                    )
                )

                hora = fecha.astimezone(
                    zona
                ).strftime("%H:%M")
            else:
                hora = "Todo el día"

            respuesta.append(
                f"- {hora} - {titulo}"
            )

        return "\n".join(respuesta)

    def eventos_fecha(self, fecha_iso):
        service = self.obtener_servicio()

        zona = ZoneInfo(
            "America/Mexico_City"
        )

        fecha = datetime.fromisoformat(
            fecha_iso
        ).date()

        inicio_dia = datetime.combine(
            fecha,
            time.min,
            tzinfo=zona
        )

        fin_dia = datetime.combine(
            fecha,
            time.max,
            tzinfo=zona
        )

        resultado = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=inicio_dia.isoformat(),
                timeMax=fin_dia.isoformat(),
                maxResults=20,
                singleEvents=True,
                orderBy="startTime"
            )
            .execute()
        )

        eventos = resultado.get(
            "items",
            []
        )

        if not eventos:
            return (
                "No tienes eventos para "
                f"{fecha.strftime('%d/%m/%Y')}."
            )

        respuesta = [
            "Tus eventos son:"
        ]

        for evento in eventos:
            inicio = evento["start"].get(
                "dateTime",
                evento["start"].get("date")
            )

            titulo = evento.get(
                "summary",
                "Sin título"
            )

            if inicio and "T" in inicio:
                fecha_inicio = (
                    datetime.fromisoformat(
                        inicio.replace(
                            "Z",
                            "+00:00"
                        )
                    )
                )

                hora = fecha_inicio.astimezone(
                    zona
                ).strftime("%H:%M")
            else:
                hora = "Todo el día"

            respuesta.append(
                f"- {hora} - {titulo}"
            )

        return "\n".join(respuesta)

    def crear_evento(
        self,
        titulo,
        inicio,
        fin
    ):
        service = self.obtener_servicio()

        evento = {
            "summary": titulo,
            "start": {
                "dateTime": inicio,
                "timeZone": (
                    "America/Mexico_City"
                )
            },
            "end": {
                "dateTime": fin,
                "timeZone": (
                    "America/Mexico_City"
                )
            }
        }

        evento_creado = (
            service.events()
            .insert(
                calendarId="primary",
                body=evento
            )
            .execute()
        )

        return (
            "Evento creado: "
            + evento_creado.get(
                "summary",
                titulo
            )
        )

    def buscar_eventos(self, texto):
        service = self.obtener_servicio()

        zona = ZoneInfo(
            "America/Mexico_City"
        )

        ahora = datetime.now(
            zona
        )

        resultado = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=ahora.isoformat(),
                maxResults=20,
                singleEvents=True,
                orderBy="startTime",
                q=texto
            )
            .execute()
        )

        eventos = resultado.get(
            "items",
            []
        )

        if not eventos:
            return (
                "No encontré eventos "
                "relacionados."
            )

        respuesta = [
            "Encontré estos eventos:"
        ]

        for evento in eventos:
            titulo = evento.get(
                "summary",
                "Sin título"
            )

            inicio = evento["start"].get(
                "dateTime",
                evento["start"].get("date")
            )

            if inicio and "T" in inicio:
                fecha_inicio = (
                    datetime.fromisoformat(
                        inicio.replace(
                            "Z",
                            "+00:00"
                        )
                    )
                )

                fecha_local = (
                    fecha_inicio.astimezone(
                        zona
                    )
                )

                fecha_texto = (
                    fecha_local.strftime(
                        "%d/%m/%Y %H:%M"
                    )
                )
            else:
                fecha_texto = (
                    f"{inicio} - Todo el día"
                )

            respuesta.append(
                f"- {fecha_texto} - {titulo}"
            )

        return "\n".join(respuesta)

    def mover_evento(
        self,
        texto,
        nuevo_inicio,
        nuevo_fin
    ):
        service = self.obtener_servicio()

        resultado = (
            service.events()
            .list(
                calendarId="primary",
                maxResults=5,
                singleEvents=True,
                orderBy="startTime",
                q=texto
            )
            .execute()
        )

        eventos = resultado.get(
            "items",
            []
        )

        if not eventos:
            return (
                "No encontré un evento "
                "para mover."
            )

        evento = eventos[0]

        evento["start"] = {
            "dateTime": nuevo_inicio,
            "timeZone": (
                "America/Mexico_City"
            )
        }

        evento["end"] = {
            "dateTime": nuevo_fin,
            "timeZone": (
                "America/Mexico_City"
            )
        }

        actualizado = (
            service.events()
            .update(
                calendarId="primary",
                eventId=evento["id"],
                body=evento
            )
            .execute()
        )

        return (
            "Moví el evento: "
            + actualizado.get(
                "summary",
                "Sin título"
            )
        )

    def eliminar_evento(self, texto):
        service = self.obtener_servicio()

        resultado = (
            service.events()
            .list(
                calendarId="primary",
                maxResults=5,
                singleEvents=True,
                orderBy="startTime",
                q=texto
            )
            .execute()
        )

        eventos = resultado.get(
            "items",
            []
        )

        if not eventos:
            return (
                "No encontré un evento "
                "para eliminar."
            )

        evento = eventos[0]

        titulo = evento.get(
            "summary",
            "Sin título"
        )

        (
            service.events()
            .delete(
                calendarId="primary",
                eventId=evento["id"]
            )
            .execute()
        )

        return f"Eliminé el evento: {titulo}"