import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()


class SpotifyService:

    def __init__(self):
        self.spotify = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=os.getenv("SPOTIFY_CLIENT_ID"),
                client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
                redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
                scope="user-read-playback-state user-modify-playback-state user-read-currently-playing"
            )
        )

    def reproducir(self):
        dispositivos = self.spotify.devices()["devices"]

        if not dispositivos:
            return "No encontré dispositivos activos de Spotify. Abre Spotify en tu iPhone, PC o CarPlay primero."

        dispositivo_id = dispositivos[0]["id"]

        self.spotify.start_playback(device_id=dispositivo_id)

        return f"Reproduciendo Spotify en {dispositivos[0]['name']}."

    def pausar(self):
        self.spotify.pause_playback()
        return "Spotify pausado."

    def siguiente(self):
        self.spotify.next_track()
        return "Siguiente canción."

    def anterior(self):
        self.spotify.previous_track()
        return "Canción anterior."

    def cancion_actual(self):
        actual = self.spotify.current_playback()
    
    

        if not actual or not actual.get("item"):
            return "No hay una canción reproduciéndose."

        cancion = actual["item"]["name"]
        artista = actual["item"]["artists"][0]["name"]

        return f"Está sonando {cancion}, de {artista}."
    
    def reproducir_busqueda(self, busqueda):
        dispositivos = self.spotify.devices()["devices"]

        if not dispositivos:
            return "No encontré dispositivos activos de Spotify. Abre Spotify primero."

        dispositivo_id = dispositivos[0]["id"]

        resultados = self.spotify.search(
            q=busqueda,
            type="artist,track,playlist",
            limit=1
        )

        if resultados["artists"]["items"]:
            artista = resultados["artists"]["items"][0]
            uri = artista["uri"]

            self.spotify.start_playback(
                device_id=dispositivo_id,
                context_uri=uri
            )

            return f"Reproduciendo música de {artista['name']}."

        if resultados["tracks"]["items"]:
            cancion = resultados["tracks"]["items"][0]
            uri = cancion["uri"]

            self.spotify.start_playback(
                device_id=dispositivo_id,
                uris=[uri]
            )

            return f"Reproduciendo {cancion['name']}."

        if resultados["playlists"]["items"]:
            playlist = resultados["playlists"]["items"][0]
            uri = playlist["uri"]

            self.spotify.start_playback(
                device_id=dispositivo_id,
                context_uri=uri
            )

            return f"Reproduciendo la playlist {playlist['name']}."

        return f"No encontré resultados para {busqueda}."