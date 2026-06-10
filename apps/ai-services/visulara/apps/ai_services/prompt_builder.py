CATEGORY_GUIDANCE = {
    "relaxation": {
        "focus": "Stress relief, softness, rest, and calm regulation of the nervous system.",
        "imagery": "Beach, rain, sunset, warm stillness, and exhaling tension.",
        "affirmations": "I can soften now. I am safe to rest.",
    },
    "self love": {
        "focus": "Compassion, self-acceptance, forgiveness, and worthiness.",
        "imagery": "Warm light around the heart, gentle mirrors, blooming flowers.",
        "affirmations": "I am enough. I deserve kindness.",
    },
    "focus & clarity": {
        "focus": "Concentration, mental clarity, discernment, and steady attention.",
        "imagery": "Mountain peak, clear lake, crisp morning air.",
        "affirmations": "My mind is clear. I return to what matters.",
    },
    "gratitude": {
        "focus": "Thankfulness, joy, abundance, and appreciation for the present moment.",
        "imagery": "Golden light, open fields, a full heart.",
        "affirmations": "There is goodness here. I receive this moment.",
    },
    "trust": {
        "focus": "Safety, surrender, grounded confidence, and letting go of control.",
        "imagery": "Strong roots, calm horizons, held and supported space.",
        "affirmations": "I can trust this moment. I am supported.",
    },
    "energy": {
        "focus": "Vitality, motivation, strength, and a gentle return to aliveness.",
        "imagery": "Sunrise, golden warmth, sparkling air, awakening fire.",
        "affirmations": "Energy moves through me. I welcome fresh strength.",
    },
    "transformation": {
        "focus": "Growth, release, renewal, and new beginnings.",
        "imagery": "Butterfly, phoenix, spring forest, shedding old layers.",
        "affirmations": "I allow change. I welcome my next chapter.",
    },
    "inner peace": {
        "focus": "Stillness, silence, presence, spaciousness, and deep inner calm.",
        "imagery": "Zen garden, moonlight, still lake, soft open sky.",
        "affirmations": "Peace lives within me. I return to stillness.",
    },
}

CATEGORY_ALIASES = {
    "relaxation": "relaxation",
    "self love": "self love",
    "self_love": "self love",
    "focus & clarity": "focus & clarity",
    "focus_clarity": "focus & clarity",
    "gratitude": "gratitude",
    "trust": "trust",
    "energy": "energy",
    "transformation": "transformation",
    "inner peace": "inner peace",
    "inner_peace": "inner peace",
}

DURATION_GUIDANCE = {
    5: "short meditation, concise guidance, and compact pacing.",
    10: "medium meditation, steady pacing, and a little more settling.",
    20: "detailed meditation with balanced pacing and room to deepen.",
    30: "deep meditation with spacious pacing, silence, and integration.",
}

EXPERIENCE_GUIDANCE = {
    "beginner": "Use more guidance, gentle explanations, and supportive instructions.",
    "intermediate": "Use balanced guidance with self-reflection and soft transitions.",
    "advanced": "Use less instruction, longer pauses, and deeper awareness practices.",
}

DEFAULT_STRUCTURE = [
    "greeting",
    "breathing",
    "body_scan",
    "personal_reflection",
    "suggestion",
    "affirmation",
    "visualization",
    "conclusion",
]


def _safe_join(values):
    if not values:
        return "None specified"
    if isinstance(values, str):
        return values
    return ", ".join(str(value) for value in values)


def build_prompt(data):
    category_key = CATEGORY_ALIASES.get(str(data.get("category") or "relaxation").strip().lower(), "relaxation")
    guidance = CATEGORY_GUIDANCE.get(category_key, CATEGORY_GUIDANCE["relaxation"])
    duration_minutes = int(data.get("duration") or 20)
    duration_guidance = DURATION_GUIDANCE.get(duration_minutes, DURATION_GUIDANCE[20])
    experience = str(data.get("experience") or "beginner").strip().lower()
    experience_guidance = EXPERIENCE_GUIDANCE.get(experience, EXPERIENCE_GUIDANCE["beginner"])
    total_duration = duration_minutes * 60

    return f"""
You are a world-class meditation teacher creating a highly personalized guided meditation.

Write the meditation in {data.get("language", "German")}.
Use warm, calming, emotionally intelligent language.
Return valid JSON only with no markdown fences or extra commentary.

User Profile:
- Category: {data.get("category", "Relaxation")}
- Emotion: {data.get("emotion", "Not specified")}
- Goal: {data.get("goal", "Not specified")}
- Experience: {experience}
- Duration: {duration_minutes} minutes
- Body Tension: {_safe_join(data.get("body_tension"))}
- Nature Sound: {data.get("nature_sound", "Not specified")}
- Visualization Theme: {data.get("landscape", "Not specified")}
- User Name: {data.get("user_name", "Not specified")}
- Stressors To Release: {data.get("stress_input", "Not specified")}
- Additional Answers: {_safe_join(data.get("questionnaire_context"))}

Category Guidance:
- Focus: {guidance["focus"]}
- Imagery: {guidance["imagery"]}
- Affirmation tone: {guidance["affirmations"]}
- Duration guidance: {duration_guidance}
- Experience guidance: {experience_guidance}

Requirements:
1. Personalize the meditation based on the user's emotional state and goal.
2. Reference the listed body tension areas naturally.
3. Include the selected landscape and soundscape in the visualization.
4. If stressors are provided, help the user release them gently without sounding clinical.
5. Match the requested duration closely. The total duration must equal {total_duration} seconds.
6. Use this structure in order: {", ".join(DEFAULT_STRUCTURE)}.
7. Make the language suitable for a {experience} meditator.
8. Keep suggestion and affirmation sections strong, memorable, and easy to replay.

Return JSON in this exact shape:
{{
  "title": "",
  "summary": "",
  "total_duration": {total_duration},
  "steps": [
    {{
      "step_type": "greeting",
      "duration": 0,
      "content": ""
    }}
  ]
}}
"""
