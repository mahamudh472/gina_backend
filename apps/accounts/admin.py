from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import OTP, User

@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    list_display = ('email', 'full_name', 'phone_number', 'account_status', 'staff_status', 'joined_at', 'last_login')
    search_fields = ('email', 'full_name', 'phone_number', 'username')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'gender', 'joined_at')
    readonly_fields = ('id', 'joined_at', 'last_login')
    ordering = ('-joined_at',)
    list_per_page = 25
    fieldsets = (
        ('Identity', {
            'fields': ('id', 'email', 'username', 'full_name', 'phone_number', 'avatar'),
        }),
        ('Profile', {
            'fields': ('gender', 'age', 'date_of_birth'),
        }),
        ('Access', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'password'),
        }),
        ('Permissions', {
            'classes': ('collapse',),
            'fields': ('groups', 'user_permissions'),
        }),
        ('Activity', {
            'classes': ('collapse',),
            'fields': ('joined_at', 'last_login'),
        }),
    )
    add_fieldsets = (
        ('Create user', {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_active', 'is_staff'),
        }),
    )
    filter_horizontal = ('groups', 'user_permissions')

    @display(description='Account', label={True: 'success', False: 'danger'})
    def account_status(self, obj):
        return obj.is_active, 'Active' if obj.is_active else 'Inactive'

    @display(description='Role', label={True: 'primary', False: 'info'})
    def staff_status(self, obj):
        return obj.is_staff, 'Staff' if obj.is_staff else 'Customer'


@admin.register(OTP)
class OTPAdmin(ModelAdmin):
    list_display = ('user', 'code', 'used_status', 'created_at', 'expires_at')
    list_filter = ('is_used', 'created_at', 'expires_at')
    search_fields = ('user__email', 'code')
    autocomplete_fields = ('user',)
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    list_per_page = 25

    @display(description='Status', label={True: 'success', False: 'warning'})
    def used_status(self, obj):
        return obj.is_used, 'Used' if obj.is_used else 'Open'
