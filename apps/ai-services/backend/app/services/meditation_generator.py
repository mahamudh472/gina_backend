import math
from jsonschema import Draft202012Validator
from app.constants.meditation import STEP_ORDER
from app.constants.meditation import (
    CATEGORY_PROMPT_GUIDANCE,
    DURATION_PROMPT_GUIDANCE,
    EXPERIENCE_PROMPT_GUIDANCE,
    get_category_label,
    normalize_category,
    normalize_experience_level,
    validate_duration,
)
from app.services.ai_generator import AIGenerationError, OpenAIMeditationGenerator
from app.services.prompt_builder import build_meditation_prompt

MEDITATION_JSON_SCHEMA = {
    "type": "object",
    "required": ["title", "summary", "total_duration", "steps"],
    "properties": {
        "title": {"type": "string", "minLength": 1},
        "summary": {"type": "string", "minLength": 1},
        "total_duration": {"type": "integer", "minimum": 60},
        "steps": {
            "type": "array",
            "minItems": 8,
            "items": {
                "type": "object",
                "required": ["step_type", "content", "duration", "start_time", "end_time"],
                "properties": {
                    "step_type": {"type": "string", "minLength": 1},
                    "content": {"type": "string", "minLength": 1},
                    "duration": {"type": "integer", "minimum": 1},
                    "start_time": {"type": "integer", "minimum": 0},
                    "end_time": {"type": "integer", "minimum": 1},
                },
                "additionalProperties": False,
            },
        },
    },
    "additionalProperties": False,
}

validator = Draft202012Validator(MEDITATION_JSON_SCHEMA)

def validate_meditation_json(payload: dict) -> None:
    errors = sorted(validator.iter_errors(payload), key=lambda err: list(err.path))
    if errors:
        message = "; ".join(error.message for error in errors[:3])
        raise ValueError(f"Invalid meditation JSON: {message}")

def _ensure_timing(payload: dict) -> dict:
    cursor = 0
    normalized_steps = []
    for index, expected_step in enumerate(STEP_ORDER):
        step = payload["steps"][index]
        step["step_type"] = expected_step
        duration = int(step["duration"])
        step["start_time"] = cursor
        step["end_time"] = cursor + duration
        cursor += duration
        normalized_steps.append(step)
    payload["steps"] = normalized_steps
    payload["total_duration"] = cursor
    return payload

class MeditationOrchestrator:
    def __init__(self, ai_generator: OpenAIMeditationGenerator | None = None) -> None:
        self.ai_generator = ai_generator or OpenAIMeditationGenerator()

    def _build_fallback_script(self, normalized_request: dict) -> dict:
        category = normalize_category(normalized_request["category"])
        category_label = get_category_label(category)
        duration_minutes = validate_duration(normalized_request.get("duration") or 20)
        experience = normalize_experience_level(normalized_request.get("experience") or "beginner")
        total_duration = duration_minutes * 60

        guidance = CATEGORY_PROMPT_GUIDANCE.get(category, CATEGORY_PROMPT_GUIDANCE["relaxation"])
        duration_guidance = DURATION_PROMPT_GUIDANCE[duration_minutes]
        experience_guidance = EXPERIENCE_PROMPT_GUIDANCE[experience]

        weights = [0.08, 0.12, 0.16, 0.10, 0.18, 0.14, 0.14, 0.08]
        durations = [max(1, math.floor(total_duration * weight)) for weight in weights]
        diff = total_duration - sum(durations)
        durations[-1] += diff

        body_tension = normalized_request.get("body_tension") or []
        body_tension_text = ", ".join(body_tension) if body_tension else "the places that are holding tension"

        step_texts = {
            "greeting": f"Welcome into this {duration_minutes}-minute {category_label.lower()} meditation. {duration_guidance}",
            "breathing": f"Breathe with {experience_guidance.lower()} and let the breath steady your whole system.",
            "body_scan": f"Notice {body_tension_text} and soften those areas with {guidance['focus']}.",
            "personal_reflection": f"Let the intention of {normalized_request.get('goal', 'feeling better')} become clear without pressure.",
            "suggestion": f"Repeat quietly: {guidance['affirmations']}",
            "affirmation": f"You can trust this {category_label.lower()} practice. {normalized_request.get('stress_input', 'Everything outside this moment can wait.')}",
            "visualization": f"Imagine {normalized_request.get('landscape', 'a peaceful landscape')} while {normalized_request.get('nature_sound', 'a gentle soundscape')} surrounds you.",
            "conclusion": f"Carry this calm forward with {experience_guidance.lower()} and return whenever you need it.",
        }

        steps = []
        cursor = 0
        for step_type, duration in zip(STEP_ORDER, durations):
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
            "title": f"{category_label} Meditation",
            "summary": f"A {duration_minutes}-minute {category_label.lower()} meditation shaped for {experience} practice.",
            "total_duration": total_duration,
            "steps": steps,
        }

    async def generate(self, *, request_data: dict) -> dict:
        prompt = build_meditation_prompt(request_data=request_data)
        normalized = {
            "category": request_data.get("category"),
            "duration": request_data.get("duration") or request_data.get("duration_minutes") or 20,
            "experience": request_data.get("experience") or request_data.get("experience_level") or "beginner",
            "body_tension": request_data.get("body_tension") or request_data.get("body_tension_areas") or [],
            "goal": request_data.get("goal") or "General wellbeing",
            "stress_input": request_data.get("stress_input") or "",
            "nature_sound": request_data.get("nature_sound") or "",
            "landscape": request_data.get("landscape") or "",
        }

        try:
            payload = await self.ai_generator.generate_json(prompt)
        except AIGenerationError:
            payload = self._build_fallback_script(normalized)
        payload = _ensure_timing(payload)
        validate_meditation_json(payload)
        return payload
