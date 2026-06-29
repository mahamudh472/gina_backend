from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from unfold.admin import ModelAdmin

from .models import TTSSettings


class TTSSettingsAdmin(ModelAdmin):
    def has_add_permission(self, request):
        # Allow adding only if no instance exists yet
        return not TTSSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of settings
        return False

    def changelist_view(self, request, extra_context=None):
        # Automatically redirect list page to the single instance edit page
        obj = TTSSettings.get_settings()
        return redirect(reverse('admin:ai_service_ttssettings_change', args=[obj.pk]))


admin.site.register(TTSSettings, TTSSettingsAdmin)
