from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import CharecterVoice, NatureSounds, BackgroundImage, Meditation, MeditationSteps

class CharacterVoiceAdmin(ModelAdmin):
    list_display = ['name']
    list_filter = ['is_active']
    search_fields = ['name']
    ordering = ['-created_at']

class NatureSoundsAdmin(ModelAdmin):
    list_display = ['name']
    list_filter = ['is_active']
    search_fields = ['name']
    ordering = ['-created_at']

class BackgroundImageAdmin(ModelAdmin):
    list_display = ['name']
    list_filter = ['is_active']
    search_fields = ['name']
    ordering = ['-created_at']

class MeditationStepsInline(admin.TabularInline):
    model = MeditationSteps
    extra = 0
    fields = ['step_type', 'content', 'duration', 'audio_file']

class MeditationAdmin(ModelAdmin):
    list_display = ['title', 'category', 'charecter_voice', 'nature_sound', 'created_at']
    list_filter = ['category', 'charecter_voice', 'nature_sound']
    search_fields = ['title']
    inlines = [MeditationStepsInline]

admin.site.register(CharecterVoice, CharacterVoiceAdmin)
admin.site.register(NatureSounds, NatureSoundsAdmin)
admin.site.register(BackgroundImage, BackgroundImageAdmin)
admin.site.register(Meditation, MeditationAdmin)

