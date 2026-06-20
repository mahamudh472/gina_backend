from django.templatetags.static import static

UNFOLD = {
    "THEME": "dark",
    "SITE_TITLE": "VISULARA Admin",
    "SITE_HEADER": "VISULARA",
    "SITE_SUBHEADER": "Meditation operations",
    "SITE_URL": "/",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "SHOW_BACK_BUTTON": True,
    "DASHBOARD_CALLBACK": "visulara.admin_dashboard.dashboard_callback",
    "SITE_LOGO": {
        "light": lambda request: static("logo.svg"),
        "dark": lambda request: static("logo.svg"),
    },
    "SITE_ICON": {
        "light": lambda request: static("logo.svg"),
        "dark": lambda request: static("logo.svg"),
    },
    "COLORS": {
        # Neutral blue-gray base: quiet, readable, and admin-friendly.
        "base": {
            "50": "oklch(98.3% .003 247.9)",
            "100": "oklch(96.1% .006 247.9)",
            "200": "oklch(91.8% .011 248.0)",
            "300": "oklch(84.9% .018 248.2)",
            "400": "oklch(68.7% .029 249.0)",
            "500": "oklch(53.4% .033 250.0)",
            "600": "oklch(43.9% .034 251.0)",
            "700": "oklch(32.4% .032 252.0)",
            "800": "oklch(22.2% .028 254.0)",
            "900": "oklch(15.8% .024 255.0)",
            "950": "oklch(10.6% .020 256.0)",
        },
        # Muted gold accent, used sparingly for primary actions and focus states.
        "primary": {
            "50": "oklch(98.4% .020 94.3)",
            "100": "oklch(95.5% .050 92.7)",
            "200": "oklch(90.2% .100 91.0)",
            "300": "oklch(83.7% .150 88.5)",
            "400": "oklch(76.8% .185 85.0)",
            "500": "oklch(70.2% .175 80.0)",
            "600": "oklch(60.1% .150 75.0)",
            "700": "oklch(48.0% .120 71.0)",
            "800": "oklch(36.8% .090 69.0)",
            "900": "oklch(27.6% .065 68.0)",
            "950": "oklch(18.4% .045 66.0)",
        },
        "font": {
            "subtle-light": "var(--color-base-500)",
            "subtle-dark": "var(--color-base-400)",
            "default-light": "var(--color-base-700)",
            "default-dark": "var(--color-base-200)",
            "important-light": "var(--color-base-900)",
            "important-dark": "var(--color-base-50)",
        },
    },
    "STYLES": [
        lambda request: static("css/custom_admin.css"),
    ],
    "COMMAND": {
        "search_models": True,
        "show_history": True,
    },
    "SIDEBAR": {
        "show_search": True,
        "command_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Workspace",
                "separator": True,
                "items": [
                    {
                        "title": "Dashboard",
                        "icon": "dashboard",
                        "link": "/admin/",
                    },
                ],
            },
            {
                "title": "Content",
                "separator": True,
                "items": [
                    {
                        "title": "Meditations",
                        "icon": "self_improvement",
                        "link": "/admin/main/meditation/",
                    },
                    {
                        "title": "Voices",
                        "icon": "record_voice_over",
                        "link": "/admin/main/charectervoice/",
                    },
                    {
                        "title": "Nature sounds",
                        "icon": "graphic_eq",
                        "link": "/admin/main/naturesounds/",
                    },
                    {
                        "title": "Background images",
                        "icon": "image",
                        "link": "/admin/main/backgroundimage/",
                    },
                ],
            },
            {
                "title": "Customers",
                "separator": True,
                "items": [
                    {
                        "title": "Users",
                        "icon": "group",
                        "link": "/admin/accounts/user/",
                    },
                    {
                        "title": "Credit wallets",
                        "icon": "account_balance_wallet",
                        "link": "/admin/finance/creditwallet/",
                    },
                    {
                        "title": "Subscriptions",
                        "icon": "payments",
                        "link": "/admin/finance/subscription/",
                    },
                    {
                        "title": "Plans",
                        "icon": "sell",
                        "link": "/admin/finance/plan/",
                    },
                ],
            },
        ],
    },
}
