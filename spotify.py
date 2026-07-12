import keyboard
import os

def controlar_spotify(accion):

    if accion == "abrir":
        os.system("spotify")
        return "Spotify abierto"

    elif accion == "pausa":
        keyboard.send("play/pause media")
        return "Spotify pausado"
    elif accion == "subir_volumen":
        keyboard.send("volume up")
        return "Subí el volumen"

    elif accion == "bajar_volumen":
        keyboard.send("volume down")
        return "Bajé el volumen"
        

    elif accion == "siguiente":
        keyboard.send("next track")
        return "Siguiente canción"

    elif accion == "anterior":
        keyboard.send("previous track")
        return "Canción anterior"

    else:
        return f"No conozco la acción: {accion}"