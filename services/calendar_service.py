

from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/calendar"]

class CalendarService:

    def __init__(self):
        self.service = self.conectar_google_calendar()

    def conectar_google_calendar(self):
        creds = None

        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json",
                    SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open("token.json", "w") as token:
                token.write(creds.to_json())

        return build("calendar", "v3", credentials=creds)

    def eventos_hoy(self):
        zona = ZoneInfo("America/Mexico_City")

        hoy = datetime.now(zona).date()

        inicio_dia = datetime.combine(hoy, time.min, tzinfo=zona)
        fin_dia = datetime.combine(hoy, time.max, tzinfo=zona)

        eventos_resultado = self.service.events().list(
            calendarId="primary",
            timeMin=inicio_dia.isoformat(),
            timeMax=fin_dia.isoformat(),
            maxResults=20,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        eventos = eventos_resultado.get("items", [])

        if not eventos:
            return "No tienes eventos hoy."

        respuesta = "Tus eventos de hoy son:\n"

        for evento in eventos:
            inicio = evento["start"].get("dateTime", evento["start"].get("date"))
            titulo = evento.get("summary", "Sin título")

            if "T" in inicio:
                hora = inicio[11:16]
            else:
                hora = "Todo el día"

            respuesta += f"- {hora} - {titulo}\n"

        return respuesta
    def crear_evento(self, titulo, inicio, fin):

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


        evento_creado = self.service.events().insert(
            calendarId="primary",
            body=evento
        ).execute()


        return f"Evento creado: {evento_creado.get('summary')}"
    
    def buscar_eventos(self, texto):

        eventos_resultado = self.service.events().list(
            calendarId="primary",
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
            q=texto
        ).execute()

        eventos = eventos_resultado.get("items", [])

        if not eventos:
            return "No encontré eventos relacionados."

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

            hora = inicio[11:16] if "T" in inicio else "Todo el día"

            respuesta += f"{hora} - {titulo}\n"


        return respuesta
    
    def mover_evento(self, texto, nuevo_inicio, nuevo_fin):

        eventos_resultado = self.service.events().list(
            calendarId="primary",
            maxResults=5,
            singleEvents=True,
            orderBy="startTime",
            q=texto
        ).execute()

        eventos = eventos_resultado.get("items", [])

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

        evento_actualizado = self.service.events().update(
            calendarId="primary",
            eventId=evento_id,
            body=evento
        ).execute()

        return f"Moví el evento: {evento_actualizado.get('summary')}"

    def eliminar_evento(self, texto):

        eventos_resultado = self.service.events().list(
            calendarId="primary",
            maxResults=5,
            singleEvents=True,
            orderBy="startTime",
            q=texto
        ).execute()


        eventos = eventos_resultado.get("items", [])


        if not eventos:
            return "No encontré un evento para eliminar."


        evento = eventos[0]

        titulo = evento.get(
            "summary",
            "Sin título"
        )


        self.service.events().delete(
            calendarId="primary",
            eventId=evento["id"]
        ).execute()


        return f"Eliminé el evento: {titulo}"