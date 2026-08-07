from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.main.models import MeditationCategory


class TTSSettings(models.Model):
    stability = models.FloatField(
        default=0.40,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Stability value must be between 0.0 and 1.0 (Default: 0.40)"
    )
    similarity_boost = models.FloatField(
        default=0.60,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Similarity boost must be between 0.0 and 1.0 (Default: 0.60)"
    )
    style = models.FloatField(
        default=0.45,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Style must be between 0.0 and 1.0 (Default: 0.45)"
    )
    use_speaker_boost = models.BooleanField(
        default=True,
        help_text="Toggle speaker boost (Default: True)"
    )

    class Meta:
        verbose_name = "TTS Settings"
        verbose_name_plural = "TTS Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"Global TTS Settings (Stability: {self.stability}, Similarity Boost: {self.similarity_boost}, Style: {self.style}, Speaker Boost: {self.use_speaker_boost})"


class MeditationPrompt(models.Model):
    name = models.CharField(max_length=255)
    category = models.CharField(
        max_length=50,
        choices=MeditationCategory.choices,
        default=MeditationCategory.RELAXATION,
    )
    prompt_template = models.TextField()
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Meditation Prompt"
        verbose_name_plural = "Meditation Prompts"

    def save(self, *args, **kwargs):
        if self.is_active:
            # Set all other instances of the same category to inactive
            MeditationPrompt.objects.filter(category=self.category, is_active=True).exclude(pk=self.pk).update(is_active=False)
        else:
            # Enforce at least one active prompt for this category if any exist
            if not MeditationPrompt.objects.filter(category=self.category, is_active=True).exclude(pk=self.pk).exists():
                self.is_active = True
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        was_active = self.is_active
        category = self.category
        super().delete(*args, **kwargs)
        if was_active:
            # Find another prompt of the same category and make it active
            another = MeditationPrompt.objects.filter(category=category).first()
            if another:
                another.is_active = True
                another.save()

    def __str__(self):
        return f"{self.name} - {self.get_category_display()} ({'Active' if self.is_active else 'Inactive'})"

