import datetime
from django.db import models



class CharecterVoice(models.Model):
    name = models.CharField(max_length=100)
    avatar_url = models.ImageField(upload_to='uploads/characters', null=True, blank=True)
    short_description = models.CharField(max_length=512)
    tags = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to='uploads/audio')
    elevenlabs_voice_id = models.CharField(max_length=255, blank=True, null=True)

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


class MeditationTemplate(models.Model):
    category = models.CharField(max_length=50, choices=MeditationCategory.choices, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.is_active and self.category:
            MeditationTemplate.objects.filter(
                category=self.category,
                is_active=True
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Template - {self.get_category_display()} ({'Active' if self.is_active else 'Inactive'})"


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

    def get_combined_steps(self):
        db_steps = {step.step_type: step for step in self.steps.all()}
        
        active_template = MeditationTemplate.objects.filter(
            category=self.category,
            is_active=True
        ).first()
        
        template_steps = {}
        if active_template:
            template_steps = {
                step.step_type: step 
                for step in active_template.steps.all()
            }
            
        combined = []
        for step_type in [
            MeditationStep.GREETING,
            MeditationStep.PERSONAL,
            MeditationStep.INTRODUCTION,
            MeditationStep.SUGGESTION,
            MeditationStep.CONFIRMATION,
            MeditationStep.VISUALIZATION,
            MeditationStep.CONCLUSION,
        ]:
            if step_type in [MeditationStep.INTRODUCTION, MeditationStep.VISUALIZATION, MeditationStep.CONCLUSION]:
                step = template_steps.get(step_type)
                if step:
                    step.meditation = self  # Inject self for percentage calculations
                    combined.append(step)
            else:
                step = db_steps.get(step_type)
                if step:
                    combined.append(step)
        return combined

    @property
    def total_duration(self):
        total = datetime.timedelta(seconds=0)
        for step in self.get_combined_steps():
            if step.duration:
                total += step.duration
        return total

class MeditationSteps(models.Model):
    meditation = models.ForeignKey(Meditation, on_delete=models.CASCADE, related_name='steps', null=True, blank=True)
    meditation_template = models.ForeignKey(MeditationTemplate, on_delete=models.CASCADE, related_name='steps', null=True, blank=True)
    step_type = models.CharField(max_length=50, choices=MeditationStep.choices)
    content = models.TextField()
    audio_file = models.FileField(upload_to='uploads/audio', null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if not self.meditation and not self.meditation_template:
            raise ValidationError("A meditation step must be associated with either a Meditation or a MeditationTemplate.")
        if self.meditation and self.meditation_template:
            raise ValidationError("A meditation step cannot be associated with both a Meditation and a MeditationTemplate.")
        if self.meditation_template:
            allowed_steps = [MeditationStep.INTRODUCTION, MeditationStep.VISUALIZATION, MeditationStep.CONCLUSION]
            if self.step_type not in allowed_steps:
                raise ValidationError(f"MeditationTemplate steps only support step types: {', '.join(allowed_steps)}")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.meditation:
            return f"{self.meditation.title} - {self.step_type}"
        elif self.meditation_template:
            return f"Template ({self.meditation_template.get_category_display()}) - {self.step_type}"
        return f"Step - {self.step_type}"

class Music(models.Model):
    name = models.CharField(max_length=100)
    file = models.FileField(upload_to='uploads/audio')
    category = models.CharField(max_length=100, blank=True, choices=MeditationCategory.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.is_active and self.category:
            Music.objects.filter(category=self.category, is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

