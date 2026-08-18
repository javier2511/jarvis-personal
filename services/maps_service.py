from urllib.parse import quote

from services.places_service import PlacesService


class MapsService:

    def __init__(self):
        self.places = PlacesService()

    def resolver_destino(self, destino):
        destino = str(destino or "").strip()
        return self.places.resolver(destino) or destino

    def generar_url(self, destino, modo="driving"):
        destino_resuelto = self.resolver_destino(destino)
        return (
            "https://www.google.com/maps/dir/?api=1"
            f"&destination={quote(destino_resuelto)}"
            f"&travelmode={modo}"
        )

    def abrir_ruta(self, destino, modo="driving"):
        destino_resuelto = self.resolver_destino(destino)
        texto = destino if destino_resuelto == destino else f"{destino} ({destino_resuelto})"
        return {
            "texto": f"Abriendo la ruta hacia {texto}.",
            "acciones": [
                {"tipo": "abrir_url", "url": self.generar_url(destino, modo)}
            ]
        }

    def abrir_lugar(self, lugar):
        lugar_resuelto = self.resolver_destino(lugar)
        texto = lugar if lugar_resuelto == lugar else f"{lugar} ({lugar_resuelto})"
        return {
            "texto": f"Buscando {texto}.",
            "acciones": [
                {
                    "tipo": "abrir_url",
                    "url": (
                        "https://www.google.com/maps/search/?api=1&query="
                        + quote(lugar_resuelto)
                    )
                }
            ]
        }
