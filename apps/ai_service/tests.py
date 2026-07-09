from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.ai_service.models import TTSSettings
from apps.ai_service.tts import _normalize_tts_settings


class TTSSettingsTests(TestCase):
    def test_singleton_creation(self):
        # Initial call to get_settings should create the instance
        settings = TTSSettings.get_settings()
        self.assertEqual(settings.pk, 1)
        self.assertEqual(settings.stability, 0.40)
        self.assertEqual(settings.similarity_boost, 0.60)
        self.assertEqual(settings.style, 0.45)
        self.assertEqual(settings.use_speaker_boost, True)

        # Re-fetching should return the same object
        settings_again = TTSSettings.get_settings()
        self.assertEqual(settings_again.pk, 1)
        self.assertEqual(TTSSettings.objects.count(), 1)

    def test_singleton_save_forces_pk(self):
        # Save a new instance with different pk - it should overwrite pk=1
        new_settings = TTSSettings(pk=2, stability=0.80)
        new_settings.save()
        self.assertEqual(new_settings.pk, 1)
        self.assertEqual(TTSSettings.objects.count(), 1)

        fetched = TTSSettings.get_settings()
        self.assertEqual(fetched.stability, 0.80)

    def test_validators_enforce_range(self):
        # stability validation
        invalid_settings = TTSSettings(stability=1.5)
        with self.assertRaises(ValidationError):
            invalid_settings.full_clean()

        # similarity_boost validation
        invalid_settings = TTSSettings(similarity_boost=-0.1)
        with self.assertRaises(ValidationError):
            invalid_settings.full_clean()

    def test_normalize_tts_settings_uses_db_values(self):
        # Set custom settings in DB
        db_settings = TTSSettings.get_settings()
        db_settings.stability = 0.75
        db_settings.similarity_boost = 0.85
        db_settings.style = 0.95
        db_settings.use_speaker_boost = False
        db_settings.save()

        # Call normalization without input parameters - should yield DB values
        normalized = _normalize_tts_settings(None)
        self.assertEqual(normalized["stability"], 0.75)
        self.assertEqual(normalized["similarity_boost"], 0.85)
        self.assertEqual(normalized["style"], 0.95)
        self.assertEqual(normalized["use_speaker_boost"], False)

        # Call normalization with specific overriding parameters - should override
        normalized = _normalize_tts_settings({
            "stability": 0.50,
            "use_speaker_boost": True
        })
        self.assertEqual(normalized["stability"], 0.50)
        self.assertEqual(normalized["similarity_boost"], 0.85)
        self.assertEqual(normalized["style"], 0.95)
        self.assertEqual(normalized["use_speaker_boost"], True)


from unittest.mock import patch
from django.test import override_settings
from apps.ai_service.tts import generate_step_audio

class TTSGenerationTests(TestCase):
    @patch("apps.ai_service.tts._generate_elevenlabs_audio")
    @override_settings(
        TTS_GENERATE_AUDIO=True,
        TTS_PROVIDER="elevenlabs",
        TTS_API_KEY="test-api-key",
        TTS_DEFAULT_VOICE_ID="default-voice-id-env",
        TTS_VOICE_ID_MAP='{"Aura": "aura-voice-id-env"}'
    )
    def test_generate_step_audio_resolves_voice_id(self, mock_generate):
        mock_generate.return_value = b"mock audio content"

        # Scenario 1: voice_id is passed and is valid -> should use the passed voice_id
        generate_step_audio(text="Hello", voice_name="Aura", voice_id="custom-voice-id")
        mock_generate.assert_called_with(
            text="Hello",
            voice_id="custom-voice-id",
            api_key="test-api-key",
            tts_settings=None
        )

        # Scenario 2: voice_id is None -> should fall back to voice_name matching env voice map
        generate_step_audio(text="Hello", voice_name="Aura", voice_id=None)
        mock_generate.assert_called_with(
            text="Hello",
            voice_id="aura-voice-id-env",
            api_key="test-api-key",
            tts_settings=None
        )

        # Scenario 3: voice_id is empty string -> should fall back to voice_name matching env voice map
        generate_step_audio(text="Hello", voice_name="Aura", voice_id="")
        mock_generate.assert_called_with(
            text="Hello",
            voice_id="aura-voice-id-env",
            api_key="test-api-key",
            tts_settings=None
        )

        # Scenario 4: voice_name doesn't match map, voice_id is missing -> should use default env voice ID
        generate_step_audio(text="Hello", voice_name="Unknown", voice_id="")
        mock_generate.assert_called_with(
            text="Hello",
            voice_id="default-voice-id-env",
            api_key="test-api-key",
            tts_settings=None
        )


