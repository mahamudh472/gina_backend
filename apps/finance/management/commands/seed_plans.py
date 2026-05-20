from django.core.management.base import BaseCommand
from apps.finance.models import Plan

class Command(BaseCommand):
    help = 'Seeds or updates default subscription plans (Basic, Core, Pro)'

    def handle(self, *args, **options):
        features = [
            "Individualisierte Deep Meditation",
            "Stimme frei wählbar (w / m)",
            "Themenspezifische binaurale Musik",
            "Dauerhafte Portalnutzung",
            "Volle Mixersteuerung",
            "Automatische Archiv- Speicherung"
        ]

        plans_data = [
            {
                'name': 'Basic',
                'slug': 'basic',
                'price': 9.90,
                'currency': 'eur',
                'credit_amount': 1,
                'stripe_price_id': 'price_basic_mock_123',
                'stripe_product_id': 'prod_basic_mock_123',
                'badge': 'EINSTEIGER',
                'top_badge': None,
                'features': features,
            },
            {
                'name': 'Core',
                'slug': 'core',
                'price': 29.90,
                'currency': 'eur',
                'credit_amount': 3,
                'stripe_price_id': 'price_core_mock_123',
                'stripe_product_id': 'prod_core_mock_123',
                'badge': 'EMPFEHLUNG',
                'top_badge': 'MEISTGEWÄHLT',
                'features': features,
            },
            {
                'name': 'Pro',
                'slug': 'pro',
                'price': 89.90,
                'currency': 'eur',
                'credit_amount': 10,
                'stripe_price_id': 'price_pro_mock_123',
                'stripe_product_id': 'prod_pro_mock_123',
                'badge': 'BUSINESS',
                'top_badge': None,
                'features': features,
            }
        ]

        for p_data in plans_data:
            plan, created = Plan.objects.update_or_create(
                slug=p_data['slug'],
                defaults={
                    'name': p_data['name'],
                    'price': p_data['price'],
                    'currency': p_data['currency'],
                    'credit_amount': p_data['credit_amount'],
                    'stripe_price_id': p_data['stripe_price_id'],
                    'stripe_product_id': p_data['stripe_product_id'],
                    'badge': p_data['badge'],
                    'top_badge': p_data['top_badge'],
                    'features': p_data['features'],
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Successfully created plan: {plan.name}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Successfully updated plan: {plan.name}"))
