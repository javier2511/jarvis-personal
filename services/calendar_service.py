import os
from datetime import datetime, time
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/calendar"
]


class CalendarService:

    def __init__(self):
        self.service = self.conectar_google_calendar()

    def esta_en_cloud(self):
        """
        Detecta si Jarvis está ejecutándose en Railway.

        En Railway no podemos usar el flujo OAuth local que abre
        un navegador con run_local_server().
        """
        return bool(
            os.getenv("RAILWAY_ENVIRONMENT")
            or os.getenv("RAILWAY_PROJECT_ID")
            or os.getenv("RAILWAY_SERVICE_ID")
        )

    def conectar_google_calendar(self):
        """
        En PC usa credentials.json y token.json.

        En Railway se desactiva temporalmente Calendar para permitir
        que Jarvis Cloud arranque correctamente.
        """
        if self.esta_en_cloud():
            print(
                "CalendarService: Google Calendar local "
                "desactivado en Railway."
            )
            return None

        creds = None

        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file(
                "token.json",
                SCOPES
            )

        if not creds or not creds.valid:

            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())

            else:
                if not os.path.exists("credentials.json"):
                    raise FileNotFoundError(
                        "No encontré credentials.json en la carpeta "
                        "principal de Jarvis."
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json",
                    SCOPES
                )

                creds = flow.run_local_server(port=0)

            with open(
                "token.json",
                "w",
                encoding="utf-8"
            ) as token:
                token.write(creds.to_json())

        return build(
            "calendar",
            "v3",
            credentials=creds
        )

    def verificar_disponibilidad(self):
        """
        Devuelve un mensaje cuando Calendar todavía no está disponible
        en la versión cloud.
        """
        if self.service is None:
            return (
                "Google Calendar todavía no está configurado "
                "en la versión cloud de Jarvis."
            )

        return None

    def eventos_hoy(self):
        error = self.verificar_disponibilidad()

        if error:
            return error

        zona = ZoneInfo("America/Mexico_City")
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

        eventos_resultado = (
            self.service.events()
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

        eventos = eventos_resultado.get(
            "items",
            []
        )

        if not eventos:
            return "No tienes eventos hoy."

        respuesta = "Tus eventos de hoy son:\n"

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
                fecha_inicio = datetime.fromisoformat(
                    inicio.replace("Z", "+00:00")
                )

                hora = fecha_inicio.astimezone(
                    zona
                ).strftime("%H:%M")

            else:
                hora = "Todo el día"

            respuesta += f"- {hora} - {titulo}\n"

        return respuesta.strip()

    def crear_evento(
        self,
        titulo,
        inicio,
        fin
    ):
        error = self.verificar_disponibilidad()

        if error:
            return error

        evento = {
            "summary": titulo,
            "start": {
                "dateTime": inicio,
                "timeZone": "America/Mexico_City"
            },
            "end": {
                "dateTime": fin,
                "timeZone": "America/Mexico_City"
            }
        }

        evento_creado = (
            self.service.events()
            .insert(
                calendarId="primary",
                body=evento
            )
            .execute()
        )

        titulo_creado = evento_creado.get(
            "summary",
            titulo
        )

        return f"Evento creado: {titulo_creado}"

    def buscar_eventos(self, texto):
        error = self.verificar_disponibilidad()

        if error:
            return error

        eventos_resultado = (
            self.service.events()
            .list(
                calendarId="primary",
                maxResults=10,
                singleEvents=True,
                orderBy="startTime",
                q=texto
            )
            .execute()
        )

        eventos = eventos_resultado.get(
            "items",
            []
        )

        if not eventos:
            return "No encontré eventos relacionados."

        zona = ZoneInfo("America/Mexico_City")
        respuesta = "Encontré estos eventos:\n"

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
                fecha_inicio = datetime.fromisoformat(
                    inicio.replace("Z", "+00:00")
                )

                fecha_local = fecha_inicio.astimezone(
                    zona
                )

                fecha_formateada = fecha_local.strftime(
                    "%d/%m/%Y %H:%M"
                )

            else:
                fecha_formateada = (
                    f"{inicio} - Todo el día"
                )

            respuesta += (
                f"- {fecha_formateada} - {titulo}\n"
            )

        return respuesta.strip()

    def mover_evento(
        self,
        texto,
        nuevo_inicio,
        nuevo_fin
    ):
        error = self.verificar_disponibilidad()

        if error:
            return error

        eventos_resultado = (
            self.service.events()
            .list(
                calendarId="primary",
                maxResults=5,
                singleEvents=True,
                orderBy="startTime",
                q=texto
            )
            .execute()
        )

        eventos = eventos_resultado.get(
            "items",
            []
        )

        if not eventos:
            return "No encontré un evento para mover."

        evento = eventos[0]
        evento_id = evento["id"]

        evento["start"] = {
            "dateTime": nuevo_inicio,
            "timeZone": "America/Mexico_City"
        }

        evento["end"] = {
            "dateTime": nuevo_fin,
            "timeZone": "America/Mexico_City"
        }

        evento_actualizado = (
            self.service.events()
            .update(
                calendarId="primary",
                eventId=evento_id,
                body=evento
            )
            .execute()
        )

        titulo = evento_actualizado.get(
            "summary",
            "Sin título"
        )

        return f"Moví el evento: {titulo}"

    def eliminar_evento(self, texto):
        error = self.verificar_disponibilidad()

        if error:
            return error

        eventos_resultado = (
            self.service.events()
            .list(
                calendarId="primary",
                maxResults=5,
                singleEvents=True,
                orderBy="startTime",
                q=texto
            )
            .execute()
        )

        eventos = eventos_resultado.get(
            "items",
            []
        )

        if not eventos:
            return "No encontré un evento para eliminar."

        evento = eventos[0]

        titulo = evento.get(
            "summary",
            "Sin título"
        )

        (
            self.service.events()
            .delete(
                calendarId="primary",
                eventId=evento["id"]
            )
            .execute()
        )

        return f"Eliminé el evento: {titulo}"