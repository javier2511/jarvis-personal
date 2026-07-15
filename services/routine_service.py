import os

from services.calendar_service import CalendarService
from services.weather_service import WeatherService
from services.traffic_service import TrafficService


class RoutineService:

    def __init__(self):
        self.calendar = CalendarService()
        self.weather = WeatherService()
        self.traffic = TrafficService()

    def buenos_dias(self):
        eventos = self.calendar.eventos_hoy()

        clima = self.weather.clima_actual(
            "Ciudad de México"
        )

        origen = os.getenv(
            "HOME_ORIGIN"
        )

        destino = os.getenv(
            "WORK_DESTINATION"
        )

        try:
            trafico = self.traffic.resumen_ruta(
                origen=origen,
                destino=destino,
                nombre_destino="el trabajo"
            )

        except Exception as error:
            print(
                "Error consultando tráfico:",
                error
            )

            trafico = (
                "No pude consultar el tráfico "
                "en este momento."
            )

        return f"""
Buenos días, Javier.

Calendario:
{eventos}

Clima:
{clima}

Tráfico:
{trafico}

Ahora iniciaré Spotify para empezar el día.
""".strip()