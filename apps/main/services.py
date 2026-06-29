from typing import Dict, Any
import datetime
import re
from django.db import transaction
from django.core.files.base import ContentFile
from apps.main.models import Meditation, MeditationSteps, CharecterVoice, BackgroundImage, NatureSounds
from apps.ai_service.exceptions import TTSGenerationError
from apps.ai_service.tts import generate_step_audio
from apps.main.utils import generate_meditation_content
from apps.accounts.models import User

def create_generated_meditation(data: Dict[str, Any], user: User) -> Meditation:
    """
    Creates and generates a complete Meditation object and its associated MeditationSteps.
    All parameters are resolved, and the generation process runs inside an atomic transaction.
    """
    category = data.get('category')
    charecter_voice_id = data.get('charecter_voice_id')
    experience_question_answers = data.get('experience_question_answers')
    nature_sound_name = data.get('nature_sound_name')
    background_image_id = data.get('background_image_id')

    # Fetch required CharacterVoice
    charecter_voice = CharecterVoice.objects.get(id=charecter_voice_id)
    
    # Resolve optional background image
    background_image = None
    if background_image_id:
        background_image = BackgroundImage.objects.filter(id=background_image_id).first()

    # Resolve nature sound by name (case-insensitive search)
    nature_sound = None
    if nature_sound_name:
        nature_sound = NatureSounds.objects.filter(name__iexact=nature_sound_name.strip()).first()

    # Generate personalized title and beautiful German step texts
    # This function is configured to pass all context for future AI generation
    title, steps_data = generate_meditation_content(
        category=category, 
        q_a=experience_question_answers,
        voice_name=charecter_voice.name,
        nature_sound_name=nature_sound.name if nature_sound else "",
        background_image_name=background_image.name if background_image else ""
    )


    # Set the static cover image for the banner based on meditation category
    from django.templatetags.static import static
    
    cover_map = {
        "relaxation": "Cover_Entspannung.jpg",
        "self_love": "Cover_Selbstliebe.jpg",
        "focus_clarity": "Cover-Fokus_Klarheit.jpg",
        "gratitude": "Cover-Dankbarkeit.jpg",
        "trust": "Cover_Vertrauen.jpg",
        "energy": "Cover_Energie.jpg",
        "transformation": "Cover_Transformation.jpg",
        "inner_peace": "Cover-innerer-Frieden.jpg"
    }
    
    cover_filename = cover_map.get(category)
    banner_url = static(f"Cover/{cover_filename}") if cover_filename else None


    with transaction.atomic():
        # Create primary Meditation
        meditation = Meditation.objects.create(
            user=user,
            title=title,
            banner_url=banner_url,
            background_image=background_image,
            charecter_voice=charecter_voice,
            nature_sound=nature_sound,
            experience_question_answer=experience_question_answers,
            category=category
        )

        # Create associated steps
        for index, step in enumerate(steps_data, start=1):
            audio_file, measured_duration = _build_step_audio_file(
                step=step,
                meditation_id=meditation.id,
                sequence=index,
                voice_name=charecter_voice.name,
                voice_id=charecter_voice.elevenlabs_voice_id,
            )
            
            MeditationSteps.objects.create(
                meditation=meditation,
                step_type=step["step_type"],
                content=step["content"],
                duration=measured_duration,
                audio_file=audio_file
            )

    return meditation


def _build_step_audio_file(
    *,
    step: Dict[str, Any],
    meditation_id: int,
    sequence: int,
    voice_name: str,
    voice_id: str | None = None,
):
    audio_bytes = generate_step_audio(
        text=step["content"],
        voice_name=voice_name,
        voice_id=voice_id,
        tts_settings=step.get("tts_settings"),
    )
    if not audio_bytes:
        raise TTSGenerationError("TTS provider returned empty audio.")

    step_type = _slugify_audio_name(step["step_type"])
    filename = f"generated/meditation-{meditation_id}-step-{sequence}-{step_type}.mp3"

    # Use the AI-generated duration from the step data (already a timedelta)
    duration = step.get("duration")
    if not isinstance(duration, datetime.timedelta):
        raise TTSGenerationError("Step is missing a valid duration.")

    return ContentFile(audio_bytes, name=filename), duration


def _slugify_audio_name(value: Any) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return slug or "audio"
