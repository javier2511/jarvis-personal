from services.action_service import ActionService
from services.ai_service import AIService
from services.voice_service import VoiceService


class Jarvis:
    def __init__(self):
        self.nombre = "Jarvis"
        self.version = "1.1"
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

    def accion_despues_de_hablar(self, resultado):
        if not resultado:
            return None

        texto = str(resultado).lower()

        debe_iniciar_spotify = any(
            frase in texto
            for frase in (
                "ahora iniciaré spotify",
                "ahora iniciare spotify",
                "ahora abriré spotify",
                "ahora abrire spotify",
            )
        )

        if not debe_iniciar_spotify:
            return None

        try:
            return self.actions.ejecutar(
                {
                    "modulo": "spotify",
                    "accion": "abrir",
                    "parametros": {},
                }
            )
        except Exception as error:
            print(f"No se pudo iniciar Spotify después de la rutina: {error}")
            return None

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

        resultado = self.procesar_comando(texto_limpio)
        self.hablar(resultado)
        self.accion_despues_de_hablar(resultado)

        return {
            "usuario": texto_usuario,
            "resultado": resultado,
            "salir": False,
        }
