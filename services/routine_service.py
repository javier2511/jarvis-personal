from services.calendar_service import CalendarService
from services.weather_service import WeatherService
from spotify import controlar_spotify
import time


class RoutineService:

    def __init__(self):
        self.calendar = CalendarService()
        self.weather = WeatherService()

    def buenos_dias(self):
        eventos = self.calendar.eventos_hoy()
        clima = self.weather.clima_actual("Ciudad de México")

        respuesta = f"""
    Buenos días, Javier.

    Calendario:
    {eventos}

    Clima:
    {clima}

    Ahora iniciaré Spotify para empezar el día.
    """

        return respuesta