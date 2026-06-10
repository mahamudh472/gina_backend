from app.constants.meditation import (
    CATEGORY_PROMPT_GUIDANCE,
    DURATION_PROMPT_GUIDANCE,
    EXPERIENCE_PROMPT_GUIDANCE,
    STEP_ORDER,
    get_category_label,
    normalize_category,
    normalize_experience_level,
    validate_duration,
)

def build_meditation_prompt(*, request_data: dict) -> str:
    category = normalize_category(request_data.get("category"))
    guidance = CATEGORY_PROMPT_GUIDANCE.get(category, CATEGORY_PROMPT_GUIDANCE["relaxation"])
    duration_minutes = validate_duration(request_data.get("duration") or request_data.get("duration_minutes") or 20)
    experience = normalize_experience_level(request_data.get("experience") or request_data.get("experience_level"))
    body_tension = ", ".join(request_data.get("body_tension") or request_data.get("body_tension_areas") or []) or "Nicht angegeben"
    questionnaire_context = request_data.get("questionnaire_answers") or {}
    questionnaire_lines = "\n".join(f"- {key}: {value}" for key, value in questionnaire_context.items()) or "- Keine zusätzlichen Antworten"
    total_duration = duration_minutes * 60
    category_label = get_category_label(category)
    duration_guidance = DURATION_PROMPT_GUIDANCE[duration_minutes]
    experience_guidance = EXPERIENCE_PROMPT_GUIDANCE[experience]

    return f"""
Du bist eine weltklasse Meditationslehrerin und erstellst eine hochpersonalisierte geführte Meditation.

Antworte ausschließlich als valides JSON ohne Markdown.
Die Meditation muss auf Deutsch geschrieben werden.

Benutzerprofil:
- Kategorie: {category_label}
- Emotion: {request_data.get("emotion", "")}
- Ziel: {request_data.get("goal", "")}
- Dauer: {duration_minutes} Minuten
- Erfahrung: {experience}
- Körperspannung: {body_tension}
- Naturklang: {request_data.get("nature_sound") or "Nicht angegeben"}
- Visualisierungslandschaft: {request_data.get("landscape") or "Nicht angegeben"}
- Erzählerstimme: {request_data.get("voice_name", "")}
- Zusätzliche Antworten:
{questionnaire_lines}

Kategoriespezifische Führung:
- Fokus: {guidance["focus"]}
- Visualisierung: {guidance["visualization"]}
- Sprachstil: {guidance["coaching_language"]}
- Affirmationsrichtung: {guidance["affirmations"]}

Dauer-Richtung:
- Diese Meditation ist für {duration_minutes} Minuten ausgelegt.
- {duration_guidance}
- Passe Dichte, Pausen und Wiederholungen an diese Länge an.

Erfahrungs-Richtung:
- {experience_guidance}

Pflichtanforderungen:
1. Erstelle einzigartige Inhalte und keine statischen Templates.
2. Nutze genau diese Struktur in dieser Reihenfolge: {", ".join(STEP_ORDER)}.
3. Jede Section muss enthalten: step_type, content, duration, start_time, end_time.
4. start_time und end_time müssen als Sekundenwerte entlang der Gesamtmeditation konsistent sein.
5. total_duration muss genau {total_duration} sein.
6. Integriere Emotion, Ziel, Körperspannung, Naturklang und Landschaft spürbar und natürlich.
7. Die Suggestion und Affirmation sollen einprägsam und wiederholbar sein.

Erwarte dieses JSON:
{{
  "title": "string",
  "summary": "string",
  "total_duration": {total_duration},
  "steps": [
    {{
      "step_type": "greeting",
      "content": "string",
      "duration": 60,
      "start_time": 0,
      "end_time": 60
    }}
  ]
}}
"""
