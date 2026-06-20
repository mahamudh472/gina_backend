from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import CreditWallet, Plan, Subscription

@admin.register(Plan)
class PlanAdmin(ModelAdmin):
    list_display = ('name', 'slug', 'formatted_price', 'credit_amount', 'interval', 'active_status', 'stripe_price_id', 'updated_at')
    list_filter = ('is_active', 'interval', 'currency')
    search_fields = ('name', 'slug', 'stripe_price_id')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('credit_amount',)
    list_per_page = 25
    fieldsets = (
        ('Plan', {
            'fields': ('name', 'slug', 'is_active', 'badge', 'top_badge'),
        }),
        ('Billing', {
            'fields': ('price', 'currency', 'interval', 'credit_amount'),
        }),
        ('Stripe', {
            'classes': ('collapse',),
            'fields': ('stripe_price_id', 'stripe_product_id'),
        }),
        ('Features', {
            'fields': ('features',),
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    @display(description='Price')
    def formatted_price(self, obj):
        return f'{obj.price} {obj.currency.upper()} / {obj.interval}'

    @display(description='Status', label={True: 'success', False: 'danger'})
    def active_status(self, obj):
        return obj.is_active, 'Active' if obj.is_active else 'Inactive'


@admin.register(CreditWallet)
class CreditWalletAdmin(ModelAdmin):
    list_display = ('user', 'balance_badge', 'last_reset_at', 'updated_at')
    list_filter = ('last_reset_at', 'updated_at')
    search_fields = ('user__email', 'user__full_name')
    autocomplete_fields = ('user',)
    readonly_fields = ('last_reset_at', 'created_at', 'updated_at')
    ordering = ('-updated_at',)
    list_select_related = ('user',)
    list_per_page = 25
    fieldsets = (
        ('Wallet', {
            'fields': ('user', 'balance'),
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('last_reset_at', 'created_at', 'updated_at'),
        }),
    )

    @display(description='Balance', label='primary')
    def balance_badge(self, obj):
        return obj.balance


@admin.register(Subscription)
class SubscriptionAdmin(ModelAdmin):
    list_display = ('user', 'plan', 'status_badge', 'current_period_end', 'cancel_badge', 'pending_plan', 'updated_at')
    list_filter = ('status', 'cancel_at_period_end', 'plan')
    search_fields = ('user__email', 'stripe_subscription_id', 'stripe_customer_id')
    autocomplete_fields = ('user', 'plan', 'pending_plan')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-updated_at',)
    list_select_related = ('user', 'plan', 'pending_plan')
    list_per_page = 25
    fieldsets = (
        ('Customer subscription', {
            'fields': ('user', 'plan', 'status', 'pending_plan'),
        }),
        ('Billing period', {
            'fields': ('current_period_start', 'current_period_end', 'cancel_at_period_end'),
        }),
        ('Stripe', {
            'classes': ('collapse',),
            'fields': ('stripe_subscription_id', 'stripe_customer_id'),
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    @display(
        description='Status',
        label={
            'active': 'success',
            'trialing': 'info',
            'past_due': 'warning',
            'canceled': 'danger',
            'incomplete': 'warning',
            'incomplete_expired': 'danger',
            'unpaid': 'danger',
            'paused': 'warning',
            'inactive': 'info',
        },
    )
    def status_badge(self, obj):
        return obj.status, obj.get_status_display()

    @display(description='Renews?', label={True: 'warning', False: 'success'})
    def cancel_badge(self, obj):
        return obj.cancel_at_period_end, 'Cancels' if obj.cancel_at_period_end else 'Renews'
