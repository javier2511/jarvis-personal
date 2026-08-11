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

    API_BASE = "https://api.prod.whoop.com/developer/v2"

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
            raise RuntimeError("Falta WHOOP_CLIENT_ID.")

        if not self.client_secret:
            raise RuntimeError("Falta WHOOP_CLIENT_SECRET.")

        if not self.redirect_uri:
            raise RuntimeError("Falta WHOOP_REDIRECT_URI.")

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
    # OAUTH
    # ------------------------------------------------------------------

    def obtener_url_autorizacion(
        self,
    ) -> tuple[str, str]:

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
                "WHOOP rechazó el intercambio del código: "
                f"{respuesta.status_code} "
                f"{respuesta.text}"
            )

        token = respuesta.json()

        self._guardar_token(token)

        return token

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
                "WHOOP no tiene refresh_token. "
                "Vuelve a realizar /whoop/login."
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
    # REQUESTS
    # ------------------------------------------------------------------

    def _request(
        self,
        endpoint: str,
        params: Dict[str, Any] | None = None,
        reintentar: bool = True,
    ) -> Dict[str, Any]:

        token = self._leer_token()

        if not token:

            raise RuntimeError(
                "WHOOP no está conectado."
            )

        access_token = token.get(
            "access_token"
        )

        if not access_token:

            raise RuntimeError(
                "No encontré access_token de WHOOP."
            )

        respuesta = requests.get(
            f"{self.API_BASE}{endpoint}",
            headers={
                "Authorization":
                    f"Bearer {access_token}",
            },
            params=params,
            timeout=20,
        )


        
        if (
            respuesta.status_code == 401
            and reintentar
        ):

            self.refrescar_token()

            return self._request(
                endpoint=endpoint,
                params=params,
                reintentar=False,
            )

        if not respuesta.ok:

            raise RuntimeError(
                "Error consultando WHOOP "
                f"{endpoint}: "
                f"{respuesta.status_code} "
                f"{respuesta.text}"
            )

        return respuesta.json()

    # ------------------------------------------------------------------
    # PERFIL
    # ------------------------------------------------------------------

    def perfil(
        self,
    ) -> Dict[str, Any]:

        return self._request(
            "/user/profile/basic"
        )

    # ------------------------------------------------------------------
    # RECOVERY
    # ------------------------------------------------------------------

    def recovery_actual(
        self,
    ) -> Dict[str, Any] | None:

        datos = self._request(
            "/recovery",
            params={
                "limit": 1,
            },
        )

        records = datos.get(
            "records",
            [],
        )

        if not records:
            return None

        return records[0]

    # ------------------------------------------------------------------
    # CYCLE / STRAIN
    # ------------------------------------------------------------------

    def cycle_actual(
        self,
    ) -> Dict[str, Any] | None:

        datos = self._request(
            "/cycle",
            params={
                "limit": 1,
            },
        )

        records = datos.get(
            "records",
            [],
        )

        if not records:
            return None

        return records[0]

    # ------------------------------------------------------------------
    # SLEEP
    # ------------------------------------------------------------------

    def sleep_actual(
        self,
    ) -> Dict[str, Any] | None:

        datos = self._request(
            "/activity/sleep",
            params={
                "limit": 5,
            },
        )

        records = datos.get(
            "records",
            [],
        )

        if not records:
            return None

        /*
            Evitamos devolver una siesta como
            sueño principal.
        */

        for sleep in records:

            if not sleep.get(
                "nap",
                False,
            ):

                return sleep

        return records[0]

    # ------------------------------------------------------------------
    # RESUMEN
    # ------------------------------------------------------------------

    @staticmethod
    def _horas_desde_milisegundos(
        milisegundos,
    ) -> float | None:

        if milisegundos is None:
            return None

        return round(
            milisegundos
            / 1000
            / 60
            / 60,
            2,
        )

    def resumen_hoy(
        self,
    ) -> Dict[str, Any]:

        recovery = self.recovery_actual()
        cycle = self.cycle_actual()
        sleep = self.sleep_actual()

        resultado = {
            "recovery": None,
            "hrv": None,
            "resting_heart_rate": None,
            "spo2": None,
            "skin_temp_celsius": None,
            "strain": None,
            "sleep_hours": None,
            "sleep_performance": None,
            "sleep_efficiency": None,
            "sleep_consistency": None,
            "respiratory_rate": None,
        }

        # Recovery

        if (
            recovery
            and recovery.get(
                "score_state"
            ) == "SCORED"
        ):

            score = recovery.get(
                "score",
                {},
            )

            resultado["recovery"] = (
                score.get(
                    "recovery_score"
                )
            )

            resultado["hrv"] = (
                score.get(
                    "hrv_rmssd_milli"
                )
            )

            resultado[
                "resting_heart_rate"
            ] = score.get(
                "resting_heart_rate"
            )

            resultado["spo2"] = (
                score.get(
                    "spo2_percentage"
                )
            )

            resultado[
                "skin_temp_celsius"
            ] = score.get(
                "skin_temp_celsius"
            )

        # Cycle / Strain

        if (
            cycle
            and cycle.get(
                "score_state"
            ) == "SCORED"
        ):

            score = cycle.get(
                "score",
                {},
            )

            resultado["strain"] = (
                score.get(
                    "strain"
                )
            )

        # Sleep

        if (
            sleep
            and sleep.get(
                "score_state"
            ) == "SCORED"
        ):

            score = sleep.get(
                "score",
                {},
            )

            stages = score.get(
                "stage_summary",
                {},
            )

            total_sleep_milli = (
                stages.get(
                    "total_light_sleep_time_milli",
                    0,
                )
                + stages.get(
                    "total_slow_wave_sleep_time_milli",
                    0,
                )
                + stages.get(
                    "total_rem_sleep_time_milli",
                    0,
                )
            )

            resultado["sleep_hours"] = (
                self._horas_desde_milisegundos(
                    total_sleep_milli
                )
            )

            resultado[
                "sleep_performance"
            ] = score.get(
                "sleep_performance_percentage"
            )

            resultado[
                "sleep_efficiency"
            ] = score.get(
                "sleep_efficiency_percentage"
            )

            resultado[
                "sleep_consistency"
            ] = score.get(
                "sleep_consistency_percentage"
            )

            resultado[
                "respiratory_rate"
            ] = score.get(
                "respiratory_rate"
            )

        return resultado

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
            token.get(
                "access_token"
            )
        )