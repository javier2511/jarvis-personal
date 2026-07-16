import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from services.news_service import NewsService


class SportsService:
    BASE_URL = "https://www.thesportsdb.com/api/v1/json"

    def __init__(self):
        # TheSportsDB permite usar 123 como llave gratuita de prueba.
        self.api_key = os.getenv(
            "SPORTSDB_API_KEY",
            "123"
        )

        self.news = NewsService()

        self.equipos_preferidos = {
            "giants": "New York Giants",
            "new york giants": "New York Giants",
            "gigantes": "New York Giants",
            "méxico": "Mexico",
            "mexico": "Mexico",
            "selección mexicana": "Mexico",
            "seleccion mexicana": "Mexico"
        }

    def _get(self, endpoint, params=None):
        url = (
            f"{self.BASE_URL}/"
            f"{self.api_key}/"
            f"{endpoint}"
        )

        ultimo_error = None

        for intento in range(3):
            try:
                respuesta = requests.get(
                    url,
                    params=params or {},
                    timeout=15
                )

                respuesta.raise_for_status()
                return respuesta.json()

            except requests.RequestException as error:
                ultimo_error = error

                if intento < 2:
                    time.sleep(1.5)

        raise RuntimeError(
            "No pude consultar la información deportiva."
        ) from ultimo_error

    def _normalizar_equipo(self, equipo):
        texto = (equipo or "").strip().lower()

        return self.equipos_preferidos.get(
            texto,
            equipo.strip()
        )

    def buscar_equipo(self, equipo):
        nombre = self._normalizar_equipo(equipo)

        datos = self._get(
            "searchteams.php",
            {"t": nombre}
        )

        equipos = datos.get("teams") or []

        if not equipos:
            raise RuntimeError(
                f"No encontré el equipo {nombre}."
            )

        # Preferimos coincidencia exacta.
        for resultado in equipos:
            if (
                resultado.get("strTeam", "").lower()
                == nombre.lower()
            ):
                return resultado

        return equipos[0]

    def _formatear_fecha(self, fecha):
        if not fecha:
            return "fecha pendiente"

        try:
            fecha_objeto = datetime.fromisoformat(
                fecha
            )

            return fecha_objeto.strftime(
                "%d/%m/%Y"
            )

        except ValueError:
            return fecha

    def _formatear_hora(self, evento):
        hora = evento.get("strTime")

        if not hora:
            return ""

        return hora[:5]

    def proximo_evento(self, equipo):
        equipo_info = self.buscar_equipo(equipo)

        equipo_id = equipo_info["idTeam"]
        nombre = equipo_info["strTeam"]

        datos = self._get(
            "eventsnext.php",
            {"id": equipo_id}
        )

        eventos = datos.get("events") or []

        if not eventos:
            return (
                f"No encontré un próximo partido "
                f"confirmado para {nombre}."
            )

        evento = eventos[0]

        local = evento.get(
            "strHomeTeam",
            "Local pendiente"
        )

        visitante = evento.get(
            "strAwayTeam",
            "Visitante pendiente"
        )

        fecha = self._formatear_fecha(
            evento.get("dateEvent")
        )

        hora = self._formatear_hora(
            evento
        )

        competicion = evento.get(
            "strLeague",
            ""
        )

        respuesta = (
            f"El próximo partido de {nombre} "
            f"es {local} contra {visitante}, "
            f"el {fecha}"
        )

        if hora:
            respuesta += f" a las {hora}"

        if competicion:
            respuesta += f", en {competicion}"

        return respuesta + "."

    def ultimo_resultado(self, equipo):
        equipo_info = self.buscar_equipo(equipo)

        equipo_id = equipo_info["idTeam"]
        nombre = equipo_info["strTeam"]

        datos = self._get(
            "eventslast.php",
            {"id": equipo_id}
        )

        resultados = datos.get("results") or []

        if not resultados:
            return (
                f"No encontré un resultado reciente "
                f"para {nombre}."
            )

        evento = resultados[0]

        local = evento.get(
            "strHomeTeam",
            "Local"
        )

        visitante = evento.get(
            "strAwayTeam",
            "Visitante"
        )

        marcador_local = evento.get(
            "intHomeScore"
        )

        marcador_visitante = evento.get(
            "intAwayScore"
        )

        fecha = self._formatear_fecha(
            evento.get("dateEvent")
        )

        if (
            marcador_local is None
            or marcador_visitante is None
        ):
            return (
                f"El último partido registrado fue "
                f"{local} contra {visitante}, "
                f"el {fecha}, pero no encontré "
                f"el marcador."
            )

        return (
            f"El último resultado fue "
            f"{local} {marcador_local}, "
            f"{visitante} {marcador_visitante}, "
            f"el {fecha}."
        )

    def noticias_equipo(
        self,
        equipo,
        limite=3
    ):
        nombre = self._normalizar_equipo(
            equipo
        )

        return self.news.noticias_tema(
            tema=nombre,
            limite=limite
        )