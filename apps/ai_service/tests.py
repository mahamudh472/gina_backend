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
