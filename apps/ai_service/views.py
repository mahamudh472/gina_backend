import logging
import os
import time
import uuid
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.shortcuts import redirect, render

from apps.ai_service.exceptions import TTSGenerationError
from apps.ai_service.models import TTSSettings
from apps.ai_service.tts import DEFAULT_TTS_SETTINGS, generate_step_audio
from apps.main.models import CharecterVoice

logger = logging.getLogger(__name__)


def cleanup_old_temp_audio():
    """Deletes temporary generated audio files in media/tmp_audio/ older than 1 hour."""
    try:
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'tmp_audio')
        if os.path.exists(temp_dir):
            now = time.time()
            for f in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, f)
                # 3600 seconds = 1 hour
                if os.path.isfile(file_path) and os.stat(file_path).st_mtime < now - 3600:
                    try:
                        os.remove(file_path)
                    except OSError as e:
                        logger.warning("Could not delete temp audio file %s: %s", file_path, e)
    except Exception as e:
        logger.error("Error running temp audio cleanup: %s", e)


@staff_member_required
def generate_audio_admin_view(request):
    voices = CharecterVoice.objects.filter(is_active=True).order_by('name')

    # Load defaults
    try:
        db_settings = TTSSettings.get_settings()
        default_settings = {
            "stability": db_settings.stability,
            "similarity_boost": db_settings.similarity_boost,
            "style": db_settings.style,
            "use_speaker_boost": db_settings.use_speaker_boost,
        }
    except Exception as e:
        logger.warning("Could not load dynamic TTS settings for admin page, using code defaults: %s", e)
        default_settings = DEFAULT_TTS_SETTINGS

    # Read overrides from session, or default
    stability = request.session.get('tts_stability', default_settings['stability'])
    similarity_boost = request.session.get('tts_similarity_boost', default_settings['similarity_boost'])
    style = request.session.get('tts_style', default_settings['style'])
    use_speaker_boost = request.session.get('tts_use_speaker_boost', default_settings['use_speaker_boost'])
    voice_id = request.session.get('tts_voice_id', '')
    text = request.session.get('tts_text', '')

    audio_url = None

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'reset':
            # Clear overrides from session
            for key in ['tts_stability', 'tts_similarity_boost', 'tts_style', 'tts_use_speaker_boost', 'tts_voice_id', 'tts_text']:
                if key in request.session:
                    del request.session[key]
            messages.success(request, "TTS settings reset to defaults.")
            return redirect('admin_generate_audio')

        elif action == 'generate':
            # Extract form values
            text = request.POST.get('text', '').strip()
            voice_id = request.POST.get('voice_id', '').strip()

            try:
                stability = float(request.POST.get('stability', stability))
                similarity_boost = float(request.POST.get('similarity_boost', similarity_boost))
                style = float(request.POST.get('style', style))
            except ValueError:
                pass

            use_speaker_boost = request.POST.get('use_speaker_boost') in ['on', 'true', True]

            # Save overrides in session
            request.session['tts_stability'] = stability
            request.session['tts_similarity_boost'] = similarity_boost
            request.session['tts_style'] = style
            request.session['tts_use_speaker_boost'] = use_speaker_boost
            request.session['tts_voice_id'] = voice_id
            request.session['tts_text'] = text

            if not text:
                messages.error(request, "Please enter some script text.")
            else:
                try:
                    # Resolve voice name if matching CharacterVoice is found
                    voice_name = ""
                    if voice_id:
                        voice_obj = CharecterVoice.objects.filter(elevenlabs_voice_id=voice_id).first()
                        if voice_obj:
                            voice_name = voice_obj.name

                    tts_settings = {
                        "stability": stability,
                        "similarity_boost": similarity_boost,
                        "style": style,
                        "use_speaker_boost": use_speaker_boost,
                    }

                    audio_bytes = generate_step_audio(
                        text=text,
                        voice_name=voice_name,
                        voice_id=voice_id,
                        tts_settings=tts_settings,
                    )

                    if not audio_bytes:
                        raise TTSGenerationError("TTS provider returned empty audio content.")

                    # Save temporary file
                    os.makedirs(os.path.join(settings.MEDIA_ROOT, 'tmp_audio'), exist_ok=True)
                    filename = f"tmp_audio/tts_gen_{uuid.uuid4().hex}.mp3"
                    saved_path = default_storage.save(filename, ContentFile(audio_bytes))
                    audio_url = default_storage.url(saved_path)

                    messages.success(request, "Audio generated successfully!")
                    cleanup_old_temp_audio()

                except TTSGenerationError as e:
                    messages.error(request, f"TTS Generation Error: {e}")
                except Exception as e:
                    logger.exception("Unexpected error during TTS generation: %s", e)
                    messages.error(request, f"An unexpected error occurred: {e}")

    context = {
        **admin.site.each_context(request),
        'title': 'Audio Generator',
        'subtitle': 'Generate speech audio using ElevenLabs',
        'voices': voices,
        'stability': stability,
        'similarity_boost': similarity_boost,
        'style': style,
        'use_speaker_boost': use_speaker_boost,
        'voice_id': voice_id,
        'text': text,
        'audio_url': audio_url,
    }

    return render(request, 'admin/generate_audio.html', context)
