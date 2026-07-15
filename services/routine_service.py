import os

from services.briefing_service import BriefingService
from services.calendar_service import CalendarService
from services.news_service import NewsService
from services.traffic_service import TrafficService
from services.weather_service import WeatherService


class RoutineService:

    def __init__(self):
        self.calendar = CalendarService()
        self.weather = WeatherService()
        self.traffic = TrafficService()
        self.news = NewsService()
        self.briefing = BriefingService()

    def _consultar_calendario(self):
        try:
            return self.calendar.eventos_hoy()

        except Exception as error:
            print(
                "Error consultando calendario:",
                error
            )

            return "Sin información."

    def _consultar_clima(self):
        try:
            return self.weather.clima_actual(
                "Ciudad de México"
            )

        except Exception as error:
            print(
                "Error consultando clima:",
                error
            )

            return "Sin información."

    def _consultar_trafico(self):
        origen = os.getenv(
            "HOME_ORIGIN"
        )

        destino = os.getenv(
            "WORK_DESTINATION"
        )

        try:
            return self.traffic.resumen_ruta(
                origen=origen,
                destino=destino,
                nombre_destino="el trabajo"
            )

        except Exception as error:
            print(
                "Error consultando tráfico:",
                error
            )

            return "Sin información."

    def _consultar_noticias(self):
        try:
            return self.news.noticias_por_intereses(
                limite=3
            )

        except Exception as error:
            print(
                "Error consultando noticias:",
                error
            )

            return []

    def _crear_respaldo(
        self,
        calendario,
        clima,
        trafico,
        noticias
    ):
        noticias_texto = (
            self.news.resumen_para_voz(
                articulos=noticias,
                limite=3
            )
            if noticias
            else "No encontré noticias relevantes."
        )

        return f"""
Buenos días, Javier.

{calendario}

{clima}

{trafico}

{noticias_texto}

Ahora iniciaré Spotify para empezar el día.
""".strip()

    def buenos_dias(self):
        calendario = (
            self._consultar_calendario()
        )

        clima = (
            self._consultar_clima()
        )

        trafico = (
            self._consultar_trafico()
        )

        noticias = (
            self._consultar_noticias()
        )

        datos = {
            "calendario": calendario,
            "clima": clima,
            "trafico": trafico,
            "noticias": noticias
        }

        respaldo = self._crear_respaldo(
            calendario=calendario,
            clima=clima,
            trafico=trafico,
            noticias=noticias
        )

        return (
            self.briefing
            .generar_briefing_seguro(
                datos=datos,
                respaldo=respaldo
            )
        )