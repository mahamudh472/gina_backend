import datetime
import json
import logging
import re
from typing import Any

import requests
from django.conf import settings

from apps.ai_service.exceptions import MeditationGenerationError
from apps.main.models import MeditationCategory, MeditationStep

logger = logging.getLogger(__name__)



AI_STEP_ORDER = [
    "greeting",        
    "body_focus",      
    "suggestion",      
    "affirmation",     
    "visualization",   
]

DJANGO_STEP_ORDER = [
    MeditationStep.GREETING,       
    MeditationStep.PERSONAL,       
    MeditationStep.SUGGESTION,     
    MeditationStep.CONFIRMATION,   
    MeditationStep.VISUALIZATION,  
]

CATEGORY_LABELS = {
    MeditationCategory.RELAXATION: "Entspannung",
    MeditationCategory.SELF_LOVE: "Selbstliebe",
    MeditationCategory.FOCUS_CLARITY: "Fokus und Klarheit",
    MeditationCategory.GRATITUDE: "Dankbarkeit",
    MeditationCategory.TRUST: "Vertrauen",
    MeditationCategory.ENERGY: "Energie",
    MeditationCategory.TRANSFORMATION: "Transformation",
    MeditationCategory.INNER_PEACE: "Innerer Frieden",
}

CATEGORY_GUIDANCE = {
    MeditationCategory.RELAXATION: {
        "focus": "Stressabbau, Weichheit, tiefe Ruhe und Regulation des Nervensystems",
        "visualization": "Strand, Regen, Sonnenuntergang oder warme Stille",
        "affirmation": "Ich darf loslassen. Ich bin sicher. Ruhe ist jetzt erlaubt.",
    },
    MeditationCategory.SELF_LOVE: {
        "focus": "Selbstmitgefuehl, Annahme, Vergebung und Wuerde",
        "visualization": "warmes Herzlicht, Blumen, sanfte Spiegel und Morgenlicht",
        "affirmation": "Ich bin genug. Ich darf freundlich mit mir sein.",
    },
    MeditationCategory.FOCUS_CLARITY: {
        "focus": "Konzentration, Klarheit, Stabilitaet und ausgerichtete Aufmerksamkeit",
        "visualization": "Berggipfel, klarer See und frische Morgenluft",
        "affirmation": "Mein Geist wird klar. Ich kehre zu dem zurueck, was zaehlt.",
    },
    MeditationCategory.GRATITUDE: {
        "focus": "Dankbarkeit, Fuelle, Freude und Wertschaetzung des Moments",
        "visualization": "goldene Wiese, offener Himmel und warmes Licht",
        "affirmation": "Dankbarkeit lebt in mir. Ich empfange diesen Moment.",
    },
    MeditationCategory.TRUST: {
        "focus": "Sicherheit, Hingabe, Vertrauen und Loslassen von Kontrolle",
        "visualization": "starke Wurzeln, weiter Horizont und gehaltene Raeume",
        "affirmation": "Ich darf vertrauen. Ich bin getragen.",
    },
    MeditationCategory.ENERGY: {
        "focus": "Lebendigkeit, Motivation, Kraft und sanftes Erwachen",
        "visualization": "Sonnenaufgang, goldenes Licht und klare, funkelnde Luft",
        "affirmation": "Neue Energie fliesst durch mich. Ich bin lebendig und bereit.",
    },
    MeditationCategory.TRANSFORMATION: {
        "focus": "Wachstum, Erneuerung, Loslassen und Neubeginn",
        "visualization": "Schmetterling, Phonix, Fruehlingswald und neue Wege",
        "affirmation": "Ich oeffne mich fuer Wandel. Ich wachse in mein Neues hinein.",
    },
    MeditationCategory.INNER_PEACE: {
        "focus": "Stille, Praesenz, innerer Raum und tiefer Frieden",
        "visualization": "Zen-Garten, Mondlicht, stiller See und weiter Himmel",
        "affirmation": "Stille lebt in mir. Frieden ist bereits da.",
    },
}


def generate_ai_meditation_content(
    *,
    category: str,
    q_a: Any,
    voice_name: str = "",
    nature_sound_name: str = "",
    background_image_name: str = "",
) -> tuple[str, list[dict[str, Any]]]:
    request_data = _build_request_data(
        category=category,
        q_a=q_a,
        voice_name=voice_name,
        nature_sound_name=nature_sound_name,
        background_image_name=background_image_name,
    )

    payload = _generate_with_llm(request_data)
    return _convert_payload_to_django_steps(payload)


