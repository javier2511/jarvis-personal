
from brain import interpretar_comando
from router import ejecutar_interpretacion
from history import guardar_evento

print("Jarvis iniciado")

while True:
    texto_usuario = input("Tú: ")

    if texto_usuario.lower().strip() == "salir":
        print("Jarvis: Hasta luego, Javier.")
        break

    try:
        interpretacion = interpretar_comando(texto_usuario)

        resultado = ejecutar_interpretacion(interpretacion)

        guardar_evento(
            usuario=texto_usuario,
            interpretacion=interpretacion,
            resultado=resultado
        )

        print(f"Jarvis: {resultado}")

    except Exception as error:
        guardar_evento(
            usuario=texto_usuario,
            interpretacion={},
            resultado="error",
            error=str(error)
        )

        print(f"Jarvis: Ocurrió un error: {error}")