from system import abrir_programa
from memory import guardar_dato, consultar_dato

from session import actualizar_estado
from services.calendar_service import CalendarService
from services.routine_service import RoutineService
from services.spotify_service import SpotifyService
from services.sports_service import SportsService

calendar = CalendarService()
routine = RoutineService()
spotify_api = SpotifyService()
sports = SportsService()

def ejecutar_calendar(accion, parametros):
    if accion == "eventos_hoy":
        return calendar.eventos_hoy()
    if accion == "proximo_evento":
        return calendar.proximo_evento()
    

    if accion == "crear_evento":

        titulo = parametros["titulo"]
        inicio = parametros["inicio"]
        fin = parametros["fin"]

        return calendar.crear_evento(
            titulo,
            inicio,
            fin
        )

    if accion == "buscar_eventos":

        texto = parametros["texto"]

        return calendar.buscar_eventos(texto)

    if accion == "mover_evento":

        texto = parametros["texto"]
        nuevo_inicio = parametros["nuevo_inicio"]
        nuevo_fin = parametros["nuevo_fin"]

        return calendar.mover_evento(
            texto,
            nuevo_inicio,
            nuevo_fin
        )
    
    if accion == "eliminar_evento":

        texto = parametros["texto"]

        return calendar.eliminar_evento(texto)
    
    return "No conozco esa acción de calendario"
    
def ejecutar_system(accion, parametros):
    if accion == "abrir_programa":
        programa = parametros["programa"]
        return abrir_programa(programa)

    return f"Acción de system no reconocida: {accion}"

def ejecutar_memory(accion, parametros):
    if accion == "guardar_dato":
        campo = parametros["campo"]
        valor = parametros["valor"]
        return guardar_dato(campo, valor)

    if accion == "consultar_dato":
        campo = parametros["campo"]
        return consultar_dato(campo)

    return f"Acción de memory no reconocida: {accion}"

def ejecutar_spotify(accion, parametros):
    if accion == "abrir":
        return spotify_api.reproducir()

    if accion == "reproducir":
        return spotify_api.reproducir()

    if accion == "reproducir_busqueda":
        busqueda = parametros.get("busqueda", "").strip()

        if not busqueda:
            return "Necesito saber qué quieres reproducir."

        return spotify_api.reproducir_busqueda(busqueda)

    if accion == "pausa":
        return spotify_api.pausar()

    if accion == "siguiente":
        return spotify_api.siguiente()

    if accion == "anterior":
        return spotify_api.anterior()

    if accion == "cancion_actual":
        return spotify_api.cancion_actual()

    return f"No conozco la acción de Spotify: {accion}"
def ejecutar_routine(accion, parametros):

    if accion == "buenos_dias":
        return routine.buenos_dias()

    return "No conozco esa rutina."

def ejecutar_sports(accion, parametros):
    equipo = parametros.get(
        "equipo",
        ""
    ).strip()

    if not equipo:
        return (
            "Necesito saber de qué equipo "
            "quieres información."
        )

    if accion == "proximo_evento":
        return sports.proximo_evento(
            equipo
        )

    if accion == "ultimo_resultado":
        return sports.ultimo_resultado(
            equipo
        )

    if accion == "noticias_equipo":
        return sports.noticias_equipo(
            equipo=equipo,
            limite=3
        )

    return (
        f"No conozco la acción deportiva: "
        f"{accion}"
    )

def ejecutar_interpretacion(interpretacion):
    modulo = interpretacion["modulo"]
    accion = interpretacion["accion"]
    parametros = interpretacion["parametros"]
    

    ejecutores = {
        "system": ejecutar_system,
        "memory": ejecutar_memory,
        "spotify": ejecutar_spotify,
        "calendar": ejecutar_calendar,
        "routine": ejecutar_routine,
        "sports": ejecutar_sports
    }


    if modulo in ejecutores:
        resultado = ejecutores[modulo](accion, parametros)
        actualizar_estado(modulo, accion)
        return resultado
    return f"Módulo no reconocido: {modulo}"