def _build_request_data(
    *,
    category: str,
    q_a: Any,
    voice_name: str,
    nature_sound_name: str,
    background_image_name: str,
) -> dict[str, Any]:
    answers = _normalize_answers(q_a)

    return {
        "category": category,
        "category_label": CATEGORY_LABELS.get(
            category,
            CATEGORY_LABELS[MeditationCategory.RELAXATION]
        ),
        "user_name": answers.get("name")
            or answers.get("user_name")
            or answers.get("username")
            or "",

        "mood": answers.get("current_mood")
            or answers.get("feeling")
            or answers.get("emotion")
            or "",

        "stress_input": answers.get("stress_input")
            or answers.get("stressors")
            or answers.get("avoid")
            or "",

        "goal": answers.get("goal")
            or answers.get("focus")
            or answers.get("intention")
            or "innere Balance",

        "duration": _normalize_duration(
            answers.get("duration")
            or answers.get("duration_minutes")
        ),

        "experience": answers.get("experience")
            or answers.get("experience_level")
            or "beginner",

        "body_focus": answers.get("body_focus")
            or answers.get("body_tension")
            or "",

        "audio_anchor": answers.get("audio_anchor"),

        "landscape_env": answers.get("landscape_env"),

        "voice_name": voice_name,

        "questionnaire_answers": answers,
    }

def _normalize_answers(q_a: Any) -> dict[str, Any]:
    if isinstance(q_a, dict):
        return dict(q_a)

    answers: dict[str, Any] = {}
    if isinstance(q_a, list):
        for index, item in enumerate(q_a):
            if not isinstance(item, dict):
                continue
            key = item.get("key") or item.get("name") or item.get("question") or f"answer_{index}"
            answer = item.get("answer", item.get("value"))
            answers[str(key)] = answer

            question = str(item.get("question", "")).lower()
            if "name" in question:
                answers.setdefault("name", answer)
            if any(word in question for word in ["goal", "ziel", "focus", "fokus", "intention"]):
                answers.setdefault("goal", answer)
            if any(word in question for word in ["duration", "dauer"]):
                answers.setdefault("duration", answer)
            if any(word in question for word in ["experience", "erfahrung"]):
                answers.setdefault("experience", answer)

    return answers


def _normalize_duration(value: Any) -> int:
    try:
        duration = int(value or 10)
    except (TypeError, ValueError):
        duration = 10
    return duration if duration in {5, 10, 20, 30} else 10


def _normalize_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def _generate_with_llm(request_data: dict[str, Any]) -> dict[str, Any] | None:
    provider = str(getattr(settings, "LLM_PROVIDER", "openai")).lower()
    if provider == "openai":
        return _generate_with_openai(request_data)
    if provider == "gemini":
        return _generate_with_gemini(request_data)

    raise MeditationGenerationError(f"Unsupported LLM_PROVIDER '{provider}'.")


def _generate_with_openai(request_data: dict[str, Any]) -> dict[str, Any] | None:
    provider = str(getattr(settings, "LLM_PROVIDER", "openai")).lower()
    if provider != "openai":
        raise MeditationGenerationError(
            f"OpenAI generator cannot handle provider '{provider}'."
        )

    api_key = getattr(settings, "LLM_API_KEY", None)
    if not api_key:
        raise MeditationGenerationError("LLM_API_KEY is not configured.")

    try:
        from openai import OpenAI
    except ImportError:
        raise MeditationGenerationError(
            "The openai package is not installed."
        )

    prompt = _build_prompt(request_data)

    logger.info(
        "Calling OpenAI model '%s'...",
        getattr(settings, "LLM_MODEL", "gpt-4o-mini")
    )

    try:
        response = OpenAI(api_key=api_key).chat.completions.create(
            model=getattr(settings, "LLM_MODEL", None) or "gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You generate valid meditation JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                },
            ],
            timeout=getattr(settings, "LLM_TIMEOUT_SECONDS", 60),
        )

        logger.info("OpenAI response received successfully.")

        content = response.choices[0].message.content or "{}"

        payload = json.loads(content)

        logger.info(
            "Meditation generated successfully. Title='%s', Steps=%s",
            payload.get("title", "Untitled"),
            len(payload.get("steps", []))
        )

        validated_payload = _validate_payload(
            payload,
            request_data["duration"] * 60
        )

        logger.info(
            "Meditation payload validated successfully. Duration=%s seconds",
            validated_payload.get("total_duration")
        )

        return validated_payload

    except Exception as exc:
        logger.exception("OpenAI meditation generation failed")
        raise MeditationGenerationError(
            f"OpenAI meditation generation failed: {exc}"
        ) from exc


