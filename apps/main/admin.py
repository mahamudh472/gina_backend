from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from unfold.widgets import UnfoldAdminFileFieldWidget

from .models import CharecterVoice, NatureSounds, BackgroundImage, Meditation, MeditationSteps, Music, MeditationTemplate, MeditationStep


class UnfoldAdminAudioFileWidget(UnfoldAdminFileFieldWidget):
    def render(self, name, value, attrs=None, renderer=None):
        html = super().render(name, value, attrs, renderer)
        if value and hasattr(value, 'url'):
            audio_html = format_html(
                '<div style="margin-top: 8px;"><audio src="{}" controls style="max-width: 100%; height: 36px;"></audio></div>',
                value.url
            )
            return format_html('{}{}', html, audio_html)
        return html


class AudioAdminMixin:
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in ['file', 'audio_file']:
            kwargs['widget'] = UnfoldAdminAudioFileWidget
        return super().formfield_for_dbfield(db_field, request, **kwargs)


class CharacterVoiceAdmin(AudioAdminMixin, ModelAdmin):
    list_display = ['name', 'short_description', 'tags', 'active_status', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'short_description', 'tags']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 25
    fieldsets = (
        ('Voice profile', {
            'fields': ('name', 'short_description', 'tags', 'avatar_url', 'is_active'),
        }),
        ('Audio', {
            'fields': ('file', 'elevenlabs_voice_id'),
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    @display(description='Status', label={True: 'success', False: 'danger'})
    def active_status(self, obj):
        return obj.is_active, 'Active' if obj.is_active else 'Inactive'


class NatureSoundsAdmin(AudioAdminMixin, ModelAdmin):
    list_display = ['name', 'active_status', 'created_at', 'updated_at']
    list_filter = ['is_active']
    search_fields = ['name']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 25
    fieldsets = (
        ('Sound', {
            'fields': ('name', 'file', 'is_active'),
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    @display(description='Status', label={True: 'success', False: 'danger'})
    def active_status(self, obj):
        return obj.is_active, 'Active' if obj.is_active else 'Inactive'


class BackgroundImageAdmin(ModelAdmin):
    list_display = ['name', 'active_status', 'created_at', 'updated_at']
    list_filter = ['is_active']
    search_fields = ['name']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 25
    fieldsets = (
        ('Image', {
            'fields': ('name', 'file', 'is_active'),
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    @display(description='Status', label={True: 'success', False: 'danger'})
    def active_status(self, obj):
        return obj.is_active, 'Active' if obj.is_active else 'Inactive'


class MeditationStepsInline(AudioAdminMixin, TabularInline):
    model = MeditationSteps
    extra = 0
    fields = ['step_type', 'content', 'duration', 'audio_file', 'created_at']
    readonly_fields = ['created_at']
    ordering = ['created_at']
    show_count = True
    tab = True


class MeditationAdmin(ModelAdmin):
    list_display = ['title', 'user', 'category_badge', 'charecter_voice', 'nature_sound', 'step_count', 'total_duration', 'created_at']
    list_filter = ['category', 'charecter_voice', 'nature_sound', 'background_image']
    search_fields = ['title', 'user__email', 'user__full_name']
    autocomplete_fields = ['user', 'background_image', 'charecter_voice', 'nature_sound']
    readonly_fields = ['created_at', 'total_duration', 'step_count']
    list_select_related = ['user', 'background_image', 'charecter_voice', 'nature_sound']
    list_per_page = 25
    ordering = ['-created_at']
    inlines = [MeditationStepsInline]
    fieldsets = (
        ('Meditation', {
            'fields': ('title', 'user', 'category'),
        }),
        ('Experience', {
            'fields': ('charecter_voice', 'nature_sound', 'background_image', 'banner_url'),
        }),
        ('Generated content', {
            'fields': ('experience_question_answer',),
        }),
        ('Read-only summary', {
            'classes': ('collapse',),
            'fields': ('step_count', 'total_duration', 'created_at'),
        }),
    )

    @display(description='Category', label=True)
    def category_badge(self, obj):
        return obj.get_category_display()

    @display(description='Steps')
    def step_count(self, obj):
        if not obj.pk:
            return 0
        return obj.steps.count()

class MusicAdmin(AudioAdminMixin, ModelAdmin):
    list_display = ['name', 'category', 'active_status', 'created_at', 'updated_at']
    list_filter = ['is_active', 'category']
    search_fields = ['name', 'category']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 25
    fieldsets = (
        ('Music', {
            'fields': ('name', 'file', 'category', 'is_active'),
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    @display(description='Status', label={True: 'success', False: 'danger'})
    def active_status(self, obj):
        return obj.is_active, 'Active' if obj.is_active else 'Inactive'


class MeditationTemplateStepsInline(AudioAdminMixin, TabularInline):
    model = MeditationSteps
    extra = 0
    fields = ['step_type', 'content', 'duration', 'audio_file', 'created_at']
    readonly_fields = ['created_at']
    ordering = ['created_at']
    show_count = True
    tab = True


class MeditationTemplateAdmin(ModelAdmin):
    list_display = ['category_badge', 'charecter_voice', 'active_status', 'steps_configured', 'created_at']
    list_filter = ['is_active', 'category', 'charecter_voice']
    ordering = ['category', 'charecter_voice', '-created_at']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 25
    autocomplete_fields = ['charecter_voice']
    inlines = [MeditationTemplateStepsInline]
    fieldsets = (
        ('Template details', {
            'fields': ('category', 'charecter_voice', 'is_active'),
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    @display(description='Category', label=True)
    def category_badge(self, obj):
        return obj.get_category_display()

    @display(description='Status', label={True: 'success', False: 'danger'})
    def active_status(self, obj):
        return obj.is_active, 'Active' if obj.is_active else 'Inactive'

    @display(description='Steps Configured')
    def steps_configured(self, obj):
        steps = list(obj.steps.values_list('step_type', flat=True))
        required = [MeditationStep.INTRODUCTION, MeditationStep.VISUALIZATION, MeditationStep.CONCLUSION]
        step_names = {
            MeditationStep.INTRODUCTION: 'Intro',
            MeditationStep.VISUALIZATION: 'Viz',
            MeditationStep.CONCLUSION: 'Outro'
        }
        parts = []
        for r in required:
            if r in steps:
                parts.append(f'<span style="color: #22c55e; font-weight: bold;">{step_names[r]}</span>')
            else:
                parts.append(f'<span style="color: #ef4444; text-decoration: line-through;">{step_names[r]}</span>')
        return format_html(" | ".join(parts))


admin.site.register(CharecterVoice, CharacterVoiceAdmin)
admin.site.register(NatureSounds, NatureSoundsAdmin)
admin.site.register(BackgroundImage, BackgroundImageAdmin)
admin.site.register(Meditation, MeditationAdmin)
admin.site.register(Music, MusicAdmin)
admin.site.register(MeditationTemplate, MeditationTemplateAdmin)
