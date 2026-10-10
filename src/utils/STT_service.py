# python service che implementa il servizio di riconoscimento vocale (STT)
# PIPELINE: speech -> audio file .wav -> mono audio file .wav -> text

import urllib.request
import zipfile
from pathlib import Path

from pydub import AudioSegment
import wave
from vosk import Model, KaldiRecognizer
import json

#-------------------------------------------------------------------------------
# Scelta del modello VOSK e creazione delle cartelle necessarie
BASE_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = BASE_DIR / "models"
VOSK_MODEL_NAME = "vosk-model-small-it-0.22"
VOSK_MODEL_PATH = MODELS_DIR / VOSK_MODEL_NAME
VOSK_URL = "https://alphacephei.com/vosk/models/vosk-model-small-it-0.22.zip"
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Download (solo se non presente) e inizializzazione del modello scelto
def manage_vosk_model():
    """Scarica ed estrae il modello Vosk se manca in /code/models."""
    if VOSK_MODEL_PATH.exists():
        return

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    tmp_zip = MODELS_DIR / "vosk-it.zip"

    with urllib.request.urlopen(VOSK_URL) as r, open(tmp_zip, "wb") as f:
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)

    # Estrai nella stessa folder MODELS_DIR
    with zipfile.ZipFile(tmp_zip, "r") as z:
        z.extractall(MODELS_DIR)

    tmp_zip.unlink(missing_ok=True)

manage_vosk_model()
if not VOSK_MODEL_PATH.exists():
    raise FileNotFoundError(f"Modello VOSK non trovato: {VOSK_MODEL_PATH}")

vosk_model = Model(str(VOSK_MODEL_PATH))

# Inizializzazione del riconoscitore Kaldi
#rec = KaldiRecognizer(vosk_model, 16000)
#-------------------------------------------------------------------------------

def transcribe_audio_to_text(audio_file_path: str) -> str:
    """
    Questa funzione usa il modello VOSK per trascrivere un file audio .wav in testo.
    """

    # Conversione del file audio in un formato mono per una migliore compatibilità
    # Uso pydub per caricare e convertire il file
    # Quelle che seguono sono impostazioni tipiche richieste dal modello VOSK
    audio = AudioSegment.from_file(audio_file_path)
    audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)

    tmp_wav = Path(audio_file_path).with_suffix(".mono16k.wav")
    audio.export(tmp_wav, format="wav")

    wf_mono = wave.open(str(tmp_wav), "rb")

    # Lista per accumulare i risultati della trascrizione
    transcribe_text_list = []

    rec = KaldiRecognizer(vosk_model, 16000)

    while True:
        data = wf_mono.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            transcribe_text_list.append(result["text"])

    # Gestione dell'ultimo frammento di audio
    final_result = json.loads(rec.FinalResult())
    transcribe_text_list.append(final_result["text"])

    # pulizia tmp wav file: dopo la trascrizione, rimuovo *.mono16k.wav
    #try:
    #    tmp_wav.unlink(missing_ok=True)
    #except Exception:
    #    pass

    # Unione dei risultati in un'unica stringa
    complete_text = ' '.join(transcribe_text_list)

    return complete_text.strip()



