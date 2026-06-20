from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import CharecterVoice, NatureSounds, BackgroundImage, Meditation, MeditationSteps


class CharacterVoiceAdmin(ModelAdmin):
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
            'fields': ('file',),
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    @display(description='Status', label={True: 'success', False: 'danger'})
    def active_status(self, obj):
        return obj.is_active, 'Active' if obj.is_active else 'Inactive'


class NatureSoundsAdmin(ModelAdmin):
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


class MeditationStepsInline(TabularInline):
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


admin.site.register(CharecterVoice, CharacterVoiceAdmin)
admin.site.register(NatureSounds, NatureSoundsAdmin)
admin.site.register(BackgroundImage, BackgroundImageAdmin)
admin.site.register(Meditation, MeditationAdmin)