from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from apps.main.models import CharecterVoice

class AdminAudioGeneratorTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.admin_user = self.User.objects.create_superuser(
            email="admin@example.com",
            password="adminpassword"
        )
        self.client = Client()
        
    def test_view_requires_staff(self):
        url = reverse('admin_generate_audio')
        response = self.client.get(url)
        # Should redirect to login page because user is not authenticated
        self.assertEqual(response.status_code, 302)
        self.assertTrue("login" in response.url)

    def test_get_renders_defaults(self):
        self.client.force_login(self.admin_user)
        url = reverse('admin_generate_audio')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TTS Audio Generator")
        
        # Stability field default value is 0.40 in TTSSettings/DEFAULT_TTS_SETTINGS
        self.assertContains(response, 'value="0.4"')
        self.assertContains(response, '0.40')

    def test_get_renders_session_overrides(self):
        self.client.force_login(self.admin_user)
        session = self.client.session
        session['tts_stability'] = 0.88
        session['tts_similarity_boost'] = 0.99
        session['tts_style'] = 0.12
        session['tts_use_speaker_boost'] = False
        session['tts_text'] = "Override text"
        session.save()
        
        url = reverse('admin_generate_audio')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="0.88"')
        self.assertContains(response, '0.88')
        self.assertContains(response, 'Override text')

    @patch("apps.ai_service.views.generate_step_audio")
    def test_post_generate_saves_overrides_and_creates_file(self, mock_generate):
        mock_generate.return_value = b"fake audio bytes"
        self.client.force_login(self.admin_user)
        
        # Create character voice
        voice = CharecterVoice.objects.create(
            name="Test Voice",
            elevenlabs_voice_id="test-voice-id",
            file="uploads/audio/dummy.mp3",
            is_active=True
        )

        url = reverse('admin_generate_audio')
        post_data = {
            "action": "generate",
            "voice_id": "test-voice-id",
            "stability": "0.77",
            "similarity_boost": "0.88",
            "style": "0.15",
            "use_speaker_boost": "on",
            "text": "Hello, this is a test script."
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Audio generated successfully!")
        
        # Verify call parameters
        mock_generate.assert_called_once_with(
            text="Hello, this is a test script.",
            voice_name="Test Voice",
            voice_id="test-voice-id",
            tts_settings={
                "stability": 0.77,
                "similarity_boost": 0.88,
                "style": 0.15,
                "use_speaker_boost": True
            }
        )

        # Verify session values
        session = self.client.session
        self.assertEqual(session.get("tts_stability"), 0.77)
        self.assertEqual(session.get("tts_similarity_boost"), 0.88)
        self.assertEqual(session.get("tts_style"), 0.15)
        self.assertEqual(session.get("tts_use_speaker_boost"), True)
        self.assertEqual(session.get("tts_voice_id"), "test-voice-id")
        self.assertEqual(session.get("tts_text"), "Hello, this is a test script.")

    def test_post_reset_clears_session(self):
        self.client.force_login(self.admin_user)
        session = self.client.session
        session['tts_stability'] = 0.88
        session['tts_text'] = "some script text"
        session.save()

        url = reverse('admin_generate_audio')
        response = self.client.post(url, {"action": "reset"})
        
        # Should redirect back
        self.assertEqual(response.status_code, 302)
        
        # Check that session is cleared
        session_after = self.client.session
        self.assertNotIn("tts_stability", session_after)
        self.assertNotIn("tts_text", session_after)

