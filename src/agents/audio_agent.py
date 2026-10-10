# web/agents/audio_agent.py
from utils.STT_service import transcribe_audio_to_text
from utils.TTS_service import generate_audio

class AudioAgent:
    """
    Agente specializzato per i servizi speech -> text (STT) e text -> speech (TTS)
    """

    def transcribe_file(self, file_path: str) -> str:
        """
        Utilizza un modello VOSK per trascrivere la richista vocale dell'utente nel chatbot.
        """
        return transcribe_audio_to_text(file_path)

    def synthesize(self, text: str) -> str:
        """
        Ritorna percorso assoluto del file audio .wav associato alla risposta Genhapi.
        """
        return generate_audio(text)

audio_agent = AudioAgent()
