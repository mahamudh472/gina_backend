import json
import logging
import re
import subprocess
import tempfile
from typing import Any

import requests
from django.conf import settings

from apps.ai_service.exceptions import TTSGenerationError

logger = logging.getLogger(__name__)

DEFAULT_TTS_SETTINGS = {
    "stability": 0.75,
    "similarity_boost": 0.70,
    "style": 0.35,
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

    return _generate_elevenlabs_audio(
        text=text,
        voice_id=resolved_voice_id,
        api_key=api_key,
        tts_settings=tts_settings,
    )


def get_audio_duration(audio_bytes: bytes) -> float | None:
    """Return audio duration in seconds for generated audio bytes."""
    if not audio_bytes:
        return None

    with tempfile.NamedTemporaryFile(suffix=".mp3") as audio_file:
        audio_file.write(audio_bytes)
        audio_file.flush()

        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    audio_file.name,
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (subprocess.SubprocessError, FileNotFoundError) as exc:
            logger.warning("Could not read generated audio duration with ffprobe: %s", exc)
            return None

    try:
        duration = float(result.stdout.strip())
    except ValueError:
        logger.warning("ffprobe returned an invalid duration: %r", result.stdout)
        return None

    return duration if duration > 0 else None


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

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=getattr(settings, "TTS_TIMEOUT_SECONDS", 120),
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise TTSGenerationError(f"ElevenLabs TTS generation failed: {exc}") from exc

    if len(response.content) < 1000:
        raise TTSGenerationError(
            f"ElevenLabs returned unexpectedly small audio: {len(response.content)} bytes."
        )
    return response.content


def _normalize_tts_settings(tts_settings: dict[str, Any] | None) -> dict[str, Any]:
    normalized = dict(DEFAULT_TTS_SETTINGS)
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
