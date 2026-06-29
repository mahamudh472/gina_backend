from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


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
