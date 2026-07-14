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



function setState(state) {
    reactorButton.classList.remove(
        "is-listening",
        "is-thinking",
        "is-speaking"
    );

    if (state === "listening") {
        reactorButton.classList.add("is-listening");

        statusText.textContent = "Escuchando · Toca para terminar";
        userState.textContent = "GRABANDO";
        jarvisState.textContent = "ESPERANDO";

        return;
    }

    if (state === "thinking") {
        reactorButton.classList.add("is-thinking");

        statusText.textContent = "Analizando comando...";
        userState.textContent = "RECIBIDO";
        jarvisState.textContent = "PROCESANDO";

        return;
    }

    if (state === "speaking") {
        reactorButton.classList.add("is-speaking");

        statusText.textContent = "Jarvis está respondiendo";
        userState.textContent = "COMPLETADO";
        jarvisState.textContent = "HABLANDO";

        return;
    }

    statusText.textContent = "Toca el reactor para hablar";
    userState.textContent = "ESPERANDO";
    jarvisState.textContent = "LISTO";
}

function getSupportedMimeType() {
    const types = [
        "audio/mp4",
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/ogg;codecs=opus"
    ];

    return types.find(type => MediaRecorder.isTypeSupported(type)) || "";
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

async function startRecording() {
    if (isProcessing) {
        return;
    }

    try {
        if (responseAudio) {
            responseAudio.pause();
            responseAudio = null;
        }

        mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: true
        });

        const mimeType = getSupportedMimeType();

        mediaRecorder = mimeType
            ? new MediaRecorder(mediaStream, { mimeType })
            : new MediaRecorder(mediaStream);

        audioChunks = [];

        mediaRecorder.addEventListener("dataavailable", event => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        });

        mediaRecorder.addEventListener("stop", processRecording);

        mediaRecorder.start();

        isRecording = true;

        userText.textContent = "Escuchando tu comando...";
        jarvisText.textContent = "Procesaré el audio cuando vuelvas a tocar el reactor.";

        setState("listening");

    } catch (error) {
        console.error(error);

        userText.textContent = "No se pudo acceder al micrófono.";
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
        .forEach(track => track.stop());

    mediaStream = null;
}

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

async function processRecording() {
    try {
        const mimeType =
            mediaRecorder.mimeType ||
            audioChunks[0]?.type ||
            "audio/webm";

        const extension = getAudioExtension(mimeType);

        const audioBlob = new Blob(audioChunks, {
            type: mimeType
        });

        if (audioBlob.size === 0) {
            throw new Error("El audio está vacío.");
        }

        const formData = new FormData();

        formData.append(
            "audio",
            audioBlob,
            `comando.${extension}`
        );

        const response = await fetch("/audio", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error(
                `Error del servidor: ${response.status}`
            );
        }

        const data = await response.json();

        userText.textContent =
            data.usuario || "No pude transcribir el audio.";

        jarvisText.textContent =
            data.resultado || "No pude generar una respuesta.";

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

            statusText.textContent =
                "Comando completado";
        }

    } catch (error) {
        console.error(error);

        jarvisText.textContent =
            "Ocurrió un problema procesando el audio. Revisa la terminal de Jarvis.";

        setState("idle");

    } finally {
        isProcessing = false;
        audioChunks = [];
    }
}

async function playJarvisVoice(text) {
    if (!text) {
        setState("idle");
        return;
    }

    setState("speaking");

    const response = await fetch("/voz", {
        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({
            texto: text
        })
    });

    if (!response.ok) {
        throw new Error(
            `Error generando voz: ${response.status}`
        );
    }

    const audioBlob = await response.blob();

    if (!audioBlob.size) {
        throw new Error(
            "El servidor devolvió audio vacío."
        );
    }

    if (currentAudioUrl) {
        URL.revokeObjectURL(currentAudioUrl);
    }

    currentAudioUrl =
        URL.createObjectURL(audioBlob);

    jarvisAudio.pause();
    jarvisAudio.src = currentAudioUrl;
    jarvisAudio.load();
    jarvisAudio.volume = 1;
    jarvisAudio.muted = false;

    jarvisAudio.onended = () => {
        if (currentAudioUrl) {
            URL.revokeObjectURL(
                currentAudioUrl
            );

            currentAudioUrl = null;
        }

        setState("idle");
    };

    jarvisAudio.onerror = () => {
        console.error(
            "Safari no pudo reproducir el audio.",
            jarvisAudio.error
        );

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

        jarvisText.textContent +=
            "\n\nToca nuevamente el reactor para habilitar la voz.";

        jarvisState.textContent =
            "AUDIO BLOQUEADO";

        setState("idle");

        throw error;
    }
}

reactorButton.addEventListener(
    "click",
    async () => {

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
setState("idle");

async function ejecutarAccionDespues(resultado) {
    if (!resultado) {
        return;
    }

    try {
        const response = await fetch("/accion-despues", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                resultado: resultado
            })
        });

        const data = await response.json();

        if (!data.ok) {
            console.error(
                "Error en acción posterior:",
                data.error
            );
        }

    } catch (error) {
        console.error(
            "No se pudo ejecutar la acción posterior:",
            error
        );
    }
}