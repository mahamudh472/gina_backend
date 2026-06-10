import math
import json
import logging

from visulara.apps.ai_services.ai_generator import generate_script as generate_openai_script
from visulara.apps.ai_services.prompt_builder import build_prompt

logger = logging.getLogger(__name__)

SECTION_VOICE_DIRECTIONS = {
    "meditation": {
        "pitch": "Warm, grounded, and steady",
        "pacing": "Slow with restful pauses",
        "emotion": "Calm and reassuring",
        "tts_settings": {
            "stability": 0.84,
            "similarity_boost": 0.72,
            "style": 0.28,
        },
    },
    "suggestion": {
        "pitch": "Softly intimate and focused",
        "pacing": "Rhythmic and loop-friendly",
        "emotion": "Encouraging and immersive",
        "tts_settings": {
            "stability": 0.82,
            "similarity_boost": 0.75,
            "style": 0.32,
        },
    },
    "affirmation": {
        "pitch": "Centered and heart-led",
        "pacing": "Measured and memorable",
        "emotion": "Empowering and gentle",
        "tts_settings": {
            "stability": 0.9,
            "similarity_boost": 0.8,
            "style": 0.2,
        },
    },
}

MEDITATION_STEP_TYPES = {
    "greeting",
    "breathing",
    "body_scan",
    "personal_reflection",
    "visualization",
    "conclusion",
}


def build_questionnaire(category: str | None = None) -> list[dict]:
    category_label = category or "Relaxation"
    return [
        {
            "key": "emotion",
            "question": f"What best describes how you feel right now in your {category_label.lower()} practice?",
            "options": ["Stressed", "Restless", "Tired", "Open"],
        },
        {
            "key": "goal",
            "question": "What would you most like to feel after this meditation?",
            "options": ["Lighter", "Safer", "Clearer", "More energized"],
        },
        {
            "key": "duration",
            "question": "How long should this meditation be?",
            "options": ["5", "10", "20", "30"],
        },
        {
            "key": "experience",
            "question": "What is your meditation experience level?",
            "options": ["Beginner", "Intermediate", "Advanced"],
        },
        {
            "key": "body_tension",
            "question": "Where are you carrying the most tension?",
            "options": ["Neck", "Shoulders", "Chest", "Jaw"],
        },
        {
            "key": "nature_sound",
            "question": "Which soundscape feels most supportive today?",
            "options": ["Rain", "Ocean waves", "Wind", "Silence"],
        },
        {
            "key": "landscape",
            "question": "Which landscape would you like to visualize?",
            "options": ["Mountain lake", "Beach", "Forest", "Temple above clouds"],
        },
    ]


def normalize_generation_payload(data: dict) -> dict:
    body_tension = data.get("body_tension") or data.get("body_tension_areas") or data.get("body_focus") or []
    if isinstance(body_tension, str):
        body_tension = [part.strip() for part in body_tension.split(",") if part.strip()]

    duration = data.get("duration")
    if duration in (None, ""):
        duration = 20

    experience = data.get("experience") or data.get("experience_level") or "beginner"

    questionnaire_answers = data.get("questionnaire_answers") or {}
    questionnaire_context = [
        f"{question}: {answer}" for question, answer in questionnaire_answers.items()
    ]

    return {
        "category": data.get("category") or data.get("intention") or "Relaxation",
        "emotion": data.get("emotion") or data.get("current_mood") or "Not specified",
        "goal": data.get("goal") or data.get("meditation_goal") or data.get("intention") or "General relaxation",
        "avoid": data.get("avoid") or data.get("stress_input") or "Not specified",
        "duration": int(duration),
        "experience": experience,
        "body_tension": body_tension,
        "nature_sound": data.get("nature_sound") or data.get("audio_anchor") or "Not specified",
        "landscape": data.get("landscape") or data.get("landscape_env") or "Not specified",
        "language": data.get("language") or "German",
        "user_name": data.get("name") or data.get("user_name") or "Not specified",
        "stress_input": data.get("stress_input") or data.get("avoid") or "Not specified",
        "questionnaire_context": questionnaire_context,
    }


def _parse_json_response(raw_text: str) -> dict:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.rsplit("```", 1)[0]
    return json.loads(cleaned)


