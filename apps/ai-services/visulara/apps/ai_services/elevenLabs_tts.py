import requests
import os
import re
import logging
from dotenv import load_dotenv
from fastapi import HTTPException

from pathlib import Path

# Load environment variables
env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

# Default voice settings for meditation (calm and consistent)
DEFAULT_TTS_SETTINGS = {
    "stability": 0.75,
    "similarity_boost": 0.70,
    "style": 0.35,
    "use_speaker_boost": True,
}


def _clean_ssml_for_elevenlabs(text: str) -> str:
    """
    ElevenLabs only supports <break time="Xs"/> tags.
    Strip any other SSML tags that Gemini might have included.
    """
    # Keep <break .../> tags
    # Remove any other XML/SSML tags like <prosody>, <speak>, etc.
    # First, preserve break tags by replacing them with placeholders
    break_tags = re.findall(r'<break\s+time="[^"]*"\s*/>', text)
    for i, tag in enumerate(break_tags):
        text = text.replace(tag, f"__BREAK_{i}__", 1)

    # Remove all remaining XML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Restore break tags
    for i, tag in enumerate(break_tags):
        text = text.replace(f"__BREAK_{i}__", tag, 1)

    return text.strip()


def generate_voice(
    text: str,
    voice_id: str,
    tts_settings: dict | None = None,
) -> bytes:
    """
    Convert text to speech using ElevenLabs API.
    
    Args:
        text: The script text (may contain <break> tags for pauses)
        voice_id: ElevenLabs voice ID
        tts_settings: Optional voice settings (stability, similarity_boost, style)
                      from Gemini's voice_direction. Falls back to meditation defaults.
    
    Returns: Audio bytes (mp3)
    """

    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text for voice generation cannot be empty.")

    if not voice_id or not voice_id.strip():
        raise HTTPException(status_code=400, detail="Voice ID is required.")

    # Resilient voice ID handling (fix known typos/case issues)
    if voice_id == "GeMOKAyLhgh6H4xez46a": # Common typo from previous config
        voice_id = "GeMOKAylhgh6H4xez46a"

    # Clean the text — keep only supported SSML tags
    cleaned_text = _clean_ssml_for_elevenlabs(text)

    # Merge provided TTS settings with defaults
    settings = {**DEFAULT_TTS_SETTINGS}
    if tts_settings:
        for key in ("stability", "similarity_boost", "style"):
            if key in tts_settings:
                # Clamp values between 0 and 1
                settings[key] = max(0.0, min(1.0, float(tts_settings[key])))

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json",
    }

    data = {
        "text": cleaned_text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": settings["stability"],
            "similarity_boost": settings["similarity_boost"],
            "style": settings["style"],
            "use_speaker_boost": settings.get("use_speaker_boost", True),
        },
    }

    logger.info(
        f"ElevenLabs request — voice: {voice_id}, "
        f"stability: {settings['stability']}, "
        f"style: {settings['style']}, "
        f"text length: {len(cleaned_text)} chars"
    )

    try:
        response = requests.post(url, headers=headers, json=data, timeout=120)
    except requests.exceptions.Timeout:
        logger.error("ElevenLabs API request timed out.")
        raise HTTPException(status_code=504, detail="Voice service timed out. Please try again.")
    except requests.exceptions.RequestException as e:
        logger.error(f"ElevenLabs API request failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to connect to voice service.")

    if response.status_code != 200:
        logger.error(f"ElevenLabs API returned status {response.status_code}: {response.text}")

        if response.status_code == 401:
            raise HTTPException(status_code=502, detail="Voice service authentication failed.")
        elif response.status_code == 429:
            raise HTTPException(status_code=429, detail="Voice service rate limit reached. Please wait and try again.")
        else:
            raise HTTPException(
                status_code=502,
                detail="Voice service returned an error. Please try again later.",
            )

    if not response.content or len(response.content) < 1000:
        logger.error(f"ElevenLabs returned suspiciously small audio: {len(response.content)} bytes")
        raise HTTPException(status_code=502, detail="Voice service returned invalid audio data.")

    logger.info(f"ElevenLabs returned {len(response.content)} bytes of audio")
    return response.content