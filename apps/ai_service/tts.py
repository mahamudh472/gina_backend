import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from typing import Any

import requests
from django.conf import settings

from apps.ai_service.exceptions import TTSGenerationError

logger = logging.getLogger(__name__)

DEFAULT_TTS_SETTINGS = {
    "stability": 0.40,        
    "similarity_boost": 0.60, 
    "style": 0.45,            
    "use_speaker_boost": True,
}


def generate_step_audio(
    *,
    text: str,
    voice_name: str = "",
    voice_id: str | None = None,
    tts_settings: dict[str, Any] | None = None,
) -> bytes | None:
    """Generate speech audio for one meditation step when TTS is configured."""
    if not getattr(settings, "TTS_GENERATE_AUDIO", True):
        raise TTSGenerationError("TTS generation is disabled.")
    if not text or not text.strip():
        raise TTSGenerationError("Text for TTS generation is empty.")

    provider = str(getattr(settings, "TTS_PROVIDER", "elevenlabs")).lower()
    if provider != "elevenlabs":
        raise TTSGenerationError(f"Unsupported TTS_PROVIDER '{provider}'.")

    resolved_voice_id = voice_id or resolve_voice_id(voice_name)
    if not resolved_voice_id:
        raise TTSGenerationError(f"No TTS voice ID configured for '{voice_name}'.")

    api_key = getattr(settings, "TTS_API_KEY", None)
    if not api_key:
        raise TTSGenerationError("TTS_API_KEY is not configured.")

    audio_bytes = _generate_elevenlabs_audio(
        text=text,
        voice_id=resolved_voice_id,
        api_key=api_key,
        tts_settings=tts_settings,
    )

    return audio_bytes


def get_audio_duration(audio_bytes: bytes) -> float | None:
    # Removed ffprobe dependency. We simply return None.
    return None


def resolve_voice_id(voice_name: str = "") -> str:
    voice_map = _load_voice_map()
    voice_key = str(voice_name or "").strip()
    if voice_key:
        for candidate in (voice_key, voice_key.lower()):
            if candidate in voice_map:
                return str(voice_map[candidate]).strip()
    return _clean_config_value(getattr(settings, "TTS_DEFAULT_VOICE_ID", ""))


def _load_voice_map() -> dict[str, str]:
    raw_map = getattr(settings, "TTS_VOICE_ID_MAP", {}) or {}
    if isinstance(raw_map, dict):
        parsed = raw_map
    else:
        try:
            parsed = json.loads(str(raw_map))
        except json.JSONDecodeError:
            logger.warning("TTS_VOICE_ID_MAP is not valid JSON; ignoring it.")
            parsed = {}

    normalized = {}
    for key, value in parsed.items():
        cleaned_value = _clean_config_value(value)
        if not cleaned_value:
            continue
        normalized[str(key).strip()] = cleaned_value
        normalized[str(key).strip().lower()] = cleaned_value
    return normalized


def _clean_config_value(value: Any) -> str:
    cleaned = str(value or "").strip()
    if cleaned in {"", "...", "None", "none", "null", "NULL"}:
        return ""
    return cleaned


def _generate_elevenlabs_audio(
    *,
    text: str,
    voice_id: str,
    api_key: str,
    tts_settings: dict[str, Any] | None,
) -> bytes | None:
    cleaned_text = _clean_ssml_for_elevenlabs(text)
    cleaned_text = _normalize_meditation_text(cleaned_text)

    voice_settings = _normalize_tts_settings(tts_settings)

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": cleaned_text,
        "model_id": getattr(settings, "TTS_MODEL", "eleven_multilingual_v2"),
        "voice_settings": voice_settings,
    }
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }

    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(
                "ElevenLabs request — voice: %s, stability: %.2f, style: %.2f, text length: %s chars",
                voice_id,
                voice_settings["stability"],
                voice_settings["style"],
                len(cleaned_text),
            )

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=getattr(settings, "TTS_TIMEOUT_SECONDS", 120),
            )

            response.raise_for_status()

            logger.info(
                "ElevenLabs returned %s bytes of audio",
                len(response.content)
            )
            break
        except requests.RequestException as exc:
            if attempt == max_retries - 1:
                raise TTSGenerationError(
                    f"ElevenLabs TTS generation failed after {max_retries} attempts: {exc}"
                ) from exc
            logger.warning("ElevenLabs connection failed (attempt %d/%d): %s. Retrying...", attempt + 1, max_retries, exc)
            time.sleep(2 ** attempt)

    if len(response.content) < 1000:
        raise TTSGenerationError(
            f"ElevenLabs returned unexpectedly small audio: {len(response.content)} bytes."
        )
    return response.content


def _normalize_tts_settings(tts_settings: dict[str, Any] | None) -> dict[str, Any]:
    try:
        from apps.ai_service.models import TTSSettings
        db_settings = TTSSettings.get_settings()
        default_settings = {
            "stability": db_settings.stability,
            "similarity_boost": db_settings.similarity_boost,
            "style": db_settings.style,
            "use_speaker_boost": db_settings.use_speaker_boost,
        }
    except Exception as e:
        logger.warning("Could not fetch dynamic TTS settings: %s. Using hardcoded defaults.", e)
        default_settings = DEFAULT_TTS_SETTINGS

    normalized = dict(default_settings)
    if tts_settings:
        for key in ("stability", "similarity_boost", "style"):
            if key in tts_settings:
                normalized[key] = max(0.0, min(1.0, float(tts_settings[key])))
        if "use_speaker_boost" in tts_settings:
            normalized["use_speaker_boost"] = bool(tts_settings["use_speaker_boost"])
    return normalized


def _clean_ssml_for_elevenlabs(text: str) -> str:
    break_tags = re.findall(r'<break\s+time="[^"]*"\s*/>', text)
    for index, tag in enumerate(break_tags):
        text = text.replace(tag, f"__BREAK_{index}__", 1)
    text = re.sub(r"<[^>]+>", "", text)
    for index, tag in enumerate(break_tags):
        text = text.replace(f"__BREAK_{index}__", tag, 1)
    return text.strip()


def _normalize_meditation_text(text: str) -> str:
    """Force an extremely slow, uniform meditation pacing for ElevenLabs using 
    natural punctuation syntax, avoiding invalid SSML tags.
    """
    import re as _re
    
    # 1. Strip out any accidental XML/SSML tags entirely
    text = _re.sub(r'<[^>]+>', '', text)
    
    # 2. Standardize all dashes, colons, and semi-colons into clean commas
    text = text.replace(' - ', ', ')
    text = text.replace(' — ', ', ')
    text = text.replace('–', ', ')
    text = text.replace(':', ', ')
    text = text.replace(';', ', ')
    
    # 3. Clean up multiple periods or spaces
    text = _re.sub(r'\.{2,}', '.', text)
    text = _re.sub(r'\s+', ' ', text)
    
    # 4. Convert commas and periods to trailing reflections.
    # ElevenLabs treats '... ' as a natural trailing pause.
    text = text.replace(', ', '... , ')
    text = text.replace('. ', '... .   ')
    text = text.replace('! ', '... .   ')
    text = text.replace('? ', '... .   ')
    
    return text.strip()
