# ms_speech.py
import os
import azure.cognitiveservices.speech as speechsdk

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def _get_speech_config():
    speech_key = os.getenv("SPEECH_KEY")
    speech_region = os.getenv("SPEECH_REGION")
    if not speech_key or not speech_region:
        raise RuntimeError("Variáveis SPEECH_KEY e SPEECH_REGION não definidas no .env")
    return speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)


def avaliar_pronuncia(audio_path: str, reference_text: str) -> dict:
    speech_config = _get_speech_config()

    def _score_or_zero(obj, attr_name: str) -> float:
        value = getattr(obj, attr_name, None)
        return float(value) if isinstance(value, (int, float)) else 0.0

    # Reconhecimento livre para capturar exatamente o que foi dito
    free_audio_config = speechsdk.AudioConfig(filename=audio_path)
    free_recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        audio_config=free_audio_config,
        language="en-US",
    )
    free_result = free_recognizer.recognize_once()
    text_raw = free_result.text or ""
    print(f"fala reconhecida: {text_raw}")

    # Configuração de avaliação de pronúncia
    pron_config = speechsdk.PronunciationAssessmentConfig(
        reference_text=reference_text,
        grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
        granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
        enable_miscue=True,
    )

    # Avaliação de pronúncia (usa a mesma gravação, mas com a config de avaliação)
    audio_config = speechsdk.AudioConfig(filename=audio_path)
    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        audio_config=audio_config,
        language="en-US",
    )

    pron_config.apply_to(recognizer)

    result = recognizer.recognize_once()

    # Se não houver fala reconhecida, devolve estrutura consistente sem quebrar.
    if result.reason != speechsdk.ResultReason.RecognizedSpeech:
        error_detail = "Nenhuma fala reconhecida"
        if result.reason == speechsdk.ResultReason.Canceled:
            cancellation = speechsdk.CancellationDetails(result)
            if cancellation.error_details:
                error_detail = cancellation.error_details

        return {
            "text_recognized": text_raw or "",
            "overall_score": 0.0,
            "accuracy": 0.0,
            "fluency": 0.0,
            "completeness": 0.0,
            "words": [],
            "error": error_detail,
        }

    pron_result = speechsdk.PronunciationAssessmentResult(result)

    # Retorna o texto reconhecido livre; se vazio, usa o da avaliação
    text_recognized = text_raw or result.text
    data = {
        "text_recognized": text_recognized,
        "overall_score": _score_or_zero(pron_result, "pronunciation_score"),
        "accuracy": _score_or_zero(pron_result, "accuracy_score"),
        "fluency": _score_or_zero(pron_result, "fluency_score"),
        "completeness": _score_or_zero(pron_result, "completeness_score"),
        "words": [
            {
                "word": w.word,
                "accuracy_score": _score_or_zero(w, "accuracy_score"),
            }
            for w in getattr(pron_result, "words", [])
        ],
    }

    return data


def sintetizar_frase(texto: str) -> bytes:
    """
    Converte texto em áudio usando Azure Text-to-Speech.
    
    Args:
        texto: Texto a ser convertido em áudio
        
    Returns:
        bytes: Dados de áudio em formato WAV
    """
    speech_config = _get_speech_config()
    
    # Configura para não usar speaker (áudio será retornado em memória)
    # Quando audio_config é None, o SDK retorna o áudio em result.audio_data
    audio_config = None
    
    # Cria o sintetizador de fala
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )
    
    # Sintetiza o texto
    result = synthesizer.speak_text_async(texto).get()
    if result is None:
        raise RuntimeError("Erro ao sintetizar fala: resposta vazia do SDK")
    
    # Verifica se houve erro
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return result.audio_data
    else:
        cancellation = getattr(result, "cancellation_details", None)
        if cancellation:
            details = (cancellation.error_details or "Erro desconhecido").strip()
            raise RuntimeError(f"Erro ao sintetizar fala: {details}")
        raise RuntimeError(f"Erro ao sintetizar fala. Reason: {result.reason}")
