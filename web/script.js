const reactorButton = document.getElementById("reactorButton");
const statusText = document.getElementById("status");

const userText = document.getElementById("userText");
const jarvisText = document.getElementById("jarvisText");

const userState = document.getElementById("userState");
const jarvisState = document.getElementById("jarvisState");

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

        await playJarvisVoice(data.resultado);

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
        throw new Error("No se pudo generar la voz.");
    }

    const audioBlob = await response.blob();
    const audioUrl = URL.createObjectURL(audioBlob);

    responseAudio = new Audio(audioUrl);

    responseAudio.addEventListener("ended", () => {
        URL.revokeObjectURL(audioUrl);

        responseAudio = null;

        setState("idle");
    });

    responseAudio.addEventListener("error", () => {
        URL.revokeObjectURL(audioUrl);

        responseAudio = null;

        setState("idle");
    });

    await responseAudio.play();
}

reactorButton.addEventListener("click", () => {
    if (isProcessing) {
        return;
    }

    if (isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
});

setState("idle");