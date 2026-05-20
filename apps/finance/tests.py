from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch, MagicMock
from datetime import datetime

from apps.finance.models import Plan, CreditWallet, Subscription
from apps.finance.services import SubscriptionService

User = get_user_model()

class MockStripeSubscription(dict):
    """
    Mock class that supports both dict key lookup and attribute lookup
    to match the Stripe SDK's subscription response structure.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for key, value in kwargs.items():
            setattr(self, key, value)


class SubscriptionTestCase(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpassword123',
            full_name='Test User'
        )
        
        # Create plans
        self.basic_plan = Plan.objects.create(
            name='Basic',
            slug='basic',
            price=9.99,
            credit_amount=1,
            stripe_price_id='price_basic_mock_123',
            stripe_product_id='prod_basic_mock_123'
        )
        self.core_plan = Plan.objects.create(
            name='Core',
            slug='core',
            price=24.99,
            credit_amount=3,
            stripe_price_id='price_core_mock_123',
            stripe_product_id='prod_core_mock_123'
        )
        self.pro_plan = Plan.objects.create(
            name='Pro',
            slug='pro',
            price=79.99,
            credit_amount=10,
            stripe_price_id='price_pro_mock_123',
            stripe_product_id='prod_pro_mock_123'
        )

    def test_wallet_auto_created(self):
        """
        Verify that a CreditWallet is automatically created when a User is created.
        """
        wallet = CreditWallet.objects.filter(user=self.user).first()
        self.assertIsNotNone(wallet)
        self.assertEqual(wallet.balance, 0)

    @patch('apps.finance.utils.StripeUtil.get_or_create_customer')
    @patch('stripe.checkout.Session.create')
    def test_create_checkout_session(self, mock_checkout_create, mock_get_customer):
        """
        Verify checkout session creation service call.
        """
        mock_get_customer.return_value = 'cus_mock_123'
        mock_checkout_create.return_value = MagicMock(url='https://checkout.stripe.com/mock_session')
        
        url = SubscriptionService.create_checkout_session(
            user=self.user,
            plan_slug='core',
            success_url='https://example.com/success',
            cancel_url='https://example.com/cancel'
        )
        
        self.assertEqual(url, 'https://checkout.stripe.com/mock_session')
        mock_checkout_create.assert_called_once()

    @patch('stripe.Subscription.retrieve')
    def test_checkout_webhook_initializes_subscription(self, mock_sub_retrieve):
        """
        Verify webhook setup handles checkout completed.
        """
        # Mock stripe sub retrieve using MockStripeSubscription
        mock_sub_retrieve.return_value = MockStripeSubscription(
            id='sub_mock_123',
            current_period_start=1700000000,
            current_period_end=1702592000,
            status='active',
            cancel_at_period_end=False,
            items={
                'data': [{'id': 'sub_item_123'}]
            }
        )

        session_data = {
            'metadata': {
                'user_id': str(self.user.id),
                'stripe_price_id': 'price_core_mock_123'
            },
            'subscription': 'sub_mock_123',
            'customer': 'cus_mock_123'
        }

        SubscriptionService._handle_checkout_session_completed(session_data)

        # Check DB
        subscription = Subscription.objects.filter(user=self.user).first()
        self.assertIsNotNone(subscription)
        self.assertEqual(subscription.plan, self.core_plan)
        self.assertEqual(subscription.stripe_subscription_id, 'sub_mock_123')
        self.assertEqual(subscription.status, 'active')

        # Check wallet credit balance
        wallet = CreditWallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, 3)  # Core plan should grant 3 credits

    @patch('stripe.Subscription.retrieve')
    @patch('stripe.Subscription.modify')
    def test_upgrade_plan_immediate(self, mock_sub_modify, mock_sub_retrieve):
        """
        Verify that upgrading a plan takes effect immediately and resets credits.
        """
        # Mock retrieve so StripeUtil.update_subscription works
        mock_sub_retrieve.return_value = MockStripeSubscription(
            id='sub_mock_123',
            current_period_start=1700000000,
            current_period_end=1702592000,
            status='active',
            cancel_at_period_end=False,
            items={
                'data': [{'id': 'sub_item_123'}]
            }
        )

        # Pre-subscribe user to Core
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.core_plan,
            stripe_subscription_id='sub_mock_123',
            stripe_customer_id='cus_mock_123',
            status='active',
            current_period_start=timezone.now() - timezone.timedelta(days=10),
            current_period_end=timezone.now() + timezone.timedelta(days=20)
        )
        self.user.wallet.balance = 1  # user spent 2 credits, 1 left
        self.user.wallet.save()

        # Upgrade to Pro
        updated_sub, action = SubscriptionService.change_plan(self.user, 'pro')

        self.assertEqual(action, 'upgrade')
        self.assertEqual(updated_sub.plan, self.pro_plan)
        self.assertIsNone(updated_sub.pending_plan)

        # Check Stripe was updated with proration always_invoice
        mock_sub_modify.assert_called_once_with(
            'sub_mock_123',
            proration_behavior='always_invoice',
            items=[{
                'id': 'sub_item_123',
                'price': 'price_pro_mock_123'
            }]
        )

        # Check wallet got Pro credits (10) immediately
        wallet = CreditWallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, 10)

    @patch('stripe.Subscription.retrieve')
    @patch('stripe.Subscription.modify')
    def test_downgrade_plan_scheduled(self, mock_sub_modify, mock_sub_retrieve):
        """
        Verify that downgrading schedules the change for the next billing cycle.
        """
        # Mock retrieve so StripeUtil.update_subscription works
        mock_sub_retrieve.return_value = MockStripeSubscription(
            id='sub_mock_123',
            current_period_start=1700000000,
            current_period_end=1702592000,
            status='active',
            cancel_at_period_end=False,
            items={
                'data': [{'id': 'sub_item_123'}]
            }
        )

        # Pre-subscribe user to Pro
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.pro_plan,
            stripe_subscription_id='sub_mock_123',
            stripe_customer_id='cus_mock_123',
            status='active',
            current_period_start=timezone.now() - timezone.timedelta(days=10),
            current_period_end=timezone.now() + timezone.timedelta(days=20)
        )
        self.user.wallet.balance = 5  # spent 5, 5 left
        self.user.wallet.save()

        # Downgrade to Core
        updated_sub, action = SubscriptionService.change_plan(self.user, 'core')

        self.assertEqual(action, 'downgrade')
        # Active plan should still be Pro
        self.assertEqual(updated_sub.plan, self.pro_plan)
        # Pending plan should be Core
        self.assertEqual(updated_sub.pending_plan, self.core_plan)

        # Stripe should have been modified with proration_behavior='none'
        mock_sub_modify.assert_called_once_with(
            'sub_mock_123',
            proration_behavior='none',
            items=[{
                'id': 'sub_item_123',
                'price': 'price_core_mock_123'
            }]
        )

        # Wallet should NOT have changed balance yet (should still be 5)
        wallet = CreditWallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, 5)

    @patch('stripe.Subscription.retrieve')
    def test_billing_renewal_applies_downgrade(self, mock_sub_retrieve):
        """
        Verify that the next billing cycle triggers the downgrade promotion and credit reset.
        """
        # Pre-subscribe user to Pro with pending Core downgrade
        subscription = Subscription.objects.create(
            user=self.user,
            plan=self.pro_plan,
            pending_plan=self.core_plan,
            stripe_subscription_id='sub_mock_123',
            stripe_customer_id='cus_mock_123',
            status='active',
            current_period_start=timezone.now() - timezone.timedelta(days=30),
            current_period_end=timezone.now()
        )
        self.user.wallet.balance = 0
        self.user.wallet.save()

        # Mock Stripe Subscription return for the new period
        now_ts = int(timezone.now().timestamp())
        mock_sub_retrieve.return_value = MockStripeSubscription(
            id='sub_mock_123',
            current_period_start=now_ts,
            current_period_end=now_ts + 2592000,
            status='active',
            cancel_at_period_end=False,
            items={
                'data': [{'id': 'sub_item_123'}]
            }
        )

        invoice_data = {
            'subscription': 'sub_mock_123'
        }

        # Simulate invoice paid webhook (which marks start of new billing cycle)
        SubscriptionService._handle_invoice_paid(invoice_data)

        # Refresh subscription from DB
        subscription.refresh_from_db()

        # The plan should now be promoted to Core, pending plan cleared
        self.assertEqual(subscription.plan, self.core_plan)
        self.assertIsNone(subscription.pending_plan)

        # Wallet balance should be reset to Core's limit (3)
        wallet = CreditWallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, 3)
