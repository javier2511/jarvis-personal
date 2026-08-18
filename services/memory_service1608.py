import json
import os
import re
import threading
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path


class MemoryService:
    def __init__(self, ruta=None):
        self.ruta = Path(
            ruta
            or os.getenv(
                "JARVIS_MEMORY_PATH",
                "/app/data/jarvis_memory.json",
            )
        )
        self.max_contexto = int(
            os.getenv("JARVIS_MEMORY_MAX_CONTEXT", "12")
        )
        self._lock = threading.RLock()
        self._asegurar_archivo()

    def _asegurar_archivo(self):
        self.ruta.parent.mkdir(parents=True, exist_ok=True)

        if not self.ruta.exists():
            self._escribir([])

    def _leer(self):
        with self._lock:
            try:
                contenido = self.ruta.read_text(encoding="utf-8")
                datos = json.loads(contenido or "[]")
                return datos if isinstance(datos, list) else []
            except (OSError, json.JSONDecodeError):
                return []

    def _escribir(self, recuerdos):
        with self._lock:
            temporal = self.ruta.with_suffix(
                self.ruta.suffix + ".tmp"
            )
            temporal.write_text(
                json.dumps(
                    recuerdos,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            temporal.replace(self.ruta)

    @staticmethod
    def _normalizar(texto):
        texto = str(texto or "").lower().strip()
        texto = unicodedata.normalize("NFKD", texto)
        texto = "".join(
            caracter
            for caracter in texto
            if not unicodedata.combining(caracter)
        )
        texto = re.sub(r"[^a-z0-9ñ\s]", " ", texto)
        return re.sub(r"\s+", " ", texto).strip()

    @staticmethod
    def _ahora():
        return datetime.now(timezone.utc).isoformat()

    def guardar(
        self,
        contenido,
        categoria="otro",
        importancia=3,
        etiquetas=None,
    ):
        contenido = str(contenido or "").strip()

        if not contenido:
            raise ValueError("El recuerdo no puede estar vacío.")

        try:
            importancia = int(importancia)
        except (TypeError, ValueError):
            importancia = 3

        importancia = max(1, min(importancia, 5))

        if not isinstance(etiquetas, list):
            etiquetas = []

        etiquetas = [
            str(etiqueta).strip()
            for etiqueta in etiquetas
            if str(etiqueta).strip()
        ]

        recuerdos = self._leer()
        contenido_normalizado = self._normalizar(contenido)

        for recuerdo in recuerdos:
            if self._normalizar(
                recuerdo.get("contenido")
            ) == contenido_normalizado:
                return {**recuerdo, "duplicado": True}

        ahora = self._ahora()
        recuerdo = {
            "id": str(uuid.uuid4()),
            "contenido": contenido,
            "categoria": str(categoria or "otro").strip(),
            "importancia": importancia,
            "etiquetas": etiquetas,
            "creado_en": ahora,
            "actualizado_en": ahora,
        }

        recuerdos.append(recuerdo)
        self._escribir(recuerdos)

        return {**recuerdo, "duplicado": False}

    def listar(self, categoria=None, limite=None):
        recuerdos = self._leer()

        if categoria:
            categoria_normalizada = self._normalizar(categoria)
            recuerdos = [
                recuerdo
                for recuerdo in recuerdos
                if self._normalizar(
                    recuerdo.get("categoria")
                ) == categoria_normalizada
            ]

        recuerdos.sort(
            key=lambda recuerdo: (
                int(recuerdo.get("importancia", 3)),
                recuerdo.get("actualizado_en", ""),
            ),
            reverse=True,
        )

        if limite is not None:
            recuerdos = recuerdos[: int(limite)]

        return recuerdos

    def obtener(self, recuerdo_id):
        return next(
            (
                recuerdo
                for recuerdo in self._leer()
                if recuerdo.get("id") == recuerdo_id
            ),
            None,
        )

    def buscar(self, consulta, limite=8):
        consulta_normalizada = self._normalizar(consulta)

        if not consulta_normalizada:
            return []

        palabras = set(consulta_normalizada.split())
        resultados = []

        for recuerdo in self._leer():
            texto = " ".join(
                [
                    str(recuerdo.get("contenido", "")),
                    str(recuerdo.get("categoria", "")),
                    " ".join(recuerdo.get("etiquetas", [])),
                ]
            )
            texto_normalizado = self._normalizar(texto)
            palabras_recuerdo = set(texto_normalizado.split())

            coincidencias = len(palabras & palabras_recuerdo)
            frase_completa = consulta_normalizada in texto_normalizado

            if coincidencias == 0 and not frase_completa:
                continue

            puntaje = (
                coincidencias * 10
                + (25 if frase_completa else 0)
                + int(recuerdo.get("importancia", 3))
            )
            resultados.append((puntaje, recuerdo))

        resultados.sort(
            key=lambda elemento: elemento[0],
            reverse=True,
        )

        return [
            recuerdo
            for _, recuerdo in resultados[:limite]
        ]

    def actualizar(self, recuerdo_id, **cambios):
        recuerdos = self._leer()

        for recuerdo in recuerdos:
            if recuerdo.get("id") != recuerdo_id:
                continue

            for campo in (
                "contenido",
                "categoria",
                "importancia",
                "etiquetas",
            ):
                if campo in cambios:
                    recuerdo[campo] = cambios[campo]

            recuerdo["actualizado_en"] = self._ahora()
            self._escribir(recuerdos)
            return recuerdo

        return None

    def eliminar(self, recuerdo_id):
        recuerdos = self._leer()
        restantes = [
            recuerdo
            for recuerdo in recuerdos
            if recuerdo.get("id") != recuerdo_id
        ]

        if len(restantes) == len(recuerdos):
            return False

        self._escribir(restantes)
        return True

    def eliminar_por_consulta(self, consulta):
        coincidencias = self.buscar(
            consulta,
            limite=100,
        )

        if not coincidencias:
            return 0

        ids = {
            recuerdo.get("id")
            for recuerdo in coincidencias
        }

        recuerdos = self._leer()
        restantes = [
            recuerdo
            for recuerdo in recuerdos
            if recuerdo.get("id") not in ids
        ]

        self._escribir(restantes)
        return len(recuerdos) - len(restantes)

    def contexto_para_ai(self, consulta=None):
        recuerdos = (
            self.buscar(
                consulta,
                limite=self.max_contexto,
            )
            if consulta
            else self.listar(
                limite=self.max_contexto
            )
        )

        if not recuerdos:
            return "Sin recuerdos relevantes."

        return "\n".join(
            f"- {recuerdo.get('contenido', '')}"
            for recuerdo in recuerdos
        )

    def contexto_para_briefing(self):
        return self.contexto_para_ai()

    def resumen_para_voz(self, recuerdos=None):
        recuerdos = recuerdos or []

        if not recuerdos:
            return "No tengo recuerdos para mostrar."

        contenidos = [
            recuerdo.get("contenido", "").strip()
            for recuerdo in recuerdos
            if recuerdo.get("contenido", "").strip()
        ]

        if not contenidos:
            return "No tengo recuerdos para mostrar."

        if len(contenidos) == 1:
            return f"Recuerdo que {contenidos[0]}"

        lineas = [
            f"{indice}. {contenido}"
            for indice, contenido in enumerate(
                contenidos,
                start=1,
            )
        ]

        return "Esto es lo que recuerdo:\n" + "\n".join(lineas)

    def estadisticas(self):
        recuerdos = self._leer()
        categorias = {}

        for recuerdo in recuerdos:
            categoria = recuerdo.get("categoria", "otro")
            categorias[categoria] = categorias.get(categoria, 0) + 1

        return {
            "total": len(recuerdos),
            "categorias": categorias,
            "ruta": str(self.ruta),
        }
