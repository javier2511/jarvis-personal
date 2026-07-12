from openai import OpenAI
from playsound import playsound
import os


class TTSService:

    def __init__(self):
        self.client = OpenAI()

    def generar_audio(self, texto, archivo):
        respuesta = self.client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="ash",
            input=texto,
            instructions="""
Eres Jarvis, un asistente personal avanzado de Javier.
Habla con tono tranquilo, inteligente y seguro.
Profesional pero cercano.
Español mexicano natural.
No suenes como locutor ni narrador.
"""
        )

        respuesta.write_to_file(archivo)

    def hablar(self, texto):
        archivo = "jarvis_voice.mp3"

        self.generar_audio(texto, archivo)

        playsound(archivo)

        os.remove(archivo)