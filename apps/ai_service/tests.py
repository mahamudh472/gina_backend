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
                "use_speaker_boost": True,
                "volume_boost_db": 0.0,
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


from apps.ai_service.models import MeditationPrompt
from apps.ai_service.meditation import (
    build_prompt,
    build_request_data,
    DEFAULT_CATEGORY,
    DEFAULT_PROMPT_TEMPLATE,
    CATEGORY_GUIDANCE,
    CATEGORY_LABELS,
)
from apps.main.models import MeditationCategory

class MeditationPromptTests(TestCase):
    def test_singleton_active_prompt_saving(self):
        # Clean up any prompts created by data migrations first
        MeditationPrompt.objects.all().delete()

        # Create first active prompt
        prompt1 = MeditationPrompt.objects.create(
            name="Prompt 1",
            prompt_template="Template 1 {user_name}",
            is_active=True
        )
        self.assertTrue(prompt1.is_active)

        # Create second active prompt
        prompt2 = MeditationPrompt.objects.create(
            name="Prompt 2",
            prompt_template="Template 2 {user_name}",
            is_active=True
        )
        # prompt1 should now be deactivated
        prompt1.refresh_from_db()
        self.assertFalse(prompt1.is_active)
        self.assertTrue(prompt2.is_active)

        # Ensure only one is active in DB
        self.assertEqual(MeditationPrompt.objects.filter(is_active=True).count(), 1)

    def test_singleton_active_prompt_deletion(self):
        # Clean up existing prompts
        MeditationPrompt.objects.all().delete()

        # Create two prompts
        prompt1 = MeditationPrompt.objects.create(
            name="Prompt 1",
            prompt_template="Template 1 {user_name}",
            is_active=True
        )
        prompt2 = MeditationPrompt.objects.create(
            name="Prompt 2",
            prompt_template="Template 2 {user_name}",
            is_active=False
        )

        # Delete active prompt
        prompt1.delete()

        # prompt2 should automatically become active
        prompt2.refresh_from_db()
        self.assertTrue(prompt2.is_active)
        self.assertEqual(MeditationPrompt.objects.filter(is_active=True).count(), 1)

    def test_build_prompt_uses_active_prompt_from_db(self):
        # Clean up existing prompts
        MeditationPrompt.objects.all().delete()

        # Create active prompt
        MeditationPrompt.objects.create(
            name="Custom Prompt",
            prompt_template="Hello {user_name}, you chose {category_label}.",
            is_active=True
        )

        data = {
            "category": "self_discovery",
            "category_label": "Identität & Selbstfindung",
            "user_name": "Anna",
            "goal": "Stress abbauen",
            "avoid": "Sorgen",
            "duration": 10,
            "experience": "intermediate",
            "body_tension": ["Nacken"],
            "nature_sound": "ocean",
            "landscape": "beach",
            "voice_name": "Aura",
            "questionnaire_answers": {}
        }

        prompt = build_prompt(data)
        self.assertEqual(prompt, "Hello Anna, you chose Identität & Selbstfindung.")

    def test_build_prompt_fallback_to_default(self):
        # Clean up existing prompts
        MeditationPrompt.objects.all().delete()

        data = {
            "category": "self_discovery",
            "category_label": "Identität & Selbstfindung",
            "user_name": "Anna",
            "goal": "Stress abbauen",
            "avoid": "Sorgen",
            "duration": 10,
            "experience": "intermediate",
            "body_tension": ["Nacken"],
            "nature_sound": "ocean",
            "landscape": "beach",
            "voice_name": "Aura",
            "questionnaire_answers": {}
        }

        # No active prompt in DB, should use fallback
        prompt = build_prompt(data)
        self.assertIn("Du bist eine weltklasse Meditationslehrerin", prompt)
        self.assertIn("Name: Anna", prompt)

    def test_per_category_active_prompts_dont_interfere(self):
        # Clean up existing prompts
        MeditationPrompt.objects.all().delete()

        # Create active prompt for self_discovery
        prompt_relaxation = MeditationPrompt.objects.create(
            name="Self Discovery Prompt",
            category="self_discovery",
            prompt_template="Self Discovery template {user_name}",
            is_active=True
        )

        # Create active prompt for emotional_healing
        prompt_self_love = MeditationPrompt.objects.create(
            name="Emotional Healing Prompt",
            category="emotional_healing",
            prompt_template="Emotional Healing template {user_name}",
            is_active=True
        )

        # Both should remain active since they are in different categories
        prompt_relaxation.refresh_from_db()
        prompt_self_love.refresh_from_db()
        self.assertTrue(prompt_relaxation.is_active)
        self.assertTrue(prompt_self_love.is_active)

    def test_per_category_active_prompt_deletion(self):
        # Clean up existing prompts
        MeditationPrompt.objects.all().delete()

        # Create active prompt for self_discovery
        prompt_relaxation1 = MeditationPrompt.objects.create(
            name="Self Discovery Prompt 1",
            category="self_discovery",
            prompt_template="Self Discovery template 1",
            is_active=True
        )

        # Create inactive prompt for self_discovery
        prompt_relaxation2 = MeditationPrompt.objects.create(
            name="Self Discovery Prompt 2",
            category="self_discovery",
            prompt_template="Self Discovery template 2",
            is_active=False
        )

        # Create active prompt for emotional_healing
        prompt_self_love = MeditationPrompt.objects.create(
            name="Emotional Healing Prompt",
            category="emotional_healing",
            prompt_template="Emotional Healing template",
            is_active=True
        )

        # Delete the active self_discovery prompt
        prompt_relaxation1.delete()

        # self_discovery2 should automatically become active, emotional_healing should remain active
        prompt_relaxation2.refresh_from_db()
        prompt_self_love.refresh_from_db()
        self.assertTrue(prompt_relaxation2.is_active)
        self.assertTrue(prompt_self_love.is_active)

    def test_build_prompt_selects_correct_category_prompt(self):
        # Clean up existing prompts
        MeditationPrompt.objects.all().delete()

        # Create active prompt for self_discovery
        MeditationPrompt.objects.create(
            name="Self Discovery Prompt",
            category="self_discovery",
            prompt_template="Self Discovery {user_name}",
            is_active=True
        )

        # Create active prompt for emotional_healing
        MeditationPrompt.objects.create(
            name="Emotional Healing Prompt",
            category="emotional_healing",
            prompt_template="Emotional Healing {user_name}",
            is_active=True
        )

        data = {
            "category": "emotional_healing",
            "category_label": "Emotionale Heilung",
            "user_name": "Anna",
            "goal": "Selbstliebe staerken",
            "avoid": "Selbstzweifel",
            "duration": 10,
            "experience": "intermediate",
            "body_tension": ["Herzbereich"],
            "nature_sound": "rain",
            "landscape": "forest",
            "voice_name": "Aura",
            "questionnaire_answers": {}
        }

        # Should select the emotional_healing prompt
        prompt = build_prompt(data)
        self.assertEqual(prompt, "Emotional Healing Anna")

    def test_build_prompt_fallback_only_if_category_missing(self):
        # Clean up existing prompts
        MeditationPrompt.objects.all().delete()

        # Create active prompt for self_discovery
        MeditationPrompt.objects.create(
            name="Self Discovery Prompt",
            category="self_discovery",
            prompt_template="Self Discovery {user_name}",
            is_active=True
        )

        # Request emotional_healing which has no prompt
        data = {
            "category": "emotional_healing",
            "category_label": "Emotionale Heilung",
            "user_name": "Anna",
            "goal": "Emotionale Heilung",
            "avoid": "Selbstzweifel",
            "duration": 10,
            "experience": "intermediate",
            "body_tension": ["Herzbereich"],
            "nature_sound": "rain",
            "landscape": "forest",
            "voice_name": "Aura",
            "questionnaire_answers": {}
        }

        # Should fallback to default because emotional_healing has no prompt
        prompt = build_prompt(data)
        self.assertIn("Du bist eine weltklasse Meditationslehrerin", prompt)
        self.assertIn("Name: Anna", prompt)


