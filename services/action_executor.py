from typing import Any, Dict

from system import abrir_archivo, abrir_programa, abrir_url


class ActionExecutor:
    """Ejecuta acciones locales simples ya estructuradas."""

    def ejecutar(self, accion: Dict[str, Any]) -> str:
        if not isinstance(accion, dict):
            return "La acción debe ser un diccionario."

        tipo = str(accion.get("tipo", "")).strip().lower()

        if tipo == "abrir_programa":
            return abrir_programa(str(accion.get("programa", "")))

        if tipo == "abrir_url":
            return abrir_url(str(accion.get("url", "")))

        if tipo == "abrir_archivo":
            return abrir_archivo(str(accion.get("ruta", "")))

        return f"Tipo de acción no reconocido: {tipo or 'sin tipo'}"

    def abrir_programa(self, nombre: str) -> str:
        return abrir_programa(nombre)

    def abrir_url(self, url: str) -> str:
        return abrir_url(url)

    def abrir_archivo(self, ruta: str) -> str:
        return abrir_archivo(ruta)
