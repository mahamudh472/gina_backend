import datetime
from typing import Dict, Any, List, Tuple
from apps.main.models import MeditationCategory, MeditationStep

def generate_meditation_content(
    category: str, 
    q_a: Any, 
    voice_name: str = "", 
    nature_sound_name: str = "",
    background_image_name: str = ""
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Generates the meditation content. Currently returns static data, 
    but is set up with all necessary parameters to easily integrate an AI provider later.
    
    In the future:
    1. Construct a prompt using category, q_a, voice_name, etc.
    2. Call the AI service (e.g., OpenAI, Gemini).
    3. Parse the AI response into a title and steps list.
    """
    # prompt = f"Create a {category} meditation. Focus on user answers: {q_a}. Voice: {voice_name}..."
    # ai_response = ai_provider.generate_content(prompt)
    # return parse_response(ai_response)
    
    # Returning static fallback data for now:
    return _generate_static_meditation_steps(category, q_a)

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
        MeditationCategory.RELAXATION: {
            "title": f"Tiefenentspannung für{personal_touch or ' den Geist'}",
            "greeting": f"Willkommen{personal_touch} zu deiner heutigen Meditationsreise für tiefe Entspannung. Schön, dass du hier bist.",
            "personal": "Nimm dir einen Moment Zeit, um ganz bei dir anzukommen. Du darfst jetzt alles loslassen.",
            "introduction": "Finde eine bequeme Haltung, schließe deine Augen und nimm einen tiefen Atemzug. Lass die Welt draußen leiser werden.",
            "suggestion": "Spüre, wie mit jedem Ausatmen die Anspannung aus deinem Körper weicht. Deine Muskeln entspannen sich vollständig.",
            "confirmation": "Es gibt jetzt nichts zu tun und nirgendwo hinzugehen. Du bist genau richtig, so wie du bist.",
            "visualization": "Stell dir ein weites, ruhiges Meer vor. Die Wellen kommen und gehen im Rhythmus deines Atems.",
            "conclusion": "Bringe die Aufmerksamkeit langsam zurück. Bewege deine Finger, nimm einen tiefen Atemzug und öffne deine Augen. Du bist vollkommen entspannt."
        },
        MeditationCategory.SELF_LOVE: {
            "title": f"Liebevolles Annehmen{personal_touch or ' deines Selbst'}",
            "greeting": f"Willkommen{personal_touch} zu dieser Reise der Selbstliebe. Heute ehren wir dich und dein Wesen.",
            "personal": "Erlaube dir selbst, Mitgefühl und Wärme zu empfinden. Du bist ein wertvoller Teil dieser Welt.",
            "introduction": "Lege eine Hand auf dein Herz. Spüre den sanften Schlag deines Herzens und atme tief ein.",
            "suggestion": "Schenke dir selbst ein inneres Lächeln. Nimm all deine Gedanken und Gefühle ohne Urteil an.",
            "confirmation": "Du bist genug. Genau in diesem Moment, mit all deinen Stärken und all deinen Schwächen.",
            "visualization": "Visualisiere ein warmes, goldenes Licht in deinem Herzen, das sich mit jedem Atemzug weiter ausbreitet.",
            "conclusion": "Nimm dieses Gefühl der Geborgenheit mit in deinen Tag. Wenn du bereit bist, öffne langsam deine Augen."
        },
        MeditationCategory.FOCUS_CLARITY: {
            "title": f"Klarheit und Fokus{personal_touch}",
            "greeting": f"Willkommen{personal_touch} zu dieser Fokus-Meditation. Lass uns deinen Geist klären und zentrieren.",
            "personal": "Lass die Ablenkungen des Tages verblassen. Richte deine Aufmerksamkeit ganz auf diesen Moment.",
            "introduction": "Sitz aufrecht und spüre die Stabilität deines Körpers. Atme klar und fokussiert ein.",
            "suggestion": "Beobachte deine Gedanken wie vorbeiziehende Wolken. Kehre immer wieder sanft zum Atem zurück.",
            "confirmation": "Dein Geist wird ruhig, klar und vollkommen fokussiert. Du fühlst dich innerlich geordnet.",
            "visualization": "Stell dir einen kristallklaren Bergsee vor, der den weiten, wolkenlosen Himmel spiegelt.",
            "conclusion": "Spüre die neu gewonnene mentale Stärke. Nimm diese Klarheit mit in deine Aufgaben. Öffne sanft deine Augen."
        },
        MeditationCategory.GRATITUDE: {
            "title": f"Dankbarkeit & Fülle{personal_touch}",
            "greeting": f"Willkommen{personal_touch} zu dieser Meditation der Dankbarkeit. Lass uns die Fülle in deinem Leben feiern.",
            "personal": "Spüre nach, wofür du in deinem Leben von ganzem Herzen dankbar bist.",
            "introduction": "Atme tief ein und spüre das Leben in dir. Lass Dankbarkeit durch deine Adern fließen.",
            "suggestion": "Erinnere dich an kleine Momente der Freude, ein Lächeln, eine warme Geste. Lass dieses Gefühl wachsen.",
            "confirmation": "Du bist reich beschenkt. Dankbarkeit ist der Schlüssel zu wahrer Zufriedenheit.",
            "visualization": "Stell dir vor, wie mit jedem Atemzug funkelnde Lichter der Dankbarkeit von dir ausströmen.",
            "conclusion": "Trage dieses Gefühl der Fülle im Herzen. Wenn du bereit bist, öffne sanft die Augen."
        },
        MeditationCategory.TRUST: {
            "title": f"Urvertrauen & Zuversicht{personal_touch}",
            "greeting": f"Willkommen{personal_touch} zu dieser Reise der Stärkung deines Urvertrauens. Du bist getragen.",
            "personal": "Lass alle Sorgen und Zweifel los. Vertraue darauf, dass alles zu deinem Besten geschieht.",
            "introduction": "Spüre den festen Boden unter dir. Er trägt dich, ohne dass du etwas dafür tun musst. Atme tief.",
            "suggestion": "Lass das Gefühl von Sicherheit und Zuversicht in dir wachsen. Du bist stärker als jede Herausforderung.",
            "confirmation": "Alles entfaltet sich zur richtigen Zeit. Hab Vertrauen in den Fluss deines Lebens.",
            "visualization": "Visualisiere, wie du auf einer sicheren, warmen Wolke schwebst und dich ganz dem Fluss des Lebens hingibst.",
            "conclusion": "Komme zurück in das Hier und Jetzt mit einem unerschütterlichen Vertrauen im Herzen. Öffne langsam die Augen."
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
        {"step_type": MeditationStep.INTRODUCTION, "content": theme["introduction"], "duration": datetime.timedelta(seconds=90)},
        {"step_type": MeditationStep.SUGGESTION, "content": theme["suggestion"], "duration": datetime.timedelta(seconds=120)},
        {"step_type": MeditationStep.CONFIRMATION, "content": theme["confirmation"], "duration": datetime.timedelta(seconds=60)},
        {"step_type": MeditationStep.VISUALIZATION, "content": theme["visualization"], "duration": datetime.timedelta(seconds=180)},
        {"step_type": MeditationStep.CONCLUSION, "content": theme["conclusion"], "duration": datetime.timedelta(seconds=45)},
    ]

    return title, steps_data