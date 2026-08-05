import os
import subprocess
import webbrowser
from pathlib import Path


PROGRAMAS = {
    "notepad": "notepad",
    "bloc de notas": "notepad",
    "calculadora": "calc",
    "spotify": "spotify",
}


def abrir_programa(programa: str) -> str:
    """Abre un programa conocido en Windows."""
    nombre = (programa or "").strip().lower()

    if not nombre:
        return "Debes indicar qué programa quieres abrir."

    comando = PROGRAMAS.get(nombre)

    if not comando:
        return f"No conozco el programa: {programa}"

    try:
        subprocess.Popen(comando, shell=True)
        return "ejecutado"
    except Exception as error:
        return f"No pude abrir {programa}: {error}"


def abrir_url(url: str) -> str:
    """Abre una URL en el navegador predeterminado."""
    destino = (url or "").strip()

    if not destino:
        return "Debes indicar una URL."

    if not destino.startswith(("http://", "https://")):
        return "La URL debe comenzar con http:// o https://"

    try:
        abierto = webbrowser.open(destino, new=2)
        return "ejecutado" if abierto else "No pude abrir la URL."
    except Exception as error:
        return f"No pude abrir la URL: {error}"


def abrir_archivo(ruta: str) -> str:
    """Abre un archivo o carpeta con la aplicación predeterminada de Windows."""
    destino = Path(ruta).expanduser()

    if not destino.exists():
        return f"No encontré la ruta: {destino}"

    try:
        os.startfile(str(destino))
        return "ejecutado"
    except Exception as error:
        return f"No pude abrir la ruta: {error}"
