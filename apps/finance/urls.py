from django.urls import path
from .views import (
    PlanListView, WalletDetailView, SubscriptionDetailView,
    CreateCheckoutSessionView, ChangePlanView, CancelSubscriptionView,
    StripeWebhookView
)

urlpatterns = [
    path('plans/', PlanListView.as_view(), name='plan-list'),
    path('wallet/', WalletDetailView.as_view(), name='wallet-detail'),
    path('subscription/', SubscriptionDetailView.as_view(), name='subscription-detail'),
    path('subscription/checkout/', CreateCheckoutSessionView.as_view(), name='subscription-checkout'),
    path('subscription/change/', ChangePlanView.as_view(), name='subscription-change'),
    path('subscription/cancel/', CancelSubscriptionView.as_view(), name='subscription-cancel'),
    path('webhooks/stripe/', StripeWebhookView.as_view(), name='stripe-webhook'),
]
