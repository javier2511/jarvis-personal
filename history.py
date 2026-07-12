import json
from datetime import datetime

HISTORY_FILE = "history.json"

def cargar_historial():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except FileNotFoundError:
        return []

def guardar_evento(usuario, interpretacion, resultado, error=None):
    historial = cargar_historial()

    evento = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "usuario": usuario,
        "interpretacion": interpretacion,
        "resultado": resultado,
        "error": error
    }

    historial.append(evento)

    with open(HISTORY_FILE, "w", encoding="utf-8") as archivo:
        json.dump(historial, archivo, indent=4, ensure_ascii=False)