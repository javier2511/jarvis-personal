from __future__ import annotations

import base64
import os
from datetime import datetime, timedelta
from email.header import decode_header, make_header
from pathlib import Path
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from services.calendar_service import SCOPES


MEXICO_TZ = ZoneInfo("America/Mexico_City")


class GmailService:
    """
    Lectura de Gmail para Jarvis.

    Reutiliza el mismo token OAuth de Google Calendar.
    Por ahora usa gmail.readonly: no envía, elimina ni modifica correos.
    """

    def __init__(self):
        self.token_path = Path(
            os.getenv(
                "GOOGLE_TOKEN_PATH",
                "token.json",
            )
        )

    def cargar_credenciales(self):
        if not self.token_path.exists():
            return None

        try:
            credentials = Credentials.from_authorized_user_file(
                str(self.token_path),
                SCOPES,
            )
        except Exception:
            return None

        if credentials.expired and credentials.refresh_token:
            credentials.refresh(GoogleRequest())

            self.token_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            self.token_path.write_text(
                credentials.to_json(),
                encoding="utf-8",
            )

        if not credentials.valid:
            return None

        if not credentials.has_scopes(
            ["https://www.googleapis.com/auth/gmail.readonly"]
        ):
            return None

        return credentials

    def esta_conectado(self) -> bool:
        try:
            return self.cargar_credenciales() is not None
        except Exception:
            return False

    def obtener_servicio(self):
        credentials = self.cargar_credenciales()

        if not credentials:
            raise RuntimeError(
                "Gmail todavía no está autorizado. "
                "Abre /google/login una vez para conceder acceso de lectura."
            )

        return build(
            "gmail",
            "v1",
            credentials=credentials,
            cache_discovery=False,
        )

    @staticmethod
    def _decode_header(valor: str | None) -> str:
        if not valor:
            return ""

        try:
            return str(make_header(decode_header(valor)))
        except Exception:
            return valor

    @staticmethod
    def _headers_a_dict(payload: Dict[str, Any]) -> Dict[str, str]:
        headers = payload.get("headers", []) or []

        return {
            str(item.get("name", "")).lower():
                str(item.get("value", ""))
            for item in headers
            if item.get("name")
        }

    @staticmethod
    def _extraer_texto_payload(payload: Dict[str, Any]) -> str:
        mime_type = payload.get("mimeType", "")
        body = payload.get("body", {}) or {}
        data = body.get("data")

        if mime_type == "text/plain" and data:
            try:
                padding = "=" * (-len(data) % 4)
                decoded = base64.urlsafe_b64decode(data + padding)
                return decoded.decode(
                    "utf-8",
                    errors="replace",
                ).strip()
            except Exception:
                pass

        for parte in payload.get("parts", []) or []:
            texto = GmailService._extraer_texto_payload(parte)
            if texto:
                return texto

        return ""

    def _obtener_mensaje(self, message_id: str) -> Dict[str, Any]:
        service = self.obtener_servicio()

        mensaje = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=message_id,
                format="full",
            )
            .execute()
        )

        payload = mensaje.get("payload", {}) or {}
        headers = self._headers_a_dict(payload)

        timestamp_ms = mensaje.get("internalDate")
        fecha_local = None

        if timestamp_ms:
            try:
                fecha_local = datetime.fromtimestamp(
                    int(timestamp_ms) / 1000,
                    tz=MEXICO_TZ,
                )
            except Exception:
                fecha_local = None

        cuerpo = self._extraer_texto_payload(payload)

        if len(cuerpo) > 1400:
            cuerpo = cuerpo[:1400].rstrip() + "..."

        return {
            "id": mensaje.get("id"),
            "thread_id": mensaje.get("threadId"),
            "remitente": self._decode_header(
                headers.get("from")
            ),
            "asunto": self._decode_header(
                headers.get("subject")
            ) or "(Sin asunto)",
            "fecha": (
                fecha_local.isoformat()
                if fecha_local
                else headers.get("date", "")
            ),
            "snippet": (
                mensaje.get("snippet", "")
                or ""
            ).strip(),
            "cuerpo": cuerpo,
            "labels": mensaje.get(
                "labelIds",
                [],
            ),
        }

    def _buscar(
        self,
        query: str,
        limite: int = 8,
    ) -> List[Dict[str, Any]]:
        service = self.obtener_servicio()

        resultado = (
            service.users()
            .messages()
            .list(
                userId="me",
                q=query,
                maxResults=max(
                    1,
                    min(int(limite), 20),
                ),
            )
            .execute()
        )

        mensajes = resultado.get("messages", [])

        return [
            self._obtener_mensaje(item["id"])
            for item in mensajes
            if item.get("id")
        ]

    @staticmethod
    def _resumir_lista(
        mensajes: List[Dict[str, Any]],
        encabezado: str,
    ) -> str:
        if not mensajes:
            return "No encontré correos que coincidan."

        partes = [encabezado]

        for mensaje in mensajes:
            remitente = (
                mensaje.get("remitente")
                or "remitente desconocido"
            )
            asunto = (
                mensaje.get("asunto")
                or "(Sin asunto)"
            )
            snippet = (
                mensaje.get("snippet")
                or mensaje.get("cuerpo")
                or ""
            ).strip()

            if len(snippet) > 180:
                snippet = snippet[:177].rstrip() + "..."

            texto = f"De {remitente}: {asunto}"

            if snippet:
                texto += f". {snippet}"

            partes.append(texto)

        return "\n".join(partes)

    def correos_hoy(self, limite: int = 8) -> str:
        hoy = datetime.now(MEXICO_TZ).date()
        manana = hoy + timedelta(days=1)

        query = (
            f"after:{hoy.strftime('%Y/%m/%d')} "
            f"before:{manana.strftime('%Y/%m/%d')} "
            "-category:promotions -category:social"
        )

        mensajes = self._buscar(
            query,
            limite=limite,
        )

        if not mensajes:
            return "No encontré correos relevantes de hoy."

        return self._resumir_lista(
            mensajes,
            f"Tienes {len(mensajes)} correos relevantes de hoy.",
        )

    def importantes(self, limite: int = 6) -> str:
        query = (
            "(is:important OR is:unread) "
            "newer_than:7d "
            "-category:promotions "
            "-category:social "
            "-category:forums"
        )

        mensajes = self._buscar(
            query,
            limite=limite,
        )

        if not mensajes:
            return (
                "No encontré correos importantes "
                "o no leídos recientes."
            )

        return self._resumir_lista(
            mensajes,
            f"Encontré {len(mensajes)} correos que conviene revisar.",
        )

    def buscar(
        self,
        consulta: str,
        limite: int = 6,
    ) -> str:
        consulta = (consulta or "").strip()

        if not consulta:
            return "Necesito saber qué correo quieres buscar."

        mensajes = self._buscar(
            consulta,
            limite=limite,
        )

        if not mensajes:
            return (
                f"No encontré correos relacionados con {consulta}."
            )

        return self._resumir_lista(
            mensajes,
            f"Encontré {len(mensajes)} correos relacionados con {consulta}.",
        )

    def de_remitente(
        self,
        remitente: str,
        limite: int = 6,
    ) -> str:
        remitente = (remitente or "").strip()

        if not remitente:
            return "Necesito saber de quién quieres buscar correos."

        mensajes = self._buscar(
            f"from:({remitente}) newer_than:90d",
            limite=limite,
        )

        if not mensajes:
            mensajes = self._buscar(
                f'"{remitente}" newer_than:90d',
                limite=limite,
            )

        if not mensajes:
            return (
                f"No encontré correos recientes de {remitente}."
            )

        return self._resumir_lista(
            mensajes,
            f"Encontré {len(mensajes)} correos recientes de {remitente}.",
        )

    def ultimos(self, limite: int = 5) -> str:
        mensajes = self._buscar(
            "-category:promotions -category:social",
            limite=limite,
        )

        if not mensajes:
            return "No encontré correos recientes."

        return self._resumir_lista(
            mensajes,
            f"Tus últimos {len(mensajes)} correos relevantes son:",
        )
