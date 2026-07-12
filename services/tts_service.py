import os
from openai import OpenAI


class TTSService:

    def __init__(self):
        self.client = OpenAI()

    def generar_audio(self, texto, archivo):
        respuesta = self.client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="ash",
            input=texto,
            instructions="""
Eres Jarvis, el asistente personal avanzado de Javier.
Habla con un tono tranquilo, inteligente y seguro.
Sé profesional pero cercano.
Usa español mexicano natural.
No suenes como locutor ni narrador.
"""
        )

        respuesta.write_to_file(archivo)

    def hablar(self, texto):
        # Este método solo se utiliza en la versión local de PC.
        archivo = "jarvis_voice.mp3"
        self.generar_audio(texto, archivo)

        try:
            from playsound import playsound
            playsound(archivo)
        finally:
            if os.path.exists(archivo):
                os.remove(archivo)