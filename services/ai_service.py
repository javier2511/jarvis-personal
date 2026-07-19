from brain import interpretar_comando
from services.memory_service import MemoryService


class AIService:
    def __init__(self):
        self.memory = MemoryService()

    def interpretar(self, texto):
        contexto_memoria = self.memory.contexto_para_ai(
            consulta=texto
        )

        return interpretar_comando(
            texto_usuario=texto,
            memoria_contexto=contexto_memoria,
        )
