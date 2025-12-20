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
    pron_result = speechsdk.PronunciationAssessmentResult(result)

    # Retorna o texto reconhecido livre; se vazio, usa o da avaliação
    text_recognized = text_raw or result.text
    data = {
        "text_recognized": text_recognized,
        "overall_score": pron_result.pronunciation_score,
        "accuracy": pron_result.accuracy_score,
        "fluency": pron_result.fluency_score,
        "completeness": pron_result.completeness_score,
        "words": [
            {
                "word": w.word,
                "accuracy_score": w.accuracy_score,
            }
            for w in pron_result.words
        ],
    }

    return data
