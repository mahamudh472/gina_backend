"""
Debugging & Testing Script for ElevenLabs Voice Generation in Meditation Pipeline.

This script isolates and simulates the exact workflow from script input -> text normalization -> 
ElevenLabs TTS API call -> audio duration calculation -> saving the output audio file.
It uses real functions from the codebase.
"""

import os
import sys
import logging
import datetime
from pathlib import Path

# -----------------------------------------------------------------------------
# 1. Setup Django Environment
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visulara.settings')

import django
django.setup()

from django.conf import settings
from apps.ai_service.tts import (
    generate_step_audio,
    get_audio_duration,
    resolve_voice_id,
    _replace_pauses_with_ssml,
    _clean_ssml_for_elevenlabs,
    _normalize_meditation_text,
    _normalize_tts_settings,
)
from apps.ai_service.exceptions import TTSGenerationError
from apps.main.models import CharecterVoice

# Setup logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s [%(name)s]: %(message)s'
)
logger = logging.getLogger("test_voice_generation")


# =============================================================================
# USER CONFIGURABLE VARIABLES FOR DEBUGGING
# Edit the text, voice, and settings below to test different scenarios:
# =============================================================================

# Add your speech / meditation step text here
# You can use pause tags like [[pause_2s]], standard punctuation, or German text.
SPEECH_TEXT = """
Eine kurze Mediationsrede

Guten Tag zusammen,

ich möchte kurz die wichtigsten Informationen zu diesem Thema zusammenfassen und sie für alle verständlich erklären.

Zunächst ist es wichtig zu wissen, dass unterschiedliche Menschen oft verschiedene Meinungen und Erfahrungen haben. Deshalb sollte man versuchen, die Perspektiven aller Beteiligten zu berücksichtigen. Wenn es zu einem Konflikt kommt, ist es besonders wichtig, ruhig miteinander zu sprechen und einander zuzuhören.

Ein möglicher Lösungsansatz besteht darin, zunächst die unterschiedlichen Standpunkte zu klären. Danach kann man gemeinsam überlegen, welche Lösung für alle Beteiligten möglichst fair ist. Dabei sollte niemand das Gefühl haben, dass seine Meinung ignoriert wird.

Meiner Meinung nach ist eine offene und respektvolle Kommunikation der beste Weg, um Missverständnisse zu vermeiden und gemeinsam eine gute Lösung zu finden.

Vielen Dank fürs Zuhören.
"""

# Voice Name (e.g. "Alexander", "Serena") or explicit ElevenLabs Voice ID
VOICE_NAME = "Serena"  
VOICE_ID = ""  # If set, this overrides VOICE_NAME

# Recommended settings for WARM + LOUDER voice:
# - stability (0.50): Keeps the voice warm and steady without sounding harsh or formal.
# - similarity_boost (0.85): High similarity preserves rich, warm vocal frequencies.
# - style (0.05): Low style avoids artificial dramatic shouting or strained cadence.
# - use_speaker_boost (True): Boosts ElevenLabs audio output power and clarity.
# - volume_boost_db (4.0): Applies clean +4.0 dB volume gain boost via FFmpeg backend.
TTS_SETTINGS_OVERRIDE = {
    "stability": 0.50,
    "similarity_boost": 0.85,
    "style": 0.05,
    "use_speaker_boost": True,
    "volume_boost_db": 4.0,
}

# Output file path where the generated audio file will be saved
OUTPUT_FILENAME = "debug_meditation_voice.mp3"


# =============================================================================
# TEST / DEBUG EXECUTION FUNCTION
# =============================================================================

