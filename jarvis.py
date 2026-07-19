
from services.voice_service import VoiceService
from services.ai_service import AIService
from services.action_service import ActionService
from services.memory_service import MemoryService


class Jarvis:

    def __init__(self):
        self.nombre = "Jarvis"
        self.version = "1.0"
        self.estado = "en_espera"

        self.voice = VoiceService()
        self.ai = AIService()
        self.actions = ActionService()
        self.memory = MemoryService()
        self.contexto = self.memory.obtener_contexto()

        print(f"{self.nombre} {self.version} inicializado.")

    def cambiar_estado(self, nuevo_estado):
        self.estado = nuevo_estado

    def escuchar(self):
        self.cambiar_estado("escuchando")
        return self.voice.escuchar()

    def hablar(self, texto):
        self.cambiar_estado("hablando")
        self.voice.hablar(texto)
        self.cambiar_estado("en_espera")

    def interpretar(self, texto_usuario):
        self.cambiar_estado("pensando")
        return self.ai.interpretar(texto_usuario)

    def ejecutar(self, interpretacion):
        self.cambiar_estado("ejecutando")

        resultado = self.actions.ejecutar(interpretacion)

        self.memoria = self.memory.cargar_memoria()
        self.contexto = self.memory.obtener_contexto()

        return resultado

    def procesar_comando(self, texto_usuario):
        try:
            interpretacion = self.interpretar(texto_usuario)
            resultado = self.ejecutar(interpretacion)

            self.memory.guardar_evento(
                usuario=texto_usuario,
                interpretacion=interpretacion,
                resultado=resultado
            )

            self.cambiar_estado("en_espera")
            return resultado

        except Exception as error:
            self.memory.guardar_evento(
                usuario=texto_usuario,
                interpretacion={},
                resultado="error"
            )

            self.cambiar_estado("error")
            return f"Ocurrió un error: {error}"

    def accion_despues_de_hablar(self, resultado):
        if not resultado:
            return None

        texto = resultado.lower()

        debe_iniciar_spotify = any(
            frase in texto
            for frase in (
                "ahora iniciaré spotify",
                "ahora iniciare spotify",
                "ahora abriré spotify",
                "ahora abrire spotify"
            )
        )

        if not debe_iniciar_spotify:
            return None

        try:
            return self.actions.ejecutar({
                "modulo": "spotify",
                "accion": "abrir",
                "parametros": {}
            })

        except Exception as error:
            print(
                "No se pudo iniciar Spotify "
                f"después de la rutina: {error}"
            )
            return None
    def ciclo_voz(self):
        texto_usuario = self.escuchar()

        if texto_usuario == "":
            self.hablar("No entendí")
            return {
                "usuario": "No entendí",
                "resultado": "No entendí",
                "salir": False
            }

        texto_limpio = texto_usuario.lower().strip()

        if "jarvis" in texto_limpio:
            texto_limpio = texto_limpio.replace("jarvis", "").strip()

        if texto_limpio == "salir":
            self.hablar("Hasta luego, Javier.")
            return {
                "usuario": texto_usuario,
                "resultado": "Hasta luego, Javier.",
                "salir": True
            }

        resultado = self.procesar_comando(texto_limpio)

        self.hablar(resultado)

        self.accion_despues_de_hablar(resultado)

        return {
            "usuario": texto_usuario,
            "resultado": resultado,
            "salir": False
        }