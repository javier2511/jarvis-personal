
import os

def abrir_programa(programa):
    programas = {
        "notepad": "notepad",
        "bloc de notas": "notepad",
        "calculadora": "calc",
        "spotify": "spotify"
    }

    if programa in programas:
        os.system(programas[programa])
        return "ejecutado"
    else:
        return f"No conozco el programa: {programa}"