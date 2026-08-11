import os
from pathlib import Path

import spotipy
from spotipy.cache_handler import CacheFileHandler
from spotipy.oauth2 import SpotifyOAuth


SCOPES = (
    "user-read-playback-state "
    "user-modify-playback-state "
    "user-read-currently-playing"
)


class SpotifyService:

    def __init__(self):
        self.cache_path = os.getenv(
            "SPOTIFY_CACHE_PATH",
            "/app/data/spotify_cache"
        )

        self.cache_handler = CacheFileHandler(
            cache_path=self.cache_path
        )

        self.auth_manager = SpotifyOAuth(
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
            scope=SCOPES,
            cache_handler=self.cache_handler,
            open_browser=False
        )
    def obtener_url_autorizacion(self):
        return self.auth_manager.get_authorize_url()

    def procesar_callback(self, codigo):
        token_info = self.auth_manager.get_access_token(
            code=codigo,
            check_cache=False
        )

        if not token_info:
            raise RuntimeError(
                "Spotify no devolvió un token."
            )

        # Guardado explícito en el volumen de Railway
        self.cache_handler.save_token_to_cache(
            token_info
        )

        return token_info

    def cliente(self):
        token_info = self.cache_handler.get_cached_token()

        if not token_info:
            raise RuntimeError(
                "Spotify no está conectado. "
                "Abre /spotify/login para autorizarlo."
            )

        if self.auth_manager.is_token_expired(token_info):
            refresh_token = token_info.get("refresh_token")

            if not refresh_token:
                raise RuntimeError(
                    "El token de Spotify expiró y no tiene refresh token. "
                    "Vuelve a conectar Spotify."
                )

            token_info = self.auth_manager.refresh_access_token(
                refresh_token
            )

            self.cache_handler.save_token_to_cache(
                token_info
            )

        return spotipy.Spotify(
            auth=token_info["access_token"]
        )

    def esta_conectado(self):
        token_info = self.cache_handler.get_cached_token()

        return bool(
            token_info
            and token_info.get("access_token")
        )
    def dispositivos(self):
        spotify = self.cliente()
        return spotify.devices().get("devices", [])

    def _playback_actual(self):
        spotify = self.cliente()
        return spotify.current_playback()

    def dispositivo_activo(self):
        dispositivos = self.dispositivos()

        if not dispositivos:
            raise RuntimeError(
                "No encontré dispositivos de Spotify. "
                "Abre Spotify en tu iPhone, Alexa o PC y vuelve a intentarlo."
            )

        activos = [
            dispositivo
            for dispositivo in dispositivos
            if dispositivo.get("is_active")
        ]

        if activos:
            return activos[0]

        # Si Spotify recuerda un dispositivo restringido, evitamos elegirlo
        # cuando existe otra opción controlable.
        controlables = [
            dispositivo
            for dispositivo in dispositivos
            if not dispositivo.get("is_restricted")
        ]

        if controlables:
            return controlables[0]

        return dispositivos[0]

    def _asegurar_dispositivo(self):
        dispositivo = self.dispositivo_activo()

        if dispositivo.get("is_restricted"):
            raise RuntimeError(
                f"Spotify detectó {dispositivo.get('name', 'un dispositivo')}, "
                "pero no permite controlarlo desde Jarvis."
            )

        return dispositivo

    def reproducir(self):
        spotify = self.cliente()
        dispositivo = self._asegurar_dispositivo()

        spotify.start_playback(
            device_id=dispositivo["id"]
        )

        return (
            f"Reanudando Spotify en "
            f"{dispositivo['name']}."
        )

    def _buscar_playlist_usuario(self, spotify, busqueda):
        """
        Busca primero entre playlists accesibles por el usuario.

        Esto mejora frases como:
        'pon mi playlist de gym'.
        """
        texto = (busqueda or "").strip().lower()

        for prefijo in (
            "mi playlist de ",
            "mi playlist ",
            "playlist de ",
            "playlist ",
        ):
            if texto.startswith(prefijo):
                texto = texto[len(prefijo):].strip()
                break

        if not texto:
            return None

        try:
            pagina = spotify.current_user_playlists(limit=50)

            while pagina:
                for playlist in pagina.get("items", []):
                    if not playlist:
                        continue

                    nombre = (playlist.get("name") or "").strip().lower()

                    if texto == nombre or texto in nombre or nombre in texto:
                        return playlist

                if pagina.get("next"):
                    pagina = spotify.next(pagina)
                else:
                    break

        except Exception:
            # La búsqueda general seguirá funcionando aunque este intento falle.
            return None

        return None

    def reproducir_busqueda(self, busqueda):
        spotify = self.cliente()
        dispositivo = self._asegurar_dispositivo()
        busqueda = (busqueda or "").strip()

        if not busqueda:
            return "Necesito saber qué quieres reproducir."

        # 1) Si el usuario habla de "mi playlist", priorizamos sus playlists.
        if "playlist" in busqueda.lower():
            playlist_usuario = self._buscar_playlist_usuario(
                spotify,
                busqueda,
            )

            if playlist_usuario:
                spotify.start_playback(
                    device_id=dispositivo["id"],
                    context_uri=playlist_usuario["uri"],
                )

                return (
                    f"Reproduciendo tu playlist "
                    f"{playlist_usuario['name']}."
                )

        # 2) Hacemos búsquedas separadas. Spotify no garantiza que el primer
        # resultado combinado represente la intención del usuario.
        canciones = spotify.search(
            q=busqueda,
            type="track",
            limit=5,
        ).get("tracks", {}).get("items", [])

        artistas = spotify.search(
            q=busqueda,
            type="artist",
            limit=5,
        ).get("artists", {}).get("items", [])

        playlists = spotify.search(
            q=busqueda,
            type="playlist",
            limit=5,
        ).get("playlists", {}).get("items", [])

        consulta = busqueda.lower()

        # Si parece una petición de playlist, género, mood o música general,
        # preferimos contexto continuo antes que una canción aislada.
        pistas_contexto = (
            "playlist",
            "música",
            "musica",
            "para ",
            "tranquila",
            "relajante",
            "gym",
            "entrenar",
            "correr",
            "concentrarme",
            "trabajar",
            "fiesta",
        )

        if any(pista in consulta for pista in pistas_contexto):
            if playlists:
                playlist = playlists[0]

                spotify.start_playback(
                    device_id=dispositivo["id"],
                    context_uri=playlist["uri"],
                )

                return (
                    f"Reproduciendo la playlist "
                    f"{playlist['name']}."
                )

        # Si la consulta coincide claramente con un artista, reproducimos
        # su contexto en lugar de una sola canción encontrada por casualidad.
        if artistas:
            artista = artistas[0]
            nombre_artista = (artista.get("name") or "").lower()

            if (
                consulta == nombre_artista
                or nombre_artista in consulta
            ):
                spotify.start_playback(
                    device_id=dispositivo["id"],
                    context_uri=artista["uri"],
                )

                return (
                    f"Reproduciendo música de "
                    f"{artista['name']}."
                )

        # Para títulos o búsquedas concretas, priorizamos track.
        if canciones:
            cancion = canciones[0]

            spotify.start_playback(
                device_id=dispositivo["id"],
                uris=[cancion["uri"]],
            )

            artistas_cancion = ", ".join(
                artista["name"]
                for artista in cancion.get("artists", [])
            )

            return (
                f"Reproduciendo {cancion['name']} "
                f"de {artistas_cancion}."
            )

        if artistas:
            artista = artistas[0]

            spotify.start_playback(
                device_id=dispositivo["id"],
                context_uri=artista["uri"],
            )

            return (
                f"Reproduciendo música de "
                f"{artista['name']}."
            )

        if playlists:
            playlist = playlists[0]

            spotify.start_playback(
                device_id=dispositivo["id"],
                context_uri=playlist["uri"],
            )

            return (
                f"Reproduciendo la playlist "
                f"{playlist['name']}."
            )

        return f"No encontré resultados para {busqueda}."

    def pausar(self):
        spotify = self.cliente()
        actual = spotify.current_playback()

        if not actual:
            return "Spotify no tiene una reproducción activa."

        if not actual.get("is_playing"):
            return "Spotify ya está pausado."

        dispositivo = self._asegurar_dispositivo()

        spotify.pause_playback(
            device_id=dispositivo["id"]
        )

        return "Spotify pausado."

    def siguiente(self):
        spotify = self.cliente()
        dispositivo = self._asegurar_dispositivo()

        spotify.next_track(
            device_id=dispositivo["id"]
        )

        return "Siguiente canción."

    def anterior(self):
        spotify = self.cliente()
        dispositivo = self._asegurar_dispositivo()

        spotify.previous_track(
            device_id=dispositivo["id"]
        )

        return "Canción anterior."

    def cancion_actual(self):
        spotify = self.cliente()
        actual = spotify.current_playback()

        if not actual or not actual.get("item"):
            return "No hay una canción reproduciéndose."

        item = actual["item"]
        cancion = item.get("name", "una canción")
        artistas = ", ".join(
            artista["name"]
            for artista in item.get("artists", [])
        )

        if actual.get("is_playing"):
            estado = "Está sonando"
        else:
            estado = "Tienes pausada"

        if artistas:
            return f"{estado} {cancion}, de {artistas}."

        return f"{estado} {cancion}."
