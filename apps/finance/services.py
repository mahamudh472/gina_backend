import stripe
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from datetime import datetime, timezone as dt_timezone
import logging

logger = logging.getLogger(__name__)

from .models import Plan, CreditWallet, Subscription
from .utils import StripeUtil

User = get_user_model()

class SubscriptionService:
    @staticmethod
    def _parse_timestamp(timestamp):
        if timestamp:
            try:
                return datetime.fromtimestamp(int(timestamp), tz=dt_timezone.utc)
            except Exception:
                pass
        return None

    @staticmethod
    def _to_dict(stripe_obj):
        if stripe_obj is None:
            return {}
        if hasattr(stripe_obj, 'to_dict'):
            try:
                return stripe_obj.to_dict()
            except Exception:
                pass
        return dict(stripe_obj)

    @staticmethod
    def create_checkout_session(user, plan_slug, success_url, cancel_url):
        """
        Creates a Stripe checkout session for subscribing to a plan.
        """
        try:
            plan = Plan.objects.get(slug=plan_slug, is_active=True)
        except Plan.DoesNotExist:
            raise ValueError(f"Plan with slug '{plan_slug}' does not exist or is inactive.")

        if not plan.stripe_price_id:
            raise ValueError(f"Plan '{plan.name}' is not linked to any Stripe Price ID.")

        session = StripeUtil.create_checkout_session(
            user=user,
            price_id=plan.stripe_price_id,
            success_url=success_url,
            cancel_url=cancel_url
        )
        return session.url

    @staticmethod
    @transaction.atomic
    def change_plan(user, new_plan_slug):
        """
        Upgrades or downgrades a user's subscription.
        Upgrades are immediate, while downgrades are scheduled for the next billing cycle.
        """
        try:
            subscription = Subscription.objects.select_for_update().get(user=user)
        except Subscription.DoesNotExist:
            raise ValueError("User does not have an active subscription to change.")

        if subscription.status != 'active' and subscription.status != 'trialing':
            raise ValueError("Subscription is not active. Cannot change plans.")

        try:
            new_plan = Plan.objects.get(slug=new_plan_slug, is_active=True)
        except Plan.DoesNotExist:
            raise ValueError(f"Plan with slug '{new_plan_slug}' does not exist.")

        current_plan = subscription.plan

        if current_plan.id == new_plan.id:
            raise ValueError("User is already subscribed to this plan.")

        # Determine upgrade vs downgrade based on credits (Basic=1, Core=3, Pro=10)
        is_upgrade = new_plan.credit_amount > current_plan.credit_amount

        if is_upgrade:
            # Upgrade directly
            if not subscription.stripe_subscription_id:
                # If they don't have a Stripe ID, we just upgrade them locally
                subscription.plan = new_plan
                subscription.pending_plan = None
                subscription.save()
                
                # Reset wallet credit balance
                wallet = user.wallet
                wallet.balance = new_plan.credit_amount
                wallet.last_reset_at = timezone.now()
                wallet.save()
                return subscription, "upgrade"

            # Modify Stripe subscription immediately (always_invoice prorates and invoices immediately)
            StripeUtil.update_subscription(
                stripe_subscription_id=subscription.stripe_subscription_id,
                new_price_id=new_plan.stripe_price_id,
                proration_behavior='always_invoice'
            )

            # Update local DB immediately
            subscription.plan = new_plan
            subscription.pending_plan = None
            subscription.save()

            # Grant new plan's credits immediately
            wallet = user.wallet
            wallet.balance = new_plan.credit_amount
            wallet.last_reset_at = timezone.now()
            wallet.save()

            return subscription, "upgrade"
        else:
            # Downgrade - schedule for next billing cycle
            if not subscription.stripe_subscription_id:
                # If no stripe sub, just downgrade immediately
                subscription.plan = new_plan
                subscription.pending_plan = None
                subscription.save()
                
                wallet = user.wallet
                wallet.balance = new_plan.credit_amount
                wallet.last_reset_at = timezone.now()
                wallet.save()
                return subscription, "upgrade"

            # Tell Stripe to change price at next billing cycle (proration_behavior='none')
            # Stripe updates the price on the sub item but does not charge/refund.
            StripeUtil.update_subscription(
                stripe_subscription_id=subscription.stripe_subscription_id,
                new_price_id=new_plan.stripe_price_id,
                proration_behavior='none'
            )

            # Save the pending plan to Django subscription
            subscription.pending_plan = new_plan
            subscription.save()

            return subscription, "downgrade"

    @staticmethod
    @transaction.atomic
    def cancel_subscription(user):
        """
        Cancels the active subscription at the end of the current period.
        """
        try:
            subscription = Subscription.objects.select_for_update().get(user=user)
        except Subscription.DoesNotExist:
            raise ValueError("No active subscription found.")

        if not subscription.stripe_subscription_id:
            subscription.status = 'canceled'
            subscription.save()
            return subscription

        StripeUtil.cancel_subscription(subscription.stripe_subscription_id, at_period_end=True)
        subscription.cancel_at_period_end = True
        subscription.save()
        return subscription

    @staticmethod
    def handle_webhook(payload, sig_header):
        """
        Handles incoming Stripe webhook events.
        """
        try:
            event = StripeUtil.verify_webhook(payload, sig_header)
            event = SubscriptionService._to_dict(event)
        except Exception as e:
            raise ValueError(f"Webhook verification failed: {str(e)}")

        event_type = event.get('type')
        data_object = event.get('data', {}).get('object', {})

        logger.info("Received Stripe webhook event: %s", event_type)

        if event_type == 'checkout.session.completed':
            SubscriptionService._handle_checkout_session_completed(data_object)
        elif event_type in ['invoice.paid', 'invoice.payment_succeeded']:
            SubscriptionService._handle_invoice_paid(data_object)
        elif event_type == 'customer.subscription.created':
            SubscriptionService._handle_subscription_created(data_object)
        elif event_type == 'customer.subscription.updated':
            SubscriptionService._handle_subscription_updated(data_object)
        elif event_type == 'customer.subscription.deleted':
            SubscriptionService._handle_subscription_deleted(data_object)
        else:
            logger.info("Ignoring unhandled Stripe webhook event: %s", event_type)

        return event

    @staticmethod
    @transaction.atomic
    def _handle_checkout_session_completed(session):
        """
        Processes checkout.session.completed to initialize the user subscription.
        """
        metadata = session.get('metadata', {})
        user_id = metadata.get('user_id')
        price_id = metadata.get('stripe_price_id')
        stripe_sub_id = session.get('subscription')
        stripe_customer_id = session.get('customer')

        if not user_id or not stripe_sub_id:
            logger.warning(
                "Skipping checkout.session.completed: missing user_id or subscription "
                "(user_id=%s, subscription=%s)",
                user_id,
                stripe_sub_id,
            )
            return

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.warning("Skipping checkout.session.completed: user %s not found", user_id)
            return

        try:
            plan = Plan.objects.get(stripe_price_id=price_id)
        except Plan.DoesNotExist:
            logger.warning(
                "Skipping checkout.session.completed: plan with stripe_price_id %s not found",
                price_id,
            )
            return

        # Fetch full subscription details from Stripe
        try:
            stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)
            stripe_sub_dict = SubscriptionService._to_dict(stripe_sub)
            current_period_start = SubscriptionService._parse_timestamp(stripe_sub_dict.get('current_period_start')) or timezone.now()
            current_period_end = SubscriptionService._parse_timestamp(stripe_sub_dict.get('current_period_end')) or (timezone.now() + timezone.timedelta(days=30))
            status = stripe_sub_dict.get('status') or 'active'
            cancel_at_period_end = stripe_sub_dict.get('cancel_at_period_end') or False
        except Exception:
            current_period_start = timezone.now()
            current_period_end = timezone.now() + timezone.timedelta(days=30)
            status = 'active'
            cancel_at_period_end = False

        subscription, created = Subscription.objects.get_or_create(
            user=user,
            defaults={
                'plan': plan,
                'stripe_subscription_id': stripe_sub_id,
                'stripe_customer_id': stripe_customer_id,
                'status': status,
                'current_period_start': current_period_start,
                'current_period_end': current_period_end,
                'cancel_at_period_end': cancel_at_period_end
            }
        )

        if not created:
            subscription.plan = plan
            subscription.stripe_subscription_id = stripe_sub_id
            subscription.stripe_customer_id = stripe_customer_id
            subscription.status = status
            subscription.current_period_start = current_period_start
            subscription.current_period_end = current_period_end
            subscription.cancel_at_period_end = cancel_at_period_end
            subscription.save()

        # Update credit wallet
        wallet, _ = CreditWallet.objects.get_or_create(user=user)
        wallet.balance = plan.credit_amount
        wallet.last_reset_at = timezone.now()
        wallet.save()

    @staticmethod
    @transaction.atomic
    def _handle_subscription_created(stripe_sub):
        """
        Creates a local subscription from a Stripe subscription event.
        This is a fallback for event ordering and dashboard webhook configs where
        customer.subscription.created arrives before checkout.session.completed.
        """
        stripe_sub_id = stripe_sub.get('id')
        metadata = stripe_sub.get('metadata') or {}
        user_id = metadata.get('user_id')
        price_id = metadata.get('stripe_price_id')

        if not price_id:
            price_id = stripe_sub.get('items', {}).get('data', [{}])[0].get('price', {}).get('id')

        if not user_id:
            logger.warning(
                "Skipping customer.subscription.created for %s: missing user_id metadata",
                stripe_sub_id,
            )
            return

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.warning(
                "Skipping customer.subscription.created for %s: user %s not found",
                stripe_sub_id,
                user_id,
            )
            return

        try:
            plan = Plan.objects.get(stripe_price_id=price_id)
        except Plan.DoesNotExist:
            logger.warning(
                "Skipping customer.subscription.created for %s: plan with stripe_price_id %s not found",
                stripe_sub_id,
                price_id,
            )
            return

        current_period_start = SubscriptionService._parse_timestamp(stripe_sub.get('current_period_start')) or timezone.now()
        current_period_end = SubscriptionService._parse_timestamp(stripe_sub.get('current_period_end')) or (timezone.now() + timezone.timedelta(days=30))

        subscription, _ = Subscription.objects.update_or_create(
            user=user,
            defaults={
                'plan': plan,
                'stripe_subscription_id': stripe_sub_id,
                'stripe_customer_id': stripe_sub.get('customer'),
                'status': stripe_sub.get('status') or 'active',
                'current_period_start': current_period_start,
                'current_period_end': current_period_end,
                'cancel_at_period_end': stripe_sub.get('cancel_at_period_end') or False,
            }
        )

        wallet, _ = CreditWallet.objects.get_or_create(user=user)
        wallet.balance = subscription.plan.credit_amount
        wallet.last_reset_at = timezone.now()
        wallet.save()

    @staticmethod
    @transaction.atomic
    def _handle_invoice_paid(invoice):
        """
        Handles invoice payment to renew subscription periods and reset credit balance.
        """
        stripe_sub_id = invoice.get('subscription')
        if not stripe_sub_id:
            return

        try:
            subscription = Subscription.objects.select_for_update().get(stripe_subscription_id=stripe_sub_id)
        except Subscription.DoesNotExist:
            logger.warning(f"Subscription not found for stripe_sub_id {stripe_sub_id}")
            return

        try:
            stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)
            stripe_sub_dict = SubscriptionService._to_dict(stripe_sub)
            new_start = SubscriptionService._parse_timestamp(stripe_sub_dict.get('current_period_start')) or subscription.current_period_start or timezone.now()
            new_end = SubscriptionService._parse_timestamp(stripe_sub_dict.get('current_period_end')) or subscription.current_period_end or (timezone.now() + timezone.timedelta(days=30))
            status = stripe_sub_dict.get('status') or 'active'
            cancel_at_period_end = stripe_sub_dict.get('cancel_at_period_end') or False
        except Exception as e:
            logger.error(f"Error retrieving subscription details: {str(e)}", exc_info=True)
            return

        # Check if this is a new billing cycle or initial cycle
        is_new_cycle = not subscription.current_period_start or new_start > subscription.current_period_start

        subscription.status = status
        subscription.cancel_at_period_end = cancel_at_period_end

        if is_new_cycle:
            subscription.current_period_start = new_start
            subscription.current_period_end = new_end

            # Promote pending plan if a downgrade is scheduled and active price matches pending plan
            if subscription.pending_plan:
                subscription.plan = subscription.pending_plan
                subscription.pending_plan = None
            
            # Reset wallet balance
            wallet, _ = CreditWallet.objects.get_or_create(user=subscription.user)
            wallet.balance = subscription.plan.credit_amount
            wallet.last_reset_at = timezone.now()
            wallet.save()

        subscription.save()

    @staticmethod
    @transaction.atomic
    def _handle_subscription_updated(stripe_sub):
        """
        Handles subscription updates (status change, cancellation setting, etc.).
        """
        stripe_sub_id = stripe_sub.get('id')
        try:
            subscription = Subscription.objects.select_for_update().get(stripe_subscription_id=stripe_sub_id)
        except Subscription.DoesNotExist:
            SubscriptionService._handle_subscription_created(stripe_sub)
            return

        new_start = SubscriptionService._parse_timestamp(stripe_sub.get('current_period_start')) or subscription.current_period_start or timezone.now()
        new_end = SubscriptionService._parse_timestamp(stripe_sub.get('current_period_end')) or subscription.current_period_end or (timezone.now() + timezone.timedelta(days=30))
        status = stripe_sub.get('status')
        cancel_at_period_end = stripe_sub.get('cancel_at_period_end')

        is_new_cycle = not subscription.current_period_start or new_start > subscription.current_period_start

        subscription.status = status
        subscription.cancel_at_period_end = cancel_at_period_end

        if is_new_cycle:
            subscription.current_period_start = new_start
            subscription.current_period_end = new_end

            if subscription.pending_plan:
                subscription.plan = subscription.pending_plan
                subscription.pending_plan = None

            wallet, _ = CreditWallet.objects.get_or_create(user=subscription.user)
            wallet.balance = subscription.plan.credit_amount
            wallet.last_reset_at = timezone.now()
            wallet.save()
        else:
            # If Stripe reports a different price than subscription.plan, and we have a pending plan matching it, promote it
            stripe_price_id = stripe_sub.get('items', {}).get('data', [{}])[0].get('price', {}).get('id')
            if stripe_price_id and subscription.pending_plan and subscription.pending_plan.stripe_price_id == stripe_price_id:
                # If Stripe already transitioned to the new price, promote it.
                subscription.plan = subscription.pending_plan
                subscription.pending_plan = None
                
                wallet, _ = CreditWallet.objects.get_or_create(user=subscription.user)
                wallet.balance = subscription.plan.credit_amount
                wallet.last_reset_at = timezone.now()
                wallet.save()

        subscription.save()

    @staticmethod
    @transaction.atomic
    def _handle_subscription_deleted(stripe_sub):
        """
        Handles subscription cancellation/deletion.
        """
        stripe_sub_id = stripe_sub.get('id')
        try:
            subscription = Subscription.objects.select_for_update().get(stripe_subscription_id=stripe_sub_id)
        except Subscription.DoesNotExist:
            return

        subscription.status = 'canceled'
        subscription.save()

        # Optionally set user's wallet credit balance to 0 on subscription termination
        wallet, _ = CreditWallet.objects.get_or_create(user=subscription.user)
        wallet.balance = 0
        wallet.save()