def _generate_with_gemini(request_data: dict[str, Any]) -> dict[str, Any] | None:
    api_key = getattr(settings, "LLM_API_KEY", None)
    if not api_key:
        raise MeditationGenerationError("LLM_API_KEY is not configured.")

    model_candidates = _gemini_model_candidates()
    prompt = _build_prompt(request_data)
    last_error = ""

    logger.info(
        "Starting Gemini meditation generation. Models=%s",
        model_candidates
    )

    for model in model_candidates:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

        try:
            logger.info("Calling Gemini model '%s'...", model)

            response = requests.post(
                url,
                params={"key": api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "response_mime_type": "application/json",
                    },
                },
                timeout=getattr(settings, "LLM_TIMEOUT_SECONDS", 60),
            )

            response.raise_for_status()

            logger.info(
                "Gemini response received successfully from model '%s'.",
                model
            )

            payload = _extract_gemini_json(response.json())

            logger.info(
                "Meditation generated successfully. Title='%s', Steps=%s",
                payload.get("title", "Untitled"),
                len(payload.get("steps", []))
            )

            validated_payload = _validate_payload(
                payload,
                request_data["duration"] * 60
            )

            logger.info(
                "Meditation payload validated successfully. Duration=%s seconds",
                validated_payload.get("total_duration")
            )

            return validated_payload

        except Exception as exc:
            last_error = _redact_api_key(str(exc))

            logger.exception(
                "Gemini meditation generation failed for model '%s'",
                model
            )

            logger.warning(
                "Gemini model '%s' failed: %s",
                model,
                last_error
            )

    raise MeditationGenerationError(
        f"All Gemini models failed. Last error: {last_error}"
    )



def _gemini_model_candidates() -> list[str]:
    configured_models = list(getattr(settings, "LLM_MODELS", []) or [])
    configured_model = str(getattr(settings, "LLM_MODEL", "") or "").strip()
    candidates = []
    for model in configured_models:
        cleaned_model = str(model).strip()
        if cleaned_model and cleaned_model not in candidates:
            candidates.append(cleaned_model)
    if configured_model and configured_model not in candidates:
        candidates.append(configured_model)
    for fallback in ["gemini-2.5-flash", "gemini-2.5-flash-lite"]:
        if fallback and fallback not in candidates:
            candidates.append(fallback)
    return candidates


def _redact_api_key(message: str) -> str:
    return re.sub(r"([?&]key=)[^&\\s]+", r"\1[redacted]", message)


def _extract_gemini_json(response_data: dict[str, Any]) -> dict[str, Any]:
    raw_text = response_data["candidates"][0]["content"]["parts"][0]["text"]
    cleaned = str(raw_text).strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.rsplit("```", 1)[0]
    return json.loads(cleaned)


def _build_prompt(data: dict[str, Any]) -> str:
    category = data["category"]
    guidance = CATEGORY_GUIDANCE.get(category, CATEGORY_GUIDANCE[MeditationCategory.RELAXATION])
    questionnaire_lines = "\n".join(
        f"- {key}: {value}" for key, value in data["questionnaire_answers"].items()
    ) or "- Keine zusaetzlichen Antworten"
    total_duration = data["duration"] * 60
    
    body_focus = data.get("body_focus") or "Nicht angegeben"
    audio_anchor = data.get("audio_anchor") or "Nicht angegeben"
    landscape_env = data.get("landscape_env") or "Nicht angegeben"

    return f"""
    Du bist ein professioneller Meditationsleiter für VISULARA.

    Erstelle basierend auf den User-Inputs ein Skript für die personalisierten Teile der Meditation.

    Deine Antwort MUSS ausschließlich ein valides JSON-Objekt sein.

    Sprache: Deutsch.
    Tonfall: Sanft, ruhig, empathisch, langsame Sprechweise.

Schreibstil für Audio-Optimierung:
- Schreibe in einem ruhigen, gesprächigen Meditationsstil.
- Verwende häufig Kommas (,), Auslassungspunkte (...) und Gedankenstriche (—), um natürliche Atempausen zu schaffen.
- Füge doppelte Zeilenumbrüche (\\n\\n) zwischen wichtigen Gedanken und Übergängen ein.
- Verwende kürzere Sätze und eine weichere Ausdrucksweise, die für geführte Meditationen geeignet ist.

Benutzerprofil:

- Kategorie: {data["category_label"]}
- Name: {data["user_name"] or "Nicht angegeben"}
- Emotion: {data["mood"] or "Nicht angegeben"}
- Ziel: {data["goal"]}
- Zu lösende Belastung: {data["stress_input"] or "Nicht angegeben"}
- Körperbereich: {body_focus}
- Naturklang: {audio_anchor}
- Visualisierungslandschaft: {landscape_env}
- Dauer: {data["duration"]} Minuten
- Erfahrung: {data["experience"]}
- Stimme: {data["voice_name"] or "Nicht angegeben"}

Weitere Antworten:
{questionnaire_lines}


Kategoriespezifische Richtung:
- Fokus: {guidance["focus"]}
- Visualisierung: {guidance["visualization"]}
- Affirmation: {guidance["affirmation"]}

Pflichtanforderungen:

1. Erstelle einzigartige Inhalte und keine statische Vorlage.

2. Nutze exakt diese VISULARA Slot Reihenfolge:
   - greeting
   - body_focus
   - suggestion
   - affirmation
   - visualization

3. greeting:
   - Nutze user_name und mood.

4. body_focus:
   - Nutze body_focus.
   - Konzentriere dich auf den gewählten Körperbereich.

5. suggestion:
   - Nutze goal.
   - Formuliere einen kurzen, kraftvollen Satz.

6. affirmation:
   - Nutze goal.
   - Erstelle eine kurze, wiederholbare Affirmation.

7. visualization:
   - Nutze landscape_env und audio_anchor.
   - Führe den Nutzer in die gewählte Landschaft.

8. Jede Section muss enthalten:
   - step_type
   - content
   - duration
   - start_time
   - end_time

9. total_duration muss exakt {total_duration} Sekunden sein.
10. Integriere Ziel, Körperbereich, Naturklang und Landschaft natürlich.

JSON-Form:
{{
  "title": "string",
  "summary": "string",
  "total_duration": {total_duration},
  "steps": [
    {{"step_type": "greeting", "content": "string", "duration": 60, "start_time": 0, "end_time": 60}}
  ]
}}
"""


