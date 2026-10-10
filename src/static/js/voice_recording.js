const ContextManager = {
    context: {},
    set(intent, parameters) {
        this.context = {intent, parameters};
    },
    clear() {
        this.context = {};
    },
    getIntent() {
        return this.context.intent || null;
    },
    getParameters() {
        return this.context.parameters || {};
    },
    isValid() {
        return !!(this.context.intent && this.context.parameters);
    }
};

window.addEventListener("DOMContentLoaded", function () {
    fetch("/reset_memory", {method: "POST"})
        .then(res => res.json())
        .then(data => {
            console.log(data.message, "Memoria resettata");
        });
    fetch("/intents")
        .then(response => response.json())
        .then(data => {
            const intents = data.intents;
            const list = intents.map(i => `• ${i.description}`).join("<br/>");
            renderBotMessage(`Ciao! Sono il tuo assistente.<br/>
            Posso aiutarti nella realizzazione di queste azioni:<br/>
            ${list}<br/><br/>
            Scrivimi pure la tua richiesta!`);
        })
        .catch(() => {
            renderBotMessage("👋 Ciao! Sono il tuo assistente finanziario. Scrivimi pure la tua richiesta!");
        });
});

function createBotBlock(innerHTML) {
    const block = document.createElement("div");
    block.className = "message bot-message";
    const converter = new showdown.Converter();

    block.innerHTML = converter.makeHtml(innerHTML);
    document.getElementById("messages").appendChild(block);
}

function renderBotMessage(text) {
    createBotBlock(text);
}

function renderSuggestions(suggestions) {
    let html = "Seleziona il cliente:<br/>";
    suggestions.forEach(s => {
        html += `<button class="customer-option" onclick="submitCustomerChoice('${s.name}')">${s.name} - ${s.address}</button><br/>`;
    });
    html += `<button class="customer-option" style="background-color: gray;" onclick="cancelCustomerChoice()"> Annulla</button>`;
    createBotBlock(html);
}


function updateOrAppendMissingFields(data) {
    const formContainer = document.getElementById("missing-fields-form");

    if (!formContainer) {
        // Se il form non esiste, crealo come nuovo messaggio
        const formHtml = data.missing.map(field => {
            const fieldId = `field-${field.field}`;
            const value = data.parameters?.[field.field];
            return value !== undefined && value !== ""
                ? `<label for="${fieldId}">${field.question}</label><br/><div class="answered-value"><strong>${value}</strong></div><br/>`
                : `<label for="${fieldId}">${field.question}</label><br/><input type="text" id="${fieldId}" placeholder="${field.type}"><br/>`;
        }).join("");

        const fullForm = `
            <div id="missing-fields-form">
                ${formHtml}
                <button onclick="submitMissing()">Invia Dati Mancanti</button>
            </div>
        `;

        const messageDiv = document.createElement("div");
        messageDiv.className = "message bot-message";
        messageDiv.innerHTML = fullForm;
        document.getElementById("messages").appendChild(messageDiv);

        return;
    }

    // Se esiste il form: aggiorna solo i campi necessari
    data.missing.forEach(field => {
        const fieldId = `field-${field.field}`;
        const value = data.parameters?.[field.field];
        const inputEl = document.getElementById(fieldId);

        if (inputEl && value !== undefined && value !== "") {
            //Sostituisci input compilato con testo statico
            const labelEl = document.querySelector(`label[for="${fieldId}"]`);

            const messageBlock = inputEl.closest(".message.bot-message");
            if (messageBlock) {
                messageBlock.innerHTML = `
                    ${labelEl?.outerHTML || ''}
                    <div class="answered-value"><strong>${value}</strong></div><br/>
                `;
            }
        }
    });

    
    const newFieldsHtml = data.missing.map(field => {
        const fieldId = `field-${field.field}`;
        const alreadyExists = document.getElementById(fieldId);
        const value = data.parameters?.[field.field];

        if (!alreadyExists && (value === undefined || value === "")) {
            return `
                <label for="${fieldId}">${field.question}</label><br/>
                <input type="text" id="${fieldId}" placeholder="${field.type}"><br/>
            `;
        }
        return "";
    }).join("");

    if (newFieldsHtml.trim()) {
        formContainer.insertAdjacentHTML("beforeend", newFieldsHtml);
    }

    // Aggiungi bottone se non presente
    if (!formContainer.querySelector("button")) {
        const submitButton = document.createElement("button");
        submitButton.textContent = "Invia Dati Mancanti";
        submitButton.onclick = submitMissing;
        formContainer.appendChild(submitButton);
    }
}


