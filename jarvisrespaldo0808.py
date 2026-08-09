from __future__ import annotations

from typing import Any, Dict, List, Tuple

from services.action_service import ActionService
from services.ai_service import AIService
from services.voice_service import VoiceService


class Jarvis:
    def __init__(self):
        self.nombre = "Jarvis"
        self.version = "1.2"
        self.estado = "en_espera"

        self.voice = VoiceService()
        self.ai = AIService()
        self.actions = ActionService()

        print(f"{self.nombre} {self.version} inicializado.")

    def cambiar_estado(self, nuevo_estado):
        self.estado = nuevo_estado

    def escuchar(self):
        self.cambiar_estado("escuchando")
        return self.voice.escuchar()

    def hablar(self, texto):
        self.cambiar_estado("hablando")
        self.voice.hablar(str(texto))
        self.cambiar_estado("en_espera")

    def interpretar(self, texto_usuario):
        self.cambiar_estado("pensando")
        return self.ai.interpretar(texto_usuario)

    def ejecutar(self, interpretacion):
        self.cambiar_estado("ejecutando")
        return self.actions.ejecutar(interpretacion)

    def procesar_comando(self, texto_usuario):
        try:
            interpretacion = self.interpretar(texto_usuario)
            resultado = self.ejecutar(interpretacion)
            self.cambiar_estado("en_espera")
            return resultado

        except Exception as error:
            print(f"Error procesando comando: {error}")
            self.cambiar_estado("error")
            return f"Ocurrió un error: {error}"

    @staticmethod
    def _normalizar_resultado(resultado: Any) -> Tuple[str, List[Dict[str, Any]]]:
        """Extrae el texto hablado y las acciones posteriores.

        Mantiene compatibilidad con resultados antiguos de tipo ``str`` y con
        respuestas estructuradas que usen ``texto``, ``briefing`` o
        ``resultado`` como campo principal.
        """

        if resultado is None:
            return "", []

        if not isinstance(resultado, dict):
            return str(resultado), []

        texto = (
            resultado.get("texto")
            or resultado.get("briefing")
            or resultado.get("mensaje")
            or resultado.get("resultado")
            or ""
        )

        acciones_crudas = resultado.get("acciones") or []
        acciones: List[Dict[str, Any]] = []

        if isinstance(acciones_crudas, dict):
            acciones_crudas = [acciones_crudas]

        if isinstance(acciones_crudas, list):
            for accion in acciones_crudas:
                if isinstance(accion, dict):
                    acciones.append(accion)

        return str(texto), acciones

    def ejecutar_acciones_posteriores(self, acciones: List[Dict[str, Any]]):
        """Ejecuta de forma aislada las acciones posteriores al habla.

        Una acción que falle no impide que se intenten las siguientes.
        """

        resultados = []

        for accion in acciones:
            try:
                resultados.append(self.actions.ejecutar(accion))
            except Exception as error:
                modulo = accion.get("modulo", "desconocido")
                nombre_accion = accion.get("accion", "desconocida")
                print(
                    "No se pudo ejecutar la acción posterior "
                    f"{modulo}.{nombre_accion}: {error}"
                )

        return resultados

    def accion_despues_de_hablar(self, resultado):
        """Compatibilidad con llamadas existentes.

        Ya no analiza el texto generado por GPT. Solo ejecuta la lista
        estructurada de acciones incluida en el resultado.
        """

        _, acciones = self._normalizar_resultado(resultado)

        if not acciones:
            return None

        return self.ejecutar_acciones_posteriores(acciones)

    def ciclo_voz(self):
        texto_usuario = self.escuchar()

        if not texto_usuario:
            respuesta = "No entendí."
            self.hablar(respuesta)
            return {
                "usuario": respuesta,
                "resultado": respuesta,
                "salir": False,
            }

        texto_limpio = str(texto_usuario).lower().strip()

        if "jarvis" in texto_limpio:
            texto_limpio = texto_limpio.replace("jarvis", "").strip()

        if texto_limpio == "salir":
            respuesta = "Hasta luego, Javier."
            self.hablar(respuesta)
            return {
                "usuario": texto_usuario,
                "resultado": respuesta,
                "salir": True,
            }

        resultado_crudo = self.procesar_comando(texto_limpio)
        texto_respuesta, acciones = self._normalizar_resultado(resultado_crudo)

        if not texto_respuesta:
            texto_respuesta = "La acción terminó, pero no recibí una respuesta para leer."

        self.hablar(texto_respuesta)
        self.ejecutar_acciones_posteriores(acciones)

        return {
            "usuario": texto_usuario,
            "resultado": texto_respuesta,
            "acciones": acciones,
            "salir": False,
        }
