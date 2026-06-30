from decimal import Decimal

from django.db.models import Count, Sum
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.finance.models import CreditWallet, Plan, Subscription
from apps.main.models import BackgroundImage, CharecterVoice, Meditation, NatureSounds


def _admin_url(name, *args):
    try:
        return reverse(f"admin:{name}", args=args)
    except NoReverseMatch:
        return "#"


def _percent(value, total):
    if not total:
        return 0
    return round((value / total) * 100)


def _money(value):
    return f"€{value.quantize(Decimal('0.01'))}"


def _subscription_mrr():
    total = Decimal("0")

    subscriptions = Subscription.objects.filter(
        status__in=["active", "trialing"],
        plan__is_active=True,
    ).select_related("plan")

    for subscription in subscriptions:
        price = subscription.plan.price or Decimal("0")
        if subscription.plan.interval == "year":
            total += price / Decimal("12")
        else:
            total += price

    return total


def dashboard_callback(request, context):
    now = timezone.now()
    week_start = now - timezone.timedelta(days=7)
    month_start = now - timezone.timedelta(days=30)

    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    total_meditations = Meditation.objects.count()
    meditations_this_week = Meditation.objects.filter(created_at__gte=week_start).count()
    active_subscriptions = Subscription.objects.filter(status__in=["active", "trialing"]).count()
    total_wallet_balance = CreditWallet.objects.aggregate(total=Sum("balance"))["total"] or 0

    voice_total = CharecterVoice.objects.count()
    sound_total = NatureSounds.objects.count()
    image_total = BackgroundImage.objects.count()

    category_rows = (
        Meditation.objects.values("category")
        .annotate(total=Count("id"))
        .order_by("-total")[:6]
    )
    category_total = sum(row["total"] for row in category_rows)
    category_labels = dict(Meditation._meta.get_field("category").choices)

    subscription_rows = (
        Subscription.objects.values("status")
        .annotate(total=Count("id"))
        .order_by("-total")[:6]
    )
    subscription_total = sum(row["total"] for row in subscription_rows)
    subscription_labels = dict(Subscription.STATUS_CHOICES)

    from apps.main.models import MeditationCategory, MeditationStep, MeditationTemplate

    template_status = []
    required_steps = {
        MeditationStep.INTRODUCTION,
        MeditationStep.VISUALIZATION,
        MeditationStep.CONCLUSION
    }

    active_templates = {
        t.category: t 
        for t in MeditationTemplate.objects.filter(is_active=True).prefetch_related('steps')
    }

    for value, label in MeditationCategory.choices:
        active_template = active_templates.get(value)
        if not active_template:
            template_status.append({
                "category": value,
                "label": label,
                "status": "missing_template",
                "status_label": "No active template",
                "missing": ["Introduction", "Visualization", "Conclusion"],
                "href": _admin_url("main_meditationtemplate_changelist"),
            })
        else:
            existing_steps = {step.step_type for step in active_template.steps.all()}
            missing_types = required_steps - existing_steps
            if not missing_types:
                template_status.append({
                    "category": value,
                    "label": label,
                    "status": "healthy",
                    "status_label": "Healthy",
                    "missing": [],
                    "href": _admin_url("main_meditationtemplate_change", active_template.pk),
                })
            else:
                step_labels = {
                    MeditationStep.INTRODUCTION: "Introduction",
                    MeditationStep.VISUALIZATION: "Visualization",
                    MeditationStep.CONCLUSION: "Conclusion"
                }
                missing_labels = [step_labels[st] for st in required_steps if st in missing_types]
                template_status.append({
                    "category": value,
                    "label": label,
                    "status": "missing_steps",
                    "status_label": f"Missing steps: {', '.join(missing_labels)}",
                    "missing": missing_labels,
                    "href": _admin_url("main_meditationtemplate_change", active_template.pk),
                })

    context.update(
        {
            "dashboard": {
                "generated_at": timezone.localtime(now).strftime("%b %-d, %Y %H:%M"),
                "template_status": template_status,
                "stats": [
                    {
                        "label": "Users",
                        "value": f"{total_users:,}",
                        "meta": f"{active_users:,} active",
                        "icon": "group",
                        "href": _admin_url("accounts_user_changelist"),
                    },
                    {
                        "label": "Meditations",
                        "value": f"{total_meditations:,}",
                        "meta": f"{meditations_this_week:,} created this week",
                        "icon": "self_improvement",
                        "href": _admin_url("main_meditation_changelist"),
                    },
                    {
                        "label": "Subscriptions",
                        "value": f"{active_subscriptions:,}",
                        "meta": f"{_money(_subscription_mrr())} estimated MRR",
                        "icon": "payments",
                        "href": _admin_url("finance_subscription_changelist"),
                    },
                    {
                        "label": "Credits",
                        "value": f"{total_wallet_balance:,}",
                        "meta": "total wallet balance",
                        "icon": "account_balance_wallet",
                        "href": _admin_url("finance_creditwallet_changelist"),
                    },
                ],
                "content_health": [
                    {
                        "label": "Voices",
                        "active": CharecterVoice.objects.filter(is_active=True).count(),
                        "total": voice_total,
                        "href": _admin_url("main_charectervoice_changelist"),
                    },
                    {
                        "label": "Nature sounds",
                        "active": NatureSounds.objects.filter(is_active=True).count(),
                        "total": sound_total,
                        "href": _admin_url("main_naturesounds_changelist"),
                    },
                    {
                        "label": "Backgrounds",
                        "active": BackgroundImage.objects.filter(is_active=True).count(),
                        "total": image_total,
                        "href": _admin_url("main_backgroundimage_changelist"),
                    },
                    {
                        "label": "Plans",
                        "active": Plan.objects.filter(is_active=True).count(),
                        "total": Plan.objects.count(),
                        "href": _admin_url("finance_plan_changelist"),
                    },
                ],
                "categories": [
                    {
                        "label": category_labels.get(row["category"], row["category"]),
                        "total": row["total"],
                        "percent": _percent(row["total"], category_total),
                    }
                    for row in category_rows
                ],
                "subscriptions": [
                    {
                        "label": subscription_labels.get(row["status"], row["status"]),
                        "total": row["total"],
                        "percent": _percent(row["total"], subscription_total),
                    }
                    for row in subscription_rows
                ],
                "recent_meditations": [
                    {
                        "title": meditation.title,
                        "user": meditation.user.email,
                        "category": meditation.get_category_display(),
                        "created": timezone.localtime(meditation.created_at).strftime("%b %-d, %H:%M"),
                        "href": _admin_url("main_meditation_change", meditation.pk),
                    }
                    for meditation in Meditation.objects.select_related("user").order_by("-created_at")[:6]
                ],
                "recent_users": [
                    {
                        "name": user.full_name or user.email,
                        "email": user.email,
                        "joined": timezone.localtime(user.joined_at).strftime("%b %-d, %H:%M"),
                        "active": user.is_active,
                        "href": _admin_url("accounts_user_change", user.pk),
                    }
                    for user in User.objects.order_by("-joined_at")[:6]
                ],
                "activity_window": {
                    "new_users": User.objects.filter(joined_at__gte=month_start).count(),
                    "new_meditations": Meditation.objects.filter(created_at__gte=month_start).count(),
                    "active_or_trialing": active_subscriptions,
                },
            },
        }
    )

    return context
