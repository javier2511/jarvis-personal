import customtkinter as ctk
import threading

from brain import interpretar_comando
from router import ejecutar_interpretacion
from history import guardar_evento
from voice import escuchar, hablar

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Jarvis MVP")
app.geometry("600x500")

estado_label = ctk.CTkLabel(app, text="JARVIS", font=("Arial", 32, "bold"))
estado_label.pack(pady=20)

status_label = ctk.CTkLabel(app, text="Estado: En espera", font=("Arial", 16))
status_label.pack(pady=10)

usuario_box = ctk.CTkTextbox(app, height=100)
usuario_box.pack(padx=20, pady=10, fill="x")

respuesta_box = ctk.CTkTextbox(app, height=140)
respuesta_box.pack(padx=20, pady=10, fill="x")

def escribir_usuario(texto):
    usuario_box.delete("1.0", "end")
    usuario_box.insert("end", texto)

def escribir_respuesta(texto):
    respuesta_box.delete("1.0", "end")
    respuesta_box.insert("end", texto)

def procesar_comando(texto_usuario):
    try:
        status_label.configure(text="Estado: Pensando...")

        interpretacion = interpretar_comando(texto_usuario)
        resultado = ejecutar_interpretacion(interpretacion)

        guardar_evento(
            usuario=texto_usuario,
            interpretacion=interpretacion,
            resultado=resultado
        )

        escribir_respuesta(resultado)
        status_label.configure(text="Estado: Respondiendo...")
        hablar(resultado)

        status_label.configure(text="Estado: En espera")

    except Exception as error:
        escribir_respuesta(f"Ocurrió un error: {error}")
        status_label.configure(text="Estado: Error")
        hablar("Ocurrió un error")

def escuchar_con_voz():
    status_label.configure(text="Estado: Escuchando...")

    texto_usuario = escuchar()

    if texto_usuario == "":
        escribir_usuario("No entendí")
        status_label.configure(text="Estado: En espera")
        hablar("No entendí")
        return

    escribir_usuario(texto_usuario)

    texto_limpio = texto_usuario.lower().strip()

    if "jarvis" in texto_limpio:
        texto_limpio = texto_limpio.replace("jarvis", "").strip()
    if texto_limpio == "salir":
        hablar("Hasta luego, Javier.")
        app.quit()
        return
    procesar_comando(texto_limpio)

def iniciar_escucha():
    hilo = threading.Thread(target=escuchar_con_voz)
    hilo.start()

boton_voz = ctk.CTkButton(
    app,
    text="🎤 Hablar con Jarvis",
    command=iniciar_escucha,
    height=50
)
boton_voz.pack(pady=20)

app.mainloop()