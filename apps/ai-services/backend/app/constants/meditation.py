MEDITATION_CATEGORIES = [
    ("relaxation", "Relaxation"),
    ("self_love", "Self Love"),
    ("focus_clarity", "Focus & Clarity"),
    ("gratitude", "Gratitude"),
    ("trust", "Trust"),
    ("energy", "Energy"),
    ("transformation", "Transformation"),
    ("inner_peace", "Inner Peace"),
]

EXPERIENCE_LEVELS = [
    ("beginner", "Beginner"),
    ("intermediate", "Intermediate"),
    ("advanced", "Advanced"),
]

DURATION_OPTIONS = [5, 10, 20, 30]

CATEGORY_ALIASES = {
    "relaxation": "relaxation",
    "self love": "self_love",
    "self_love": "self_love",
    "focus & clarity": "focus_clarity",
    "focus_clarity": "focus_clarity",
    "gratitude": "gratitude",
    "trust": "trust",
    "energy": "energy",
    "transformation": "transformation",
    "inner peace": "inner_peace",
    "inner_peace": "inner_peace",
}

CATEGORY_LABELS = {key: label for key, label in MEDITATION_CATEGORIES}
EXPERIENCE_LABELS = {key: label for key, label in EXPERIENCE_LEVELS}

DURATION_PROMPT_GUIDANCE = {
    5: "short, direct, and compact with only the essential guidance.",
    10: "medium-length with enough space to settle, but still concise.",
    20: "detailed, balanced, and comfortably immersive.",
    30: "deep, spacious, and slow with room for silence and integration.",
}

EXPERIENCE_PROMPT_GUIDANCE = {
    "beginner": "Use more guidance, simple explanations, and supportive instructions.",
    "intermediate": "Use balanced guidance with some self-reflection and spaciousness.",
    "advanced": "Use less instruction, longer silent spaces, and deeper awareness practices.",
}

GENERATION_STATUSES = [
    ("pending", "Pending"),
    ("generated", "Generated"),
    ("failed", "Failed"),
]

STEP_ORDER = [
    "greeting",
    "breathing",
    "body_scan",
    "personal_reflection",
    "suggestion",
    "affirmation",
    "visualization",
    "conclusion",
]

CATEGORY_PROMPT_GUIDANCE = {
    "relaxation": {
        "focus": "stress relief, calmness, softening tension, rest",
        "visualization": "beach, rain, sunset, warm stillness",
        "coaching_language": "slow, grounding, soothing",
        "affirmations": "Ich darf loslassen. Ich bin sicher. Ruhe ist jetzt erlaubt.",
    },
    "self_love": {
        "focus": "self-compassion, self-acceptance, forgiveness, worthiness",
        "visualization": "warm heart light, flowers, sunrise glow",
        "coaching_language": "compassionate, intimate, nurturing",
        "affirmations": "Ich bin genug. Ich bin liebenswert. Ich darf mich annehmen.",
    },
    "focus_clarity": {
        "focus": "concentration, mental clarity, stability, discernment",
        "visualization": "mountain peak, clear lake, crisp air",
        "coaching_language": "clear, centered, steady",
        "affirmations": "Mein Geist wird klar. Ich bin gesammelt. Ich sehe deutlich.",
    },
    "gratitude": {
        "focus": "appreciation, abundance, gratitude, joy",
        "visualization": "golden meadow, warm horizon, open sky",
        "coaching_language": "uplifting, appreciative, warm",
        "affirmations": "Dankbarkeit lebt in mir. Ich empfange diesen Moment.",
    },
    "trust": {
        "focus": "confidence, safety, surrender, letting go",
        "visualization": "roots, wide horizon, held space",
        "coaching_language": "reassuring, steady, protective",
        "affirmations": "Ich darf vertrauen. Ich bin getragen. Ich lasse Kontrolle weich werden.",
    },
    "energy": {
        "focus": "vitality, motivation, strength, aliveness",
        "visualization": "sunrise, golden light, bright movement",
        "coaching_language": "encouraging, bright, revitalizing",
        "affirmations": "Neue Energie fließt durch mich. Ich bin lebendig und bereit.",
    },
    "transformation": {
        "focus": "growth, renewal, change, new beginnings",
        "visualization": "phoenix, butterfly, spring forest",
        "coaching_language": "courageous, hopeful, expansive",
        "affirmations": "Ich öffne mich für Wandel. Ich wachse in mein Neues hinein.",
    },
    "inner_peace": {
        "focus": "stillness, silence, presence, spaciousness",
        "visualization": "moonlight, zen garden, still lake",
        "coaching_language": "minimal, spacious, serene",
        "affirmations": "Stille lebt in mir. Frieden ist bereits da.",
    },
}

def normalize_category(value: str | None) -> str:
    if not value:
        return "relaxation"
    normalized = str(value).strip().lower()
    return CATEGORY_ALIASES.get(normalized, normalized)

def get_category_label(value: str | None) -> str:
    return CATEGORY_LABELS.get(normalize_category(value), "Relaxation")

def normalize_experience_level(value: str | None) -> str:
    if not value:
        return "beginner"
    normalized = str(value).strip().lower().replace(" ", "_")
    if normalized in EXPERIENCE_LABELS:
        return normalized
    if normalized in {label.lower() for label in EXPERIENCE_LABELS.values()}:
        for key, label in EXPERIENCE_LABELS.items():
            if label.lower() == normalized:
                return key
    return normalized

def validate_duration(value: int | str | None) -> int:
    duration = int(value or 20)
    if duration not in DURATION_OPTIONS:
        raise ValueError(f"Duration must be one of: {', '.join(str(option) for option in DURATION_OPTIONS)}.")
    return duration
