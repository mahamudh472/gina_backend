from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Plan, CreditWallet, Subscription




@admin.register(Plan)
class PlanAdmin(ModelAdmin):
    list_display = ('name', 'slug', 'price', 'currency', 'credit_amount', 'interval', 'is_active', 'stripe_price_id')
    list_filter = ('is_active', 'interval', 'currency')
    search_fields = ('name', 'slug', 'stripe_price_id')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(CreditWallet)
class CreditWalletAdmin(ModelAdmin):
    list_display = ('user', 'balance', 'last_reset_at', 'updated_at')
    search_fields = ('user__email', 'user__full_name')
    readonly_fields = ('last_reset_at', 'created_at', 'updated_at')


@admin.register(Subscription)
class SubscriptionAdmin(ModelAdmin):
    list_display = ('user', 'plan', 'status', 'current_period_end', 'cancel_at_period_end', 'pending_plan')
    list_filter = ('status', 'cancel_at_period_end', 'plan')
    search_fields = ('user__email', 'stripe_subscription_id', 'stripe_customer_id')
    readonly_fields = ('created_at', 'updated_at')
