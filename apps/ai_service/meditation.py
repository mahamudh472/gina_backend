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
    "personal_reflection",
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

DEFAULT_CATEGORY = MeditationCategory.SELF_DISCOVERY

CATEGORY_LABELS = {
    "self_discovery": "Identität & Selbstfindung",
    "emotional_healing": "Emotionale Heilung",
    "inner_peace": "Innerer Frieden",
    "transformation": "Transformation",
    "energy": "Energie",
    "grounding": "Erdung & Stressmanagement",
}

CATEGORY_GUIDANCE = {
    "self_discovery": {
        "focus": "Selbsterkenntnis, Identität, innere Wahrheit und authentisches Sein",
        "visualization": "Spiegel, klarer See, Sternenhimmel und innere Kompass",
        "affirmation": "Ich erkenne mich selbst. Mein wahres Selbst führt mich.",
    },
    "emotional_healing": {
        "focus": "Emotionale Verarbeitung, Heilung alter Wunden, Loslassen und Vergebung",
        "visualization": "heilendes Licht, fließendes Wasser, schützender Kokon und sanfte Umarmung",
        "affirmation": "Ich erlaube mir zu fühlen und zu heilen. Meine Emotionen sind willkommen.",
    },
    "inner_peace": {
        "focus": "Stille, Präsenz, innerer Raum und tiefer Frieden",
        "visualization": "Zen-Garten, Mondlicht, stiller See und weiter Himmel",
        "affirmation": "Stille lebt in mir. Frieden ist bereits da.",
    },
    "transformation": {
        "focus": "Wachstum, Erneuerung, Loslassen und Neubeginn",
        "visualization": "Schmetterling, Phoenix, Frühlingswald und neue Wege",
        "affirmation": "Ich öffne mich für Wandel. Ich wachse in mein Neues hinein.",
    },
    "energy": {
        "focus": "Lebendigkeit, Motivation, Kraft und sanftes Erwachen",
        "visualization": "Sonnenaufgang, goldenes Licht und klare, funkelnde Luft",
        "affirmation": "Neue Energie fließt durch mich. Ich bin lebendig und bereit.",
    },
    "grounding": {
        "focus": "Stressabbau, Stabilität, Erdung und Bewältigung des Alltags",
        "visualization": "starke Wurzeln, Berg, fester Boden und schützender Baum",
        "affirmation": "Ich bin geerdet und stabil. Ich meistere meinen Alltag mit Ruhe.",
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
    if not payload:
        raise MeditationGenerationError("AI meditation generator returned no payload.")
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
        "category_label": CATEGORY_LABELS.get(category) or CATEGORY_LABELS[DEFAULT_CATEGORY],
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

    raise MeditationGenerationError(f"Unsupported LLM_PROVIDER '{provider}'. Only 'openai' is supported.")


MANDATORY_JSON_FORMAT_TEMPLATE = """
# PFLICHTANFORDERUNGEN AN DAS AUSGABEFORMAT (JSON):
Antworte ausschliesslich als valides JSON-Objekt ohne Markdown (kein ```json).
Das JSON-Objekt MUSS zwingend folgende Struktur und Felder aufweisen:
{
  "title": "<Aussagekraeftiger Titel der Meditation als String>",
  "summary": "<Kurze Zusammenfassung>",
  "total_duration": {total_duration},
  "steps": [
    {
      "step_type": "greeting",
      "content": "<Begruessungstext fuer gesprochenes Audio>",
      "duration": 60,
      "start_time": 0,
      "end_time": 60
    },
    {
      "step_type": "personal_reflection",
      "content": "<Text fuer persoenliche Reflexion und Koerperfokus>",
      "duration": 240,
      "start_time": 60,
      "end_time": 300
    },
    {
      "step_type": "suggestion",
      "content": "<Suggestionen mit [[PAUSE_4S]] Pausenmarkern>",
      "duration": 120,
      "start_time": 300,
      "end_time": 420
    },
    {
      "step_type": "affirmation",
      "content": "<Affirmationen mit [[PAUSE_4S]] Pausenmarkern>",
      "duration": 60,
      "start_time": 420,
      "end_time": 480
    },
    {
      "step_type": "visualization",
      "content": "<Visualisierungsreise in der gewaehlten Landschaft>",
      "duration": 240,
      "start_time": 480,
      "end_time": 720
    }
  ]
}

KRITISCHE REGELN:
1. Das Feld "title" ist zwingend erforderlich (darf nicht fehlen oder leer sein).
2. Das Feld "steps" muss eine Liste von Objekten sein, genau in der Reihenfolge: greeting, personal_reflection, suggestion, affirmation, visualization.
3. Jeder Schritt in "steps" MUSS die Felder "step_type", "content" und "duration" (in Sekunden) enthalten.
"""


def _ensure_format_instructions(prompt: str, total_duration: int) -> str:
    """Ensure that the prompt sent to the LLM always contains the required JSON schema instructions.
    If a custom prompt template configured in the database omits the JSON format or required fields,
    this automatically appends the mandatory JSON format instructions.
    """
    has_title_instruction = '"title"' in prompt or "'title'" in prompt
    has_steps_instruction = '"steps"' in prompt or "'steps'" in prompt
    has_step_type = "step_type" in prompt

    if not (has_title_instruction and has_steps_instruction and has_step_type):
        format_instructions = MANDATORY_JSON_FORMAT_TEMPLATE.replace("{total_duration}", str(total_duration))
        prompt = f"{prompt.strip()}\n\n{format_instructions.strip()}"

    return prompt


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
    total_duration = request_data.get("duration", 10) * 60
    prompt = _ensure_format_instructions(prompt, total_duration)

    content = ""
    try:
        response = OpenAI(api_key=api_key).chat.completions.create(
            model=getattr(settings, "LLM_MODEL", None) or "gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert meditation instructor. "
                        "You must respond ONLY with a valid JSON object (no markdown, no code fences). "
                        "The JSON object must contain the top-level keys: 'title' (string), 'summary' (string), "
                        "'total_duration' (number), and 'steps' (array of objects with 'step_type', 'content', 'duration'). "
                        "Allowed step_type values: 'greeting', 'personal_reflection', 'suggestion', 'affirmation', 'visualization'."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            timeout=getattr(settings, "LLM_TIMEOUT_SECONDS", 60),
        )
        content = response.choices[0].message.content or "{}"
        payload = json.loads(content)
        category_label = request_data.get("category_label")
        default_title = f"{category_label} Meditation" if category_label else "Geführte Meditation"
        return _validate_payload(payload, total_duration, default_title=default_title)
    except Exception as exc:
        logger.error(
            "OpenAI meditation generation failed: %s. Raw LLM content: %s",
            exc,
            content or "N/A",
        )
        raise MeditationGenerationError(f"OpenAI meditation generation failed: {exc}") from exc


DEFAULT_PROMPT_TEMPLATE = """Du bist eine weltklasse Meditationslehrerin und erstellst eine hochpersonalisierte gefuehrte Meditation.
Antworte ausschliesslich als valides JSON ohne Markdown.

Sprache: Deutsch.

# GLOBALE REGELN FÜR ALLE AI-GENERIERTEN MEDITATIONSBLÖCKE
- **TONFALL**: Ruhig, warm, achtsam und vertrauenswürdig (calm, warm, mindful, trustworthy).
- **SPRACHE**: Einfach, klar und leicht verständlich.
- **KEIN STORYTELLING**: Erzähle keine Geschichten. Führe und leite den Nutzer lediglich an.
- **PAUSEN**: Setze bewusste Sprechpausen für die Sprachsynthese ein (signalisiert durch natürliche Kommas und Punkte).
- **EINHEITLICHER SPRECHRHYTHMUS (KRITISCH)**:
  Die gesamte Meditation muss wie ein einziger, ununterbrochener, extrem langsamer Fluss klingen.
  Es darf keinen Unterschied in Geschwindigkeit, Tonfall oder Energie zwischen den Schritten geben.
- **SCHREIBMUSTER**:
  Schreibe in einem ruhigen, poetischen, fließenden Rhythmus.
  Beende jeden Satz normal mit einem Punkt.
  Verwende KEINE Ausrufezeichen, Fragezeichen oder SSML/Code-Tags.
- **VERBOTENE MUSTER**:
  KEINE Sätze über 8-10 Wörter ohne Komma. KEINE Aufzählungen. KEINE rhetorischen Fragen. KEINE energischen Formulierungen.

Benutzerprofil:
- Kategorie: {category_label}
- Emotion / aktuelle Stimmung: (Extrahiere die aktuelle Stimmung, Emotion oder das Gefühl des Nutzers selbstständig aus den unten stehenden Antworten des Fragebogens)
- Ziel: {goal}
- Zu loesende Belastung: {avoid}
- Dauer: {duration} Minuten
- Erfahrung: {experience}
- Koerperspannung: {body_tension}
- Naturklang (Audio-Anker): {nature_sound}
- Visualisierungslandschaft: {landscape}
- Stimme: {voice_name}
- Name: {user_name}
- Weitere Antworten:
{questionnaire_lines}

Kategoriespezifische Richtung:
- Fokus: {focus}
- Visualisierung: {visualization}
- Affirmation: {affirmation}

# SPEZIFISCHE ANFORDERUNGEN AN DIE AI-BLÖCKE:

## A: greeting (Personal Welcome)
- **Zweck**: Emotionaler Anker und Abholen des Nutzers.
- **Variablen**: Name des Nutzers ({user_name}), aktuelle Stimmung/Emotion.
- **Aufgabe**: Hole den Nutzer genau da ab, wo er emotional steht, und gestalte den Übergang zur darauffolgenden Einführung (Intro).
- **Beispiel-Struktur**: "Hallo {user_name}. Wie schön, dass du dir heute diesen Moment für dich nimmst. Du hast angegeben, dass du dich gerade [Stimmung/Gefühl aus dem Fragebogen] fühlst. Das ist vollkommen okay – alles darf genau so sein, wie es jetzt ist. Gemeinsam schaffen wir den Raum, um diesen Zustand sanft zu verändern. Lass uns beginnen..."

## B: personal_reflection (Personalized Main Section)
- **Zweck**: Emotionaler Kern, Körperfokus und Lösen von Anspannungen.
- **Dauer**: Ca. 4-6 Minuten spoken audio (Wortanzahl ca. 450-700 Wörter).
- **Variablen**: Körperfokus/Körperspannung ({body_tension}), zu lösende Belastung/Stressoren ({avoid}).
- **Anforderungen**:
  - Sprich den Nutzer direkt mit "du" / "dir" / "dein" an.
  - Leite den Nutzer Schritt für Schritt an.
  - Behalte einen ruhigen, unterstützenden und beruhigenden Tonfall bei.
  - Wiederhole Schlüsselideen auf natürliche Weise mit anderen Worten.
  - Baue Atemmomente und Reflektionspausen ein.
  - Vertiefe die Erfahrung, statt nur kurze Anweisungen zu geben.
  - Nutze Metaphern und Bilder, die zur Intention des Nutzers passen.
  - Greife die ausgewählten Körperbereiche ({body_tension}) mehrmals auf und beschreibe, wie sich Entspannung, Wärme, Heilung oder Leichtigkeit dort ausbreiten.
  - Verbinde Körperempfindungen, Emotionen und Visualisierung zu einer kontinuierlichen inneren Reise.
  - Vermeide kurze Befehle (z. B. "Konzentriere dich auf... Fühle... Lass los... Atme..."). Schreibe fließende Absätze, die Entspannung und Verbundenheit erzeugen.
  - Schreibe für gesprochenes Audio: Verwende kurze bis mittellange Sätze und einen natürlichen Rhythmus.

## C: suggestion (Suggestions Section)
- **Zweck**: Verankerung des Ziels ({goal}) durch Suggestionen.
- **Pacing**: Ruhig, geräumig und tiefenwirksam.
- **Aufgabe**: Generiere einen kurzen Übergangssatz, der den Hörer vorbereitet (z.B. "Erlaube diesen Suggestionen, sich sanft in deinem Unterbewusstsein niederzulassen. Du musst nichts tun. Höre einfach zu, atme und erlaube jedem Wort, sich ganz natürlich in dir zu entfalten."). Generiere dann 3 bis 4 wirkungsvolle Suggestionssätze basierend auf dem Ziel des Nutzers.
- **Pausen**: Nach JEDER Suggestion (auch der allerletzten) MUSS der Pausen-Marker [[PAUSE_4S]] stehen, damit der Hörer Raum zum Absorbieren hat.
- **Beispiel**:
  "Lass diese Gedanken nun ganz sanft in dein Unterbewusstsein sinken. [[PAUSE_4S]] Du bist vollkommen sicher. [[PAUSE_4S]] Mit jedem Atemzug entspannt sich dein Körper mehr. [[PAUSE_4S]] Vertrauen wächst in dir. [[PAUSE_4S]]"

## D: affirmation (Affirmations Loop)
- **Zweck**: Wiederholbare Affirmationen zur Verankerung des Meditationsziels ({goal}).
- **Aufgabe**: Generiere 2-3 kurze, kraftvolle Affirmationssätze basierend auf dem Ziel. Sie müssen loopbar sein (kein Intro/Outro).
- **Pausen**: Setze nach JEDER Affirmation (auch der letzten) den Pausen-Marker [[PAUSE_4S]] ein.
- **Beispiel**:
  "Ich bin ruhig und geschützt. [[PAUSE_4S]] Ich vertraue dem Fluss meines Lebens. [[PAUSE_4S]]"

## E: visualization (Generated Journey / Power Landscape)
- **Zweck**: Emotionaler Höhepunkt in der ausgewählten Landschaft ({landscape}).
- **Dauer**: Ca. 4-6 Minuten spoken audio (Wortanzahl ca. 450-700 Wörter).
- **Aufgabe**: Führe den Nutzer in eine emotionale Innenreise. Nutze die ausgewählte Landschaft ({landscape}) als aktive therapeutische Umgebung, die die gewünschte emotionale Transformation (Ziel: {goal}, aktuelle Stimmung zu gewünschtem emotionalen Zustand) unterstützt:
  - Wald (Forest) → Erdung, Kraft, Erneuerung (grounding, strength, renewal)
  - Bergsee (Mountain Lake) → Klarheit, Stille, innerer Frieden (clarity, stillness, inner peace)
  - Blumenwiese (Flower Meadow) → Freude, Leichtigkeit, Hoffnung (joy, lightness, hope)
  - Weißer Strand (White Beach) → Freiheit, Weite, tiefe Entspannung (freedom, openness, deep relaxation)
- **Struktur der Visualisierung**:
  1. Ankommen in der ausgewählten Landschaft.
  2. Erleben der Umgebung mit allen Sinnen.
  3. Entdecken eines bedeutungsvollen Ortes, Symbols oder Erlebnisses.
  4. Die Landschaft unterstützt aktiv die gewünschte emotionale Transformation.
  5. Erleben des gewünschten emotionalen Zustands, als ob er bereits existiert.
  6. Rückkehr im Bewusstsein, diese innere Ressource mit in den Alltag zu nehmen.
- **Wichtig**: Beschreibe nicht bloß die Kulisse. Die Visualisierung muss eine emotionale Erfahrung kreieren, die den Zuhörer den gewünschten Zustand tatsächlich fühlen lässt. Die Landschaft soll zu einem Ort werden, an den der Nutzer gerne zurückkehrt.

Pflichtanforderungen:
1. Erstelle einzigartige, poetische Inhalte — keine statische Vorlage.
2. Nutze genau diese Reihenfolge: greeting, personal_reflection, suggestion, affirmation, visualization.
3. Jede Section braucht step_type, content, duration, start_time und end_time. (Schätze die Sektions-Dauer in Sekunden basierend auf der Textlänge, ca. 100-120 Wörter entsprechen 60 Sekunden).
4. total_duration muss der Summe aller step-Dauern entsprechen.
5. ALLE Sections muessen den IDENTISCHEN warmen, langsamen Tonfall haben.

JSON-Form:
{
"title": "string",
"summary": "string",
"total_duration": {total_duration},
"steps": [
    {"step_type": "greeting", "content": "string", "duration": 60, "start_time": 0, "end_time": 60},
    {"step_type": "personal_reflection", "content": "string", "duration": 240, "start_time": 60, "end_time": 300},
    {"step_type": "suggestion", "content": "string", "duration": 120, "start_time": 300, "end_time": 420},
    {"step_type": "affirmation", "content": "string", "duration": 60, "start_time": 420, "end_time": 480},
    {"step_type": "visualization", "content": "string", "duration": 240, "start_time": 480, "end_time": 720}
]
}
"""


def build_prompt(data: dict[str, Any]) -> str:
    category = data["category"]
    guidance = CATEGORY_GUIDANCE.get(category) or CATEGORY_GUIDANCE[DEFAULT_CATEGORY]
    questionnaire_lines = "\n".join(
        f"- {key}: {value}" for key, value in data["questionnaire_answers"].items()
    ) or "- Keine zusaetzlichen Antworten"
    total_duration = data["duration"] * 60
    body_tension = ", ".join(data["body_tension"]) or "Nicht angegeben"

    from apps.ai_service.models import MeditationPrompt
    active_prompt_obj = MeditationPrompt.objects.filter(category=category, is_active=True).first()
    if active_prompt_obj:
        prompt_template = active_prompt_obj.prompt_template
    else:
        prompt_template = DEFAULT_PROMPT_TEMPLATE

    context = {
        "category_label": data.get("category_label") or "",
        "goal": data.get("goal") or "innere Balance",
        "avoid": data.get("avoid") or "Nicht angegeben",
        "duration": data.get("duration") or 10,
        "experience": data.get("experience") or "beginner",
        "body_tension": body_tension,
        "nature_sound": data.get("nature_sound") or "Nicht angegeben",
        "landscape": data.get("landscape") or "Nicht angegeben",
        "voice_name": data.get("voice_name") or "Nicht angegeben",
        "user_name": data.get("user_name") or "Nutzer",
        "questionnaire_lines": questionnaire_lines,
        "focus": guidance.get("focus") or "",
        "visualization": guidance.get("visualization") or "",
        "affirmation": guidance.get("affirmation") or "",
        "total_duration": total_duration,
    }

    # Format the prompt dynamically using safe .replace calls
    formatted_prompt = prompt_template
    for key, val in context.items():
        placeholder = f"{{{key}}}"
        formatted_prompt = formatted_prompt.replace(placeholder, str(val))

    return formatted_prompt



def _validate_payload(
    payload: Any,
    expected_total_duration: int,
    default_title: str = "Geführte Meditation",
) -> dict[str, Any]:
    # Handle list response if model returned steps directly
    if isinstance(payload, list):
        payload = {"steps": payload}

    if not isinstance(payload, dict):
        raise ValueError(f"Meditation payload must be a JSON object, got {type(payload).__name__}.")

    # Unwrap root key if the model wrapped the response (e.g. {"meditation": {...}})
    for wrapper_key in ("meditation", "data", "result", "response", "output"):
        nested = payload.get(wrapper_key)
        if isinstance(nested, dict) and any(k in nested for k in ("steps", "title", "titel", "schritte")):
            payload = nested
            break

    # Look for title variants or fallback to default_title
    title = ""
    for candidate in ("title", "titel", "Title", "Titel", "name", "Name", "thema", "Thema", "ueberschrift", "überschrift", "heading", "label"):
        val = payload.get(candidate)
        if isinstance(val, str) and val.strip():
            title = val.strip()
            break
    if not title:
        title = default_title
    payload["title"] = title

    # Look for steps variants
    steps = payload.get("steps")
    if not isinstance(steps, list):
        for candidate_key in ("schritte", "sections", "meditation_steps", "items"):
            candidate = payload.get(candidate_key)
            if isinstance(candidate, list):
                steps = candidate
                break

    if not isinstance(steps, list) or not steps:
        raise ValueError("Meditation payload requires steps.")

    normalized_steps = []
    cursor = 0
    for step in steps:
        if not isinstance(step, dict):
            continue
        step_type = str(
            step.get("step_type")
            or step.get("type")
            or step.get("typ")
            or step.get("step")
            or step.get("schritt")
            or ""
        ).strip()
        content = str(
            step.get("content")
            or step.get("text")
            or step.get("inhalt")
            or ""
        ).strip()
        duration = int(step.get("duration") or step.get("dauer") or 0)
        if not step_type or not content:
            continue
        if duration <= 0:
            duration = max(30, expected_total_duration // max(1, len(steps)))

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

    if not normalized_steps:
        raise ValueError("Meditation payload steps contain no valid content.")

    if abs(cursor - expected_total_duration) > 60:
        logger.warning("Generated duration %s differs from requested %s.", cursor, expected_total_duration)

    payload["steps"] = normalized_steps
    payload["total_duration"] = cursor
    return payload


def _convert_payload_to_django_steps(payload: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {step_type: [] for step_type in DJANGO_STEP_ORDER}

    for step in payload["steps"]:
        try:
            django_step_type = _map_ai_step_to_django_step(str(step["step_type"]))
            if django_step_type in grouped:
                grouped[django_step_type].append(step)
        except MeditationGenerationError:
            pass

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
