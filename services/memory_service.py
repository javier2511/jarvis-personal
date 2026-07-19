"""
Jarvis - Memory Service
=======================

Memoria persistente y estructurada para Jarvis.

Esta primera versión utiliza un archivo JSON guardado en el volumen
persistente de Railway. No requiere base de datos ni llamadas a OpenAI.

Variables de entorno opcionales:

JARVIS_MEMORY_PATH=/app/data/jarvis_memory.json
JARVIS_MEMORY_MAX_CONTEXT=20

Ejemplos:

    memory = MemoryService()

    memory.guardar(
        contenido="Javier le va a los New York Giants",
        categoria="preferencia",
        etiquetas=["NFL", "Giants"]
    )

    recuerdos = memory.buscar("Giants")

    contexto = memory.contexto_para_briefing()
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import unicodedata
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class MemoryService:
    """
    Administra la memoria persistente de Jarvis.

    Cada recuerdo contiene:

    - id
    - contenido
    - categoría
    - etiquetas
    - importancia
    - fecha de creación
    - fecha de actualización
    - estado activo
    """

    CATEGORIAS_VALIDAS = {
        "preferencia",
        "habito",
        "persona",
        "trabajo",
        "viaje",
        "deporte",
        "salud",
        "evento",
        "proyecto",
        "dato",
        "otro",
    }

    def __init__(
        self,
        memory_path: Optional[str] = None,
    ) -> None:
        ruta_configurada = (
            memory_path
            or os.getenv("JARVIS_MEMORY_PATH")
            or "/app/data/jarvis_memory.json"
        )

        self.memory_path = Path(ruta_configurada)

        self.max_context = self._leer_entero_entorno(
            "JARVIS_MEMORY_MAX_CONTEXT",
            default=20,
            minimum=5,
            maximum=100,
        )

        self._lock = threading.RLock()

        self._asegurar_archivo()

    # ------------------------------------------------------------------
    # MÉTODOS PÚBLICOS
    # ------------------------------------------------------------------

    def guardar(
        self,
        contenido: str,
        *,
        categoria: str = "dato",
        etiquetas: Optional[List[str]] = None,
        importancia: int = 3,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Guarda un recuerdo nuevo.

        Si ya existe un recuerdo muy parecido, actualiza el existente
        en lugar de crear un duplicado.
        """

        contenido_limpio = self._limpiar_contenido(contenido)

        if not contenido_limpio:
            raise ValueError(
                "El contenido del recuerdo no puede estar vacío."
            )

        categoria_limpia = self._normalizar_categoria(categoria)
        etiquetas_limpias = self._limpiar_etiquetas(etiquetas or [])
        importancia_limpia = self._normalizar_importancia(importancia)

        ahora = self._fecha_actual()

        with self._lock:
            memoria = self._leer_memoria()

            recuerdo_existente = self._buscar_duplicado(
                memoria=memoria,
                contenido=contenido_limpio,
            )

            if recuerdo_existente:
                recuerdo_existente["contenido"] = contenido_limpio
                recuerdo_existente["categoria"] = categoria_limpia
                recuerdo_existente["etiquetas"] = self._combinar_etiquetas(
                    recuerdo_existente.get("etiquetas", []),
                    etiquetas_limpias,
                )
                recuerdo_existente["importancia"] = max(
                    int(recuerdo_existente.get("importancia", 1)),
                    importancia_limpia,
                )
                recuerdo_existente["actualizado_en"] = ahora
                recuerdo_existente["activo"] = True

                if metadata:
                    metadata_actual = recuerdo_existente.get(
                        "metadata",
                        {},
                    )

                    if not isinstance(metadata_actual, dict):
                        metadata_actual = {}

                    metadata_actual.update(metadata)
                    recuerdo_existente["metadata"] = metadata_actual

                self._guardar_memoria(memoria)

                return recuerdo_existente.copy()

            nuevo_recuerdo = {
                "id": str(uuid.uuid4()),
                "contenido": contenido_limpio,
                "categoria": categoria_limpia,
                "etiquetas": etiquetas_limpias,
                "importancia": importancia_limpia,
                "creado_en": ahora,
                "actualizado_en": ahora,
                "activo": True,
                "metadata": metadata or {},
            }

            memoria["recuerdos"].append(nuevo_recuerdo)
            memoria["actualizado_en"] = ahora

            self._guardar_memoria(memoria)

            return nuevo_recuerdo.copy()

    def buscar(
        self,
        consulta: str,
        *,
        limite: int = 10,
        categoria: Optional[str] = None,
        incluir_inactivos: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Busca recuerdos por contenido, categoría y etiquetas.
        """

        consulta_normalizada = self._normalizar_texto(consulta)

        if not consulta_normalizada:
            return []

        limite = max(1, min(limite, 100))

        categoria_normalizada = (
            self._normalizar_categoria(categoria)
            if categoria
            else None
        )

        palabras_consulta = set(
            consulta_normalizada.split()
        )

        with self._lock:
            memoria = self._leer_memoria()

        resultados = []

        for recuerdo in memoria.get("recuerdos", []):
            if not incluir_inactivos and not recuerdo.get("activo", True):
                continue

            if (
                categoria_normalizada
                and recuerdo.get("categoria") != categoria_normalizada
            ):
                continue

            puntuacion = self._calcular_relevancia(
                recuerdo=recuerdo,
                consulta=consulta_normalizada,
                palabras_consulta=palabras_consulta,
            )

            if puntuacion <= 0:
                continue

            copia = recuerdo.copy()
            copia["_relevancia"] = puntuacion
            resultados.append(copia)

        resultados.sort(
            key=lambda item: (
                item.get("_relevancia", 0),
                item.get("importancia", 1),
                item.get("actualizado_en", ""),
            ),
            reverse=True,
        )

        for resultado in resultados:
            resultado.pop("_relevancia", None)

        return resultados[:limite]

    def listar(
        self,
        *,
        categoria: Optional[str] = None,
        limite: int = 50,
        incluir_inactivos: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Lista recuerdos ordenados por importancia y actualización.
        """

        limite = max(1, min(limite, 500))

        categoria_normalizada = (
            self._normalizar_categoria(categoria)
            if categoria
            else None
        )

        with self._lock:
            memoria = self._leer_memoria()

        recuerdos = []

        for recuerdo in memoria.get("recuerdos", []):
            if not incluir_inactivos and not recuerdo.get("activo", True):
                continue

            if (
                categoria_normalizada
                and recuerdo.get("categoria") != categoria_normalizada
            ):
                continue

            recuerdos.append(recuerdo.copy())

        recuerdos.sort(
            key=lambda item: (
                item.get("importancia", 1),
                item.get("actualizado_en", ""),
            ),
            reverse=True,
        )

        return recuerdos[:limite]

    def obtener(
        self,
        memory_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene un recuerdo por su ID.
        """

        with self._lock:
            memoria = self._leer_memoria()

        for recuerdo in memoria.get("recuerdos", []):
            if recuerdo.get("id") == memory_id:
                return recuerdo.copy()

        return None

    def actualizar(
        self,
        memory_id: str,
        *,
        contenido: Optional[str] = None,
        categoria: Optional[str] = None,
        etiquetas: Optional[List[str]] = None,
        importancia: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Actualiza un recuerdo existente.
        """

        with self._lock:
            memoria = self._leer_memoria()

            for recuerdo in memoria.get("recuerdos", []):
                if recuerdo.get("id") != memory_id:
                    continue

                if contenido is not None:
                    contenido_limpio = self._limpiar_contenido(
                        contenido
                    )

                    if not contenido_limpio:
                        raise ValueError(
                            "El contenido no puede quedar vacío."
                        )

                    recuerdo["contenido"] = contenido_limpio

                if categoria is not None:
                    recuerdo["categoria"] = self._normalizar_categoria(
                        categoria
                    )

                if etiquetas is not None:
                    recuerdo["etiquetas"] = self._limpiar_etiquetas(
                        etiquetas
                    )

                if importancia is not None:
                    recuerdo["importancia"] = (
                        self._normalizar_importancia(importancia)
                    )

                if metadata is not None:
                    recuerdo["metadata"] = metadata

                recuerdo["actualizado_en"] = self._fecha_actual()

                self._guardar_memoria(memoria)

                return recuerdo.copy()

        return None

    def eliminar(
        self,
        memory_id: str,
        *,
        permanente: bool = False,
    ) -> bool:
        """
        Elimina un recuerdo.

        Por defecto realiza una eliminación lógica. Con permanente=True,
        elimina físicamente el registro del archivo.
        """

        with self._lock:
            memoria = self._leer_memoria()
            recuerdos = memoria.get("recuerdos", [])

            for indice, recuerdo in enumerate(recuerdos):
                if recuerdo.get("id") != memory_id:
                    continue

                if permanente:
                    recuerdos.pop(indice)
                else:
                    recuerdo["activo"] = False
                    recuerdo["actualizado_en"] = self._fecha_actual()

                memoria["actualizado_en"] = self._fecha_actual()
                self._guardar_memoria(memoria)

                return True

        return False

    def eliminar_por_consulta(
        self,
        consulta: str,
    ) -> int:
        """
        Desactiva los recuerdos que coincidan con una consulta.

        Este método resulta útil para órdenes como:

            "Olvida que le voy a los Giants"
        """

        coincidencias = self.buscar(
            consulta,
            limite=20,
        )

        eliminados = 0

        for recuerdo in coincidencias:
            if self.eliminar(recuerdo["id"]):
                eliminados += 1

        return eliminados

    def contexto_para_briefing(
        self,
        *,
        limite: Optional[int] = None,
        categorias: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Devuelve un contexto compacto para BriefingService.

        No entrega IDs ni metadatos técnicos.
        """

        limite_final = limite or self.max_context
        limite_final = max(1, min(limite_final, 100))

        categorias_normalizadas = None

        if categorias:
            categorias_normalizadas = {
                self._normalizar_categoria(categoria)
                for categoria in categorias
            }

        recuerdos = self.listar(
            limite=200,
        )

        contexto: List[Dict[str, Any]] = []

        for recuerdo in recuerdos:
            categoria = recuerdo.get("categoria", "dato")

            if (
                categorias_normalizadas
                and categoria not in categorias_normalizadas
            ):
                continue

            contexto.append(
                {
                    "contenido": recuerdo.get("contenido"),
                    "categoria": categoria,
                    "etiquetas": recuerdo.get("etiquetas", []),
                    "importancia": recuerdo.get("importancia", 1),
                }
            )

            if len(contexto) >= limite_final:
                break

        return {
            "memories": contexto,
            "total_included": len(contexto),
        }

    def resumen_para_voz(
        self,
        *,
        limite: int = 10,
    ) -> str:
        """
        Genera un resumen básico de recuerdos para depuración o voz.
        """

        recuerdos = self.listar(
            limite=limite,
        )

        if not recuerdos:
            return "Todavía no tengo recuerdos guardados."

        contenidos = [
            recuerdo.get("contenido", "").strip()
            for recuerdo in recuerdos
            if recuerdo.get("contenido")
        ]

        if not contenidos:
            return "Todavía no tengo recuerdos guardados."

        return "Recuerdo que " + "; ".join(contenidos) + "."

    def estadisticas(self) -> Dict[str, Any]:
        """
        Devuelve información general de la memoria.
        """

        with self._lock:
            memoria = self._leer_memoria()

        activos = [
            recuerdo
            for recuerdo in memoria.get("recuerdos", [])
            if recuerdo.get("activo", True)
        ]

        por_categoria: Dict[str, int] = {}

        for recuerdo in activos:
            categoria = recuerdo.get("categoria", "dato")
            por_categoria[categoria] = (
                por_categoria.get(categoria, 0) + 1
            )

        return {
            "total_activos": len(activos),
            "total_historico": len(
                memoria.get("recuerdos", [])
            ),
            "por_categoria": por_categoria,
            "ruta": str(self.memory_path),
        }

    # ------------------------------------------------------------------
    # ARCHIVO Y PERSISTENCIA
    # ------------------------------------------------------------------

    def _asegurar_archivo(self) -> None:
        """
        Crea el directorio y archivo inicial cuando no existen.
        """

        try:
            self.memory_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            if not self.memory_path.exists():
                self._guardar_memoria(
                    self._estructura_inicial()
                )

        except Exception as error:
            logger.exception(
                "No se pudo preparar el archivo de memoria: %s",
                error,
            )
            raise

    def _leer_memoria(self) -> Dict[str, Any]:
        """
        Lee y valida el archivo JSON.
        """

        try:
            with self.memory_path.open(
                "r",
                encoding="utf-8",
            ) as archivo:
                contenido = json.load(archivo)

            if not isinstance(contenido, dict):
                raise ValueError(
                    "El archivo de memoria no contiene un objeto JSON."
                )

            recuerdos = contenido.get("recuerdos")

            if not isinstance(recuerdos, list):
                contenido["recuerdos"] = []

            return contenido

        except FileNotFoundError:
            memoria = self._estructura_inicial()
            self._guardar_memoria(memoria)
            return memoria

        except json.JSONDecodeError as error:
            logger.error(
                "El archivo de memoria está dañado: %s",
                error,
            )

            respaldo = self.memory_path.with_suffix(
                ".corrupt.json"
            )

            try:
                self.memory_path.replace(respaldo)
            except Exception:
                logger.exception(
                    "No se pudo respaldar el archivo dañado."
                )

            memoria = self._estructura_inicial()
            self._guardar_memoria(memoria)

            return memoria

    def _guardar_memoria(
        self,
        memoria: Dict[str, Any],
    ) -> None:
        """
        Guarda el JSON de forma atómica para reducir riesgo de corrupción.
        """

        memoria["actualizado_en"] = self._fecha_actual()

        archivo_temporal = self.memory_path.with_suffix(
            ".tmp"
        )

        with archivo_temporal.open(
            "w",
            encoding="utf-8",
        ) as archivo:
            json.dump(
                memoria,
                archivo,
                ensure_ascii=False,
                indent=2,
            )

        archivo_temporal.replace(
            self.memory_path
        )

    @staticmethod
    def _estructura_inicial() -> Dict[str, Any]:
        ahora = MemoryService._fecha_actual()

        return {
            "version": 1,
            "creado_en": ahora,
            "actualizado_en": ahora,
            "recuerdos": [],
        }

    # ------------------------------------------------------------------
    # BÚSQUEDA Y NORMALIZACIÓN
    # ------------------------------------------------------------------

    def _buscar_duplicado(
        self,
        *,
        memoria: Dict[str, Any],
        contenido: str,
    ) -> Optional[Dict[str, Any]]:
        contenido_normalizado = self._normalizar_texto(
            contenido
        )

        palabras_nuevas = set(
            contenido_normalizado.split()
        )

        for recuerdo in memoria.get("recuerdos", []):
            if not recuerdo.get("activo", True):
                continue

            contenido_existente = self._normalizar_texto(
                recuerdo.get("contenido", "")
            )

            if contenido_existente == contenido_normalizado:
                return recuerdo

            palabras_existentes = set(
                contenido_existente.split()
            )

            if not palabras_nuevas or not palabras_existentes:
                continue

            interseccion = palabras_nuevas & palabras_existentes
            union = palabras_nuevas | palabras_existentes

            similitud = (
                len(interseccion) / len(union)
                if union
                else 0
            )

            if similitud >= 0.85:
                return recuerdo

        return None

    def _calcular_relevancia(
        self,
        *,
        recuerdo: Dict[str, Any],
        consulta: str,
        palabras_consulta: set[str],
    ) -> float:
        contenido = self._normalizar_texto(
            recuerdo.get("contenido", "")
        )

        categoria = self._normalizar_texto(
            recuerdo.get("categoria", "")
        )

        etiquetas = " ".join(
            self._normalizar_texto(etiqueta)
            for etiqueta in recuerdo.get("etiquetas", [])
        )

        texto_total = f"{contenido} {categoria} {etiquetas}".strip()

        puntuacion = 0.0

        if consulta in contenido:
            puntuacion += 10

        if consulta in etiquetas:
            puntuacion += 6

        if consulta == categoria:
            puntuacion += 4

        palabras_recuerdo = set(
            texto_total.split()
        )

        coincidencias = (
            palabras_consulta & palabras_recuerdo
        )

        puntuacion += len(coincidencias) * 2

        importancia = int(
            recuerdo.get("importancia", 1)
        )

        puntuacion += importancia * 0.25

        return puntuacion

    @classmethod
    def _normalizar_categoria(
        cls,
        categoria: Optional[str],
    ) -> str:
        categoria_normalizada = cls._normalizar_texto(
            categoria or "dato"
        )

        equivalencias = {
            "preferencias": "preferencia",
            "gustos": "preferencia",
            "gusto": "preferencia",
            "habitos": "habito",
            "hábito": "habito",
            "hábitos": "habito",
            "personas": "persona",
            "laboral": "trabajo",
            "viajes": "viaje",
            "deportes": "deporte",
            "salud": "salud",
            "eventos": "evento",
            "proyectos": "proyecto",
            "datos": "dato",
        }

        categoria_normalizada = equivalencias.get(
            categoria_normalizada,
            categoria_normalizada,
        )

        if categoria_normalizada not in cls.CATEGORIAS_VALIDAS:
            return "otro"

        return categoria_normalizada

    @staticmethod
    def _normalizar_importancia(
        importancia: int,
    ) -> int:
        try:
            numero = int(importancia)
        except (TypeError, ValueError):
            numero = 3

        return max(1, min(numero, 5))

    @staticmethod
    def _limpiar_contenido(
        contenido: str,
    ) -> str:
        texto = str(contenido or "").strip()

        texto = re.sub(
            r"\s+",
            " ",
            texto,
        )

        return texto[:1_000]

    @classmethod
    def _limpiar_etiquetas(
        cls,
        etiquetas: List[str],
    ) -> List[str]:
        resultado = []
        vistas = set()

        for etiqueta in etiquetas[:20]:
            texto = str(etiqueta).strip()

            if not texto:
                continue

            clave = cls._normalizar_texto(texto)

            if clave in vistas:
                continue

            vistas.add(clave)
            resultado.append(texto[:80])

        return resultado

    @classmethod
    def _combinar_etiquetas(
        cls,
        primeras: List[str],
        segundas: List[str],
    ) -> List[str]:
        return cls._limpiar_etiquetas(
            list(primeras) + list(segundas)
        )

    @staticmethod
    def _normalizar_texto(
        texto: str,
    ) -> str:
        texto = str(texto or "").lower().strip()

        texto = unicodedata.normalize(
            "NFD",
            texto,
        )

        texto = "".join(
            caracter
            for caracter in texto
            if unicodedata.category(caracter) != "Mn"
        )

        texto = re.sub(
            r"[^a-z0-9ñ\s]",
            " ",
            texto,
        )

        texto = re.sub(
            r"\s+",
            " ",
            texto,
        )

        return texto.strip()

    # ------------------------------------------------------------------
    # UTILIDADES
    # ------------------------------------------------------------------

    @staticmethod
    def _fecha_actual() -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()

    @staticmethod
    def _leer_entero_entorno(
        nombre: str,
        *,
        default: int,
        minimum: int,
        maximum: int,
    ) -> int:
        valor = os.getenv(nombre)

        if valor is None:
            return default

        try:
            numero = int(valor)
        except (TypeError, ValueError):
            return default

        return max(
            minimum,
            min(numero, maximum),
        )