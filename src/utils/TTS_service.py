# utils/TTS_service.py
import os
from pathlib import Path
from TTS.api import TTS
from datetime import datetime
from num2words import num2words
import re

# Directory locale in cui salvo i file audio generati
BASE_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = BASE_DIR / "static" / "tmp" / "audio"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Directory locale per i modelli TTS
COQUI_MODELS_DIR = BASE_DIR / "models" / "coqui"
COQUI_MODELS_DIR.mkdir(parents=True, exist_ok=True)
# Forziamo Coqui a usare la cache locale del progetto
os.environ.setdefault("TTS_HOME", str(COQUI_MODELS_DIR))

# Modello: da env se presente o fallback a un modello scelto
MODEL_NAME = os.environ.get("TTS_MODEL_NAME", "").strip() or "tts_models/it/mai_male/glow-tts"

# Se il modello non è già nella cache locale, verrà scaricato solo la prima volta in COQUI_MODELS_DIR
tts = TTS(model_name=MODEL_NAME, progress_bar=True, gpu=False)

def normalize_italian(text: str) -> str:

    LETTER_NAMES_ITA = {
        'a': 'a', 'b': 'bi', 'c': 'ci', 'd': 'di', 'e': 'e', 'f': 'effe',
        'g': 'gi', 'h': 'acca', 'i': 'i', 'j': 'i lunga', 'k': 'kappa',
        'l': 'elle', 'm': 'emme', 'n': 'enne', 'o': 'o', 'p': 'pi',
        'q': 'cu', 'r': 'erre', 's': 'esse', 't': 'ti', 'u': 'u',
        'v': 'vi', 'w': 'doppia vu', 'x': 'ics', 'y': 'ipsilon', 'z': 'zeta'
    }
    PUNCT_NAMES_ITA = {
        '-': 'trattino',
        '_': 'underscore',
        '.': 'punto',
        '/': 'barra',
        ':': 'due punti',
    }

    def spell_token(token: str) -> str:
        pieces = []
        for ch in token:
            if ch.isdigit():
                pieces.append(num2words(int(ch), lang='it'))
            elif ch.isalpha():
                pieces.append(LETTER_NAMES_ITA.get(ch.lower(), ch.lower()))
            else:
                pieces.append(PUNCT_NAMES_ITA.get(ch, ch))
        return " ".join(pieces)

    #orari (15:10 -> "quindici e dieci")
    def time_norm(m):
        hours, minu = int(m.group(1)), int(m.group(2))
        hh = num2words(hours, lang='it')
        mm = num2words(minu, lang='it')
        return hh if minu == 0 else f"{hh} e {mm}"

    text = re.sub(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", time_norm, text)

    #date dd/mm/yyyy o dd-mm-yyyy (23/09/2025 -> "ventitre settembre duemilaventicinque")
    months = ["gennaio","febbraio","marzo","aprile","maggio","giugno",
              "luglio","agosto","settembre","ottobre","novembre","dicembre"]

    def dmy_date_norm(m):
        dd, mm, yyyy = int(m.group(1)), int(m.group(2)), int(m.group(3))
        day = num2words(dd, lang='it')
        year = num2words(yyyy, lang='it')
        return f"{day} {months[mm-1]} {year}"

    text = re.sub(r"\b([0-3]?\d)[/\-]([01]?\d)[/\-](\d{4})\b", dmy_date_norm, text)

    # yyyy-mm-dd numerico
    def ymd_date_norm(m):
        yyyy, mm, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
        day = num2words(dd, lang='it')
        year = num2words(yyyy, lang='it')
        return f"{day} {months[mm-1]} {year}"

    text = re.sub(r"\b(\d{4})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b", ymd_date_norm, text)

    """
    # parole alfabetiche con trattini ("anno-mese-giorno" -> "anno mese giorno")
    # es. "anno-mese-giorno" -> "anno mese giorno"
    text = re.sub(r"\b([A-Za-zÀ-ÖØ-öø-ÿ]+(?:-[A-Za-zÀ-ÖØ-öø-ÿ]+)+)\b",
                  lambda m: m.group(1).replace('-', ' '),
                  text)

    #codici con separatori (ABCD-1234, RFC/HTTP-1.1, YYYY-MM-DD)
    text = re.sub(
        r"\b(?:[A-Za-z0-9]+(?:[-_./:][A-Za-z0-9]+)+)\b",
        lambda m: spell_token(m.group(0)),
        text
    )

    #sigle alfabetiche pure in MAIUSCOLO (>=4)
    text = re.sub(r"\b[A-Z]{4,}\b", lambda m: spell_token(m.group(0)), text)

    #alfanumerici lunghi (>=8) senza separatori
    text = re.sub(
        r"\b(?=[A-Za-z0-9]*[A-Za-z])(?=[A-Za-z0-9]*\d)[A-Za-z0-9]{8,}\b",
        lambda m: spell_token(m.group(0)),
        text
    )

    #numerici lunghi (>=6) -> letti cifra per cifra
    text = re.sub(r"\b\d{6,}\b",
                  lambda m: " ".join(num2words(int(ch), lang='it') for ch in m.group(0)),
                  text)

    #numeri rimanenti
    text = re.sub(r"\b\d+\b", lambda m: num2words(int(m.group(0)), lang='it'), text)

    return text
    """

    # --- NUMERI: decimali e migliaia prima di tutto ---

    def norm_decimal(int_part: str, frac_part: str, sep_word: str) -> str:
        # parte intera come numero
        int_words = num2words(int(int_part), lang='it') if int_part else "zero"
        # parte decimale: come numero, ma se ha zero iniziale la leggiamo cifra per cifra
        if frac_part and frac_part[0] == '0':
            frac_words = " ".join(num2words(int(d), lang='it') for d in frac_part)
        else:
            frac_words = num2words(int(frac_part), lang='it')
        return f"{int_words} {sep_word} {frac_words}"

    # stile EU: 1.234.567,89
    def norm_eu_decimal(m):
        token = m.group(0)
        token = token.replace('.', '')  # togli i separatori di migliaia
        int_part, frac_part = token.split(',')
        return norm_decimal(int_part, frac_part, "virgola")

    text = re.sub(r"\b\d{1,3}(?:\.\d{3})+,\d+\b", norm_eu_decimal, text)

    # decimale semplice: 1130.56 o 1130,56 (senza migliaia)
    def norm_simple_decimal(m):
        token = m.group(0)
        if '.' in token and token.count('.') == 1 and ',' not in token:
            int_part, frac_part = token.split('.')
            return norm_decimal(int_part, frac_part, "punto")
        if ',' in token and token.count(',') == 1 and '.' not in token:
            int_part, frac_part = token.split(',')
            return norm_decimal(int_part, frac_part, "virgola")
        return token  # fallback (non dovrebbe capitare)

    text = re.sub(r"\b\d+[.,]\d+\b", norm_simple_decimal, text)

    # interi con separatori di migliaia
    def norm_eu_int(m):
        return num2words(int(m.group(0).replace('.', '')), lang='it')

    def norm_us_int(m):
        return num2words(int(m.group(0).replace(',', '')), lang='it')

    text = re.sub(r"\b\d{1,3}(?:\.\d{3})+\b", norm_eu_int, text)
    text = re.sub(r"\b\d{1,3}(?:,\d{3})+\b", norm_us_int, text)

    # --- PAROLE composte ---
    # alfabetiche con trattini tipo "anno-mese-giorno" -> spazio ossia "anno mese giorno"
    text = re.sub(r"\b([A-Za-zÀ-ÖØ-öø-ÿ]+(?:-[A-Za-zÀ-ÖØ-öø-ÿ]+)+)\b",
                  lambda m: m.group(1).replace('-', ' '),
                  text)
    # alfabetiche con underscore -> spazio (es. client_ID -> client ID)
    text = re.sub(r"\b([A-Za-zÀ-ÖØ-öø-ÿ]+(?:_[A-Za-zÀ-ÖØ-öø-ÿ]+)+)\b",
                  lambda m: m.group(1).replace('_', ' '),
                  text)

    # codici con separatori (solo se contengono ALMENO una lettera e ALMENO una cifra)
    # es. RFC/7231, HTTP/1.1, ABCD-1234
    text = re.sub(
        r"\b(?=[A-Za-z0-9]*[A-Za-z])(?=[A-Za-z0-9]*\d)[A-Za-z0-9]+(?:[-_./:][A-Za-z0-9]+)+\b",
        lambda m: spell_token(m.group(0)),
        text
    )

    # sigle alfabetiche pure in MAIUSCOLO (>=4) -> lettera per lettera
    text = re.sub(r"\b[A-Z]{4,}\b", lambda m: spell_token(m.group(0)), text)

    # alfanumerici lunghi (>=8) senza separatori -> carattere per carattere
    text = re.sub(
        r"\b(?=[A-Za-z0-9]*[A-Za-z])(?=[A-Za-z0-9]*\d)[A-Za-z0-9]{8,}\b",
        lambda m: spell_token(m.group(0)),
        text
    )

    # numerici lunghi (>=6) -> cifra per cifra
    text = re.sub(
        r"\b\d{6,}\b",
        lambda m: " ".join(num2words(int(ch), lang='it') for ch in m.group(0)),
        text
    )

    # numeri rimanenti -> in lettere
    text = re.sub(r"\b\d+\b", lambda m: num2words(int(m.group(0)), lang='it'), text)

    return text


def generate_audio(text: str) -> str:

    #Ritorna il percorso assoluto del file WAV generato come risposta alla richiesta utente vocale.

    text_norm = normalize_italian(text)

    now = datetime.now()
    file_wav_name = f"GenhapiReply_Date({now.strftime('%Y%m%d')})_Time({now.strftime('%H%M%S')}).wav"
    out_path = OUT_DIR / file_wav_name

    tts.tts_to_file(text=text_norm, file_path=str(out_path))
    return str(out_path)