function showBotMessages(data) {
    console.log("showBotMessages", data);
    console.log(data);
    console.log(data.status);
    if (data.status === "complete") {
        console.log("Completato: rispondo");
        const response = data.response;

        if (typeof response === "string") renderBotMessage(response);
        if (typeof response === "object" && typeof response.response === "string") renderBotMessage(response.response);
        if (response.messages?.length) response.messages.forEach(renderBotMessage);
        ContextManager.clear();
    }

    console.log("ContextManager", ContextManager.context);
    const messagesDiv = document.getElementById("messages");
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}


async function submitMissing() {
    if (!ContextManager.isValid()) {
        alert("⚠️ La conversazione è scaduta o non è valida. Invia una nuova richiesta.");
        return;
    }

    const inputs = document.querySelectorAll("input[id^='field-']");
    const missing_values = {};
    const replacements = [];

    inputs.forEach(input => {
        const field = input.id.replace("field-", "");
        const value = input.value;
        missing_values[field] = value;
        replacements.push({
            id: input.id,
            label: document.querySelector(`label[for="${input.id}"]`)?.outerHTML,
            value
        });
    });
    // Invia dati mancanti al server
    const response = await fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            user_token: "token123",
            intent: ContextManager.getIntent(),
            parameters: ContextManager.getParameters(),
            missing_values
        })
    });

    const data = await response.json();
    // Sostituisci input con risposte statiche
    replacements.forEach(rep => {
        const inputEl = document.getElementById(rep.id);
        if (!inputEl) return;
        const labelEl = document.querySelector(`label[for="${rep.id}"]`);
        const messageBlock = inputEl.closest(".message.bot-message");
        if (messageBlock) {
            messageBlock.innerHTML = `
                ${labelEl?.outerHTML || ''}
                <div class="answered-value"><strong>${rep.value}</strong></div><br/>
            `;
        }
    });

    showBotMessages(data);
}

async function submitCustomerChoice(name) {
    if (!ContextManager.isValid()) {
        alert("La conversazione è scaduta. Invia una nuova richiesta.");
        return;
    }

    const parameters = ContextManager.getParameters();
    parameters["client_name"] = name;
    ContextManager.set(ContextManager.getIntent(), parameters);

    const response = await fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            user_token: "token123",
            intent: ContextManager.getIntent(),
            parameters
        })
    });

    const data = await response.json();
    showBotMessages(data);
}

function sendMessage() {
    const userMessage = document.getElementById("user-message").value.trim();

    if (!userMessage) {
        renderBotMessage("Per favore, inserisci una domanda o una richiesta per continuare la conversazione.");
        return;
    }
    document.getElementById("messages").innerHTML += `<div class="message user-message">${userMessage}</div>`;
    // RESET form e context se esistono
    document.getElementById("missing-fields-form")?.remove();
    ContextManager.clear();
    startBotTyping();
    const t0 = performance.now();
    fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({user_message: userMessage, user_token: "token123"})
    })
        .then(response => {
            const dt = performance.now() - t0;
            console.log(`Tempo di risposta: ${dt} ms`);
            stopBotTyping(); //  appena ricevi, togli loading
            return response.json();
        })
        .then(showBotMessages);

    document.getElementById("user-message").value = "";
}

