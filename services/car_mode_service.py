"""
Jarvis - Car Mode Service
=========================

Construye la bienvenida corta del modo conducción.
No abre Maps todavía: primero pregunta el destino.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from services.whoop_service import WhoopService


logger = logging.getLogger(__name__)


class CarModeService:

    def __init__(self) -> None:
        self.whoop = WhoopService()

    def _whoop_resumen(self) -> Any:
        try:
            return self.whoop.resumen_hoy()
        except Exception as error:
            logger.exception("Error consultando WHOOP en Car Mode: %s", error)
            return None

    @staticmethod
    def _texto_whoop(datos: Any) -> str:
        if not datos:
            return ""

        if isinstance(datos, str):
            texto = datos.strip()
            return texto if texto else ""

        if not isinstance(datos, dict):
            return ""

        partes = []

        recovery = (
            datos.get("recovery")
            or datos.get("recovery_score")
            or datos.get("recovery_score_percent")
        )
        sleep = (
            datos.get("sleep")
            or datos.get("sleep_performance")
            or datos.get("sleep_performance_percentage")
        )
        strain = (
            datos.get("strain")
            or datos.get("day_strain")
        )

        if recovery is not None:
            partes.append(f"tu recovery está en {recovery}")
        if sleep is not None:
            partes.append(f"tu sueño está en {sleep}")
        if strain is not None:
            partes.append(f"tu strain va en {strain}")

        if not partes:
            return ""

        if len(partes) == 1:
            return partes[0]

        return ", ".join(partes[:-1]) + " y " + partes[-1]

    def iniciar(self) -> Dict[str, Any]:
        whoop = self._whoop_resumen()
        resumen = self._texto_whoop(whoop)

        if resumen:
            texto = (
                f"Modo conducción activado. {resumen}. "
                "¿A dónde quieres ir?"
            )
        else:
            texto = (
                "Modo conducción activado. "
                "No pude consultar WHOOP en este momento. "
                "¿A dónde quieres ir?"
            )

        return {
            "texto": texto,
            "acciones": [
                {
                    "modulo": "spotify",
                    "accion": "abrir",
                    "parametros": {
                        "dispositivo": "iPhone",
                    },
                }
            ],
            "metadata": {
                "modo": "car",
                "esperando_destino": True,
            },
        }