def _validate_script(script: dict, expected_total_duration: int) -> dict:
    if not script.get("title"):
        raise ValueError("Missing meditation title.")
    if not isinstance(script.get("steps"), list) or not script["steps"]:
        raise ValueError("Meditation steps are missing.")

    total_duration = script.get("total_duration")
    if not isinstance(total_duration, int):
        raise ValueError("total_duration must be an integer.")

    if abs(total_duration - expected_total_duration) > 60:
        logger.warning(
            "Generated total_duration %s differs from requested %s.",
            total_duration,
            expected_total_duration,
        )

    for step in script["steps"]:
        if not step.get("step_type") or not step.get("content"):
            raise ValueError("Each step requires step_type and content.")
        if not isinstance(step.get("duration"), int):
            raise ValueError("Each step requires an integer duration.")

    return script


def _build_audio_sections(script: dict) -> dict:
    meditation_parts = []
    suggestion_parts = []
    affirmation_parts = []

    for step in script["steps"]:
        step_type = step["step_type"]
        content = step["content"].strip()
        if step_type in MEDITATION_STEP_TYPES:
            meditation_parts.append(content)
        elif step_type == "suggestion":
            suggestion_parts.append(content)
        elif step_type == "affirmation":
            affirmation_parts.append(content)
        else:
            meditation_parts.append(content)

    sections = {
        "meditation": {
            "script": "\n\n".join(meditation_parts).strip(),
            "voice_direction": SECTION_VOICE_DIRECTIONS["meditation"],
        },
        "suggestion": {
            "script": "\n\n".join(suggestion_parts).strip(),
            "voice_direction": SECTION_VOICE_DIRECTIONS["suggestion"],
        },
        "affirmation": {
            "script": "\n\n".join(affirmation_parts).strip(),
            "voice_direction": SECTION_VOICE_DIRECTIONS["affirmation"],
        },
    }

    for name, section in sections.items():
        if not section["script"]:
            raise ValueError(f"Generated meditation is missing the {name} section.")

    return sections


def _build_local_fallback_script(normalized: dict) -> dict:
    duration_minutes = int(normalized.get("duration") or 20)
    total_duration = duration_minutes * 60
    category = str(normalized.get("category") or "Relaxation")
    experience = str(normalized.get("experience") or "beginner")
    body_tension = normalized.get("body_tension") or []
    body_tension_text = ", ".join(body_tension) if body_tension else "the places holding tension"

    weights = [0.08, 0.12, 0.16, 0.10, 0.18, 0.14, 0.14, 0.08]
    durations = [max(1, math.floor(total_duration * weight)) for weight in weights]
    durations[-1] += total_duration - sum(durations)

    step_texts = {
        "greeting": f"Welcome into this {duration_minutes}-minute {category.lower()} meditation.",
        "breathing": f"Breathe steadily and let the breath guide you into calm.",
        "body_scan": f"Notice {body_tension_text} and allow them to soften.",
        "personal_reflection": f"Let your intention of {normalized.get('goal', 'feeling better')} become clear.",
        "suggestion": f"Repeat quietly: {normalized.get('avoid', 'Everything outside this moment can wait.')}",
        "affirmation": f"You are supported, grounded, and safe in this {category.lower()} practice.",
        "visualization": f"Imagine {normalized.get('landscape', 'a peaceful place')} while {normalized.get('nature_sound', 'a gentle soundscape')} surrounds you.",
        "conclusion": f"Carry this calm forward with {experience} awareness and return whenever you need it.",
    }

    steps = []
    cursor = 0
    for step_type, duration in zip(["greeting", "breathing", "body_scan", "personal_reflection", "suggestion", "affirmation", "visualization", "conclusion"], durations):
        end_time = cursor + duration
        steps.append(
            {
                "step_type": step_type,
                "content": step_texts[step_type],
                "duration": duration,
                "start_time": cursor,
                "end_time": end_time,
            }
        )
        cursor = end_time

    return {
        "title": f"{category} Meditation",
        "summary": f"A {duration_minutes}-minute {category.lower()} meditation designed for {experience} practice.",
        "total_duration": total_duration,
        "steps": steps,
    }


def generate_structured_meditation(data: dict) -> dict:
    normalized = normalize_generation_payload(data)
    prompt = build_prompt(normalized)
    try:
        script = generate_openai_script(prompt)
        logger.info("Meditation script generated with OpenAI.")
    except Exception as exc:
        logger.warning("OpenAI generation failed, using local fallback: %s", exc)
        script = _build_local_fallback_script(normalized)

    expected_total_duration = normalized["duration"] * 60
    structured_script = _validate_script(script, expected_total_duration)
    sections = _build_audio_sections(structured_script)
    return {
        "normalized_request": normalized,
        "meditation": structured_script,
        "sections": sections,
    }