function cancelCustomerChoice() {
    ContextManager.clear();
    renderBotMessage("Operazione annullata. Puoi inserire una nuova richiesta.");
}


let typingInterval;


function startBotTyping() {
    const typingBlock = document.createElement("div");
    typingBlock.className = "message bot-message";
    typingBlock.id = "bot-typing";
    typingBlock.innerHTML = `<span id="typing-dots">.</span>`;
    document.getElementById("messages").appendChild(typingBlock);

    // Animazione dots
    let dots = '';
    typingInterval = setInterval(() => {
        dots = dots.length < 3 ? dots + '.' : '';
        document.getElementById("typing-dots").textContent = `${dots}`;
    }, 500);

    const messagesDiv = document.getElementById("messages");
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function stopBotTyping() {
    clearInterval(typingInterval);
    const typingBlock = document.getElementById("bot-typing");
    if (typingBlock) typingBlock.remove();
}


//#####################################################################################
// Integrazione con richiesta e risposta chatbot audio

/*
Logica del front-end

    1-Cliccando sul bottone 🎙, inizia la registrazione audio;
    2-Con VAD la registrazione vocale si stoppa automaticamente;
    3-Il testo trascritto viene visualizzato come messaggio utente in chat;
    4-Cliccando poi su "Invia", il messaggio viene inviato continuando la normale PIPELINE Genhapi;
    5-Attraverso autoplay viene automaticamente letta a voce la risposta Genhapi.

*/

//####################Voice Activity Detection (VAD) LOGIC####################
const VAD_CHECK_INTERVAL_MS = 120;     // ogni quanto misurare il volume
const VAD_SILENCE_DURATION_MS = 1500;  // quanto silenzio consecutivo serve per auto-stop
const VAD_MIN_RECORDING_MS = 600;      // evita stop troppo precoce (parola singola)
const VAD_RMS_SILENCE_THRESHOLD = 0.012; // soglia "volume" (0..~0.2). Da alzare se troppo sensibile

let audioCtx = null;
let analyser = null;
let vadTimerId = null;
let vadSilenceAccumMs = 0;
let recordingStartTs = 0;

function startVAD(stream) {
    // Crea AudioContext e Analyser per misurare "energia" del segnale
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const source = audioCtx.createMediaStreamSource(stream);
    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 2048;
    source.connect(analyser);

    vadSilenceAccumMs = 0;
    recordingStartTs = Date.now();

    // loop di controllo
    vadTimerId = setInterval(() => {
        if (!isRecording || !analyser) return;
        const rms = measureRMS(analyser);
        const elapsed = Date.now() - recordingStartTs;

        // ignora i primi VAD_MIN_RECORDING_MS ms per evitare stop istantanei
        if (elapsed < VAD_MIN_RECORDING_MS) return;

        if (rms < VAD_RMS_SILENCE_THRESHOLD) {
            vadSilenceAccumMs += VAD_CHECK_INTERVAL_MS;
            if (vadSilenceAccumMs >= VAD_SILENCE_DURATION_MS) {
                // se viene riscontrato un silenzio più prolungato si stoppa automaticamente
                stopRecording();
            }
        } else {
            // finchè c'è voce azzero il silenzioa accumolato
            vadSilenceAccumMs = 0;
        }
    }, VAD_CHECK_INTERVAL_MS);
}

function stopVAD() {
    if (vadTimerId) {
        clearInterval(vadTimerId);
        vadTimerId = null;
    }
    try { audioCtx && audioCtx.close(); } catch {}
    audioCtx = null;
    analyser = null;
}

/**
 * Calcola una stima RMS (root-mean-square) dal dominio del tempo (0..~0.2)
 */
function measureRMS(analyserNode) {
    const bufferLength = analyserNode.fftSize;
    const data = new Uint8Array(bufferLength);
    analyserNode.getByteTimeDomainData(data);
    // dati sono 0..255 centrati intorno a 128
    let sum = 0;
    for (let i = 0; i < bufferLength; i++) {
        const v = (data[i] - 128) / 128; // normalizza a -1..1
        sum += v * v;
    }
    const rms = Math.sqrt(sum / bufferLength);
    return rms;
}
//################################################################################

let isRecording = false;
let mediaRecorder = null;
let mediaStream = null;
let chunks = [];
let stopTimerId = null; // per fermare la registrazione in caso di richieste audio troppo lunghe

const recBtn = document.getElementById("record-audio-button");

// Temporaneamente setto un limite di tempo di 30 secs per non generare audio troppo lunghi
const MAX_RECORDING_MS = 30000;

//-------------------------------------------------------------------------------
// Le funzioni che seguono mirano a rendere portabile la registrazione su browser diversi

// sceglie a priori il miglior formato supportato dal browser per MediaRecorder
function pick_mime_type() {
    const candidates = [
        "audio/webm;codecs=opus",
        "audio/ogg;codecs=opus",
        "audio/webm",
        "audio/ogg",
        "audio/mp4",
    ];
    for (const type of candidates) {
        try {
            if (window.MediaRecorder && MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(type)) {
                return type;
            }
        } catch (_) {
        }
    }

    return "";
}

// mappa il MIME effettivo -> estensione file giusta per il nome che salvi/invi
function extension_mime_based(mime) {
    if (!mime) return "webm";
    const m = mime.toLowerCase();
    if (m.includes("ogg")) return "ogg";
    if (m.includes("webm")) return "webm";
    if (m.includes("mp4")) return "mp4";
    return "webm";
}

// -------------------------------------------------------------------------------

/**
 * Funzione commutatore che gestisce correttamente la registrazione della richiesta
 * audio.
 */
async function toggleRecording() {
    //if (isRecording) {
    //    await stopRecording();
    //} else {
    //    await startRecording();
    //}
    if(!recBtn) return;
    if(!isRecording){
        await startRecording();
    }
}


 //Aggiorna lo stato del bottone e flag.
function setRecordingUI(recording) {
    isRecording = recording;
    //if(!isRecording) return;
    recBtn.disabled = recording;
    //recBtn.textContent = recording ? "⏹" : "🎙";
    //recBtn.disabled = false;
}


async function startRecording() {
    if (isRecording) return; // già in corso
    if (!navigator.mediaDevices?.getUserMedia) {
        renderBotMessage("Il tuo browser non supporta la registrazione audio.");
        return;
    }

    try {
        recBtn.disabled = true;

        // Richiesta permessi microfono
        mediaStream = await navigator.mediaDevices.getUserMedia({audio: true});

        const mimeType = pick_mime_type();
        mediaRecorder = new MediaRecorder(mediaStream, mimeType ? {mimeType} : {});
        chunks = [];

        mediaRecorder.addEventListener("dataavailable", (e) => {
            if (e.data && e.data.size > 0) chunks.push(e.data);
        });

        mediaRecorder.addEventListener("stop", handleRecordingStop(mimeType), {once: true});

        // Avvio
        mediaRecorder.start();
        setRecordingUI(true);
        renderBotMessage("🎙 Inizia a parlare…");

        startVAD(mediaStream)

        // Stop automatico se viene superato il limite max della durata della registrazione audio
        stopTimerId = window.setTimeout(() => {
            if (isRecording) stopRecording();
        }, MAX_RECORDING_MS);

    } catch (err) {
        console.error("Errore nell'accesso al microfono:", err);
        renderBotMessage("Permesso microfono negato o microfono non disponibile.");
        cleanupMedia();
        setRecordingUI(false);
    }
}


function stopRecording() {
    if (!isRecording || !mediaRecorder) return;
    try {
        mediaRecorder.stop();
    } catch (e) {
        console.warn("Errore su stop MediaRecorder:", e);
    }
    window.clearTimeout(stopTimerId);
    stopTimerId = null;

    stopVAD();

    setRecordingUI(false);
    renderBotMessage("⏹ Registrazione terminata. Trascrizione in corso…");
}


// Pulizia tracce microfono
function cleanupMedia() {
    try {
        if (mediaStream) {
            mediaStream.getTracks().forEach(t => t.stop());
        }
    } catch {
    }

    stopVAD();
    // azzero riferimenti e buffer per prevenire memory leak e preparare un nuova sessione pulita
    mediaStream = null;
    mediaRecorder = null;
    chunks = [];
}


//Gestione fine registrazione: upload -> trascrizione -> chat
function handleRecordingStop(defaultMime) {
    return async () => {
        try {
            const usedMime = (mediaRecorder && mediaRecorder.mimeType) || defaultMime || "audio/webm";
            const ext = extension_mime_based(usedMime);
            const blob = new Blob(chunks, {type: usedMime});
            const stamp = new Date().toISOString().replace(/[-:TZ.]/g, "").slice(0, 15); // YYYYMMDDHHMMSS
            const filename = `GenhapiReply_${stamp}.${ext}`;


            // upload per STT
            const formData = new FormData();
            formData.append("audio", blob, filename);

            recBtn.disabled = true;

            // 1) trascrizione della richista utente vocale
            const genhapiRes = await fetch("/chatbot/audio", {method: "POST", body: formData});
            let dataRes = null;
            try {
                dataRes = await genhapiRes.json();
            } catch {
                throw new Error("Risposta STT non valida.");
            }
            if (!genhapiRes.ok || !dataRes?.success) {
                throw new Error(dataRes?.error || "Trascrizione fallita.");
            }

            const text = (dataRes.text || "").trim();
            renderBotMessage("Hai detto: " + (text || "Non ho rilevato alcun parlato. Riprova"));

            startBotTyping();

            // 2) invia in pipeline Genhapi (con richiesta di TTS nella risposta)
            const chatRes = await fetch("/chat", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    user_message: text,
                    user_token: "token123",
                    voice_request: true
                })
            });

            let chatData = null;
            try {
                chatData = await chatRes.json();
            } catch {
                throw new Error("Risposta /chat non valida.");
            }

            stopBotTyping();

            showBotMessages(chatData);

            // gestisci qui eventuale audio_url in risposta
            // se il backend ha generato una risposta Genhapi TTS allora avvia la riproduzione
            play_TTS_response(chatData)

        } catch
            (err) {
            stopBotTyping();
            console.error(err);
            renderBotMessage("Errore audio: " + err.message);
        } finally {
            // rilascia tutte le risorse pulite
            recBtn.disabled = false;
            cleanupMedia();
        }
    }
        ;
}


