from typing import Dict, Any
from django.db import transaction
from apps.main.models import Meditation, MeditationSteps, CharecterVoice, BackgroundImage, NatureSounds
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
        for step in steps_data:
            # Assign the character voice's main audio file to the step's audio field
            audio_file = charecter_voice.file if charecter_voice.file else None
            
            MeditationSteps.objects.create(
                meditation=meditation,
                step_type=step["step_type"],
                content=step["content"],
                duration=step["duration"],
                audio_file=audio_file
            )

    return meditation
