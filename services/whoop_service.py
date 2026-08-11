from __future__ import annotations

import json
import os
import secrets
import time
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlencode

import requests


class WhoopService:

    AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
    TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"

    SCOPES = [
        "offline",
        "read:recovery",
        "read:cycles",
        "read:sleep",
        "read:workout",
        "read:body_measurement",
        "read:profile",
    ]

    def __init__(self):

        self.client_id = os.getenv("WHOOP_CLIENT_ID")
        self.client_secret = os.getenv("WHOOP_CLIENT_SECRET")
        self.redirect_uri = os.getenv("WHOOP_REDIRECT_URI")

        self.token_path = Path(
            os.getenv(
                "WHOOP_TOKEN_PATH",
                "/app/data/whoop_token.json",
            )
        )

        if not self.client_id:
            raise RuntimeError(
                "Falta WHOOP_CLIENT_ID."
            )

        if not self.client_secret:
            raise RuntimeError(
                "Falta WHOOP_CLIENT_SECRET."
            )

        if not self.redirect_uri:
            raise RuntimeError(
                "Falta WHOOP_REDIRECT_URI."
            )

    # ------------------------------------------------------------------
    # TOKEN
    # ------------------------------------------------------------------

    def _guardar_token(
        self,
        token: Dict[str, Any],
    ) -> None:

        self.token_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        token["saved_at"] = int(time.time())

        with self.token_path.open(
            "w",
            encoding="utf-8",
        ) as archivo:

            json.dump(
                token,
                archivo,
                indent=2,
            )

    def _leer_token(
        self,
    ) -> Dict[str, Any] | None:

        if not self.token_path.exists():
            return None

        try:

            with self.token_path.open(
                "r",
                encoding="utf-8",
            ) as archivo:

                return json.load(archivo)

        except Exception:

            return None

    # ------------------------------------------------------------------
    # LOGIN
    # ------------------------------------------------------------------

    def obtener_url_autorizacion(
        self,
    ) -> tuple[str, str]:

        # WHOOP requiere state de al menos 8 caracteres.
        state = secrets.token_urlsafe(24)

        parametros = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.SCOPES),
            "state": state,
        }

        url = (
            f"{self.AUTH_URL}?"
            f"{urlencode(parametros)}"
        )

        return url, state

    # ------------------------------------------------------------------
    # CALLBACK
    # ------------------------------------------------------------------

    def procesar_callback(
        self,
        code: str,
    ) -> Dict[str, Any]:

        respuesta = requests.post(
            self.TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
            },
            headers={
                "Content-Type":
                    "application/x-www-form-urlencoded",
            },
            timeout=20,
        )

        if not respuesta.ok:

            raise RuntimeError(
                "WHOOP rechazó el intercambio "
                f"del código: {respuesta.status_code} "
                f"{respuesta.text}"
            )

        token = respuesta.json()

        self._guardar_token(token)

        return token

    # ------------------------------------------------------------------
    # REFRESH
    # ------------------------------------------------------------------

    def refrescar_token(
        self,
    ) -> Dict[str, Any]:

        token_actual = self._leer_token()

        if not token_actual:
            raise RuntimeError(
                "WHOOP todavía no está conectado."
            )

        refresh_token = token_actual.get(
            "refresh_token"
        )

        if not refresh_token:
            raise RuntimeError(
                "WHOOP no devolvió refresh_token. "
                "Vuelve a autorizar incluyendo offline."
            )

        respuesta = requests.post(
            self.TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "offline",
            },
            headers={
                "Content-Type":
                    "application/x-www-form-urlencoded",
            },
            timeout=20,
        )

        if not respuesta.ok:

            raise RuntimeError(
                "No se pudo renovar WHOOP: "
                f"{respuesta.status_code} "
                f"{respuesta.text}"
            )

        nuevo_token = respuesta.json()

        self._guardar_token(
            nuevo_token
        )

        return nuevo_token

    # ------------------------------------------------------------------
    # ESTADO
    # ------------------------------------------------------------------

    def esta_conectado(
        self,
    ) -> bool:

        token = self._leer_token()

        if not token:
            return False

        return bool(
            token.get("access_token")
        )