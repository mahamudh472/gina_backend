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
    "breathing",
    "body_scan",
    "personal_reflection",
    "suggestion",
    "affirmation",
    "visualization",
    "conclusion",
]

DJANGO_STEP_ORDER = [
    MeditationStep.GREETING,
    MeditationStep.PERSONAL,
    MeditationStep.INTRODUCTION,
    MeditationStep.SUGGESTION,
    MeditationStep.CONFIRMATION,
    MeditationStep.VISUALIZATION,
    MeditationStep.CONCLUSION,
]

CATEGORY_LABELS = {
    "relaxation": "Entspannung",
    "self_love": "Selbstliebe",
    "focus_clarity": "Fokus und Klarheit",
    "gratitude": "Dankbarkeit",
    "trust": "Vertrauen",
    "energy": "Energie",
    "transformation": "Transformation",
    "inner_peace": "Innerer Frieden",
}

CATEGORY_GUIDANCE = {
    "relaxation": {
        "focus": "Stressabbau, Weichheit, tiefe Ruhe und Regulation des Nervensystems",
        "visualization": "Strand, Regen, Sonnenuntergang oder warme Stille",
        "affirmation": "Ich darf loslassen. Ich bin sicher. Ruhe ist jetzt erlaubt.",
    },
    "self_love": {
        "focus": "Selbstmitgefuehl, Annahme, Vergebung und Wuerde",
        "visualization": "warmes Herzlicht, Blumen, sanfte Spiegel und Morgenlicht",
        "affirmation": "Ich bin genug. Ich darf freundlich mit mir sein.",
    },
    "focus_clarity": {
        "focus": "Konzentration, Klarheit, Stabilitaet und ausgerichtete Aufmerksamkeit",
        "visualization": "Berggipfel, klarer See und frische Morgenluft",
        "affirmation": "Mein Geist wird klar. Ich kehre zu dem zurueck, was zaehlt.",
    },
    "gratitude": {
        "focus": "Dankbarkeit, Fuelle, Freude und Wertschaetzung des Moments",
        "visualization": "goldene Wiese, offener Himmel und warmes Licht",
        "affirmation": "Dankbarkeit lebt in mir. Ich empfange diesen Moment.",
    },
    "trust": {
        "focus": "Sicherheit, Hingabe, Vertrauen und Loslassen von Kontrolle",
        "visualization": "starke Wurzeln, weiter Horizont und gehaltene Raeume",
        "affirmation": "Ich darf vertrauen. Ich bin getragen.",
    },
    "energy": {
        "focus": "Lebendigkeit, Motivation, Kraft und sanftes Erwachen",
        "visualization": "Sonnenaufgang, goldenes Licht und klare, funkelnde Luft",
        "affirmation": "Neue Energie fliesst durch mich. Ich bin lebendig und bereit.",
    },
    "transformation": {
        "focus": "Wachstum, Erneuerung, Loslassen und Neubeginn",
        "visualization": "Schmetterling, Phoenix, Fruehlingswald und neue Wege",
        "affirmation": "Ich oeffne mich fuer Wandel. Ich wachse in mein Neues hinein.",
    },
    "inner_peace": {
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
    request_data = build_request_data(
        category=category,
        q_a=q_a,
        voice_name=voice_name,
        nature_sound_name=nature_sound_name,
        background_image_name=background_image_name,
    )

    payload = _generate_with_llm(request_data)
    return _convert_payload_to_django_steps(payload)


def build_request_data(
    *,
    category: str,
    q_a: Any,
    voice_name: str = "",
    nature_sound_name: str = "",
    background_image_name: str = "",
) -> dict[str, Any]:
    answers = _normalize_answers(q_a)
    return {
        "category": category,
        "category_label": CATEGORY_LABELS.get(category, CATEGORY_LABELS["relaxation"]),
        "user_name": answers.get("name") or answers.get("user_name") or answers.get("username") or "",
        "emotion": answers.get("emotion") or answers.get("current_mood") or answers.get("feeling") or "",
        "goal": answers.get("goal") or answers.get("focus") or answers.get("intention") or "innere Balance",
        "avoid": answers.get("avoid") or answers.get("stress_input") or answers.get("stressors") or "",
        "duration": _normalize_duration(answers.get("duration") or answers.get("duration_minutes")),
        "experience": answers.get("experience") or answers.get("experience_level") or "beginner",
        "body_tension": _normalize_list(answers.get("body_tension") or answers.get("body_tension_areas") or answers.get("body_focus")),
        "nature_sound": answers.get("nature_sound") or nature_sound_name or "",
        "landscape": answers.get("landscape") or answers.get("landscape_env") or background_image_name or "",
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
        raise MeditationGenerationError(f"OpenAI generator cannot handle provider '{provider}'.")

    api_key = getattr(settings, "LLM_API_KEY", None)
    if not api_key:
        raise MeditationGenerationError("LLM_API_KEY is not configured.")

    try:
        from openai import OpenAI
    except ImportError:
        raise MeditationGenerationError("The openai package is not installed.")

    prompt = build_prompt(request_data)
    try:
        response = OpenAI(api_key=api_key).chat.completions.create(
            model=getattr(settings, "LLM_MODEL", None) or "gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You generate valid meditation JSON only."},
                {"role": "user", "content": prompt},
            ],
            timeout=getattr(settings, "LLM_TIMEOUT_SECONDS", 60),
        )
        content = response.choices[0].message.content or "{}"
        payload = json.loads(content)
        return _validate_payload(payload, request_data["duration"] * 60)
    except Exception as exc:
        raise MeditationGenerationError(f"OpenAI meditation generation failed: {exc}") from exc


def _generate_with_gemini(request_data: dict[str, Any]) -> dict[str, Any] | None:
    api_key = getattr(settings, "LLM_API_KEY", None)
    if not api_key:
        raise MeditationGenerationError("LLM_API_KEY is not configured.")

    model_candidates = _gemini_model_candidates()
    prompt = build_prompt(request_data)
    last_error = ""

    for model in model_candidates:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
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
            payload = _extract_gemini_json(response.json())
            return _validate_payload(payload, request_data["duration"] * 60)
        except Exception as exc:
            last_error = _redact_api_key(str(exc))
            logger.warning("Gemini meditation generation failed for model '%s': %s", model, last_error)

    raise MeditationGenerationError(f"All Gemini models failed. Last error: {last_error}")


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


def build_prompt(data: dict[str, Any]) -> str:
    category = data["category"]
    guidance = CATEGORY_GUIDANCE.get(category, CATEGORY_GUIDANCE["relaxation"])
    questionnaire_lines = "\n".join(
        f"- {key}: {value}" for key, value in data["questionnaire_answers"].items()
    ) or "- Keine zusaetzlichen Antworten"
    total_duration = data["duration"] * 60
    body_tension = ", ".join(data["body_tension"]) or "Nicht angegeben"

    return f"""
    Du bist eine weltklasse Meditationslehrerin und erstellst eine hochpersonalisierte gefuehrte Meditation.
    Antworte ausschliesslich als valides JSON ohne Markdown.

    Sprache: Deutsch.

    # KRITISCH: EINHEITLICHER SPRECHRHYTHMUS (WICHTIGSTE REGEL)
    Die gesamte Meditation — von der ersten Silbe des Greetings bis zum letzten Wort der Conclusion —
    MUSS wie EIN einziger, ununterbrochener, extrem langsamer Fluss klingen.
    Es darf KEINEN Unterschied in Geschwindigkeit, Tonfall oder Energie zwischen den 8 Schritten geben.

    ## Schreibmuster (IDENTISCH fuer JEDEN Schritt)
    Schreibe in einem ruhigen, poetischen, fließenden Rhythmus.
    - Nutze natürliche Kommas und Punkte, um Atempausen zu signalisieren.
    - Vermeide abgehackte Halbsätze. Lass die Sätze harmonisch und beruhigend fließen.
    - Beende jeden Satz ganz normal mit einem Punkt.
    - Verwende KEINE Ausrufezeichen, Fragezeichen oder SSML/Code-Tags.

    ## Wortdichte-Regel (KRITISCH fuer gleichmaessige Geschwindigkeit)
    - Schreibe nur ca. 40-60 Woerter pro Minute Dauer.
    - Ein 60-Sekunden-Schritt = maximal 60 Woerter.
    - Weniger Text ist besser. Lass extrem viel Raum fuer Stille.

    ## Tonfall (IDENTISCH fuer alle 8 Schritte)
    - Warm, sanft, langsam, empathisch, ruhig.
    - Alle 8 Schritte sind EIN Fluss. KEINE Stimmungswechsel. KEINE Energieaenderung.
    - KEIN Unterschied zwischen Greeting und Breathing.
    - KEIN Unterschied zwischen Body Scan und Affirmation.

    ## Verbotene Muster
    - KEINE langen Saetze (ueber 8-10 Woerter ohne Komma).
    - KEINE Aufzaehlungen.
    - KEINE rhetorischen Fragen.
    - KEINE Ausrufezeichen.
    - KEINE energischen Formulierungen.

    Benutzerprofil:
    - Kategorie: {data["category_label"]}
    - Emotion: {data["emotion"] or "Nicht angegeben"}
    - Ziel: {data["goal"]}
    - Zu loesende Belastung: {data["avoid"] or "Nicht angegeben"}
    - Dauer: {data["duration"]} Minuten
    - Erfahrung: {data["experience"]}
    - Koerperspannung: {body_tension}
    - Naturklang: {data["nature_sound"] or "Nicht angegeben"}
    - Visualisierungslandschaft: {data["landscape"] or "Nicht angegeben"}
    - Stimme: {data["voice_name"] or "Nicht angegeben"}
    - Name: {data["user_name"] or "Nicht angegeben"}
    - Weitere Antworten:
    {questionnaire_lines}

    Kategoriespezifische Richtung:
    - Fokus: {guidance["focus"]}
    - Visualisierung: {guidance["visualization"]}
    - Affirmation: {guidance["affirmation"]}

    Pflichtanforderungen:
    1. Erstelle einzigartige, poetische Inhalte — keine statische Vorlage.
    2. Nutze genau diese Reihenfolge: {", ".join(AI_STEP_ORDER)}.
    3. Jede Section braucht step_type, content, duration, start_time und end_time.
    4. total_duration muss exakt {total_duration} Sekunden sein.
    5. ALLE Sections muessen den IDENTISCHEN warmen, langsamen Tonfall haben.
    6. ALLE Sections muessen die GLEICHE Wortdichte haben.

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
    if normalized == "personal_reflection":
        return MeditationStep.PERSONAL
    if normalized in {"breathing", "body_scan", "introduction"}:
        return MeditationStep.INTRODUCTION
    if normalized == "suggestion":
        return MeditationStep.SUGGESTION
    if normalized in {"affirmation", "confirmation"}:
        return MeditationStep.CONFIRMATION
    if normalized == "visualization":
        return MeditationStep.VISUALIZATION
    if normalized == "conclusion":
        return MeditationStep.CONCLUSION
    raise MeditationGenerationError(f"Generated meditation contains unknown step type '{step_type}'.")
