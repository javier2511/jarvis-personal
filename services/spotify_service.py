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
        cache_path = os.getenv(
            "SPOTIFY_CACHE_PATH",
            "/tmp/spotify_cache"
        )

        self.auth_manager = SpotifyOAuth(
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
            scope=SCOPES,
            cache_handler=CacheFileHandler(
                cache_path=cache_path
            ),
            open_browser=False
        )

    def obtener_url_autorizacion(self):
        return self.auth_manager.get_authorize_url()

    def procesar_callback(self, codigo):
        self.auth_manager.get_access_token(
            code=codigo,
            check_cache=False
        )

    def cliente(self):
        token_info = self.auth_manager.get_cached_token()

        if not token_info:
            raise RuntimeError(
                "Spotify no está conectado. "
                "Abre /spotify/login para autorizarlo."
            )

        return spotipy.Spotify(
            auth_manager=self.auth_manager
        )

    def dispositivos(self):
        spotify = self.cliente()
        return spotify.devices().get("devices", [])

    def dispositivo_activo(self):
        dispositivos = self.dispositivos()

        if not dispositivos:
            raise RuntimeError(
                "No encontré dispositivos de Spotify. "
                "Abre Spotify en tu iPhone, Alexa o PC."
            )

        activos = [
            dispositivo
            for dispositivo in dispositivos
            if dispositivo.get("is_active")
        ]

        return activos[0] if activos else dispositivos[0]

    def reproducir(self):
        spotify = self.cliente()
        dispositivo = self.dispositivo_activo()

        spotify.start_playback(
            device_id=dispositivo["id"]
        )

        return (
            f"Reproduciendo Spotify en "
            f"{dispositivo['name']}."
        )

    def reproducir_busqueda(self, busqueda):
        spotify = self.cliente()
        dispositivo = self.dispositivo_activo()

        resultados = spotify.search(
            q=busqueda,
            type="track,artist,playlist",
            limit=1
        )

        canciones = resultados.get(
            "tracks",
            {}
        ).get("items", [])

        if canciones:
            cancion = canciones[0]

            spotify.start_playback(
                device_id=dispositivo["id"],
                uris=[cancion["uri"]]
            )

            artista = cancion["artists"][0]["name"]

            return (
                f"Reproduciendo {cancion['name']} "
                f"de {artista}."
            )

        artistas = resultados.get(
            "artists",
            {}
        ).get("items", [])

        if artistas:
            artista = artistas[0]

            spotify.start_playback(
                device_id=dispositivo["id"],
                context_uri=artista["uri"]
            )

            return (
                f"Reproduciendo música de "
                f"{artista['name']}."
            )

        playlists = resultados.get(
            "playlists",
            {}
        ).get("items", [])

        if playlists:
            playlist = playlists[0]

            spotify.start_playback(
                device_id=dispositivo["id"],
                context_uri=playlist["uri"]
            )

            return (
                f"Reproduciendo la playlist "
                f"{playlist['name']}."
            )

        return f"No encontré resultados para {busqueda}."

    def pausar(self):
        spotify = self.cliente()
        spotify.pause_playback()

        return "Spotify pausado."

    def siguiente(self):
        spotify = self.cliente()
        spotify.next_track()

        return "Siguiente canción."

    def anterior(self):
        spotify = self.cliente()
        spotify.previous_track()

        return "Canción anterior."

    def cancion_actual(self):
        spotify = self.cliente()
        actual = spotify.current_playback()

        if not actual or not actual.get("item"):
            return "No hay una canción reproduciéndose."

        cancion = actual["item"]["name"]
        artista = actual["item"]["artists"][0]["name"]

        return f"Está sonando {cancion}, de {artista}."