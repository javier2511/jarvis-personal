"""
Jarvis - Briefing Service
=========================

Convierte información procedente de distintos servicios de Jarvis en un
briefing breve, natural y útil.

El servicio está preparado para recibir información de:

- Calendario
- Clima
- Tráfico
- Noticias
- Deportes
- WHOOP
- Gmail
- Trabajo
- Cualquier servicio futuro

El BriefingService realiza una sola llamada a OpenAI por cada briefing.

Variables de entorno utilizadas:

OPENAI_API_KEY
BRIEFING_MODEL
JARVIS_USER_NAME
JARVIS_CITY
JARVIS_BRIEFING_MAX_TOKENS

Ejemplo de uso:

    briefing_service = BriefingService()

    texto = briefing_service.generar_briefing_seguro(
        {
            "calendar": datos_calendario,
            "weather": datos_clima,
            "traffic": datos_trafico,
            "news": datos_noticias,
        }
    )
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from openai import OpenAI


logger = logging.getLogger(__name__)


class BriefingService:
    """
    Genera el briefing inteligente de Jarvis.

    El servicio:

    1. Recibe datos de diferentes módulos.
    2. Elimina información vacía o innecesaria.
    3. Detecta prioridades.
    4. Construye un contexto compacto.
    5. Hace una sola llamada a OpenAI.
    6. Devuelve un discurso natural.
    7. Usa un fallback local cuando OpenAI falla.
    """

    def __init__(
        self,
        client: Optional[OpenAI] = None,
        model: Optional[str] = None,
    ) -> None:
        self.user_name = os.getenv("JARVIS_USER_NAME", "Javier").strip()
        self.city = os.getenv("JARVIS_CITY", "Ciudad de México").strip()

        self.model = (
            model
            or os.getenv("BRIEFING_MODEL")
            or os.getenv("OPENAI_MODEL")
            or "gpt-5.5"
        ).strip()

        self.max_output_tokens = self._leer_entero_entorno(
            "JARVIS_BRIEFING_MAX_TOKENS",
            default=450,
            minimum=150,
            maximum=1_200,
        )

        api_key = os.getenv("OPENAI_API_KEY")

        if client is not None:
            self.client = client
        elif api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = None
            logger.warning(
                "OPENAI_API_KEY no está configurada. "
                "BriefingService utilizará el fallback local."
            )

    # ------------------------------------------------------------------
    # MÉTODOS PÚBLICOS
    # ------------------------------------------------------------------

    def generar_briefing(
        self,
        datos: Optional[Dict[str, Any]] = None,
        *,
        momento: Optional[datetime] = None,
    ) -> str:
        """
        Genera el briefing mediante OpenAI.

        Este método puede lanzar una excepción si OpenAI no está disponible.
        Para producción se recomienda usar generar_briefing_seguro().
        """

        if self.client is None:
            raise RuntimeError(
                "No se puede generar el briefing porque OPENAI_API_KEY "
                "no está configurada."
            )

        momento_actual = momento or datetime.now()
        datos_limpios = self._limpiar_valor(datos or {})

        contexto = self._construir_contexto(
            datos=datos_limpios,
            momento=momento_actual,
        )

        instrucciones = self._construir_instrucciones()

        response = self.client.responses.create(
            model=self.model,
            instructions=instrucciones,
            input=contexto,
            max_output_tokens=self.max_output_tokens,
        )

        texto = (response.output_text or "").strip()

        if not texto:
            raise RuntimeError(
                "OpenAI respondió correctamente, pero no devolvió texto."
            )

        return self._limpiar_respuesta_final(texto)

    def generar_briefing_seguro(
        self,
        datos: Optional[Dict[str, Any]] = None,
        *,
        momento: Optional[datetime] = None,
    ) -> str:
        """
        Genera el briefing y, si ocurre algún error, utiliza un fallback.

        Este es el método que deberá usar RoutineService.
        """

        momento_actual = momento or datetime.now()
        datos_recibidos = datos or {}

        try:
            return self.generar_briefing(
                datos=datos_recibidos,
                momento=momento_actual,
            )

        except Exception as exc:
            logger.exception(
                "No fue posible generar el briefing inteligente: %s",
                exc,
            )

            return self._generar_fallback(
                datos=datos_recibidos,
                momento=momento_actual,
            )

    def generate_briefing(
        self,
        data: Optional[Dict[str, Any]] = None,
        *,
        moment: Optional[datetime] = None,
    ) -> str:
        """
        Alias en inglés para compatibilidad futura.
        """

        return self.generar_briefing_seguro(
            datos=data,
            momento=moment,
        )

    # ------------------------------------------------------------------
    # CONSTRUCCIÓN DEL PROMPT
    # ------------------------------------------------------------------

    def _construir_instrucciones(self) -> str:
        """
        Define la personalidad y las reglas del briefing.
        """

        return f"""
