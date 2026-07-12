import speech_recognition as sr

from services.tts_service import TTSService


class VoiceService:

    def __init__(self):
        self.tts = TTSService()


    def escuchar(self):

        recognizer = sr.Recognizer()

        with sr.Microphone() as source:
            print("Escuchando...")
            audio = recognizer.listen(source)

        try:
            texto = recognizer.recognize_google(
                audio,
                language="es-MX"
            )

            return texto

        except:
            return ""


    def hablar(self, texto):

        self.tts.hablar(texto)