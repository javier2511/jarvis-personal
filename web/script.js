const reactorButton = document.getElementById("reactorButton");
const statusText = document.getElementById("status");

const userText = document.getElementById("userText");
const jarvisText = document.getElementById("jarvisText");

const userState = document.getElementById("userState");
const jarvisState = document.getElementById("jarvisState");

const jarvisAudio =
    document.getElementById("jarvisAudio");


let currentAudioUrl = null;
let audioUnlocked = false;

let mediaRecorder = null;
let mediaStream = null;
let audioChunks = [];

let isRecording = false;
let isProcessing = false;

let responseAudio = null;

/*
    Acciones recibidas desde Jarvis.
*/
let pendingActions = [];

/*
    URL pendiente de abrir.

    En iPhone/Safari necesitamos que la apertura ocurra
    directamente desde un toque del usuario.
*/
let pendingNavigationUrl = null;


/* =========================================================
   ESTADOS DE INTERFAZ
========================================================= */

function setState(state) {

    reactorButton.classList.remove(
        "is-listening",
        "is-thinking",
        "is-speaking"
    );

    if (state === "listening") {

        reactorButton.classList.add("is-listening");

        statusText.textContent =
            "Escuchando · Toca para terminar";

        userState.textContent = "GRABANDO";
        jarvisState.textContent = "ESPERANDO";

        return;
    }

    if (state === "thinking") {

        reactorButton.classList.add("is-thinking");

        statusText.textContent =
            "Analizando comando...";

        userState.textContent = "RECIBIDO";
        jarvisState.textContent = "PROCESANDO";

        return;
    }

    if (state === "speaking") {

        reactorButton.classList.add("is-speaking");

        statusText.textContent =
            "Jarvis está respondiendo";

        userState.textContent = "COMPLETADO";
        jarvisState.textContent = "HABLANDO";

        return;
    }

    statusText.textContent =
        "Toca el reactor para hablar";

    userState.textContent = "ESPERANDO";
    jarvisState.textContent = "LISTO";
}


/* =========================================================
   AUDIO
========================================================= */

function getSupportedMimeType() {

    const types = [
        "audio/mp4",
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/ogg;codecs=opus"
    ];

    return (
        types.find(
            type => MediaRecorder.isTypeSupported(type)
        ) || ""
    );
}


function getAudioExtension(mimeType) {

    if (mimeType.includes("mp4")) {
        return "m4a";
    }

    if (mimeType.includes("ogg")) {
        return "ogg";
    }

    return "webm";
}


/* =========================================================
   GRABACIÓN
========================================================= */

async function startRecording() {

    if (isProcessing) {
        return;
    }

    try {

        if (responseAudio) {
            responseAudio.pause();
            responseAudio = null;
        }

        /*
            Cada nuevo comando limpia cualquier navegación
            anterior.
        */
        pendingActions = [];
        pendingNavigationUrl = null;

        mediaStream =
            await navigator.mediaDevices.getUserMedia({
                audio: true
            });

        const mimeType =
            getSupportedMimeType();

        mediaRecorder = mimeType
            ? new MediaRecorder(
                mediaStream,
                { mimeType }
            )
            : new MediaRecorder(mediaStream);

        audioChunks = [];

        mediaRecorder.addEventListener(
            "dataavailable",
            event => {

                if (event.data.size > 0) {
                    audioChunks.push(event.data);
                }
            }
        );

        mediaRecorder.addEventListener(
            "stop",
            processRecording
        );

        mediaRecorder.start();

        isRecording = true;

        userText.textContent =
            "Escuchando tu comando...";

        jarvisText.textContent =
            "Procesaré el audio cuando vuelvas a tocar el reactor.";

        setState("listening");

    } catch (error) {

        console.error(error);

        userText.textContent =
            "No se pudo acceder al micrófono.";

        jarvisText.textContent =
            "Revisa el permiso del micrófono en Safari y vuelve a intentarlo.";

        setState("idle");
    }
}


function stopRecording() {

    if (!isRecording || !mediaRecorder) {
        return;
    }

    isRecording = false;
    isProcessing = true;

    setState("thinking");

    if (mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
    }

    stopMediaStream();
}


