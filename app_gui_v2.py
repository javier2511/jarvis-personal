import customtkinter as ctk
import threading
import math
from datetime import datetime

from jarvis import Jarvis
from memory import cargar_memoria
from session import obtener_contexto

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Jarvis MVP - Interface V2")
app.geometry("950x650")

estado_actual = "en_espera"
angulo = 0
modo_continuo=False
jarvis = Jarvis()

main = ctk.CTkFrame(app)
main.pack(padx=20, pady=20, fill="both", expand=True)

left = ctk.CTkFrame(main, width=300)
left.pack(side="left", padx=10, pady=10, fill="y")

right = ctk.CTkFrame(main)
right.pack(side="right", padx=10, pady=10, fill="both", expand=True)

titulo = ctk.CTkLabel(left, text="J A R V I S", font=("Arial", 34, "bold"))
titulo.pack(pady=(20, 5))

subtitulo = ctk.CTkLabel(left, text="Asistente personal de Javier", font=("Arial", 14))
subtitulo.pack(pady=(0, 20))

canvas = ctk.CTkCanvas(left, width=180, height=180, bg="#1a1a1a", highlightthickness=0)
canvas.pack(pady=10)

status_label = ctk.CTkLabel(left, text="Estado: En espera", font=("Arial", 16))
status_label.pack(pady=10)

hora_label = ctk.CTkLabel(left, text="", font=("Arial", 13))
hora_label.pack(pady=5)

boton_voz = ctk.CTkButton(left, text="▶ Activar Jarvis", height=45)
boton_voz.pack(pady=(25, 10), padx=20, fill="x")

boton_detener = ctk.CTkButton(left, text="■ Detener Jarvis", height=45)
boton_detener.pack(pady=(0, 20), padx=20, fill="x")

info_label = ctk.CTkLabel(left, text="Sistema", anchor="w", font=("Arial", 14, "bold"))
info_label.pack(padx=20, pady=(10, 0), fill="x")

info_box = ctk.CTkTextbox(left, height=150)
info_box.pack(padx=20, pady=10, fill="x")

usuario_label = ctk.CTkLabel(right, text="🎤 Tú", anchor="w", font=("Arial", 16, "bold"))
usuario_label.pack(padx=20, pady=(20, 5), fill="x")

usuario_box = ctk.CTkTextbox(right, height=140)
usuario_box.pack(padx=20, pady=10, fill="both", expand=True)

jarvis_label = ctk.CTkLabel(right, text="🤖 Jarvis", anchor="w", font=("Arial", 16, "bold"))
jarvis_label.pack(padx=20, pady=(10, 5), fill="x")

respuesta_box = ctk.CTkTextbox(right, height=180)
respuesta_box.pack(padx=20, pady=10, fill="both", expand=True)


def set_estado(nuevo_estado):
    global estado_actual
    estado_actual = nuevo_estado

    textos = {
        "en_espera": "Estado: En espera",
        "escuchando": "Estado: Escuchando...",
        "pensando": "Estado: Pensando...",
        "hablando": "Estado: Respondiendo...",
        "error": "Estado: Error"
    }

    status_label.configure(text=textos.get(nuevo_estado, "Estado: Desconocido"))


def reset_boton():
    boton_voz.configure(state="normal", text="🎤 Hablar con Jarvis")


def escribir_textbox(textbox, texto):
    textbox.delete("1.0", "end")
    textbox.insert("end", texto)


def actualizar_info():
    memoria = cargar_memoria()
    contexto = obtener_contexto()

    texto = f"""Memoria activa:
Empresa: {memoria.get("empresa", "No guardada")}
Jefe: {memoria.get("jefe", "No guardado")}
Ciudad: {memoria.get("ciudad", "No guardada")}

Última acción:
Módulo: {contexto.get("ultimo_modulo")}
Acción: {contexto.get("ultima_accion")}
"""
    escribir_textbox(info_box, texto)


def actualizar_hora():
    hora_label.configure(text=datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))
    app.after(1000, actualizar_hora)


def color_por_estado():
    if estado_actual == "escuchando":
        return "#00AEEF"
    if estado_actual == "pensando":
        return "#FFB000"
    if estado_actual == "hablando":
        return "#00FF99"
    if estado_actual == "error":
        return "#FF3B30"
    return "#4A90E2"


def animar_avatar():
    global angulo
    canvas.delete("all")

    cx, cy = 90, 90
    base = 48
    pulso = 7 * math.sin(math.radians(angulo))
    radio = base + pulso
    color = color_por_estado()

    canvas.create_oval(cx - radio, cy - radio, cx + radio, cy + radio, outline=color, width=4)
    canvas.create_oval(cx - 25, cy - 25, cx + 25, cy + 25, fill=color, outline="")
    canvas.create_text(cx, cy + 70, text=estado_actual.upper(), fill="white", font=("Arial", 10, "bold"))

    angulo = (angulo + 8) % 360
    app.after(60, animar_avatar)


def procesar_comando(texto_usuario):
    try:
        set_estado("pensando")

        interpretacion = interpretar_comando(texto_usuario)
        resultado = ejecutar_interpretacion(interpretacion)

        guardar_evento(
            usuario=texto_usuario,
            interpretacion=interpretacion,
            resultado=resultado
        )

        escribir_textbox(respuesta_box, resultado)
        actualizar_info()

        set_estado("hablando")
        hablar(resultado)

        set_estado("en_espera")

    except Exception as error:
        guardar_evento(
            usuario=texto_usuario,
            interpretacion={},
            resultado="error",
            error=str(error)
        )

        escribir_textbox(respuesta_box, f"Ocurrió un error: {error}")
        set_estado("error")
        hablar("Ocurrió un error")
        set_estado("en_espera")


def escuchar_con_voz():
    try:
        set_estado("escuchando")

        respuesta = jarvis.ciclo_voz()

        escribir_textbox(usuario_box, respuesta["usuario"])
        escribir_textbox(respuesta_box, respuesta["resultado"])

        actualizar_info()

        if respuesta["salir"]:
            app.quit()
            return

        set_estado(jarvis.estado)

    finally:
        reset_boton()

def ciclo_continuo():
    global modo_continuo

    while modo_continuo:
        try:
            set_estado("escuchando")

            respuesta = jarvis.ciclo_voz()

            escribir_textbox(usuario_box, respuesta["usuario"])
            escribir_textbox(respuesta_box, respuesta["resultado"])
            actualizar_info()

            if respuesta["salir"]:
                modo_continuo = False
                app.quit()
                return

        except Exception as error:
            escribir_textbox(respuesta_box, f"Ocurrió un error: {error}")
            set_estado("error")

    set_estado("en_espera")


def activar_jarvis():
    global modo_continuo

    if modo_continuo:
        return

    modo_continuo = True
    boton_voz.configure(state="disabled", text="Jarvis activo")
    boton_detener.configure(state="normal")

    hilo = threading.Thread(target=ciclo_continuo)
    hilo.daemon = True
    hilo.start()


def detener_jarvis():
    global modo_continuo

    modo_continuo = False
    boton_voz.configure(state="normal", text="▶ Activar Jarvis")
    boton_detener.configure(state="disabled")
    set_estado("en_espera")

boton_voz.configure(command=activar_jarvis)
boton_detener.configure(command=detener_jarvis)
boton_detener.configure(state="disabled")

actualizar_info()
actualizar_hora()
animar_avatar()

app.mainloop()