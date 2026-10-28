import datetime
from typing import Dict, Any, List, Tuple
from apps.ai_service.meditation import generate_ai_meditation_content
from apps.main.models import MeditationCategory, MeditationStep

def generate_meditation_content(
    category: str, 
    q_a: Any, 
    voice_name: str = "", 
    nature_sound_name: str = "",
    background_image_name: str = ""
) -> Tuple[str, List[Dict[str, Any]]]:
    """Generate personalized meditation content through the AI service."""
    return generate_ai_meditation_content(
        category=category,
        q_a=q_a,
        voice_name=voice_name,
        nature_sound_name=nature_sound_name,
        background_image_name=background_image_name,
    )

def _generate_static_meditation_steps(category: str, q_a: Any) -> Tuple[str, List[Dict[str, Any]]]:
    # Extract keywords from question answers if available
    personal_touch = ""
    focus_area = ""
    
    if isinstance(q_a, dict):
        # Look for typical keys or values
        # e.g., {"feelings": "stressed", "name": "Anna", "goal": "inner peace"}
        user_name = q_a.get('name') or q_a.get('username') or q_a.get('user_name') or q_a.get('userName')
        if user_name:
            personal_touch = f" {user_name}"
            
        focus_area = q_a.get('goal') or q_a.get('focus') or q_a.get('feeling') or q_a.get('intention') or ""
    elif isinstance(q_a, list):
        # Look inside list of QAs, e.g., [{"question": "...", "answer": "..."}]
        for item in q_a:
            if isinstance(item, dict):
                ans = str(item.get('answer', ''))
                ques = str(item.get('question', '')).lower()
                if 'name' in ques:
                    personal_touch = f" {ans}"
                if any(x in ques for x in ['focus', 'ziel', 'fokus', 'gefühl', 'feeling', 'goal', 'intention']):
                    focus_area = ans

    # Default category names & themes
    themes = {
        MeditationCategory.IDENTITY: {
            "title": f"Identität & Selbstfindung{personal_touch}",
            "greeting": f"Willkommen{personal_touch} zu dieser Reise zu dir selbst. Entdecke, wer du wirklich bist.",
            "personal": "Nimm dir einen Moment, um in dich hineinzuhorchen. Was macht dich einzigartig?",
            "introduction": "Finde eine bequeme Haltung. Atme tief ein und lade dein wahres Selbst ein, sich zu zeigen.",
            "suggestion": "Erlaube allen Masken zu fallen. Dein authentisches Selbst wartet darauf, gelebt zu werden.",
            "confirmation": "Du bist einzigartig und wertvoll. Deine Identität ist dein schönstes Geschenk.",
            "visualization": "Stell dir einen klaren See vor, der dein wahres Selbst ohne jede Verzerrung reflektiert.",
            "conclusion": "Nimm diese Klarheit mit. Du kennst deinen inneren Kompass."
        },
        MeditationCategory.EMOTIONS: {
            "title": f"Emotionale Balance{personal_touch}",
            "greeting": f"Willkommen{personal_touch} zu diesem geschützten Raum für deine Gefühle. Alles darf sein.",
            "personal": "Erlaube dir, all deine Emotionen willkommen zu heißen. Jedes Gefühl hat eine Botschaft für dich.",
            "introduction": "Lege eine Hand sanft auf dein Herz. Spüre, wie dein Atem dir Raum und Weite schenkt.",
            "suggestion": "Beobachte deine Emotionen wie sanfte Wellen auf dem Meer. Sie kommen, und sie ziehen wieder weiter.",
            "confirmation": "Du bist im Frieden mit deinen Gefühlen. Dein Herz ist offen, weit und stark.",
            "visualization": "Visualisiere einen weiten Himmel. Wolken ziehen vorüber, doch der Himmel bleibt unberührt.",
            "conclusion": "Nimm diese emotionale Ruhe und Ausgeglichenheit mit in deinen Tag."
        },
        MeditationCategory.HEALING: {
            "title": f"Heilung & Loslassen{personal_touch}",
            "greeting": f"Willkommen{personal_touch} zu deiner Heilungsreise. Hier darfst du loslassen und regenerieren.",
            "personal": "Schenke deinem Körper und deiner Seele die Erlaubnis, tief durchzuatmen und alte Belastungen abzugeben.",
            "introduction": "Finde eine Position vollkommener Entspannung. Atme tief ein und lass beim Ausatmen alles Schwere gehen.",
            "suggestion": "Lass alte Wunden sanft heilen. Mit jedem Atemzug fließt regenerierende Kraft durch dein ganzes Wesen.",
            "confirmation": "Du wirst getragen und beschützt. Heilung geschieht ganz sanft in deinem eigenen Tempo.",
            "visualization": "Visualisiere warmes, goldenes Licht, das sanft durch jede Zelle fließt und wohlige Heilung schenkt.",
            "conclusion": "Fühle die Erneuerung in deinem Herzen. Du bist ganz, gelöst und frei."
        },
        MeditationCategory.FUTURE: {
            "title": f"Zukunft & Vision{personal_touch}",
            "greeting": f"Willkommen{personal_touch} zu deiner Visions-Meditation. Erschaffe aktiv deine Zukunft.",
            "personal": "Öffne deinen Geist für neue Möglichkeiten. Deine Träume und Ziele warten auf dich.",
            "introduction": "Atme tief ein und spüre die Vorfreude auf das, was kommt. Atme aus und lass alte Zweifel los.",
            "suggestion": "Erlaube dir, groß zu träumen. Dein zukünftiges Ich sendet dir Kraft und Zuversicht.",
            "confirmation": "Du bist der Schöpfer deiner Realität. Jeder neue Tag ist eine Chance für deinen Neuanfang.",
            "visualization": "Visualisiere deinen Lebensweg im strahlenden Morgenlicht. Jeder Schritt führt dich sicher zu deinen Zielen.",
            "conclusion": "Gehe gestärkt und voller Vorfreude deinen Weg. Deine Zukunft beginnt im Hier und Jetzt."
        },
        MeditationCategory.ENERGY: {
            "title": f"Lebensenergie & Vitalität{personal_touch}",
            "greeting": f"Willkommen{personal_touch} zu dieser aktivierenden Meditation. Lass uns deine Lebensgeister wecken.",
            "personal": "Spüre die Kraft, die in jeder deiner Zellen schlummert und darauf wartet, entfesselt zu werden.",
            "introduction": "Atme kraftvoll ein, nimm frischen Sauerstoff auf, und atme verbrauchte Energie vollständig aus.",
            "suggestion": "Spüre ein feuriges Prickeln in deinem Körper. Energie fließt frei und ungehindert durch dich hindurch.",
            "confirmation": "Du bist voller Kraft, Vitalität und Tatendrang. Du bist bereit für alles, was kommt.",
            "visualization": "Visualisiere eine strahlende, warme Sonne direkt über deinem Kopf, die dich mit unendlicher Energie auflädt.",
            "conclusion": "Strecke dich, nimm diese kraftvolle Schwingung mit und starte voller Elan durch. Öffne energievoll die Augen."
        },
        MeditationCategory.EVERYDAY_LIFE: {
            "title": f"Gelassenheit im Alltag{personal_touch}",
            "greeting": f"Willkommen{personal_touch} zu deiner Auszeit für den Alltag. Finde Stabilität und Leichtigkeit.",
            "personal": "Egal wie hektisch der Tag ist: Dieser Moment gehört ganz dir, um innezuhalten.",
            "introduction": "Setze dich bequem und aufrecht hin. Spüre den Boden unter deinen Füßen und atme ruhig ein und aus.",
            "suggestion": "Lass alle Anspannung von den Schultern fallen. Du meisterst die Aufgaben deines Alltags mit Ruhe und Klarheit.",
            "confirmation": "In dir ruht eine feste, unerschütterliche Gelassenheit. Du bist jederzeit zentriert.",
            "visualization": "Stell dir einen mächtigen Baum vor, dessen Wurzeln tief in der Erde verankert sind.",
            "conclusion": "Spüre die Kraft deiner Wurzeln. Gehe geerdet und gelassen in deinen Tag."
        }
    }

    # Fallback/Default theme if not in dict
    default_theme = {
        "title": f"Innere Balance{personal_touch}",
        "greeting": f"Willkommen{personal_touch} zu deiner Meditation. Schön, dass du dir diese wertvolle Zeit schenkst.",
        "personal": "Dieser Moment gehört dir. Spüre in dich hinein und erlaube dir, einfach nur präsent zu sein.",
        "introduction": "Nimm eine angenehme Haltung ein. Atme tief durch die Nase ein und entspannt durch den Mund aus.",
        "suggestion": "Lass mit jedem Atemzug mehr Ruhe in dein System fließen. Genieße die Stille in dir.",
        "confirmation": "Du bist vollkommen im Einklang. Vertraue auf deinen inneren Kompass.",
        "visualization": "Stell dir ein helles, schützendes Licht vor, das dich sanft umhüllt und wärmt.",
        "conclusion": "Komme mit einem Gefühl des Friedens zurück in deinen Körper. Atme tief ein und öffne die Augen."
    }

    category_key: Any = category
    try:
        category_key = MeditationCategory(category)
    except ValueError:
        pass
    theme = themes.get(category_key, default_theme)
    title = theme["title"]
    
    # Adjust title/content if focus area is found
    if focus_area:
        title = f"{title} (Fokus: {focus_area.strip()})"
        theme["suggestion"] = f"{theme['suggestion']} Bringe deine Intention besonders zu deinem Thema: {focus_area.strip()}."

    steps_data = [
        {"step_type": MeditationStep.GREETING, "content": theme["greeting"], "duration": datetime.timedelta(seconds=45)},
        {"step_type": MeditationStep.PERSONAL, "content": theme["personal"], "duration": datetime.timedelta(seconds=60)},
        {"step_type": MeditationStep.SUGGESTION, "content": theme["suggestion"], "duration": datetime.timedelta(seconds=120)},
        {"step_type": MeditationStep.CONFIRMATION, "content": theme["confirmation"], "duration": datetime.timedelta(seconds=40)},
        {"step_type": MeditationStep.VISUALIZATION, "content": theme["visualization"], "duration": datetime.timedelta(seconds=120)},
    ]

    return title, steps_data
