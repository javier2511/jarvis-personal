import speech_recognition as sr
import pyttsx3
import threading

engine = pyttsx3.init()
voz_lock = threading.Lock()

def hablar(texto):
    with voz_lock:
        engine.say(texto)
        engine.runAndWait()

def escuchar():
    recognizer = sr.Recognizer()

    with sr.Microphone() as source:
        print("Jarvis: Escuchando...")
        recognizer.adjust_for_ambient_noise(source, duration=1)

        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=6)
        except sr.WaitTimeoutError:
            print("Jarvis: No detecté voz")
            return ""

    try:
        texto = recognizer.recognize_google(audio, language="es-MX")
        print(f"Tú dijiste: {texto}")
        return texto

    except sr.UnknownValueError:
        print("Jarvis: No entendí el audio")
        return ""

    except sr.RequestError as e:
        print(f"Error de reconocimiento: {e}")
        return ""