from session import actualizar_estado
from system import abrir_programa

from services.calendar_service import CalendarService
from services.memory_service import MemoryService
from services.routine_service import RoutineService
from services.spotify_service import SpotifyService
from services.sports_service import SportsService
from datetime import datetime, timedelta


calendar = CalendarService()
memory = MemoryService()
routine = RoutineService()
spotify_api = SpotifyService()
sports = SportsService()


def ejecutar_calendar(accion, parametros):
    if accion == "eventos_hoy":
        return calendar.eventos_hoy()

    if accion == "proximo_evento":
        return calendar.proximo_evento()

    if accion == "crear_evento":
        titulo = parametros.get("titulo", "").strip()
        inicio = parametros.get("inicio")
        fin = parametros.get("fin")

        if not titulo:
            return "Necesito saber el título del evento."

        if not inicio:
            return "Necesito saber la fecha y hora del evento."

        if not fin:
            try:
                inicio_dt = datetime.fromisoformat(
                    str(inicio).replace("Z", "+00:00")
                )
                fin_dt = inicio_dt + timedelta(hours=1)
                fin = fin_dt.isoformat()
            except ValueError:
                return (
                    "Entendí el evento, pero no pude interpretar "
                    "correctamente la fecha y la hora."
                )

        return calendar.crear_evento(
            titulo,
            inicio,
            fin,
        )
    if accion == "buscar_eventos":
        texto = parametros.get("texto", "").strip()
        if not texto:
            return "Necesito saber qué evento quieres buscar."
        return calendar.buscar_eventos(texto)

    if accion == "mover_evento":
        texto = parametros.get("texto", "").strip()
        nuevo_inicio = parametros.get("nuevo_inicio")
        nuevo_fin = parametros.get("nuevo_fin")

        if not texto or not nuevo_inicio or not nuevo_fin:
            return "Necesito el evento y su nueva fecha de inicio y fin."

        return calendar.mover_evento(
            texto,
            nuevo_inicio,
            nuevo_fin,
        )

    if accion == "eliminar_evento":
        texto = parametros.get("texto", "").strip()
        if not texto:
            return "Necesito saber qué evento quieres eliminar."
        return calendar.eliminar_evento(texto)

    return f"No conozco la acción de calendario: {accion}"


def ejecutar_system(accion, parametros):
    if accion == "abrir_programa":
        programa = parametros.get("programa", "").strip()
        if not programa:
            return "Necesito saber qué programa quieres abrir."
        return abrir_programa(programa)

    return f"Acción de sistema no reconocida: {accion}"


def ejecutar_memory(accion, parametros):
    if accion == "guardar":
        contenido = parametros.get("contenido", "").strip()

        if not contenido:
            return "Necesito saber qué quieres que recuerde."

        recuerdo = memory.guardar(
            contenido=contenido,
            categoria=parametros.get("categoria", "otro"),
            importancia=parametros.get("importancia", 3),
            etiquetas=parametros.get("etiquetas", []),
        )

        if recuerdo.get("duplicado"):
            return "Eso ya lo recordaba."

        return f"Entendido. Recordaré que {contenido}"

    if accion == "consultar":
        consulta = parametros.get("consulta", "").strip()

        if not consulta:
            return "Necesito saber qué recuerdo quieres consultar."

        resultados = memory.buscar(consulta)

        if not resultados:
            return "No encontré ningún recuerdo relacionado."

        return memory.resumen_para_voz(resultados)

    if accion == "listar":
        recuerdos = memory.listar()

        if not recuerdos:
            return "Todavía no tengo recuerdos guardados sobre ti."

        return memory.resumen_para_voz(recuerdos)

    if accion == "eliminar":
        consulta = parametros.get("consulta", "").strip()

        if not consulta:
            return "Necesito saber qué quieres que olvide."

        eliminados = memory.eliminar_por_consulta(consulta)

        if eliminados == 0:
            return "No encontré un recuerdo que coincida con eso."

        if eliminados == 1:
            return "Listo. Eliminé ese recuerdo."

        return f"Listo. Eliminé {eliminados} recuerdos relacionados."

    return f"Acción de memoria no reconocida: {accion}"


def ejecutar_spotify(accion, parametros):
    if accion in {"abrir", "reproducir"}:
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

    return f"No conozco la rutina: {accion}"


def ejecutar_sports(accion, parametros):
    equipo = parametros.get("equipo", "").strip()

    if not equipo:
        return "Necesito saber de qué equipo quieres información."

    if accion == "proximo_evento":
        return sports.proximo_evento(equipo)

    if accion == "ultimo_resultado":
        return sports.ultimo_resultado(equipo)

    if accion == "noticias_equipo":
        return sports.noticias_equipo(
            equipo=equipo,
            limite=3,
        )

    return f"No conozco la acción deportiva: {accion}"


def ejecutar_none(accion, parametros):
    return "No encontré una acción disponible para ese comando."


def ejecutar_interpretacion(interpretacion):
    if not isinstance(interpretacion, dict):
        return "La interpretación recibida no es válida."

    modulo = interpretacion.get("modulo", "none")
    accion = interpretacion.get("accion", "none")
    parametros = interpretacion.get("parametros") or {}

    ejecutores = {
        "system": ejecutar_system,
        "memory": ejecutar_memory,
        "spotify": ejecutar_spotify,
        "calendar": ejecutar_calendar,
        "routine": ejecutar_routine,
        "sports": ejecutar_sports,
        "none": ejecutar_none,
    }

    ejecutor = ejecutores.get(modulo)

    if not ejecutor:
        return f"Módulo no reconocido: {modulo}"

    resultado = ejecutor(accion, parametros)

    if modulo != "none":
        actualizar_estado(modulo, accion)

    return resultado