Eres Jarvis, el asistente personal de {self.user_name}.

Tu tarea es transformar los datos proporcionados en un briefing matutino
breve, natural, elegante y verdaderamente útil.

PERSONALIDAD

- Hablas en español de México.
- Suenas atento, seguro, inteligente y cercano.
- Tienes una personalidad similar a un asistente personal sofisticado.
- No suenas como locutor de noticias ni como chatbot.
- Puedes utilizar ocasionalmente expresiones como "señor", pero no en cada frase.
- No exageres el entusiasmo.
- No utilices emojis.
- No uses markdown.
- No uses títulos, viñetas, numeraciones ni listas.
- El texto será reproducido por voz, por lo que debe escucharse natural.

ESTRUCTURA

- Comienza con un saludo natural.
- Menciona primero lo más importante para el usuario.
- Conecta agenda, clima, tráfico, noticias, deportes y salud de forma fluida.
- Termina con una frase breve que ayude a iniciar el día.
- El briefing completo debe durar aproximadamente entre 30 y 70 segundos.
- Normalmente debe tener entre 90 y 180 palabras.
- Puede ser más corto cuando hay poca información.

PRIORIDADES

1. Eventos próximos, compromisos importantes o cambios de agenda.
2. Alertas relevantes: lluvia, tormentas, tráfico fuerte o problemas.
3.Memoria personal: recuerdos que tienes del usuario
4. Salud y recuperación, cuando haya datos de WHOOP.
5. Noticias realmente importantes.
6. Deportes relevantes para los intereses del usuario.
7. Información secundaria.

REGLAS DE CONTENIDO

- No inventes ningún dato.
- No completes información faltante mediante suposiciones.
- Si un servicio no tiene información, omítelo completamente.
- No digas que un servicio falló, salvo que eso sea útil para el usuario.
- No leas todos los campos técnicos.
- Resume y traduce los datos a decisiones prácticas.
- Evita decir temperatura, humedad, viento y otras métricas una por una.
- Si hay lluvia relevante, recomienda llevar paraguas.
- Si el tráfico es pesado, recomienda salir antes.
- Si existe un evento próximo, menciona su hora.
- Si no hay eventos, puedes decir que la agenda se ve tranquila.
- En noticias, selecciona únicamente una o dos realmente importantes.
- No leas URLs, IDs, coordenadas ni metadatos.
- No repitas información.
- No menciones que recibiste JSON.
- No expliques tu proceso de razonamiento.
- No uses frases como "según los datos proporcionados".
- No menciones nombres de campos internos como weather, traffic o calendar.

MEMORIA PERSONAL

Cuando exista información en "memory":

- Utilízala únicamente si aporta contexto útil para el día.
- No leas todos los recuerdos.
- Elige como máximo uno o dos.
- Nunca repitas el mismo recuerdo todos los días.
- Úsala para personalizar el briefing.

Ejemplos:

"Recuerdo que esta semana querías comprar una figura para tu novia."

"Hoy juegan los Giants, uno de tus equipos favoritos."

"No menciones recuerdos irrelevantes para el día."

SALUD

Cuando existan datos de WHOOP:

- Interpreta recuperación, sueño y strain de forma prudente.
- No hagas diagnósticos médicos.
- No presentes recomendaciones como órdenes médicas.
- Puedes sugerir moderar o aprovechar el entrenamiento según la recuperación.
- Si faltan datos, no inventes conclusiones.

OBJETIVO