async function play_TTS_response(chatData) {
    if (!chatData || !chatData.audio_url) return;

    const audio = document.getElementById("tts-audio");
    if (!audio) return;

    // bust cache per evitare che il browser riusi un file vecchio
    const cache = `${chatData.audio_url}?v=${Date.now()}`;
    audio.src = cache;

    // Mostra anche un player nella chat (utile se autoplay viene bloccato)
    //const messages = document.getElementById("messages");
    //const inlinePlayer = document.createElement("audio");
    //inlinePlayer.src = src;
    //inlinePlayer.controls = true;
    //inlinePlayer.style.display = "block";
    //messages?.appendChild(inlinePlayer);

    try {
        // l’autoplay può essere bloccato dal browser in alcuni casi
        await audio.play();
    } catch (e) {
        console.warn("Autoplay bloccato dal browser:", e);
    }

    // aggiungo un evento per riconoscere quando la riproduzione del file di risposta audio termina
    audio.onended = () => {
        audioPlayed(chatData.audio_url);
    };
}

// funzione che invia una richiesta POST al backend per eliminare il file .wav memorizzato
function audioPlayed(file_audio_path) {
    fetch("/audio/del", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({file_audio_path, user_token: "token123"})
    }).catch(err => console.warn("Il sistema non ha riconosciuto che il file audio è terminato:", err));

}


//#################################################################################
