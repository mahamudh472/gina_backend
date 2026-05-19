import datetime
from django.db import models



class CharecterVoice(models.Model):
    name = models.CharField(max_length=100)
    avatar_url = models.ImageField(upload_to='uploads/characters', null=True, blank=True)
    short_description = models.CharField(max_length=512)
    tags = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to='uploads/audio')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class NatureSounds(models.Model):
    name = models.CharField(max_length=100)
    file = models.FileField(upload_to='uploads/audio')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class BackgroundImage(models.Model):
    name = models.CharField(max_length=100)
    file = models.FileField(upload_to='uploads/images')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class MeditationCategory(models.TextChoices):
    RELAXATION = "relaxation", "Entspannung"
    SELF_LOVE = "self_love", "Selbstliebe"
    FOCUS_CLARITY = "focus_clarity", "Fokus & Klarheit"
    GRATITUDE = "gratitude", "Dankbarkeit"
    TRUST = "trust", "Vertrauen"
    ENERGY = "energy", "Energie"
    TRANSFORMATION = "transformation", "Transformation"
    INNER_PEACE = "inner_peace", "Innerer Frieden"

class MeditationStep(models.TextChoices):
    GREETING = "greeting", "Begrüßung"
    PERSONAL = "personal", "Persönlich"
    INTRODUCTION = "introduction", "Einführung"
    SUGGESTION = "suggestion", "Vorschlag"
    CONFIRMATION = "confirmation", "Bestätigung"
    VISUALIZATION = "visualization", "Visualisierung"
    CONCLUSION = "conclusion", "Abschluss"   

from django.conf import settings

class Meditation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meditations')
    title = models.CharField(max_length=255)
    banner_url = models.URLField(null=True, blank=True)
    background_image = models.ForeignKey(BackgroundImage, on_delete=models.CASCADE, null=True, blank=True)
    charecter_voice = models.ForeignKey(CharecterVoice, on_delete=models.CASCADE)
    nature_sound = models.ForeignKey(NatureSounds, on_delete=models.CASCADE, null=True, blank=True)
    experience_question_answer = models.JSONField(null=True, blank=True)
    category = models.CharField(max_length=50, choices=MeditationCategory.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    @property
    def total_duration(self):
        total = datetime.timedelta(seconds=0)
        for step in self.steps.all():
            if step.duration:
                total += step.duration
        return total

class MeditationSteps(models.Model):
    meditation = models.ForeignKey(Meditation, on_delete=models.CASCADE, related_name='steps')
    step_type = models.CharField(max_length=50, choices=MeditationStep.choices)
    content = models.TextField()
    audio_file = models.FileField(upload_to='uploads/audio', null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.meditation.title} - {self.step_type}"