class MeditationCategoryMappingTests(TestCase):
    """Guards the category -> label/guidance mappings against drift."""

    def test_category_labels_cover_every_known_category(self):
        known = {choice.value for choice in MeditationCategory}
        self.assertEqual(set(CATEGORY_LABELS), known)

    def test_category_guidance_covers_every_known_category(self):
        known = {choice.value for choice in MeditationCategory}
        self.assertEqual(set(CATEGORY_GUIDANCE), known)

    def test_default_category_is_known(self):
        self.assertIn(DEFAULT_CATEGORY, {choice.value for choice in MeditationCategory})
        self.assertIn(DEFAULT_CATEGORY, CATEGORY_LABELS)
        self.assertIn(DEFAULT_CATEGORY, CATEGORY_GUIDANCE)

    def test_build_request_data_resolves_label_for_every_category(self):
        for choice in MeditationCategory:
            data = build_request_data(category=choice.value, q_a={})
            self.assertEqual(data["category_label"], CATEGORY_LABELS[choice.value])

    def test_build_request_data_falls_back_for_unknown_category(self):
        data = build_request_data(category="does_not_exist", q_a={})
        self.assertEqual(data["category_label"], CATEGORY_LABELS[DEFAULT_CATEGORY])


import json
from apps.ai_service.meditation import (
    _validate_payload,
    _generate_with_openai,
    _ensure_format_instructions,
    generate_ai_meditation_content,
    MANDATORY_JSON_FORMAT_TEMPLATE,
)
from apps.ai_service.exceptions import MeditationGenerationError

