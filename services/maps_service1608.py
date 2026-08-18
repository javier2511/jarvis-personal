from urllib.parse import quote


class MapsService:

    def generar_url(self, destino, modo="driving"):

        return (
            "https://www.google.com/maps/dir/?api=1"
            f"&destination={quote(destino)}"
            f"&travelmode={modo}"
        )

    def abrir_ruta(self, destino, modo="driving"):

        return {
            "texto": f"Abriendo la ruta hacia {destino}.",
            "acciones": [
                {
                    "tipo": "abrir_url",
                    "url": self.generar_url(destino, modo)
                }
            ]
        }

    def abrir_lugar(self, lugar):

        return {
            "texto": f"Buscando {lugar}.",
            "acciones": [
                {
                    "tipo": "abrir_url",
                    "url": (
                        "https://www.google.com/maps/search/?api=1&query="
                        + quote(lugar)
                    )
                }
            ]
        }