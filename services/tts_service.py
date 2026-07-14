import os
from openai import OpenAI


class TTSService:

    def __init__(self):
        self.client = OpenAI()

    def generar_audio(self, texto, archivo):
        respuesta = self.client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="echo",
            input=texto,
            speed=1.15
            instructions="""
            
Habla en español mexicano natural.

Tu personalidad es la de Jarvis:
inteligente, elegante, tranquilo y seguro.

Habla a un ritmo ágil y conversacional,
aproximadamente un 18 por ciento más rápido
que una conversación normal.

Usa pausas cortas.
Evita pausas dramáticas.
No suenes como locutor, narrador ni robot.
No alargues las palabras.
Pronuncia con claridad y naturalidad.
Sé cálido, directo y ligeramente sofisticado.
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