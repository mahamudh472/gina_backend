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
        MeditationCategory.SELF_DISCOVERY: {
            "title": f"Selbstfindung & Identität{personal_touch}",
            "greeting": f"Willkommen{personal_touch} zu dieser Reise zu dir selbst. Entdecke, wer du wirklich bist.",
            "personal": "Nimm dir einen Moment, um in dich hineinzuhorchen. Was macht dich einzigartig?",
            "introduction": "Finde eine bequeme Haltung. Atme tief ein und lade dein wahres Selbst ein, sich zu zeigen.",
            "suggestion": "Erlaube allen Masken zu fallen. Dein authentisches Selbst wartet darauf, entdeckt zu werden.",
            "confirmation": "Du bist einzigartig und wertvoll. Deine Identität ist ein Geschenk.",
            "visualization": "Stell dir einen klaren Spiegel vor, der dein wahres Selbst ohne Verzerrung reflektiert.",
            "conclusion": "Nimm diese Erkenntnis mit in deinen Alltag. Du kennst deinen inneren Kompass."
        },
        MeditationCategory.EMOTIONAL_HEALING: {
            "title": f"Emotionale Heilung{personal_touch}",
            "greeting": f"Willkommen{personal_touch} zu diesem geschützten Raum für deine Gefühle. Heilung beginnt hier.",
            "personal": "Erlaube dir, all deine Emotionen willkommen zu heißen. Jedes Gefühl hat seinen Platz.",
            "introduction": "Lege eine Hand auf dein Herz. Spüre, wie dein Atem einen sicheren Raum für Heilung schafft.",
            "suggestion": "Lass alte Wunden im Licht der Liebe heilen. Vergebung befreit dich und andere.",
            "confirmation": "Du bist ganz, auch mit deinen Narben. Heilung geschieht in deinem Tempo.",
            "visualization": "Visualisiere warmes, goldenes Licht, das sanft durch deinen Körper fließt und alles heilt.",
            "conclusion": "Nimm dieses Gefühl der Ganzheit mit. Dein Herz ist offen und heil."
        },
        MeditationCategory.GROUNDING: {
            "title": f"Erdung & Stressbewältigung{personal_touch}",
            "greeting": f"Willkommen{personal_touch} zu dieser Meditation für Stabilität im Alltag. Finde deinen festen Stand.",
            "personal": "Spüre die Verbindung zur Erde. Du wirst getragen, egal was der Tag bringt.",
            "introduction": "Stell dich fest auf den Boden. Atme tief ein und lass Anspannung mit jedem Ausatmen los.",
            "suggestion": "Mit jedem Atem wachsen Wurzeln aus deinen Füßen tief in die Erde. Du bist stabil.",
            "confirmation": "Du meisterst Herausforderungen mit Ruhe. Dein innerer Kern ist unerschütterlich.",
            "visualization": "Stell dir einen mächtigen Baum vor, dessen Wurzeln tief in der Erde verankert sind.",
            "conclusion": "Spüre die Kraft deiner Wurzeln. Gehe geerdet und gelassen in deinen Tag."
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
        MeditationCategory.TRANSFORMATION: {
            "title": f"Wandel & Erneuerung{personal_touch}",
            "greeting": f"Willkommen{personal_touch} zu deiner Transformations-Meditation. Wandel ist das Gesetz des Lebens.",
            "personal": "Lass alte Muster, die dir nicht mehr dienen, in Liebe gehen. Platz für das Neue schaffen.",
            "introduction": "Atme tief ein und nimm die Bereitschaft zur Veränderung in dir auf. Ausatmen und Altes loslassen.",
            "suggestion": "Erlaube dir, dich weiterzuentwickeln. Transformation geschieht von innen nach außen.",
            "confirmation": "Du bist der Schöpfer deines Lebens. Jedes Ende ist der Beginn von etwas Wundervollem.",
            "visualization": "Visualisiere einen wunderschönen Schmetterling, der sich aus seinem Kokon befreit und in die Freiheit fliegt.",
            "conclusion": "Spüre die Erneuerung in dir. Begrüße die beste Version deines Selbst. Öffne mit einem Lächeln deine Augen."
        },
        MeditationCategory.INNER_PEACE: {
            "title": f"Innerer Frieden & Stille{personal_touch}",
            "greeting": f"Willkommen{personal_touch} zu dieser Reise in deine innere Oase des Friedens. Lass die Welt verstummen.",
            "personal": "Finde den stillen Ort in dir, der von äußeren Stürmen unberührt bleibt. Er ist immer da.",
            "introduction": "Lass deinen Atem ganz natürlich fließen. Beobachte die sanfte Bewegung deines Brustkorbs.",
            "suggestion": "Mit jedem Ausatmen sinkst du tiefer in diesen Ozean der Stille. Friede breitet sich in dir aus.",
            "confirmation": "In dir liegt eine tiefe, unerschütterliche Ruhe. Du bist im reinen Frieden mit dir und der Welt.",
            "visualization": "Stell dir einen friedlichen, japanischen Garten im sanften Morgenlicht vor, erfüllt von absoluter Stille.",
            "conclusion": "Nimm diese tiefe innere Ruhe mit in deinen Alltag. Öffne in deiner Zeit sanft die Augen."
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

    theme = themes.get(category, default_theme)
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
