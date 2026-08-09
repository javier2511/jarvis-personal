const reactorButton = document.getElementById("reactorButton");
const statusText = document.getElementById("status");

const userText = document.getElementById("userText");
const jarvisText = document.getElementById("jarvisText");

const userState = document.getElementById("userState");
const jarvisState = document.getElementById("jarvisState");

const jarvisAudio =
    document.getElementById("jarvisAudio");

const textCommand =
    document.getElementById("textCommand");

const sendCommand =
    document.getElementById("sendCommand");

const silentMode =
    document.getElementById("silentMode");


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
            Cada nuevo comando limpia cualquier
            navegación anterior.
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
            "Revisa el permiso del micrófono y vuelve a intentarlo.";

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
   DESBLOQUEAR AUDIO
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
            "El navegador no permitió desbloquear audio:",
            error
        );
    }
}


/* =========================================================
   PREPARAR ACCIONES
========================================================= */

function prepareActions(actions) {

    pendingActions =
        Array.isArray(actions)
            ? actions
            : [];

    const accionURL =
        pendingActions.find(
            accion =>
                accion &&
                accion.tipo === "abrir_url" &&
                accion.url
        );

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
}


/* =========================================================
   PROCESAR COMANDO DE VOZ
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
            Preparamos Maps y demás acciones ANTES
            de reproducir la voz.
        */
        prepareActions(data.acciones);


        userText.textContent =
            data.usuario ||
            "No pude transcribir el audio.";

        jarvisText.textContent =
            data.resultado ||
            "No pude generar una respuesta.";


        /*
            Si activaste modo silencioso también aplica
            aunque hayas usado el micrófono.
        */
        if (
            silentMode &&
            silentMode.checked
        ) {

            showSilentResult();
            return;
        }


        try {

            await playJarvisVoice(
                data.resultado
            );

        } catch (voiceError) {

            console.error(
                "El comando funcionó, pero falló la voz:",
                voiceError
            );

            showResultWithoutVoice();
        }

    } catch (error) {

        console.error(error);

        jarvisText.textContent =
            "Ocurrió un problema procesando el audio.";

        pendingActions = [];
        pendingNavigationUrl = null;

        setState("idle");

    } finally {

        isProcessing = false;
        audioChunks = [];
    }
}


/* =========================================================
   COMANDOS ESCRITOS
========================================================= */

async function processTextCommand() {

    if (!textCommand) {
        return;
    }

    const comando =
        textCommand.value.trim();

    if (!comando || isProcessing) {
        return;
    }


    /*
        Evitamos que quede una ruta anterior pendiente.
    */
    pendingActions = [];
    pendingNavigationUrl = null;

    isProcessing = true;


    userText.textContent =
        comando;

    jarvisText.textContent =
        "Procesando comando...";

    userState.textContent =
        "ENVIADO";

    jarvisState.textContent =
        "PROCESANDO";

    statusText.textContent =
        "Analizando comando...";

    reactorButton.classList.remove(
        "is-listening",
        "is-speaking"
    );

    reactorButton.classList.add(
        "is-thinking"
    );


    /*
        Limpiamos la caja después de mandar.
    */
    textCommand.value = "";


    try {

        const response =
            await fetch(
                "/comando",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        texto: comando
                    })
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
            Misma lógica que los comandos de voz.
        */
        prepareActions(
            data.acciones
        );


        userText.textContent =
            data.usuario ||
            comando;


        jarvisText.textContent =
            data.resultado ||
            "No pude generar una respuesta.";


        userState.textContent =
            "COMPLETADO";


        /*
            MODO OFICINA

            Jarvis responde únicamente en pantalla.
        */
        if (
            silentMode &&
            silentMode.checked
        ) {

            showSilentResult();
            return;
        }


        /*
            Si silencioso está apagado,
            Jarvis también responde hablando.
        */
        try {

            await unlockAudio();

            await playJarvisVoice(
                data.resultado
            );

        } catch (voiceError) {

            console.error(
                "El comando escrito funcionó, pero falló la voz:",
                voiceError
            );

            showResultWithoutVoice();
        }


    } catch (error) {

        console.error(error);

        jarvisText.textContent =
            "Ocurrió un problema procesando el comando escrito.";

        pendingActions = [];
        pendingNavigationUrl = null;

        setState("idle");

    } finally {

        isProcessing = false;
    }
}


/* =========================================================
   RESULTADO SILENCIOSO
========================================================= */

function showSilentResult() {

    reactorButton.classList.remove(
        "is-listening",
        "is-thinking",
        "is-speaking"
    );

    userState.textContent =
        "COMPLETADO";


    if (pendingNavigationUrl) {

        statusText.textContent =
            "Ruta lista · Toca el reactor para abrir Maps";

        jarvisState.textContent =
            "RUTA LISTA";

        return;
    }


    statusText.textContent =
        "Respuesta lista · Modo silencioso";

    jarvisState.textContent =
        "LISTO";
}


/* =========================================================
   RESULTADO SIN AUDIO
========================================================= */

function showResultWithoutVoice() {

    reactorButton.classList.remove(
        "is-listening",
        "is-thinking",
        "is-speaking"
    );


    if (pendingNavigationUrl) {

        statusText.textContent =
            "Ruta lista · Toca el reactor para abrir Maps";

        jarvisState.textContent =
            "RUTA LISTA";

        return;
    }


    statusText.textContent =
        "Respuesta lista";

    jarvisState.textContent =
        "RESPUESTA SIN AUDIO";
}


/* =========================================================
   VOZ DE JARVIS
========================================================= */

async function playJarvisVoice(text) {

    if (!text) {

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
        Cuando Jarvis termina de hablar.
    */
    jarvisAudio.onended = () => {

        if (currentAudioUrl) {

            URL.revokeObjectURL(
                currentAudioUrl
            );

            currentAudioUrl = null;
        }


        /*
            Conservamos exactamente la lógica que
            hizo funcionar Maps en iPhone.
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


        setState("idle");
    };


    jarvisAudio.onerror = () => {

        console.error(
            "No se pudo reproducir el audio.",
            jarvisAudio.error
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
   BOTÓN ENVIAR
========================================================= */

if (sendCommand) {

    sendCommand.addEventListener(
        "click",
        () => {
            processTextCommand();
        }
    );
}


/* =========================================================
   ENTER PARA ENVIAR
========================================================= */

if (textCommand) {

    textCommand.addEventListener(
        "keydown",
        event => {

            if (event.key === "Enter") {

                event.preventDefault();

                processTextCommand();
            }
        }
    );
}


/* =========================================================
   MODO SILENCIOSO
========================================================= */

if (silentMode) {

    silentMode.addEventListener(
        "change",
        () => {

            if (silentMode.checked) {

                statusText.textContent =
                    "Modo silencioso activo · Puedes escribir a Jarvis";

                return;
            }


            statusText.textContent =
                "Modo voz activo · Toca el reactor para hablar";
        }
    );
}


/* =========================================================
   BOTÓN / REACTOR
========================================================= */

reactorButton.addEventListener(
    "click",
    async () => {

        /*
            PRIORIDAD #1

            Si existe una ruta pendiente,
            el reactor abre Maps.

            Esto conserva el arreglo necesario
            para Safari/iPhone.
        */
        if (pendingNavigationUrl) {

            const url =
                pendingNavigationUrl;


            pendingNavigationUrl = null;
            pendingActions = [];


            /*
                Navegación directamente desde el click
                del usuario.
            */
            window.location.href = url;

            return;
        }


        /*
            Funcionamiento normal de voz.
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