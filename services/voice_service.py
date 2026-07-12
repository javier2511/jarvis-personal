from services.tts_service import TTSService


class VoiceService:

    def __init__(self):
        self.tts = TTSService()

    def escuchar(self):
        """
        Solo disponible en la versión local de PC.
        En la nube, el audio entra por el endpoint /audio.
        """
        try:
            import speech_recognition as sr
        except ImportError:
            return ""

        recognizer = sr.Recognizer()

        with sr.Microphone() as source:
            print("Jarvis: Escuchando...")

            try:
                audio = recognizer.listen(
                    source,
                    timeout=5,
                    phrase_time_limit=10
                )
            except sr.WaitTimeoutError:
                return ""

        try:
            return recognizer.recognize_google(
                audio,
                language="es-MX"
            )

        except sr.UnknownValueError:
            return ""

        except sr.RequestError:
            return ""

    def hablar(self, texto):
        self.tts.hablar(texto)