def run_tts_debug():
    print("=" * 80)
    print(" 🎙️ ELEVENLABS MEDITATION VOICE GENERATION DEBUGGER")
    print("=" * 80)

    # 1. Inspect Environment & Settings
    print("\n--- 1. Configuration & Settings ---")
    print(f"TTS_PROVIDER       : {getattr(settings, 'TTS_PROVIDER', 'N/A')}")
    print(f"TTS_MODEL          : {getattr(settings, 'TTS_MODEL', 'N/A')}")
    print(f"TTS_GENERATE_AUDIO : {getattr(settings, 'TTS_GENERATE_AUDIO', 'N/A')}")
    api_key = getattr(settings, "TTS_API_KEY", "")
    print(f"TTS_API_KEY        : {'Configured (' + api_key[:6] + '...' + api_key[-4:] + ')' if api_key else '❌ MISSING!'}")

    # Available Voices in DB
    db_voices = list(CharecterVoice.objects.filter(is_active=True).values('name', 'elevenlabs_voice_id'))
    print("\n[DB Active Character Voices]:")
    for v in db_voices:
        print(f"  - {v['name']}: {v['elevenlabs_voice_id']}")

    # Resolve Voice ID: Check DB CharacterVoice first (like Admin Panel / Meditation creation), then fallback to resolve_voice_id()
    db_voice = CharecterVoice.objects.filter(name__iexact=VOICE_NAME.strip()).first()
    if VOICE_ID.strip():
        resolved_voice_id = VOICE_ID.strip()
        resolution_source = "Explicit VOICE_ID variable"
    elif db_voice and db_voice.elevenlabs_voice_id:
        resolved_voice_id = db_voice.elevenlabs_voice_id.strip()
        resolution_source = f"Database CharacterVoice '{db_voice.name}'"
    else:
        resolved_voice_id = resolve_voice_id(VOICE_NAME)
        resolution_source = ".env TTS_VOICE_ID_MAP fallback"

    print(f"\nTarget Voice Name  : '{VOICE_NAME}'")
    print(f"Resolved Voice ID  : '{resolved_voice_id}' ({resolution_source})")

    if not resolved_voice_id:
        print("❌ ERROR: Could not resolve a valid ElevenLabs Voice ID!")
        return

    # 2. Text Transformation Pipeline Debug
    print("\n--- 2. Script & Text Processing Pipeline ---")
    print("[RAW SCRIPT]:")
    print(f"  {repr(SPEECH_TEXT.strip())}")

    # Check pause replacement
    processed_pauses = _replace_pauses_with_ssml(SPEECH_TEXT)
    print("\n[AFTER PAUSE TAG REPLACEMENT ([[pause_Xs]] -> SSML <break>)]:")
    print(f"  {repr(processed_pauses)}")

    # Clean SSML
    cleaned_ssml = _clean_ssml_for_elevenlabs(processed_pauses)

    # Final normalized text sent to ElevenLabs
    final_elevenlabs_text = _normalize_meditation_text(cleaned_ssml)
    print("\n[FINAL TEXT SENT TO ELEVENLABS]:")
    print(f"  {repr(final_elevenlabs_text)}")

    # Settings normalization
    effective_settings = _normalize_tts_settings(TTS_SETTINGS_OVERRIDE)
    print("\n[EFFECTIVE TTS SETTINGS]:")
    for k, v in effective_settings.items():
        print(f"  - {k}: {v}")

    # 3. ElevenLabs API Generation
    print("\n--- 3. Sending Script to ElevenLabs ---")
    try:
        print("Requesting voice audio from ElevenLabs...")
        audio_bytes = generate_step_audio(
            text=SPEECH_TEXT,
            voice_name=VOICE_NAME,
            voice_id=resolved_voice_id,
            tts_settings=TTS_SETTINGS_OVERRIDE
        )

        if not audio_bytes:
            print("❌ ERROR: Received empty audio bytes back from generate_step_audio.")
            return

        audio_len_bytes = len(audio_bytes)
        print(f"✅ Audio generated successfully! Received {audio_len_bytes} bytes ({audio_len_bytes / 1024:.2f} KB).")

        # 4. Measure Duration with Mutagen
        print("\n--- 4. Audio Duration Measurement ---")
        duration_sec = get_audio_duration(audio_bytes)
        if duration_sec is not None:
            print(f"Measured Audio Duration: {duration_sec:.2f} seconds ({datetime.timedelta(seconds=duration_sec)})")
        else:
            print("⚠️ Warning: Could not parse MP3 duration using mutagen.")

        # 5. Save Output File
        print("\n--- 5. Saving Audio File ---")
        save_dir = os.path.join(settings.MEDIA_ROOT, "generated_test_audio")
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, OUTPUT_FILENAME)

        with open(save_path, "wb") as f:
            f.write(audio_bytes)

        print(f"✅ Audio file successfully saved to:")
        print(f"   📂 Absolute Path: {os.path.abspath(save_path)}")

    except TTSGenerationError as e:
        print(f"\n❌ TTS GENERATION ERROR: {e}")
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print(" Execution finished.")
    print("=" * 80)


if __name__ == '__main__':
    run_tts_debug()
