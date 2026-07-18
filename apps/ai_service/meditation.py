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
    "affirmation_transition",
    "affirmation",
    "visualization",
]

DJANGO_STEP_ORDER = [
    MeditationStep.GREETING,
    MeditationStep.PERSONAL,
    MeditationStep.SUGGESTION,
    MeditationStep.CONFIRMATION_TRANSITION,
    MeditationStep.CONFIRMATION,
    MeditationStep.VISUALIZATION,
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

    raise MeditationGenerationError(f"Unsupported LLM_PROVIDER '{provider}'. Only 'openai' is supported.")


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
    - Kategorie: {data["category_label"]}
    - Emotion / aktuelle Stimmung: (Extrahiere die aktuelle Stimmung, Emotion oder das Gefühl des Nutzers selbstständig aus den unten stehenden Antworten des Fragebogens)
    - Ziel: {data["goal"]}
    - Zu loesende Belastung: {data["avoid"] or "Nicht angegeben"}
    - Dauer: {data["duration"]} Minuten
    - Erfahrung: {data["experience"]}
    - Koerperspannung: {body_tension}
    - Naturklang (Audio-Anker): {data["nature_sound"] or "Nicht angegeben"}
    - Visualisierungslandschaft: {data["landscape"] or "Nicht angegeben"}
    - Stimme: {data["voice_name"] or "Nicht angegeben"}
    - Name: {data["user_name"] or "Nicht angegeben"}
    - Weitere Antworten:
    {questionnaire_lines}

    Kategoriespezifische Richtung:
    - Fokus: {guidance["focus"]}
    - Visualisierung: {guidance["visualization"]}
    - Affirmation: {guidance["affirmation"]}

    # SPEZIFISCHE ANFORDERUNGEN AN DIE AI-BLÖCKE:

    ## A: greeting (Personal Welcome)
    - **Zweck**: Emotionaler Anker und Abholen des Nutzers.
    - **Variablen**: Name des Nutzers ({data["user_name"] or "Nicht angegeben"}), aktuelle Stimmung/Emotion.
    - **Aufgabe**: Hole den Nutzer genau da ab, wo er emotional steht, und gestalte den Übergang zur darauffolgenden Einführung (Intro).
    - **Beispiel-Struktur**: "Hallo {data["user_name"] or "Nutzer"}. Wie schön, dass du dir heute diesen Moment für dich nimmst. Du hast angegeben, dass du dich gerade [Stimmung/Gefühl aus dem Fragebogen] fühlst. Das ist vollkommen okay – alles darf genau so sein, wie es jetzt ist. Gemeinsam schaffen wir den Raum, um diesen Zustand sanft zu verändern. Lass uns beginnen..."

    ## B: personal_reflection (Personalized Main Section)
    - **Zweck**: Emotionaler Kern, Körperfokus und Lösen von Anspannungen.
    - **Dauer**: Ca. 4-6 Minuten spoken audio (Wortanzahl ca. 450-700 Wörter).
    - **Variablen**: Körperfokus/Körperspannung ({body_tension}), zu lösende Belastung/Stressoren ({data["avoid"] or "Nicht angegeben"}).
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
    - **Zweck**: Verankerung des Ziels ({data["goal"]}) durch Suggestionen.
    - **Pacing**: Ruhig, geräumig und tiefenwirksam.
    - **Aufgabe**: Generiere einen kurzen Übergangssatz, der den Hörer vorbereitet (z.B. "Erlaube diesen Suggestionen, sich sanft in deinem Unterbewusstsein niederzulassen. Du musst nichts tun. Höre einfach zu, atme und erlaube jedem Wort, sich ganz natürlich in dir zu entfalten."). Generiere dann 3 bis 4 wirkungsvolle Suggestionssätze basierend auf dem Ziel des Nutzers.
    - **Pausen**: Nach JEDER Suggestion (auch der allerletzten) MUSS der Pausen-Marker `[[PAUSE_4S]]` stehen, damit der Hörer Raum zum Absorbieren hat.
    - **Beispiel**:
      "Lass diese Gedanken nun ganz sanft in dein Unterbewusstsein sinken. [[PAUSE_4S]] Du bist vollkommen sicher. [[PAUSE_4S]] Mit jedem Atemzug entspannt sich dein Körper mehr. [[PAUSE_4S]] Vertrauen wächst in dir. [[PAUSE_4S]]"

    ## D: affirmation_transition (Affirmation Transition)
    - **Zweck**: Einmaliger, sanfter Übergang zur Affirmationsphase.
    - **Aufgabe**: Generiere einen kurzen, stimmigen Übergangssatz (z.B. "Wenn du diese Erfahrung noch weiter vertiefen möchtest, erlaube diesen Affirmationen, sanft Teil deiner inneren Wahrheit zu werden. Höre einfach zu, atme und lass jede Affirmation in dir nachklingen.").
    - **Wichtig**: Dieser Text wird NUR EINMAL abgespielt und darf KEINE Affirmationen enthalten. Er wird nicht geloopt.

    ## E: affirmation (Affirmations Loop)
    - **Zweck**: Wiederholbare Affirmationen zur Verankerung des Meditationsziels ({data["goal"]}).
    - **Aufgabe**: Generiere 2-3 kurze, kraftvolle Affirmationssätze basierend auf dem Ziel. Sie müssen loopbar sein (kein Intro/Outro).
    - **Pausen**: Setze nach JEDER Affirmation (auch der letzten) den Pausen-Marker `[[PAUSE_4S]]` ein.
    - **Beispiel**:
      "Ich bin ruhig und geschützt. [[PAUSE_4S]] Ich vertraue dem Fluss meines Lebens. [[PAUSE_4S]]"

    ## F: visualization (Generated Journey / Power Landscape)
    - **Zweck**: Emotionaler Höhepunkt in der ausgewählten Landschaft ({data["landscape"] or "Nicht angegeben"}).
    - **Dauer**: Ca. 4-6 Minuten spoken audio (Wortanzahl ca. 450-700 Wörter).
    - **Aufgabe**: Führe den Nutzer in eine emotionale Innenreise. Nutze die ausgewählte Landschaft ({data["landscape"]}) als aktive therapeutische Umgebung, die die gewünschte emotionale Transformation (Ziel: {data["goal"]}, aktuelle Stimmung zu gewünschtem emotionalen Zustand) unterstützt:
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
    2. Nutze genau diese Reihenfolge: {", ".join(AI_STEP_ORDER)}.
    3. Jede Section braucht step_type, content, duration, start_time und end_time. (Schätze die Sektions-Dauer in Sekunden basierend auf der Textlänge, ca. 100-120 Wörter entsprechen 60 Sekunden).
    4. total_duration muss der Summe aller step-Dauern entsprechen.
    5. ALLE Sections muessen den IDENTISCHEN warmen, langsamen Tonfall haben.

    JSON-Form:
    {{
    "title": "string",
    "summary": "string",
    "total_duration": {total_duration},
    "steps": [
        {{"step_type": "greeting", "content": "string", "duration": 60, "start_time": 0, "end_time": 60}},
        {{"step_type": "personal_reflection", "content": "string", "duration": 240, "start_time": 60, "end_time": 300}},
        {{"step_type": "suggestion", "content": "string", "duration": 120, "start_time": 300, "end_time": 420}},
        {{"step_type": "affirmation_transition", "content": "string", "duration": 30, "start_time": 420, "end_time": 450}},
        {{"step_type": "affirmation", "content": "string", "duration": 60, "start_time": 450, "end_time": 510}},
        {{"step_type": "visualization", "content": "string", "duration": 240, "start_time": 510, "end_time": 750}}
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
    if normalized == "affirmation_transition":
        return MeditationStep.CONFIRMATION_TRANSITION
    if normalized in {"affirmation", "confirmation"}:
        return MeditationStep.CONFIRMATION
    if normalized == "visualization":
        return MeditationStep.VISUALIZATION
    if normalized == "conclusion":
        return MeditationStep.CONCLUSION
    raise MeditationGenerationError(f"Generated meditation contains unknown step type '{step_type}'.")
