from rest_framework import serializers
from .models import Plan, CreditWallet, Subscription

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            'id', 'name', 'slug', 'price', 'currency', 
            'credit_amount', 'interval', 'badge', 'top_badge', 
            'features', 'is_active'
        ]


class CreditWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditWallet
        fields = ['balance', 'last_reset_at', 'updated_at']


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    pending_plan = PlanSerializer(read_only=True)
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'plan', 'status', 'current_period_start', 
            'current_period_end', 'cancel_at_period_end', 'pending_plan'
        ]


class CheckoutRequestSerializer(serializers.Serializer):
    plan_slug = serializers.SlugField()
    success_url = serializers.URLField(required=False, default="http://localhost:3000/subscription/success")
    cancel_url = serializers.URLField(required=False, default="http://localhost:3000/subscription/cancel")


class ChangePlanRequestSerializer(serializers.Serializer):
    plan_slug = serializers.SlugField()