class ValidatePayloadTests(TestCase):
    def test_standard_payload_validation(self):
        payload = {
            "title": "Inner Calm",
            "steps": [
                {"step_type": "greeting", "content": "Welcome", "duration": 60},
                {"step_type": "personal_reflection", "content": "Reflect", "duration": 240},
            ]
        }
        validated = _validate_payload(payload, 300)
        self.assertEqual(validated["title"], "Inner Calm")
        self.assertEqual(len(validated["steps"]), 2)
        self.assertEqual(validated["total_duration"], 300)

    def test_payload_with_missing_title_falls_back(self):
        payload = {
            "steps": [
                {"step_type": "greeting", "content": "Welcome", "duration": 60},
            ]
        }
        validated = _validate_payload(payload, 60, default_title="Fallback Title")
        self.assertEqual(validated["title"], "Fallback Title")

    def test_payload_with_german_titel_key(self):
        payload = {
            "titel": "Deutsche Meditation",
            "steps": [
                {"step_type": "greeting", "content": "Willkommen", "duration": 60},
            ]
        }
        validated = _validate_payload(payload, 60)
        self.assertEqual(validated["title"], "Deutsche Meditation")

    def test_payload_wrapped_under_root_key(self):
        payload = {
            "meditation": {
                "title": "Wrapped Meditation",
                "steps": [
                    {"step_type": "greeting", "content": "Welcome", "duration": 60},
                ]
            }
        }
        validated = _validate_payload(payload, 60)
        self.assertEqual(validated["title"], "Wrapped Meditation")
        self.assertEqual(len(validated["steps"]), 1)

    def test_payload_with_german_steps_and_fields(self):
        payload = {
            "titel": "Ruhe finden",
            "schritte": [
                {"schritt": "greeting", "inhalt": "Hallo", "dauer": 60},
            ]
        }
        validated = _validate_payload(payload, 60)
        self.assertEqual(validated["title"], "Ruhe finden")
        self.assertEqual(validated["steps"][0]["step_type"], "greeting")
        self.assertEqual(validated["steps"][0]["content"], "Hallo")
        self.assertEqual(validated["steps"][0]["duration"], 60)

    def test_payload_without_steps_raises(self):
        payload = {"title": "No steps"}
        with self.assertRaises(ValueError):
            _validate_payload(payload, 60)

    @patch("openai.OpenAI")
    @override_settings(LLM_PROVIDER="openai", LLM_API_KEY="test-llm-key")
    def test_openai_generation_tolerates_missing_title(self, mock_openai_cls):
        mock_client = mock_openai_cls.return_value
        mock_response = type("Response", (), {})()
        mock_choice = type("Choice", (), {})()
        mock_message = type("Message", (), {})()
        # Model returns JSON without title
        mock_message.content = json.dumps({
            "steps": [
                {"step_type": "greeting", "content": "Hello user", "duration": 60},
                {"step_type": "personal_reflection", "content": "Reflect deep", "duration": 180},
                {"step_type": "suggestion", "content": "Feel peace", "duration": 120},
                {"step_type": "affirmation", "content": "I am calm", "duration": 60},
                {"step_type": "visualization", "content": "Imagine the lake", "duration": 180},
            ]
        })
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        request_data = {
            "category": "self_discovery",
            "category_label": "Identität & Selbstfindung",
            "duration": 10,
            "goal": "Ruhe",
            "avoid": "Stress",
            "experience": "beginner",
            "body_tension": [],
            "nature_sound": "",
            "landscape": "",
            "voice_name": "",
            "user_name": "Test User",
            "questionnaire_answers": {},
        }
        result = _generate_with_openai(request_data)
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Identität & Selbstfindung Meditation")
        self.assertEqual(len(result["steps"]), 5)

    def test_ensure_format_instructions_appends_when_missing(self):
        bare_prompt = "Erstelle eine geführte Meditation für Anna."
        injected = _ensure_format_instructions(bare_prompt, 600)
        self.assertIn("Erstelle eine geführte Meditation für Anna.", injected)
        self.assertIn('"title"', injected)
        self.assertIn('"steps"', injected)
        self.assertIn('"step_type"', injected)
        self.assertIn('"total_duration": 600', injected)

    def test_ensure_format_instructions_does_not_duplicate_when_present(self):
        already_formatted = (
            'Some prompt...\nJSON-Form:\n{"title": "test", "total_duration": 600, "steps": [{"step_type": "greeting"}]}'
        )
        result = _ensure_format_instructions(already_formatted, 600)
        self.assertEqual(result, already_formatted)

    @patch("openai.OpenAI")
    @override_settings(LLM_PROVIDER="openai", LLM_API_KEY="test-llm-key")
    def test_openai_call_injects_format_into_prompt_when_db_prompt_is_bare(self, mock_openai_cls):
        MeditationPrompt.objects.all().delete()
        MeditationPrompt.objects.create(
            name="Bare Admin Prompt",
            category="self_discovery",
            prompt_template="Sprich ruhig und führe den Nutzer.",
            is_active=True,
        )

        mock_client = mock_openai_cls.return_value
        mock_response = type("Response", (), {})()
        mock_choice = type("Choice", (), {})()
        mock_message = type("Message", (), {})()
        mock_message.content = json.dumps({
            "title": "Innere Ruhe",
            "steps": [
                {"step_type": "greeting", "content": "Hi", "duration": 60},
                {"step_type": "personal_reflection", "content": "Reflect", "duration": 240},
                {"step_type": "suggestion", "content": "Suggestions", "duration": 120},
                {"step_type": "affirmation", "content": "Affirmations", "duration": 60},
                {"step_type": "visualization", "content": "Journey", "duration": 120},
            ]
        })
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        request_data = {
            "category": "self_discovery",
            "category_label": "Identität & Selbstfindung",
            "duration": 10,
            "goal": "Ruhe",
            "avoid": "Stress",
            "experience": "beginner",
            "body_tension": [],
            "nature_sound": "",
            "landscape": "",
            "voice_name": "",
            "user_name": "Test User",
            "questionnaire_answers": {},
        }
        _generate_with_openai(request_data)

        # Inspect the prompt actually sent to OpenAI
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        messages = call_kwargs["messages"]
        user_msg = next(m["content"] for m in messages if m["role"] == "user")
        self.assertIn("Sprich ruhig und führe den Nutzer.", user_msg)
        self.assertIn('"title"', user_msg)
        self.assertIn('"steps"', user_msg)
        self.assertIn('"step_type"', user_msg)





