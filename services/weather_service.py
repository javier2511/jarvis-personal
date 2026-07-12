import requests


class WeatherService:

    def clima_actual(self, ciudad="Ciudad de México"):

        try:

            url = (
                "https://wttr.in/"
                + ciudad
                + "?format=j1"
            )

            respuesta = requests.get(
                url,
                timeout=5
            )

            datos = respuesta.json()

            actual = datos["current_condition"][0]

            temperatura = int(
                actual["temp_C"]
            )

            sensacion = int(
                actual["FeelsLikeC"]
            )

            lluvia = float(
                actual["precipMM"]
            )

            descripcion = actual["weatherDesc"][0]["value"]


            mensaje = (
                f"El clima actual en {ciudad} es "
                f"{descripcion}, "
                f"con {temperatura} grados. "
            )


            if sensacion <= 15:
                mensaje += (
                    "La sensación es fresca, "
                    "te recomiendo llevar chamarra. "
                )

            elif temperatura >= 28:
                mensaje += (
                    "Hace calor, mantente hidratado. "
                )


            if lluvia > 0:
                mensaje += (
                    "Parece que puede llover, "
                    "considera llevar paraguas. "
                )

            else:
                mensaje += (
                    "No parece que vaya a llover por ahora. "
                )


            return mensaje


        except Exception as error:

            return (
                "No pude consultar el clima. "
                f"Error: {error}"
            )