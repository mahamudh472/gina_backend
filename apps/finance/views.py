from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings

from .models import Plan, CreditWallet, Subscription
from .serializers import (
    PlanSerializer, CreditWalletSerializer, SubscriptionSerializer,
    CheckoutRequestSerializer, ChangePlanRequestSerializer
)
from .services import SubscriptionService

class PlanListView(generics.ListAPIView):
    """
    List all active subscription plans.
    """
    queryset = Plan.objects.filter(is_active=True).order_by('price')
    serializer_class = PlanSerializer
    permission_classes = [AllowAny]


class WalletDetailView(APIView):
    """
    Retrieve current user's credit wallet details.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet, _ = CreditWallet.objects.get_or_create(user=request.user)
        serializer = CreditWalletSerializer(wallet)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SubscriptionDetailView(APIView):
    """
    Retrieve current user's active subscription details.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            subscription = Subscription.objects.get(user=request.user)
            serializer = SubscriptionSerializer(subscription)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Subscription.DoesNotExist:
            return Response(
                {"detail": "No subscription found for this user."},
                status=status.HTTP_404_NOT_FOUND
            )


class CreateCheckoutSessionView(APIView):
    """
    Create a Stripe checkout session for plan subscription.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckoutRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        plan_slug = serializer.validated_data['plan_slug']
        success_url = settings.FRONTEND_URL + '/account/subscription/success'
        cancel_url = settings.FRONTEND_URL + '/account/subscription/cancel'

        try:
            checkout_url = SubscriptionService.create_checkout_session(
                user=request.user,
                plan_slug=plan_slug,
                success_url=success_url,
                cancel_url=cancel_url
            )
            return Response({"checkout_url": checkout_url}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChangePlanView(APIView):
    """
    Upgrade or Downgrade a plan.
    Upgrades are immediate; downgrades are scheduled for next billing cycle.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePlanRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        plan_slug = serializer.validated_data['plan_slug']

        try:
            subscription, action = SubscriptionService.change_plan(
                user=request.user,
                new_plan_slug=plan_slug
            )
            response_serializer = SubscriptionSerializer(subscription)
            return Response({
                "message": f"Plan change initiated successfully. Action: {action}",
                "action": action,
                "subscription": response_serializer.data
            }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CancelSubscriptionView(APIView):
    """
    Cancel subscription at the end of the current period.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            subscription = SubscriptionService.cancel_subscription(user=request.user)
            serializer = SubscriptionSerializer(subscription)
            return Response({
                "message": "Subscription will be canceled at the end of the billing period.",
                "subscription": serializer.data
            }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StripeWebhookView(APIView):
    """
    Webhook receiver for Stripe events.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        if not sig_header:
            return Response({"error": "Missing signature header."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            SubscriptionService.handle_webhook(payload, sig_header)
            return Response({"status": "success"}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