function stopMediaStream() {

    if (!mediaStream) {
        return;
    }

    mediaStream
        .getTracks()
        .forEach(
            track => track.stop()
        );

    mediaStream = null;
}


/* =========================================================
   DESBLOQUEAR AUDIO EN SAFARI
========================================================= */

async function unlockAudio() {

    if (audioUnlocked) {
        return;
    }

    try {

        jarvisAudio.muted = true;

        jarvisAudio.src =
            "data:audio/mp3;base64,//uQxAAAAAAAAAAAAAAAAAAAAAAASW5mbwAAAA8AAAAEAAACcQCA";

        await jarvisAudio.play();

        jarvisAudio.pause();
        jarvisAudio.currentTime = 0;
        jarvisAudio.muted = false;

        audioUnlocked = true;

    } catch (error) {

        console.warn(
            "Safari no permitió desbloquear audio:",
            error
        );
    }
}


/* =========================================================
   PROCESAR COMANDO
========================================================= */

async function processRecording() {

    try {

        const mimeType =
            mediaRecorder.mimeType ||
            audioChunks[0]?.type ||
            "audio/webm";

        const extension =
            getAudioExtension(mimeType);

        const audioBlob =
            new Blob(
                audioChunks,
                {
                    type: mimeType
                }
            );

        if (audioBlob.size === 0) {
            throw new Error(
                "El audio está vacío."
            );
        }

        const formData =
            new FormData();

        formData.append(
            "audio",
            audioBlob,
            `comando.${extension}`
        );

        const response =
            await fetch(
                "/audio",
                {
                    method: "POST",
                    body: formData
                }
            );

        if (!response.ok) {

            throw new Error(
                `Error del servidor: ${response.status}`
            );
        }

        const data =
            await response.json();


        /*
            Guardamos las acciones ANTES de reproducir
            la respuesta de Jarvis.
        */

        pendingActions =
            Array.isArray(data.acciones)
                ? data.acciones
                : [];


        /*
            Buscamos si Jarvis quiere abrir una URL.
            Maps utiliza esta acción.
        */

        const accionURL =
            pendingActions.find(
                accion =>
                    accion &&
                    accion.tipo === "abrir_url" &&
                    accion.url
            );


        /*
            IMPORTANTE:

            Esta variable debe quedar preparada ANTES
            de que Jarvis empiece a hablar.

            Así, cuando termine el audio, ya sabemos
            que existe una ruta pendiente.
        */

        pendingNavigationUrl =
            accionURL
                ? accionURL.url
                : null;


        console.log(
            "Acciones recibidas:",
            pendingActions
        );

        console.log(
            "URL pendiente:",
            pendingNavigationUrl
        );


        userText.textContent =
            data.usuario ||
            "No pude transcribir el audio.";

        jarvisText.textContent =
            data.resultado ||
            "No pude generar una respuesta.";


        /*
            Jarvis responde por voz.
        */

        try {

            await playJarvisVoice(
                data.resultado
            );

        } catch (voiceError) {

            console.error(
                "El comando funcionó, pero falló la voz:",
                voiceError
            );

            jarvisState.textContent =
                "RESPUESTA SIN AUDIO";

            /*
                Aunque falle la voz, si tenemos una
                navegación pendiente permitimos abrirla.
            */

            if (pendingNavigationUrl) {

                statusText.textContent =
                    "Ruta lista · Toca el reactor para abrir Maps";

                jarvisState.textContent =
                    "RUTA LISTA";

            } else {

                statusText.textContent =
                    "Comando completado";
            }
        }

    } catch (error) {

        console.error(error);

        jarvisText.textContent =
            "Ocurrió un problema procesando el audio. Revisa la terminal de Jarvis.";

        pendingActions = [];
        pendingNavigationUrl = null;

        setState("idle");

    } finally {

        isProcessing = false;
        audioChunks = [];
    }
}


/* =========================================================
   VOZ DE JARVIS
========================================================= */

