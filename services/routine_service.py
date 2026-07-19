"""
Jarvis - Routine Service
========================

Coordina la rutina de "Buenos días".

Este servicio consulta:

- Google Calendar
- Clima
- Tráfico
- Noticias

Después entrega toda la información al BriefingService para generar
un único resumen natural mediante OpenAI.

Cada servicio se consulta de forma independiente. Si uno falla,
los demás continúan funcionando.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from services.briefing_service import BriefingService
from services.calendar_service import CalendarService
from services.news_service import NewsService
from services.traffic_service import TrafficService
from services.weather_service import WeatherService
from services.memory_service import MemoryService


logger = logging.getLogger(__name__)


MEXICO_TZ = ZoneInfo("America/Mexico_City")


class RoutineService:
    """
    Coordina las rutinas personales de Jarvis.
    """

    def __init__(self) -> None:
        self.calendar = CalendarService()
        self.weather = WeatherService()
        self.traffic = TrafficService()
        self.news = NewsService()
        self.briefing = BriefingService()
        self.memory = MemoryService()

        self.city = os.getenv(
            "JARVIS_CITY",
            "Ciudad de México",
        ).strip()

        self.home_origin = os.getenv(
            "HOME_ORIGIN",
            "",
        ).strip()

        self.work_destination = os.getenv(
            "WORK_DESTINATION",
            "",
        ).strip()

    # ------------------------------------------------------------------
    # CONSULTAS A SERVICIOS
    # ------------------------------------------------------------------

    def _consultar_calendario(self) -> Any:
        """
        Consulta los eventos del día.

        Si Calendar falla, devuelve una estructura vacía para que
        BriefingService omita esa sección.
        """

        try:
            return self.calendar.eventos_hoy()

        except Exception as error:
            logger.exception(
                "Error consultando calendario: %s",
                error,
            )

            return None

    def _consultar_clima(self) -> Any:
        """
        Consulta el clima actual de la ciudad configurada.
        """

        try:
            return self.weather.clima_actual(
                self.city
            )

        except Exception as error:
            logger.exception(
                "Error consultando clima: %s",
                error,
            )

            return None

    def _consultar_trafico(self) -> Any:
        """
        Consulta el tráfico entre casa y trabajo.

        Si las ubicaciones no están configuradas, omite esta sección
        sin detener la rutina.
        """

        if not self.home_origin or not self.work_destination:
            logger.warning(
                "No se consultó tráfico porque HOME_ORIGIN o "
                "WORK_DESTINATION no están configuradas."
            )

            return None

        try:
            return self.traffic.resumen_ruta(
                origen=self.home_origin,
                destino=self.work_destination,
                nombre_destino="el trabajo",
            )

        except Exception as error:
            logger.exception(
                "Error consultando tráfico: %s",
                error,
            )

            return None

    def _consultar_noticias(self) -> List[Dict[str, Any]]:
        """
        Consulta las noticias relacionadas con los intereses del usuario.
        """

        try:
            noticias = self.news.noticias_por_intereses(
                limite=3
            )

            if isinstance(noticias, list):
                return noticias

            if noticias:
                return [noticias]

            return []

        except Exception as error:
            logger.exception(
                "Error consultando noticias: %s",
                error,
            )

            return []

    # ------------------------------------------------------------------
    # CONSTRUCCIÓN DE DATOS
    # ------------------------------------------------------------------

    def _recolectar_datos(self) -> Dict[str, Any]:
        """
        Reúne la información que recibirá BriefingService.

        Las claves pueden crecer después con:

        - whoop
        - sports
        - gmail
        - work
        - memory
        """

        calendario = self._consultar_calendario()
        clima = self._consultar_clima()
        trafico = self._consultar_trafico()
        noticias = self._consultar_noticias()
        memoria = self.memory.contexto_para_briefing()

        datos: Dict[str, Any] = {
            "calendar": calendario,
            "weather": clima,
            "traffic": trafico,
            "news": noticias,
            "memory": memoria
        }

        return {
            clave: valor
            for clave, valor in datos.items()
            if not self._es_vacio(valor)
        }

    # ------------------------------------------------------------------
    # RUTINAS PÚBLICAS
    # ------------------------------------------------------------------

    def buenos_dias(self) -> Dict[str, Any]:
        """
        Ejecuta la rutina de Buenos días y devuelve un resultado estructurado.

        El texto se reproduce primero. Después, Jarvis ejecuta las acciones
        incluidas en ``acciones`` sin depender de frases generadas por GPT.
        """

        logger.info("Iniciando rutina de Buenos días.")

        momento_actual = datetime.now(MEXICO_TZ)
        datos = self._recolectar_datos()

        briefing = self.briefing.generar_briefing_seguro(
            datos=datos,
            momento=momento_actual,
        )

        resultado: Dict[str, Any] = {
            "texto": briefing,
            "acciones": [
                {
                    "modulo": "spotify",
                    "accion": "abrir",
                    "parametros": {},
                }
            ],
            "metadata": {
                "rutina": "buenos_dias",
                "fecha_local": momento_actual.isoformat(),
                "zona_horaria": str(MEXICO_TZ),
            },
        }

        logger.info("Rutina de Buenos días finalizada.")
        return resultado

    # ------------------------------------------------------------------
    # UTILIDADES
    # ------------------------------------------------------------------

    @staticmethod
    def _es_vacio(valor: Any) -> bool:
        """
        Determina si un servicio no devolvió información útil.
        """

        if valor is None:
            return True

        if isinstance(valor, str):
            texto = valor.strip().lower()

            return texto in {
                "",
                "sin información.",
                "sin información",
                "no disponible",
                "no disponible.",
            }

        if isinstance(valor, (list, tuple, dict, set)):
            return len(valor) == 0

        return False