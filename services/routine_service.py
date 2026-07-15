from services.calendar_service import CalendarService
from services.weather_service import WeatherService


class RoutineService:

    def __init__(self):
        self.calendar = CalendarService()
        self.weather = WeatherService()

    def buenos_dias(self):
        eventos = self.calendar.eventos_hoy()
        clima = self.weather.clima_actual(
            "Ciudad de México"
        )

        return f"""
Buenos días, Javier.

Calendario:
{eventos}

Clima:
{clima}

Ahora iniciaré Spotify para empezar el día.
""".strip()