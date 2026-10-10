from __future__ import annotations
import os
from django.http import JsonResponse
from agents.audio_agent import audio_agent

import json
import re
from pathlib import Path
from urllib.parse import urlparse

from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from agents.security_agent import SecurityAgent
from agents.team_agent import CoordinatorAgent, intent_memory, resolver_memory, team_memory
from utils.config import INTENTS as intents

from django.conf import settings

###############################################################################
# Inizializzazioni globali (una sola volta per processo)
###############################################################################

security_agent = SecurityAgent(valid_tokens=["*****", "*****"])
team = CoordinatorAgent                      # <─ factory con @cache

###############################################################################
# Views
###############################################################################

@csrf_exempt  # This is used to disable CSRF for now, though it should be handled in production
def index(request):
    return render(request, 'index.html')


@csrf_exempt
def get_intents(request):
    if request.method == 'GET':
        intents_list = [{"intent": key, "description": value["description"]} for key, value in intents.items()]
        return JsonResponse({"intents": intents_list})


@csrf_exempt
def chat(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_message = data.get("user_message")
        user_token = data.get("user_token")
        # ---------------------------------
        # Inizializzazione del parametro a true in caso di richiesta vocale
        voice_request = data.get("voice_request", False)
        # ---------------------------------

        # Controllo token
        if not security_agent.is_token_valid(user_token):
            return JsonResponse({"status": "error", "message": "Token non valido."})
        # LOG: Input message
        print("User input message:", user_message)
        # Chiamata al team di assistenti
        agent_response = team.run({
            "role": "user",
            "content": user_message,
            "token": user_token
        })
        # Debug tool call tracking
        for msg in agent_response.messages:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                print("Tool calls detected in assistant message:", msg.tool_calls)
            if msg.role == "tool":
                print("Tool response message found:", msg.tool_call_id)

        content = getattr(agent_response, "content", None)
        if isinstance(content, dict):
            return JsonResponse(content)

        # ---------------------------------
        # Se la richiesta è vocale, genera url dell'audio di risposta Genhapi
        response_audio_url = None
        if voice_request and content:
            response_wav = audio_agent.synthesize(str(content)) # str(content) è la risposta Genhapi alla richiesta utente
            response_wav_name = os.path.basename(response_wav)
            # Servita da Django attraverso la cartella static (vedi urls.py con static(...))
            response_audio_url = f"/static/tmp/audio/{response_wav_name}"
        # ---------------------------------

        # Fallback generico
        return JsonResponse({
            "status": "complete",
            "response": str(content) if content else " Operazione completata.",
            "audio_url": response_audio_url
        })


@csrf_exempt
def reset_memory(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Only POST allowed."})

    # Svuota le memorie, se esistono
    for mem, label in [
        (team_memory, "Team"),
        (intent_memory, "Intent"),
        (resolver_memory, "Resolver"),
    ]:
        try:
            mem.clear()
            print(f"{label} memory cleared.")
        except Exception:
            print(f"{label} memory not initialized yet.")

    return JsonResponse({"status": "success", "message": "Memorie cancellate."})

#----------------Integrazione con nuove viste---------------------#

TMP_DIR = Path("web/tmp/audio")
TMP_DIR.mkdir(parents=True, exist_ok=True)
@csrf_exempt
def transcribe_audio_view(request):
    if request.method != 'POST' or 'audio' not in request.FILES:
        return JsonResponse({"success": False, "error": "File audio non trovato."}, status=400)

    audio_file = request.FILES['audio']

    original_path = TMP_DIR / audio_file.name
    with open(original_path, 'wb+') as dest:
        for chunk in audio_file.chunks():
            dest.write(chunk)

    try:
        transcript = audio_agent.transcribe_file(str(original_path))
        return JsonResponse({"success": True, "text": transcript})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
def generate_audio_view(request):
    """
    Per la logica integrata fin qua non è necessario questa view in quanto ho integrato
    il tutto con 'audio_agent.synthesize' direttamente nella view 'chat'.
    Però potrebbe tornare utile se fornissi all'utente la possibilità di poter riascoltare
    la risposta del chatbot in un secondo momento (?)
    """


# Cartella dei file TTS prodotti da Genhapi: static/tmp/audio/
AUDIO_DIR = os.path.abspath(os.path.join(settings.BASE_DIR, "static", "tmp", "audio"))

# Utilizzo le espressioni regolari per riconoscere la struttura del file da cancellare, ossia
# GenhapiReply_Date(YYYYMMDD)_Time(HHMMSS).wav
FILENAME_RE = re.compile(r"^GenhapiReply_Date\(\d{8}\)_Time\(\d{6}\)\.wav$")

@csrf_exempt
def delete_audio_played(request):
    """
    Cancella in modo sicuro il file wav una volta che il frontend ne conferma la riproduzione.
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Metodo non consentito."}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"success": False, "error": "JSON non valido."}, status=400)

    file_audio_path = (data.get("file_audio_path") or "").strip()
    user_token = data.get("user_token")

    # verifica del token
    if not security_agent.is_token_valid(user_token):
        return JsonResponse({"success": False, "error": "Token non valido."}, status=401)

    # verifica dell'url/path del file audio
    if not file_audio_path:
        return JsonResponse({"success": False, "error": "Percorso audio mancante."}, status=400)

    # Rimuove eventuale querystring (se si osserva nel log di sistema si osserva qualcosa come ?v=timestamp)
    parsed = urlparse(file_audio_path)
    path_pure = parsed.path  # es: /static/tmp/audio/GenhapiReply_Date(20250825)_Time(145739).wav

    static_url = settings.STATIC_URL

    expected_prefix = static_url + "tmp/audio/"
    if not path_pure.startswith(expected_prefix):
        return JsonResponse({"success": False, "error": "Percorso non consentito."}, status=400)

    # estraggo il filemane dal path e lo confronto con la forma GenhapyReply_Date(YYYYMMDD)_Time(HHMMSS).wav
    filename = os.path.basename(path_pure)
    if not FILENAME_RE.match(filename):
        return JsonResponse({"success": False, "error": "Filename non valido."}, status=400)

    # ricostruisco il path assoluto
    file_path = os.path.abspath(os.path.join(AUDIO_DIR, filename))
    try:
        if os.path.commonpath([AUDIO_DIR, file_path]) != AUDIO_DIR:
            return JsonResponse({"success": False, "error": "Path non consentito."}, status=400)
    except Exception:
        return JsonResponse({"success": False, "error": "Validazione path fallita."}, status=400)

    # cancellazione del file audio
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return JsonResponse({"success": True, "deleted": filename})
        except Exception as e:
            return JsonResponse({"success": False, "error": f"Delete failed: {e}"}, status=500)
    else:
        # se già cancellato o mai esistito -> okay
        return JsonResponse({"success": True, "deleted": None, "note": "File non trovato"})

#---------------------------------------------------------------#