def _validate_payload(payload: dict[str, Any], expected_total_duration: int) -> dict[str, Any]:
    if not isinstance(payload, dict) or not payload.get("title"):
        raise ValueError("Meditation payload requires a title.")
    if not isinstance(payload.get("steps"), list) or not payload["steps"]:
        raise ValueError("Meditation payload requires steps.")

    normalized_steps = []
    cursor = 0
    for step in payload["steps"]:
        step_type = str(step.get("step_type") or "").strip()
        content = str(step.get("content") or "").strip()
        duration = int(step.get("duration") or 0)
        if not step_type or not content or duration <= 0:
            raise ValueError("Each meditation step requires step_type, content and duration.")
        normalized_steps.append(
            {
                "step_type": step_type,
                "content": content,
                "duration": duration,
                "start_time": cursor,
                "end_time": cursor + duration,
            }
        )
        cursor += duration

    if abs(cursor - expected_total_duration) > 60:
        logger.warning("Generated duration %s differs from requested %s.", cursor, expected_total_duration)

    payload["steps"] = normalized_steps
    payload["total_duration"] = cursor
    return payload


def _convert_payload_to_django_steps(payload: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {step_type: [] for step_type in DJANGO_STEP_ORDER}

    for step in payload["steps"]:
        django_step_type = _map_ai_step_to_django_step(str(step["step_type"]))
        grouped[django_step_type].append(step)

    steps_data = []
    for step_type in DJANGO_STEP_ORDER:
        source_steps = grouped[step_type]
        content = "\n\n".join(str(step["content"]).strip() for step in source_steps if step.get("content")).strip()
        duration_seconds = sum(int(step.get("duration") or 0) for step in source_steps)
        if not content:
            raise MeditationGenerationError(f"Generated meditation is missing content for step '{step_type}'.")
        if duration_seconds <= 0:
            raise MeditationGenerationError(f"Generated meditation has invalid duration for step '{step_type}'.")
        steps_data.append(
            {
                "step_type": step_type,
                "content": content,
                "duration": datetime.timedelta(seconds=max(1, duration_seconds)),
            }
        )

    return str(payload["title"]).strip(), steps_data


def _map_ai_step_to_django_step(step_type: str) -> str:
    normalized = step_type.strip().lower()
    if normalized == "greeting":
        return MeditationStep.GREETING

    if normalized == "body_focus":
        return MeditationStep.PERSONAL

    if normalized == "suggestion":
        return MeditationStep.SUGGESTION

    if normalized in {"affirmation", "confirmation"}:
        return MeditationStep.CONFIRMATION

    if normalized == "visualization":
        return MeditationStep.VISUALIZATION
   
    raise MeditationGenerationError(f"Generated meditation contains unknown step type '{step_type}'.")
