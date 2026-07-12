from brain import interpretar_comando
from router import ejecutar_interpretacion
from history import guardar_evento
from voice import escuchar, hablar

print("Jarvis por voz iniciado")
hablar("Jarvis iniciado")

while True:
    texto_usuario = escuchar()

    if texto_usuario == "":
        continue

    texto_usuario = texto_usuario.lower().strip()

    if "jarvis" not in texto_usuario:
        print("Esperando palabra de activación...")
        continue

    texto_usuario = texto_usuario.replace("jarvis", "").strip()

    if texto_usuario == "":
        hablar("Te escucho.")
        continue
    if texto_usuario == "":
        hablar("No entendí. Repite por favor.")
        continue

    if texto_usuario.lower().strip() == "salir":
        hablar("Hasta luego, Javier.")
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
        hablar(resultado)

    except Exception as error:
        guardar_evento(
            usuario=texto_usuario,
            interpretacion={},
            resultado="error",
            error=str(error)
        )

        print(f"Jarvis: Ocurrió un error: {error}")
        hablar("Ocurrió un error.")