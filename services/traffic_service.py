import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests


class TrafficService:
    BASE_URL = (
        "https://routes.googleapis.com/"
        "directions/v2:computeRoutes"
    )

    def __init__(self):
        self.api_key = os.getenv(
            "GOOGLE_ROUTES_API_KEY"
        )

        if not self.api_key:
            raise RuntimeError(
                "Falta GOOGLE_ROUTES_API_KEY."
            )

    def _convertir_duracion_segundos(
        self,
        duracion
    ):
        if not duracion:
            return 0

        texto = str(duracion).rstrip("s")

        try:
            return int(float(texto))
        except ValueError:
            return 0

    def _formatear_duracion(
        self,
        segundos
    ):
        minutos = max(
            1,
            round(segundos / 60)
        )

        horas, minutos_restantes = divmod(
            minutos,
            60
        )

        if horas == 0:
            return f"{minutos} minutos"

        if minutos_restantes == 0:
            return (
                f"{horas} "
                f"{'hora' if horas == 1 else 'horas'}"
            )

        return (
            f"{horas} "
            f"{'hora' if horas == 1 else 'horas'} "
            f"con {minutos_restantes} minutos"
        )

    def _formatear_distancia(
        self,
        metros
    ):
        kilometros = metros / 1000

        if kilometros < 10:
            return f"{kilometros:.1f} kilómetros"

        return f"{round(kilometros)} kilómetros"

    def calcular_ruta(
        self,
        origen,
        destino
    ):
        if not origen:
            raise ValueError(
                "No se indicó el origen."
            )

        if not destino:
            raise ValueError(
                "No se indicó el destino."
            )

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "routes.duration,"
                "routes.staticDuration,"
                "routes.distanceMeters"
            )
        }

        cuerpo = {
            "origin": {
                "address": origen
            },
            "destination": {
                "address": destino
            },
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE",
            "languageCode": "es-MX",
            "units": "METRIC"
        }

        try:
            respuesta = requests.post(
                self.BASE_URL,
                headers=headers,
                json=cuerpo,
                timeout=15
            )

            respuesta.raise_for_status()

        except requests.Timeout as error:
            raise RuntimeError(
                "La consulta de tráfico tardó demasiado."
            ) from error

        except requests.RequestException as error:
            detalle = ""

            if error.response is not None:
                detalle = error.response.text

            raise RuntimeError(
                "No pude consultar el tráfico. "
                f"{detalle}"
            ) from error

        datos = respuesta.json()
        rutas = datos.get("routes", [])

        if not rutas:
            raise RuntimeError(
                "No encontré una ruta entre "
                "el origen y el destino."
            )

        ruta = rutas[0]

        segundos_trafico = (
            self._convertir_duracion_segundos(
                ruta.get("duration")
            )
        )

        segundos_sin_trafico = (
            self._convertir_duracion_segundos(
                ruta.get("staticDuration")
            )
        )

        distancia_metros = ruta.get(
            "distanceMeters",
            0
        )

        zona = ZoneInfo(
            "America/Mexico_City"
        )

        llegada = (
            datetime.now(zona)
            + timedelta(
                seconds=segundos_trafico
            )
        )

        retraso_segundos = max(
            0,
            segundos_trafico
            - segundos_sin_trafico
        )

        return {
            "duracion_segundos": segundos_trafico,
            "duracion_texto": (
                self._formatear_duracion(
                    segundos_trafico
                )
            ),
            "distancia_metros": distancia_metros,
            "distancia_texto": (
                self._formatear_distancia(
                    distancia_metros
                )
            ),
            "llegada": llegada.isoformat(),
            "llegada_texto": llegada.strftime(
                "%H:%M"
            ),
            "retraso_minutos": round(
                retraso_segundos / 60
            )
        }

    def resumen_ruta(
        self,
        origen,
        destino,
        nombre_destino=None
    ):
        ruta = self.calcular_ruta(
            origen=origen,
            destino=destino
        )

        destino_texto = (
            nombre_destino
            or destino
        )

        respuesta = (
            f"Hay {ruta['duracion_texto']} "
            f"hacia {destino_texto}. "
            f"La distancia es de "
            f"{ruta['distancia_texto']} "
            f"y llegarías aproximadamente "
            f"a las {ruta['llegada_texto']}."
        )

        if ruta["retraso_minutos"] >= 5:
            respuesta += (
                f" El tráfico está agregando cerca de "
                f"{ruta['retraso_minutos']} minutos "
                f"al trayecto."
            )

        return respuesta