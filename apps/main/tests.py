import datetime
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from apps.main.models import (
    CharecterVoice, 
    NatureSounds, 
    BackgroundImage, 
    Meditation, 
    MeditationSteps, 
    MeditationCategory,
    MeditationStep,
    Music
)

User = get_user_model()

class MeditationGenerationTests(APITestCase):

    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword123",
            username="testuser"
        )
        # Create audio dummy file
        dummy_audio = SimpleUploadedFile("voice.mp3", b"dummy audio content", content_type="audio/mpeg")
        dummy_image = SimpleUploadedFile("bg.jpg", b"dummy image content", content_type="image/jpeg")

        # Create base data
        self.character_voice = CharecterVoice.objects.create(
            name="Aura",
            short_description="A soothing and calm female voice.",
            file=dummy_audio
        )
        self.background_image = BackgroundImage.objects.create(
            name="Cosmic Sky",
            file=dummy_image
        )
        self.nature_sound = NatureSounds.objects.create(
            name="Ocean Waves",
            file=dummy_audio
        )

        self.url = reverse('meditation-generate')

        # Mock the external AI service calls to make tests hermetic
        from unittest.mock import patch
        from apps.main.utils import _generate_static_meditation_steps

        def mock_generate_content_wrapper(category, q_a, **kwargs):
            return _generate_static_meditation_steps(category, q_a)

        self.mock_generate_content = patch('apps.main.services.generate_meditation_content').start()
        self.mock_generate_content.side_effect = mock_generate_content_wrapper

        self.mock_generate_audio = patch('apps.main.services.generate_step_audio').start()
        self.mock_generate_audio.return_value = b"dummy audio content"

        self.addCleanup(patch.stopall)

    def test_generate_meditation_unauthenticated(self):
        # Unauthenticated request should fail with 401
        data = {
            "category": "relaxation",
            "charecter_voice_id": self.character_voice.id,
            "experience_question_answers": {"name": "Anna", "goal": "stress release"},
            "nature_sound_name": "Ocean Waves",
            "background_image_id": self.background_image.id
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_generate_meditation_success(self):
        # Authenticate
        self.client.force_authenticate(user=self.user)

        # Set up active MeditationTemplate for relaxation category
        from apps.main.models import MeditationTemplate, MeditationSteps
        relaxation_template = MeditationTemplate.objects.create(
            category=MeditationCategory.RELAXATION,
            charecter_voice=self.character_voice,
            is_active=True
        )
        MeditationSteps.objects.create(
            meditation_template=relaxation_template,
            step_type=MeditationStep.INTRODUCTION,
            content="Introduction template content",
            duration=datetime.timedelta(seconds=90)
        )
        MeditationSteps.objects.create(
            meditation_template=relaxation_template,
            step_type=MeditationStep.VISUALIZATION,
            content="Visualization template content",
            duration=datetime.timedelta(seconds=180)
        )
        MeditationSteps.objects.create(
            meditation_template=relaxation_template,
            step_type=MeditationStep.CONCLUSION,
            content="Conclusion template content",
            duration=datetime.timedelta(seconds=45)
        )

        data = {
            "category": "relaxation",
            "charecter_voice_id": self.character_voice.id,
            "experience_question_answers": {"name": "Anna", "goal": "stress release"},
            "nature_sound_name": "Ocean Waves",
            "background_image_id": self.background_image.id
        }

        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Assert response schema
        res_data = response.data
        self.assertEqual(set(res_data.keys()), {'id', 'meditation_id', 'total_duration', 'steps'})
        self.assertEqual(res_data['total_duration'], 600.0)

        # Verify steps
        steps = res_data['steps']
        self.assertEqual(len(steps), 7)
        
        # Verify step types and percentages
        expected_steps = [
            (MeditationStep.GREETING, 7.5),
            (MeditationStep.PERSONAL, 10.0),
            (MeditationStep.INTRODUCTION, 15.0),
            (MeditationStep.SUGGESTION, 20.0),
            (MeditationStep.CONFIRMATION, 10.0),
            (MeditationStep.VISUALIZATION, 30.0),
            (MeditationStep.CONCLUSION, 7.5),
        ]
        
        for idx, (step_type, expected_percent) in enumerate(expected_steps):
            step = steps[idx]
            self.assertEqual(step['step_type'], step_type)
            self.assertEqual(step['duration_percentage'], expected_percent)

        # Assert DB items exist (only the 4 AI steps are in the DB)
        meditation = Meditation.objects.get(id=res_data['id'])
        self.assertEqual(meditation.steps.count(), 4)
        self.assertEqual(len(meditation.get_combined_steps()), 7)
        self.assertGreater(meditation.total_duration, datetime.timedelta(seconds=0))

    def test_generate_meditation_nature_sound_not_found(self):
        self.client.force_authenticate(user=self.user)

        data = {
            "category": "self_love",
            "charecter_voice_id": self.character_voice.id,
            "experience_question_answers": {"name": "Ben"},
            "nature_sound_name": "Non Existent Sound",
            "background_image_id": self.background_image.id
        }

        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        res_data = response.data
        self.assertEqual(set(res_data.keys()), {'id', 'meditation_id', 'total_duration', 'steps'})

    def test_get_meditation_detail(self):
        self.client.force_authenticate(user=self.user)
        
        # Create a meditation directly for testing retrieve
        meditation = Meditation.objects.create(
            user=self.user,
            title="Retrieve Test",
            charecter_voice=self.character_voice,
            category=MeditationCategory.ENERGY
        )
        MeditationSteps.objects.create(
            meditation=meditation,
            step_type=MeditationStep.GREETING,
            content="Hello",
            duration=datetime.timedelta(seconds=60)
        )

        detail_url = reverse('meditation-detail', args=[meditation.pk])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should return full meditation data (MeditationSerializer)
        self.assertEqual(response.data['id'], meditation.pk)
        self.assertEqual(response.data['title'], "Retrieve Test")
        self.assertEqual(response.data['category'], MeditationCategory.ENERGY)
        self.assertEqual(len(response.data['steps']), 1)
        self.assertEqual(response.data['steps'][0]['step_type'], MeditationStep.GREETING)
        self.assertEqual(response.data['total_duration'], 60.0)

    def test_get_meditation_detail_unauthorized(self):
        # Create meditation belonging to another user
        other_user = User.objects.create_user(email="other@test.com", password="pwd", username="other")
        meditation = Meditation.objects.create(
            user=other_user,
            title="Retrieve Test Other",
            charecter_voice=self.character_voice,
            category=MeditationCategory.ENERGY
        )

        self.client.force_authenticate(user=self.user)
        detail_url = reverse('meditation-detail', args=[meditation.pk])
        response = self.client.get(detail_url)
        # Queryset filters by user, so it should be a 404
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    def test_meditation_archive(self):
        self.client.force_authenticate(user=self.user)
        
        # Create a couple of meditations
        med1 = Meditation.objects.create(
            user=self.user,
            title="Archived 1",
            charecter_voice=self.character_voice,
            category=MeditationCategory.RELAXATION
        )
        MeditationSteps.objects.create(meditation=med1, step_type=MeditationStep.GREETING, content="Hi", duration=datetime.timedelta(seconds=120))
        
        med2 = Meditation.objects.create(
            user=self.user,
            title="Archived 2",
            charecter_voice=self.character_voice,
            category=MeditationCategory.ENERGY
        )
        MeditationSteps.objects.create(meditation=med2, step_type=MeditationStep.GREETING, content="Hi", duration=datetime.timedelta(seconds=180))

        archive_url = reverse('meditation-archive')
        response = self.client.get(archive_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res_data = response.data
        
        self.assertIn('all_meditation_ids', res_data)
        self.assertIn('overall_total_duration', res_data)
        self.assertIn('results', res_data)
        
        # Check IDs
        self.assertEqual(len(res_data['all_meditation_ids']), 2)
        self.assertIn(med1.id, res_data['all_meditation_ids'])
        self.assertIn(med2.id, res_data['all_meditation_ids'])
        
        # Check overall duration (120 + 180 = 300)
        self.assertEqual(res_data['overall_total_duration'], 300.0)
        
        # Check results contents
        results = res_data['results']
        self.assertEqual(len(results), 2)
        # Verify required keys in list items
        expected_keys = {'id', 'banner_url', 'category', 'category_name', 'created_at', 'total_duration'}
        self.assertEqual(set(results[0].keys()), expected_keys)
        self.assertEqual(results[0]['category_name'], "Energie") # med2 is first because of order_by('-created_at')

    def test_single_active_music_per_category(self):
        # Create first active music track in relaxation category
        music1 = Music.objects.create(
            name="Relax Track 1",
            file=SimpleUploadedFile("track1.mp3", b"content", content_type="audio/mpeg"),
            category=MeditationCategory.RELAXATION,
            is_active=True
        )
        self.assertTrue(music1.is_active)

        # Create second active music track in relaxation category
        music2 = Music.objects.create(
            name="Relax Track 2",
            file=SimpleUploadedFile("track2.mp3", b"content", content_type="audio/mpeg"),
            category=MeditationCategory.RELAXATION,
            is_active=True
        )
        # Fetch fresh instances from DB
        music1.refresh_from_db()
        music2.refresh_from_db()

        # Relax Track 1 should now be inactive, Relax Track 2 should be active
        self.assertFalse(music1.is_active)
        self.assertTrue(music2.is_active)

        # Create active music in different category (e.g. self_love)
        music3 = Music.objects.create(
            name="Self Love Track 1",
            file=SimpleUploadedFile("track3.mp3", b"content", content_type="audio/mpeg"),
            category=MeditationCategory.SELF_LOVE,
            is_active=True
        )
        music2.refresh_from_db()
        music3.refresh_from_db()

        # Both track 2 and track 3 should be active because categories are different
        self.assertTrue(music2.is_active)
        self.assertTrue(music3.is_active)

        # Toggle music1 back to active
        music1.is_active = True
        music1.save()

        music1.refresh_from_db()
        music2.refresh_from_db()
        self.assertTrue(music1.is_active)
        self.assertFalse(music2.is_active)

    def test_generate_meditation_auto_selects_active_music(self):
        self.client.force_authenticate(user=self.user)

        # Create active music for relaxation
        music = Music.objects.create(
            name="Active Relaxation Music",
            file=SimpleUploadedFile("music.mp3", b"content", content_type="audio/mpeg"),
            category=MeditationCategory.RELAXATION,
            is_active=True
        )

        data = {
            "category": "relaxation",
            "charecter_voice_id": self.character_voice.id,
            "experience_question_answers": {"name": "Anna", "goal": "stress release"},
            "nature_sound_name": "Ocean Waves",
            "background_image_id": self.background_image.id
        }

        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Retrieve detail and verify the active category music is in the payload
        meditation_id = response.data['id']
        detail_url = reverse('meditation-detail', args=[meditation_id])
        detail_response = self.client.get(detail_url)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        
        self.assertIsNotNone(detail_response.data['music'])
        self.assertEqual(detail_response.data['music']['id'], music.id)

    def test_get_meditation_detail_with_music_and_null_music(self):
        self.client.force_authenticate(user=self.user)

        # 1. Meditation with active music for its category (RELAXATION)
        music = Music.objects.create(
            name="Ambient Ocean",
            file=SimpleUploadedFile("ambient.mp3", b"content", content_type="audio/mpeg"),
            category=MeditationCategory.RELAXATION,
            is_active=True
        )
        meditation_with_music = Meditation.objects.create(
            user=self.user,
            title="Meditation With Music",
            charecter_voice=self.character_voice,
            category=MeditationCategory.RELAXATION,
        )
        detail_url = reverse('meditation-detail', args=[meditation_with_music.pk])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify music block in detail response
        self.assertIsNotNone(response.data['music'])
        self.assertEqual(response.data['music']['id'], music.id)
        self.assertEqual(response.data['music']['name'], "Ambient Ocean")
        self.assertIn("ambient", response.data['music']['file'])
        self.assertTrue(response.data['music']['file'].endswith(".mp3"))

        # 2. Meditation with category (ENERGY) that has no active music
        meditation_no_music = Meditation.objects.create(
            user=self.user,
            title="Meditation Without Music",
            charecter_voice=self.character_voice,
            category=MeditationCategory.ENERGY,
        )
        detail_url = reverse('meditation-detail', args=[meditation_no_music.pk])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['music'])

    def test_single_active_template_per_category(self):
        from apps.main.models import MeditationTemplate
        # Create first active template for energy category
        t1 = MeditationTemplate.objects.create(
            category=MeditationCategory.ENERGY,
            charecter_voice=self.character_voice,
            is_active=True
        )
        self.assertTrue(t1.is_active)

        # Create second active template for energy category
        t2 = MeditationTemplate.objects.create(
            category=MeditationCategory.ENERGY,
            charecter_voice=self.character_voice,
            is_active=True
        )
        t1.refresh_from_db()
        t2.refresh_from_db()

        # The first template should now be inactive, second active
        self.assertFalse(t1.is_active)
        self.assertTrue(t2.is_active)

    def test_multiple_active_templates_for_different_voices(self):
        from apps.main.models import MeditationTemplate
        dummy_audio = SimpleUploadedFile("voice2.mp3", b"dummy audio content", content_type="audio/mpeg")
        other_voice = CharecterVoice.objects.create(
            name="Serena",
            short_description="Another soothing voice.",
            file=dummy_audio
        )
        # Create active template for voice 1
        t1 = MeditationTemplate.objects.create(
            category=MeditationCategory.ENERGY,
            charecter_voice=self.character_voice,
            is_active=True
        )
        # Create active template for voice 2 (same category, different voice)
        t2 = MeditationTemplate.objects.create(
            category=MeditationCategory.ENERGY,
            charecter_voice=other_voice,
            is_active=True
        )
        t1.refresh_from_db()
        t2.refresh_from_db()
        # Both should remain active!
        self.assertTrue(t1.is_active)
        self.assertTrue(t2.is_active)

    def test_meditation_step_validation_for_templates(self):
        from django.core.exceptions import ValidationError
        from apps.main.models import MeditationTemplate, MeditationSteps

        template = MeditationTemplate.objects.create(
            category=MeditationCategory.SELF_LOVE,
            charecter_voice=self.character_voice,
            is_active=True
        )

        # Valid step type should succeed
        step1 = MeditationSteps.objects.create(
            meditation_template=template,
            step_type=MeditationStep.INTRODUCTION,
            content="Hello introduction",
            duration=datetime.timedelta(seconds=60)
        )
        self.assertEqual(step1.step_type, MeditationStep.INTRODUCTION)

        # Invalid step type (e.g. GREETING) for template should raise ValidationError
        with self.assertRaises(ValidationError):
            MeditationSteps.objects.create(
                meditation_template=template,
                step_type=MeditationStep.GREETING,
                content="Hello greeting",
                duration=datetime.timedelta(seconds=60)
            )

        # Step with both meditation and template should raise ValidationError
        meditation = Meditation.objects.create(
            user=self.user,
            title="Mix Test",
            charecter_voice=self.character_voice,
            category=MeditationCategory.SELF_LOVE
        )
        with self.assertRaises(ValidationError):
            MeditationSteps.objects.create(
                meditation=meditation,
                meditation_template=template,
                step_type=MeditationStep.INTRODUCTION,
                content="Mix",
                duration=datetime.timedelta(seconds=60)
            )

    def test_dashboard_callback_template_status(self):
        from visulara.admin_dashboard import dashboard_callback
        from apps.main.models import MeditationTemplate, MeditationSteps
        
        # Initially, all categories should be missing active templates
        context = {}
        res_context = dashboard_callback(None, context)
        template_status = res_context['dashboard']['template_status']
        
        # Check relaxation status (should be missing_template)
        relax_status = next(
            item for item in template_status 
            if item['category'] == 'relaxation' and item['charecter_voice'] == self.character_voice.name
        )
        self.assertEqual(relax_status['status'], 'missing_template')
        
        # Create active template for relaxation category, but missing steps
        template = MeditationTemplate.objects.create(
            category=MeditationCategory.RELAXATION,
            charecter_voice=self.character_voice,
            is_active=True
        )
        MeditationSteps.objects.create(
            meditation_template=template,
            step_type=MeditationStep.INTRODUCTION,
            content="Intro text",
            duration=datetime.timedelta(seconds=60)
        )
        
        res_context = dashboard_callback(None, context)
        template_status = res_context['dashboard']['template_status']
        relax_status = next(
            item for item in template_status 
            if item['category'] == 'relaxation' and item['charecter_voice'] == self.character_voice.name
        )
        self.assertEqual(relax_status['status'], 'missing_steps')
        self.assertIn('Visualization', relax_status['status_label'])
        
        # Add remaining steps to make it healthy
        MeditationSteps.objects.create(
            meditation_template=template,
            step_type=MeditationStep.VISUALIZATION,
            content="Viz text",
            duration=datetime.timedelta(seconds=60)
        )
        MeditationSteps.objects.create(
            meditation_template=template,
            step_type=MeditationStep.CONCLUSION,
            content="Conclusion text",
            duration=datetime.timedelta(seconds=60)
        )
        
        res_context = dashboard_callback(None, context)
        template_status = res_context['dashboard']['template_status']
        relax_status = next(
            item for item in template_status 
            if item['category'] == 'relaxation' and item['charecter_voice'] == self.character_voice.name
        )
        self.assertEqual(relax_status['status'], 'healthy')
        self.assertEqual(relax_status['status_label'], 'Healthy')

    def test_get_audio_duration_with_real_file(self):
        import os
        from django.conf import settings
        from apps.ai_service.tts import get_audio_duration
        
        # Test with None or empty
        self.assertIsNone(get_audio_duration(b""))
        
        # Test with an invalid/corrupt audio byte string
        self.assertIsNone(get_audio_duration(b"invalid audio bytes"))
        
        # Test with a real MP3 file if present in media/uploads/audio
        real_file_path = os.path.join(settings.BASE_DIR, 'media', 'uploads', 'audio', 'male_Stimme.mp3')
        if os.path.exists(real_file_path):
            with open(real_file_path, 'rb') as f:
                audio_bytes = f.read()
            duration = get_audio_duration(audio_bytes)
            self.assertIsNotNone(duration)
            self.assertGreater(duration, 0)

    def test_recalculate_durations_command(self):
        import os
        from django.conf import settings
        from django.core.management import call_command
        from io import StringIO
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.main.models import MeditationSteps
        
        real_file_path = os.path.join(settings.BASE_DIR, 'media', 'uploads', 'audio', 'male_Stimme.mp3')
        if os.path.exists(real_file_path):
            with open(real_file_path, 'rb') as f:
                file_content = f.read()
            audio_file = SimpleUploadedFile("test_duration_voice.mp3", file_content, content_type="audio/mpeg")
        else:
            audio_file = SimpleUploadedFile("dummy.mp3", b"dummy bytes", content_type="audio/mpeg")

        meditation = Meditation.objects.create(
            user=self.user,
            title="Command Test",
            charecter_voice=self.character_voice,
            category=MeditationCategory.SELF_LOVE
        )
        step = MeditationSteps.objects.create(
            meditation=meditation,
            step_type=MeditationStep.GREETING,
            content="Hello GREETING",
            duration=datetime.timedelta(seconds=99),
            audio_file=audio_file
        )

        out = StringIO()
        call_command('recalculate_durations', stdout=out)
        output_str = out.getvalue()
        
        self.assertIn("Found 1 steps with audio files to process.", output_str)
        self.assertIn("Recalculation complete.", output_str)

