import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests


class NewsService:
    BASE_URL = "https://gnews.io/api/v4"

    def __init__(self):
        self.api_key = os.getenv("GNEWS_API_KEY")

        if not self.api_key:
            raise RuntimeError(
                "Falta la variable GNEWS_API_KEY."
            )

        intereses = os.getenv(
            "NEWS_INTERESTS",
            "México, tecnología, inteligencia artificial, economía"
        )

        self.intereses = [
            interes.strip()
            for interes in intereses.split(",")
            if interes.strip()
        ]

    def _hacer_peticion(
        self,
        endpoint,
        parametros
    ):
        parametros = {
            **parametros,
            "apikey": self.api_key
        }

        ultimo_error = None

        for intento in range(3):
            try:
                respuesta = requests.get(
                    f"{self.BASE_URL}/{endpoint}",
                    params=parametros,
                    timeout=15
                )

                respuesta.raise_for_status()
                return respuesta.json()

            except requests.RequestException as error:
                ultimo_error = error

                if intento < 2:
                    time.sleep(1.5)

        detalle = ""

        if (
            ultimo_error
            and ultimo_error.response is not None
        ):
            detalle = ultimo_error.response.text

        raise RuntimeError(
            "No pude consultar las noticias. "
            f"{detalle}"
        )

    def _limpiar_articulos(
        self,
        articulos,
        limite=5
    ):
        resultados = []
        titulos_vistos = set()

        for articulo in articulos:
            titulo = (
                articulo.get("title")
                or ""
            ).strip()

            descripcion = (
                articulo.get("description")
                or ""
            ).strip()

            fuente = (
                articulo.get("source", {})
                .get("name", "Fuente desconocida")
            )

            url = articulo.get("url", "")
            fecha = articulo.get("publishedAt", "")

            if not titulo:
                continue

            clave = titulo.lower()

            if clave in titulos_vistos:
                continue

            titulos_vistos.add(clave)

            resultados.append({
                "titulo": titulo,
                "descripcion": descripcion,
                "fuente": fuente,
                "url": url,
                "fecha": fecha
            })

            if len(resultados) >= limite:
                break

        return resultados

    def titulares(
        self,
        categoria="general",
        limite=5,
        pais="mx",
        idioma="es"
    ):
        datos = self._hacer_peticion(
            "top-headlines",
            {
                "category": categoria,
                "country": pais,
                "lang": idioma,
                "max": limite
            }
        )

        return self._limpiar_articulos(
            datos.get("articles", []),
            limite=limite
        )

    def buscar(
        self,
        consulta,
        limite=5,
        idioma="es"
    ):
        if not consulta:
            raise ValueError(
                "Necesito un tema para buscar noticias."
            )

        datos = self._hacer_peticion(
            "search",
            {
                "q": consulta,
                "lang": idioma,
                "max": limite,
                "sortby": "publishedAt"
            }
        )

        return self._limpiar_articulos(
            datos.get("articles", []),
            limite=limite
        )

    def noticias_por_intereses(self, limite=5):
        consulta = " OR ".join(
            f'"{interes}"'
            for interes in self.intereses
        )

        try:
            datos = self._hacer_peticion(
                "search",
                {
                    "q": consulta,
                    "lang": "es",
                    "country": "mx",
                    "max": max(limite, 10),
                    "sortby": "publishedAt"
                }
            )

            articulos = self._limpiar_articulos(
                datos.get("articles", []),
                limite=limite
            )

            if articulos:
                return articulos

        except Exception as error:
            print(
                "Error buscando noticias personalizadas:",
                error
            )

        return self.titulares(
            categoria="general",
            limite=limite,
            pais="mx",
            idioma="es"
        )
        
    def resumen_para_voz(
        self,
        articulos,
        limite=3
    ):
        seleccion = articulos[:limite]

        if not seleccion:
            return (
                "No encontré noticias relevantes "
                "en este momento."
            )

        lineas = [
            "Estas son las noticias más relevantes:"
        ]

        for indice, articulo in enumerate(
            seleccion,
            start=1
        ):
            titulo = articulo["titulo"]
            fuente = articulo["fuente"]

            lineas.append(
                f"{indice}. {titulo}. "
                f"Fuente: {fuente}."
            )

        return "\n".join(lineas)

    def resumen_del_dia(
        self,
        limite=3
    ):
        articulos = self.noticias_por_intereses(
            limite=max(limite, 5)
        )

        return self.resumen_para_voz(
            articulos=articulos,
            limite=limite
        )

    def noticias_tema(
        self,
        tema,
        limite=3
    ):
        articulos = self.buscar(
            consulta=tema,
            limite=max(limite, 5)
        )

        return self.resumen_para_voz(
            articulos=articulos,
            limite=limite
        )