El usuario debe sentir que un asistente revisó toda su mañana y le comunicó
solo lo que realmente necesita saber.
""".strip()

    def _construir_contexto(
        self,
        datos: Dict[str, Any],
        momento: datetime,
    ) -> str:
        """
        Construye un contexto compacto para reducir tokens y evitar ruido.
        """

        prioridades = self._detectar_prioridades(datos)

        payload = {
            "usuario": self.user_name,
            "ciudad_principal": self.city,
            "fecha_local": momento.strftime("%Y-%m-%d"),
            "hora_local": momento.strftime("%H:%M"),
            "dia_semana": self._nombre_dia(momento.weekday()),
            "momento_del_dia": self._momento_del_dia(momento.hour),
            "prioridades_detectadas": prioridades,
            "datos_disponibles": datos,
        }

        return (
            "Genera el briefing personal de esta mañana utilizando "
            "exclusivamente la siguiente información:\n\n"
            + json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
                default=self._serializar_json,
            )
        )

    # ------------------------------------------------------------------
    # DETECCIÓN LOCAL DE PRIORIDADES
    # ------------------------------------------------------------------

    def _detectar_prioridades(
        self,
        datos: Dict[str, Any],
    ) -> List[str]:
        """
        Detecta señales importantes antes de enviar el contexto a GPT.

        No pretende entender todos los formatos posibles. Su función es
        destacar palabras y valores frecuentes producidos por los servicios.
        """

        prioridades: List[str] = []
        texto = json.dumps(
            datos,
            ensure_ascii=False,
            default=self._serializar_json,
        ).lower()

        # Clima
        if any(
            palabra in texto
            for palabra in (
                "lluvia",
                "rain",
                "tormenta",
                "storm",
                "thunderstorm",
                "granizo",
            )
        ):
            prioridades.append("Posible lluvia o condiciones adversas")

        if any(
            palabra in texto
            for palabra in (
                "calor extremo",
                "heat warning",
                "ola de calor",
            )
        ):
            prioridades.append("Temperatura elevada")

        if any(
            palabra in texto
            for palabra in (
                "frío extremo",
                "helada",
                "freeze warning",
            )
        ):
            prioridades.append("Temperatura muy baja")

        # Tráfico
        if any(
            palabra in texto
            for palabra in (
                "tráfico pesado",
                "trafico pesado",
                "heavy traffic",
                "severe traffic",
                "congestionado",
                "congestión severa",
                "congestion severa",
            )
        ):
            prioridades.append("Tráfico pesado")

        # Agenda
        if any(
            palabra in texto
            for palabra in (
                "reunión",
                "reunion",
                "meeting",
                "cita",
                "evento",
                "event",
            )
        ):
            prioridades.append("Hay compromisos en la agenda")

        # Noticias urgentes
        if any(
            palabra in texto
            for palabra in (
                "urgente",
                "última hora",
                "ultima hora",
                "breaking",
                "alerta",
            )
        ):
            prioridades.append("Puede haber noticias importantes")

        # Salud / WHOOP
        recovery = self._buscar_numero(
            datos,
            claves={
                "recovery",
                "recovery_score",
                "recovery_percentage",
                "recuperacion",
                "recuperación",
            },
        )

        if recovery is not None:
            if recovery < 34:
                prioridades.append("Recuperación de WHOOP baja")
            elif recovery >= 67:
                prioridades.append("Recuperación de WHOOP favorable")

        sleep_performance = self._buscar_numero(
            datos,
            claves={
                "sleep_performance",
                "sleep_performance_percentage",
                "sleep_score",
                "desempeno_sueno",
                "desempeño_sueño",
            },
        )

        if sleep_performance is not None and sleep_performance < 70:
            prioridades.append("Sueño por debajo de lo ideal")

        return self._quitar_duplicados(prioridades)

    # ------------------------------------------------------------------
    # FALLBACK SIN OPENAI
    # ------------------------------------------------------------------

    def _generar_fallback(
        self,
        datos: Dict[str, Any],
        momento: datetime,
    ) -> str:
        """
        Produce una respuesta local cuando OpenAI no está disponible.

        El fallback no intenta reemplazar al briefing inteligente; solamente
        evita que la rutina "Buenos días" quede completamente sin respuesta.
        """

        partes: List[str] = [
            self._saludo_local(momento),
        ]

        calendar_data = self._obtener_seccion(
            datos,
            "calendar",
            "calendario",
            "agenda",
            "events",
            "eventos",
        )

        weather_data = self._obtener_seccion(
            datos,
            "weather",
            "clima",
            "pronostico",
            "pronóstico",
        )

        traffic_data = self._obtener_seccion(
            datos,
            "traffic",
            "trafico",
            "tráfico",
        )

        news_data = self._obtener_seccion(
            datos,
            "news",
            "noticias",
        )

        sports_data = self._obtener_seccion(
            datos,
            "sports",
            "deportes",
        )

        whoop_data = self._obtener_seccion(
            datos,
            "whoop",
            "health",
            "salud",
        )

        agenda_texto = self._resumen_fallback_seccion(
            calendar_data,
            tipo="agenda",
        )

        clima_texto = self._resumen_fallback_seccion(
            weather_data,
            tipo="clima",
        )

        trafico_texto = self._resumen_fallback_seccion(
            traffic_data,
            tipo="tráfico",
        )

        whoop_texto = self._resumen_fallback_seccion(
            whoop_data,
            tipo="WHOOP",
        )

        noticias_texto = self._resumen_fallback_seccion(
            news_data,
            tipo="noticias",
        )

        deportes_texto = self._resumen_fallback_seccion(
            sports_data,
            tipo="deportes",
        )

        for texto in (
            agenda_texto,
            clima_texto,
            trafico_texto,
            whoop_texto,
            noticias_texto,
            deportes_texto,
        ):
            if texto:
                partes.append(texto)

        if len(partes) == 1:
            partes.append(
                "No tengo información adicional disponible para esta mañana."
            )

        partes.append("Que tengas un excelente día.")

        return " ".join(partes)

    def _resumen_fallback_seccion(
        self,
        valor: Any,
        *,
        tipo: str,
    ) -> str:
        """
        Convierte una sección a texto básico para el fallback.
        """

        if self._es_vacio(valor):
            return ""

        if isinstance(valor, str):
            texto = valor.strip()

            if not texto:
                return ""

            if len(texto) > 450:
                texto = texto[:447].rstrip() + "..."

            return texto

        if isinstance(valor, list):
            elementos = [
                self._extraer_texto_legible(item)
                for item in valor[:3]
            ]

            elementos = [
                item
                for item in elementos
                if item
            ]

            if not elementos:
                return ""

            if tipo == "agenda":
                return "En tu agenda: " + "; ".join(elementos) + "."

            if tipo == "noticias":
                return "Entre las noticias destaca: " + "; ".join(elementos) + "."

            if tipo == "deportes":
                return "En deportes: " + "; ".join(elementos) + "."

            return f"Información de {tipo}: " + "; ".join(elementos) + "."

        if isinstance(valor, dict):
            texto_directo = self._extraer_texto_directo(valor)

            if texto_directo:
                return texto_directo

            elementos = []

            for clave, contenido in list(valor.items())[:8]:
                if self._es_vacio(contenido):
                    continue

                clave_legible = str(clave).replace("_", " ").strip()
                contenido_legible = self._extraer_texto_legible(contenido)

                if contenido_legible:
                    elementos.append(
                        f"{clave_legible}: {contenido_legible}"
                    )

            if not elementos:
                return ""

            texto = "; ".join(elementos[:4])

            if tipo == "agenda":
                return "Sobre tu agenda, " + texto + "."

            if tipo == "clima":
                return "Sobre el clima, " + texto + "."

            if tipo == "tráfico":
                return "Sobre el tráfico, " + texto + "."

            if tipo == "WHOOP":
                return "Sobre tu recuperación, " + texto + "."

            if tipo == "noticias":
                return "En las noticias, " + texto + "."

            if tipo == "deportes":
                return "En deportes, " + texto + "."

            return texto + "."

        return str(valor)

    # ------------------------------------------------------------------
    # LIMPIEZA DE DATOS
    # ------------------------------------------------------------------

    def _limpiar_valor(
        self,
        valor: Any,
        *,
        profundidad: int = 0,
    ) -> Any:
        """
        Limpia estructuras antes de enviarlas a OpenAI.

        - Elimina valores vacíos.
        - Limita profundidad.
        - Limita listas demasiado largas.
        - Elimina campos técnicos innecesarios.
        """

        if profundidad > 7:
            return str(valor)[:300]

        if valor is None:
            return None

        if isinstance(valor, (datetime, date)):
            return valor.isoformat()

        if isinstance(valor, str):
            texto = valor.strip()

            if not texto:
                return None

            return texto[:2_000]

        if isinstance(valor, bool):
            return valor

        if isinstance(valor, (int, float)):
            return valor

        if isinstance(valor, list):
            elementos = []

            for item in valor[:12]:
                limpio = self._limpiar_valor(
                    item,
                    profundidad=profundidad + 1,
                )

                if not self._es_vacio(limpio):
                    elementos.append(limpio)

            return elementos

        if isinstance(valor, tuple):
            return self._limpiar_valor(
                list(valor),
                profundidad=profundidad,
            )

        if isinstance(valor, dict):
            resultado: Dict[str, Any] = {}

            campos_omitidos = {
                "url",
                "link",
                "image",
                "image_url",
                "thumbnail",
                "raw",
                "html",
                "token",
                "access_token",
                "refresh_token",
                "client_secret",
                "api_key",
                "latitude",
                "longitude",
                "lat",
                "lng",
            }

            for clave, contenido in valor.items():
                clave_texto = str(clave)

                if clave_texto.lower() in campos_omitidos:
                    continue

                limpio = self._limpiar_valor(
                    contenido,
                    profundidad=profundidad + 1,
                )

                if not self._es_vacio(limpio):
                    resultado[clave_texto] = limpio

            return resultado

        if hasattr(valor, "model_dump"):
            try:
                return self._limpiar_valor(
                    valor.model_dump(),
                    profundidad=profundidad + 1,
                )
            except Exception:
                pass

        if hasattr(valor, "__dict__"):
            try:
                return self._limpiar_valor(
                    vars(valor),
                    profundidad=profundidad + 1,
                )
            except Exception:
                pass

        return str(valor)[:500]

    # ------------------------------------------------------------------
    # UTILIDADES
    # ------------------------------------------------------------------

    @staticmethod
    def _leer_entero_entorno(
        nombre: str,
        *,
        default: int,
        minimum: int,
        maximum: int,
    ) -> int:
        valor = os.getenv(nombre)

        if valor is None:
            return default

        try:
            numero = int(valor)
        except (TypeError, ValueError):
            return default

        return max(minimum, min(numero, maximum))

    @staticmethod
    def _serializar_json(valor: Any) -> str:
        if isinstance(valor, (datetime, date)):
            return valor.isoformat()

        if hasattr(valor, "model_dump"):
            return valor.model_dump()

        return str(valor)

    @staticmethod
    def _es_vacio(valor: Any) -> bool:
        if valor is None:
            return True

        if isinstance(valor, str):
            return not valor.strip()

        if isinstance(valor, (list, tuple, dict, set)):
            return len(valor) == 0

        return False

    @staticmethod
    def _quitar_duplicados(valores: List[str]) -> List[str]:
        resultado: List[str] = []
        vistos = set()

        for valor in valores:
            clave = valor.strip().lower()

            if clave and clave not in vistos:
                vistos.add(clave)
                resultado.append(valor)

        return resultado

    @staticmethod
    def _nombre_dia(numero_dia: int) -> str:
        dias = (
            "lunes",
            "martes",
            "miércoles",
            "jueves",
            "viernes",
            "sábado",
            "domingo",
        )

        return dias[numero_dia]

    @staticmethod
    def _momento_del_dia(hora: int) -> str:
        if 5 <= hora < 12:
            return "mañana"

        if 12 <= hora < 19:
            return "tarde"

        return "noche"

    def _saludo_local(self, momento: datetime) -> str:
        if 5 <= momento.hour < 12:
            return f"Buenos días, {self.user_name}."

        if 12 <= momento.hour < 19:
            return f"Buenas tardes, {self.user_name}."

        return f"Buenas noches, {self.user_name}."

    @staticmethod
    def _limpiar_respuesta_final(texto: str) -> str:
        """
        Elimina formatos que podrían escucharse extraños en TTS.
        """

        limpio = texto.strip()

        limpio = limpio.replace("```text", "")
        limpio = limpio.replace("```markdown", "")
        limpio = limpio.replace("```", "")
        limpio = limpio.replace("**", "")
        limpio = limpio.replace("###", "")
        limpio = limpio.replace("##", "")
        limpio = limpio.replace("#", "")

        lineas_limpias = []

        for linea in limpio.splitlines():
            linea = linea.strip()

            if not linea:
                continue

            if linea.startswith(("- ", "* ", "• ")):
                linea = linea[2:].strip()

            lineas_limpias.append(linea)

        limpio = " ".join(lineas_limpias)

        while "  " in limpio:
            limpio = limpio.replace("  ", " ")

        return limpio.strip()

    @staticmethod
    def _obtener_seccion(
        datos: Dict[str, Any],
        *posibles_claves: str,
    ) -> Any:
        """
        Obtiene una sección sin importar si la clave está en español o inglés.
        """

        claves_normalizadas = {
            str(clave).strip().lower(): valor
            for clave, valor in datos.items()
        }

        for clave in posibles_claves:
            clave_normalizada = clave.strip().lower()

            if clave_normalizada in claves_normalizadas:
                return claves_normalizadas[clave_normalizada]

        return None

    def _extraer_texto_legible(self, valor: Any) -> str:
        if self._es_vacio(valor):
            return ""

        if isinstance(valor, str):
            return valor.strip()[:300]

        if isinstance(valor, (int, float, bool)):
            return str(valor)

        if isinstance(valor, dict):
            texto_directo = self._extraer_texto_directo(valor)

            if texto_directo:
                return texto_directo

            partes = []

            for clave, contenido in list(valor.items())[:4]:
                contenido_legible = self._extraer_texto_legible(contenido)

                if contenido_legible:
                    clave_legible = str(clave).replace("_", " ")
                    partes.append(
                        f"{clave_legible}: {contenido_legible}"
                    )

            return ", ".join(partes)

        if isinstance(valor, list):
            partes = [
                self._extraer_texto_legible(item)
                for item in valor[:3]
            ]

            return "; ".join(
                parte
                for parte in partes
                if parte
            )

        return str(valor)[:300]

    @staticmethod
    def _extraer_texto_directo(valor: Dict[str, Any]) -> str:
        """
        Busca campos comunes que ya contienen un resumen legible.
        """

        claves_texto = (
            "summary",
            "resumen",
            "message",
            "mensaje",
            "description",
            "descripcion",
            "descripción",
            "text",
            "texto",
            "title",
            "titulo",
            "título",
            "briefing",
        )

        for clave in claves_texto:
            contenido = valor.get(clave)

            if isinstance(contenido, str) and contenido.strip():
                return contenido.strip()[:450]

        return ""

    def _buscar_numero(
        self,
        valor: Any,
        *,
        claves: set[str],
    ) -> Optional[float]:
        """
        Busca recursivamente un número asociado con alguna de las claves.
        """

        claves_normalizadas = {
            clave.lower().strip()
            for clave in claves
        }

        if isinstance(valor, dict):
            for clave, contenido in valor.items():
                clave_normalizada = str(clave).lower().strip()

                if clave_normalizada in claves_normalizadas:
                    numero = self._convertir_numero(contenido)

                    if numero is not None:
                        return numero

            for contenido in valor.values():
                encontrado = self._buscar_numero(
                    contenido,
                    claves=claves_normalizadas,
                )

                if encontrado is not None:
                    return encontrado

        elif isinstance(valor, list):
            for elemento in valor:
                encontrado = self._buscar_numero(
                    elemento,
                    claves=claves_normalizadas,
                )

                if encontrado is not None:
                    return encontrado

        return None

    @staticmethod
    def _convertir_numero(valor: Any) -> Optional[float]:
        if isinstance(valor, bool):
            return None

        if isinstance(valor, (int, float)):
            return float(valor)

        if isinstance(valor, str):
            texto = valor.strip().replace("%", "").replace(",", ".")

            try:
                return float(texto)
            except ValueError:
                return None

        return None