async function playJarvisVoice(text) {

    if (!text) {

        /*
            Incluso sin texto, Maps podría tener
            una navegación pendiente.
        */

        if (pendingNavigationUrl) {

            statusText.textContent =
                "Ruta lista · Toca el reactor para abrir Maps";

            userState.textContent =
                "COMPLETADO";

            jarvisState.textContent =
                "RUTA LISTA";

            return;
        }

        setState("idle");
        return;
    }


    setState("speaking");


    const response =
        await fetch(
            "/voz",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    texto: text
                })
            }
        );


    if (!response.ok) {

        throw new Error(
            `Error generando voz: ${response.status}`
        );
    }


    const audioBlob =
        await response.blob();


    if (!audioBlob.size) {

        throw new Error(
            "El servidor devolvió audio vacío."
        );
    }


    if (currentAudioUrl) {

        URL.revokeObjectURL(
            currentAudioUrl
        );
    }


    currentAudioUrl =
        URL.createObjectURL(
            audioBlob
        );


    jarvisAudio.pause();

    jarvisAudio.src =
        currentAudioUrl;

    jarvisAudio.load();

    jarvisAudio.volume = 1;
    jarvisAudio.muted = false;


    /*
        CUANDO JARVIS TERMINA DE HABLAR
    */

    jarvisAudio.onended = () => {

        if (currentAudioUrl) {

            URL.revokeObjectURL(
                currentAudioUrl
            );

            currentAudioUrl = null;
        }


        /*
            Si tenemos una URL pendiente NO regresamos
            al estado normal.

            Mostramos claramente que el siguiente toque
            abrirá Maps.
        */

        if (pendingNavigationUrl) {

            reactorButton.classList.remove(
                "is-listening",
                "is-thinking",
                "is-speaking"
            );

            statusText.textContent =
                "Ruta lista · Toca el reactor para abrir Maps";

            userState.textContent =
                "COMPLETADO";

            jarvisState.textContent =
                "RUTA LISTA";

            return;
        }


        /*
            Comando normal.
        */

        setState("idle");
    };


    jarvisAudio.onerror = () => {

        console.error(
            "Safari no pudo reproducir el audio.",
            jarvisAudio.error
        );


        /*
            Si Maps está pendiente, mantenemos disponible
            la navegación incluso si falló el audio.
        */

        if (pendingNavigationUrl) {

            statusText.textContent =
                "Ruta lista · Toca el reactor para abrir Maps";

            userState.textContent =
                "COMPLETADO";

            jarvisState.textContent =
                "RUTA LISTA";

            return;
        }


        setState("idle");
    };


    try {

        await jarvisAudio.play();

    } catch (error) {

        console.error(
            "Error de reproducción:",
            error.name,
            error.message
        );


        if (pendingNavigationUrl) {

            statusText.textContent =
                "Ruta lista · Toca el reactor para abrir Maps";

            userState.textContent =
                "COMPLETADO";

            jarvisState.textContent =
                "RUTA LISTA";

            return;
        }


        jarvisText.textContent +=
            "\n\nToca nuevamente el reactor para habilitar la voz.";

        jarvisState.textContent =
            "AUDIO BLOQUEADO";

        setState("idle");

        throw error;
    }
}


/* =========================================================
   BOTÓN / REACTOR
========================================================= */

reactorButton.addEventListener(
    "click",
    async () => {

        /*
            PRIORIDAD #1:

            Si existe una navegación pendiente,
            este toque abre Maps.

            Esto es importante para iPhone porque Safari
            requiere una interacción directa del usuario.
        */

        if (pendingNavigationUrl) {

            const url =
                pendingNavigationUrl;


            /*
                Limpiamos primero para evitar que al volver
                de Maps el reactor intente abrir otra vez
                la misma dirección.
            */

            pendingNavigationUrl = null;
            pendingActions = [];


            /*
                Este cambio de página ocurre directamente
                dentro del evento click.

                Por eso Safari/iOS debe permitirlo.
            */

            window.location.href = url;

            return;
        }


        /*
            Funcionamiento normal del reactor.
        */

        await unlockAudio();


        if (isProcessing) {
            return;
        }


        if (isRecording) {

            stopRecording();

        } else {

            startRecording();
        }
    }
);


/* =========================================================
   ESTADO INICIAL
========================================================= */

setState("idle");