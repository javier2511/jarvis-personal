from memory import cargar_memoria
from session import obtener_contexto
from history import guardar_evento


class MemoryService:

    def cargar_memoria(self):
        return cargar_memoria()


    def obtener_contexto(self):
        return obtener_contexto()


    def guardar_evento(self, usuario, interpretacion, resultado):
        guardar_evento(
            usuario=usuario,
            interpretacion=interpretacion,
            resultado=resultado
        )