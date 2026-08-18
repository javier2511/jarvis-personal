from services.memory_service import MemoryService


class PlacesService:
    CATEGORIA = "lugares"

    def __init__(self):
        self.memory = MemoryService()

    @staticmethod
    def _normalizar(texto):
        return MemoryService._normalizar(texto)

    def _datos(self, recuerdo):
        alias = None
        destino = None
        for etiqueta in recuerdo.get("etiquetas", []) or []:
            if etiqueta.startswith("alias:"):
                alias = etiqueta.split(":", 1)[1].strip()
            elif etiqueta.startswith("destino:"):
                destino = etiqueta.split(":", 1)[1].strip()
        return alias, destino

    def guardar(self, alias, destino):
        alias = str(alias or "").strip()
        destino = str(destino or "").strip()
        if not alias:
            return "Necesito saber cómo quieres llamar a ese lugar."
        if not destino:
            return "Necesito la dirección o ubicación del lugar."

        normalizado = self._normalizar(alias)
        for recuerdo in self.memory.listar(categoria=self.CATEGORIA):
            alias_guardado, _ = self._datos(recuerdo)
            if alias_guardado and self._normalizar(alias_guardado) == normalizado:
                self.memory.actualizar(
                    recuerdo["id"],
                    contenido=f"{alias}: {destino}",
                    categoria=self.CATEGORIA,
                    importancia=5,
                    etiquetas=["lugar", f"alias:{alias}", f"destino:{destino}"],
                )
                return f"Listo. Actualicé {alias} como {destino}."

        self.memory.guardar(
            contenido=f"{alias}: {destino}",
            categoria=self.CATEGORIA,
            importancia=5,
            etiquetas=["lugar", f"alias:{alias}", f"destino:{destino}"],
        )
        return f"Listo. Guardé {alias} como {destino}."

    def resolver(self, alias):
        alias = str(alias or "").strip()
        if not alias:
            return None

        consulta = self._normalizar(alias)
        lugares = self.memory.listar(categoria=self.CATEGORIA)

        for recuerdo in lugares:
            guardado, destino = self._datos(recuerdo)
            if guardado and destino and self._normalizar(guardado) == consulta:
                return destino

        for recuerdo in lugares:
            guardado, destino = self._datos(recuerdo)
            if not guardado or not destino:
                continue
            nombre = self._normalizar(guardado)
            if nombre in consulta or consulta in nombre:
                return destino

        return None

    def listar(self):
        resultado = []
        for recuerdo in self.memory.listar(categoria=self.CATEGORIA):
            alias, destino = self._datos(recuerdo)
            if alias and destino:
                resultado.append({"alias": alias, "destino": destino})
        return resultado

    def resumen(self):
        lugares = self.listar()
        if not lugares:
            return "Todavía no tienes lugares guardados."
        return "Tus lugares guardados son:\n" + "\n".join(
            f"{lugar['alias']}: {lugar['destino']}" for lugar in lugares
        )

    def eliminar(self, alias):
        alias = str(alias or "").strip()
        if not alias:
            return "Necesito saber qué lugar quieres eliminar."

        consulta = self._normalizar(alias)
        for recuerdo in self.memory.listar(categoria=self.CATEGORIA):
            guardado, _ = self._datos(recuerdo)
            if guardado and self._normalizar(guardado) == consulta:
                self.memory.eliminar(recuerdo["id"])
                return f"Listo. Eliminé el lugar {guardado}."

        return f"No encontré un lugar guardado llamado {alias}."
