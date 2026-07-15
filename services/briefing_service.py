import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from openai import OpenAI


class BriefingService:
    """
    Convierte los datos recopilados por Jarvis en un resumen
    matutino breve, natural y priorizado.

    Solo realiza una llamada a OpenAI por briefing.
    """

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "Falta OPENAI_API_KEY para generar el briefing."
            )

        self.client = OpenAI(
            api_key=api_key
        )

        # Puedes cambiar este modelo desde Railway sin tocar código.
        self.model = os.getenv(
            "BRIEFING_MODEL",
            "gpt-5.5"
        )

        self.nombre_usuario = os.getenv(
            "JARVIS_USER_NAME",
            "Javier"
        )

    def _fecha_actual(self):
        zona = ZoneInfo(
            "America/Mexico_City"
        )

        ahora = datetime.now(zona)

        dias = {
            0: "lunes",
            1: "martes",
            2: "miércoles",
            3: "jueves",
            4: "viernes",
            5: "sábado",
            6: "domingo"
        }

        meses = {
            1: "enero",
            2: "febrero",
            3: "marzo",
            4: "abril",
            5: "mayo",
            6: "junio",
            7: "julio",
            8: "agosto",
            9: "septiembre",
            10: "octubre",
            11: "noviembre",
            12: "diciembre"
        }

        return {
            "fecha_iso": ahora.isoformat(),
            "dia_semana": dias[ahora.weekday()],
            "fecha_texto": (
                f"{dias[ahora.weekday()]} "
                f"{ahora.day} de "
                f"{meses[ahora.month]} de "
                f"{ahora.year}"
            ),
            "hora": ahora.strftime("%H:%M")
        }

    def _normalizar_datos(self, datos):
        """
        Evita enviar objetos no serializables o información
        excesivamente grande al modelo.
        """
        datos_limpios = {
            "fecha": self._fecha_actual(),
            "usuario": self.nombre_usuario,
            "calendario": datos.get(
                "calendario",
                "Sin información."
            ),
            "clima": datos.get(
                "clima",
                "Sin información."
            ),
            "trafico": datos.get(
                "trafico",
                "Sin información."
            ),
            "noticias": datos.get(
                "noticias",
                []
            )
        }

        # Enviamos como máximo tres noticias para controlar tokens.
        if isinstance(
            datos_limpios["noticias"],
            list
        ):
            datos_limpios["noticias"] = (
                datos_limpios["noticias"][:3]
            )

        return datos_limpios

    def generar_briefing(self, datos):
        datos_limpios = self._normalizar_datos(
            datos
        )

        contenido = json.dumps(
            datos_limpios,
            ensure_ascii=False,
            default=str
        )

        respuesta = self.client.responses.create(
            model=self.model,

            instructions=f"""
Eres Jarvis, el asistente personal de {self.nombre_usuario}.

Redacta un briefing matutino en español mexicano natural.

OBJETIVO
Convertir los datos recibidos en un mensaje útil, breve,
elegante y conversacional.

REGLAS OBLIGATORIAS

1. Comienza con:
   "Buenos días, {self.nombre_usuario}."

2. No uses encabezados como:
   "Calendario:", "Clima:", "Tráfico:" o "Noticias:".

3. Integra la información como una conversación natural.

4. Da prioridad a:
   - eventos próximos;
   - tráfico considerable;
   - lluvia o clima importante;
   - noticias realmente relevantes.

5. Si algún dato dice que no está disponible,
   omítelo sin mencionar el error.

6. No inventes información.

7. No repitas datos.

8. No leas direcciones completas.

9. Resume las noticias en una sola oración por noticia.

10. Menciona como máximo tres noticias.

11. Evita leer URLs.

12. Usa un tono inteligente, tranquilo, seguro y cercano.

13. No suenes como noticiero, locutor ni robot.

14. Usa frases relativamente cortas para que la voz
    se escuche natural.

15. El briefing completo debe tener entre 90 y 160 palabras.

16. Termina exactamente con esta frase:
    "Ahora iniciaré Spotify para empezar el día."

Devuelve únicamente el texto que Jarvis debe pronunciar.
No devuelvas JSON, títulos, markdown ni explicaciones.
""",

            input=f"""
Estos son los datos actuales de Jarvis:

{contenido}
""",

            max_output_tokens=300
        )

        texto = (
            respuesta.output_text
            or ""
        ).strip()

        if not texto:
            raise RuntimeError(
                "OpenAI no generó el briefing."
            )

        # Garantizamos que la acción posterior de Spotify
        # siga detectándose aunque el modelo omita la frase.
        frase_spotify = (
            "Ahora iniciaré Spotify "
            "para empezar el día."
        )

        if (
            frase_spotify.lower()
            not in texto.lower()
        ):
            texto = (
                f"{texto}\n\n"
                f"{frase_spotify}"
            )

        return texto

    def generar_briefing_seguro(
        self,
        datos,
        respaldo
    ):
        """
        Si OpenAI falla, devuelve el texto tradicional
        para que Buenos días nunca deje de funcionar.
        """
        try:
            return self.generar_briefing(
                datos
            )

        except Exception as error:
            print(
                "Error generando briefing inteligente:",
                error
            )

            return respaldo