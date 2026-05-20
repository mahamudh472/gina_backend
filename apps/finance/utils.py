import stripe
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeUtil:
    @staticmethod
    def get_or_create_customer(user):
        """
        Retrieves or creates a Stripe customer for the user.
        """
        # We can store stripe_customer_id on the Subscription model
        # or check if one already exists for any of the user's subscriptions.
        from .models import Subscription
        
        subscription = Subscription.objects.filter(user=user).first()
        if subscription and subscription.stripe_customer_id:
            try:
                customer = stripe.Customer.retrieve(subscription.stripe_customer_id)
                return customer.id
            except stripe.error.StripeError as e:
                logger.error(f"Error retrieving Stripe customer: {str(e)}")
        
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.full_name or user.username or user.email,
                metadata={
                    "user_id": str(user.id)
                }
            )
            return customer.id
        except stripe.error.StripeError as e:
            logger.error(f"Error creating Stripe customer: {str(e)}")
            raise e

    @staticmethod
    def create_checkout_session(user, price_id, success_url, cancel_url):
        """
        Creates a Stripe Checkout Session for a subscription.
        """
        customer_id = StripeUtil.get_or_create_customer(user)
        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "user_id": str(user.id),
                    "stripe_price_id": price_id
                }
            )
            return session
        except stripe.error.StripeError as e:
            logger.error(f"Error creating checkout session: {str(e)}")
            raise e

    @staticmethod
    def update_subscription(stripe_subscription_id, new_price_id, proration_behavior='always_invoice'):
        """
        Updates a Stripe subscription with a new price.
        """
        try:
            subscription = stripe.Subscription.retrieve(stripe_subscription_id)
            subscription_item_id = subscription['items']['data'][0]['id']
            
            updated_subscription = stripe.Subscription.modify(
                stripe_subscription_id,
                proration_behavior=proration_behavior,
                items=[{
                    'id': subscription_item_id,
                    'price': new_price_id,
                }]
            )
            return updated_subscription
        except stripe.error.StripeError as e:
            logger.error(f"Error updating Stripe subscription: {str(e)}")
            raise e

    @staticmethod
    def cancel_subscription(stripe_subscription_id, at_period_end=True):
        """
        Cancels a Stripe subscription.
        """
        try:
            if at_period_end:
                updated_subscription = stripe.Subscription.modify(
                    stripe_subscription_id,
                    cancel_at_period_end=True
                )
                return updated_subscription
            else:
                canceled_subscription = stripe.Subscription.cancel(stripe_subscription_id)
                return canceled_subscription
        except stripe.error.StripeError as e:
            logger.error(f"Error canceling Stripe subscription: {str(e)}")
            raise e

    @staticmethod
    def verify_webhook(payload, sig_header):
        """
        Verifies a Stripe webhook payload signature.
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
            return event
        except ValueError as e:
            # Invalid payload
            logger.error(f"Invalid Webhook payload: {str(e)}")
            raise e
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            logger.error(f"Invalid Webhook signature: {str(e)}")
            raise e
