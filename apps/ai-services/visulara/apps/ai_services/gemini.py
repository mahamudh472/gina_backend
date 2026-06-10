import requests
import os
import json
import logging
from dotenv import load_dotenv
from fastapi import HTTPException

from pathlib import Path

import time

# Load environment variables
env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Primary model and fallbacks to handle 503/429 errors
GEMINI_MODELS = ["gemini-1.5-flash-latest", "gemini-2.0-flash", "gemini-1.5-pro-latest"]


def _call_gemini(prompt: str, timeout: int = 60) -> dict:
    """
    Centralized helper to call Gemini with:
    1. Multiple fallback models
    2. Retry logic for temporary errors (503, 429)
    3. Proper error handling and logging
    """
    last_error_text = "Unknown error"

    for model in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        
        # Try up to 2 attempts per model for temporary issues
        for attempt in range(2):
            try:
                response = requests.post(
                    url,
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                    timeout=timeout,
                )
                
                if response.status_code == 200:
                    return response.json()
                
                # Handle temporary errors with backoff
                if response.status_code in (503, 429):
                    delay = 10 * (attempt + 1)
                    logger.warning(
                        f"Gemini {model} is busy/throttled ({response.status_code}). "
                        f"Attempt {attempt + 1}/2. Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    continue
                
                # For other errors, log and try the next model
                logger.error(f"Gemini {model} returned error {response.status_code}: {response.text}")
                last_error_text = f"Model {model} returned {response.status_code}"
                break
                
            except requests.exceptions.Timeout:
                logger.error(f"Gemini {model} request timed out.")
                last_error_text = f"Model {model} timed out"
                break
            except requests.exceptions.RequestException as e:
                logger.error(f"Gemini {model} request failed: {e}")
                last_error_text = str(e)
                break
                
    # If all models and attempts failed
    raise HTTPException(
        status_code=502,
        detail=f"The AI service is currently experiencing high demand. Please try again in a few moments. ({last_error_text})",
    )


def generate_questionnaire(intention: str) -> list[dict]:
    """Generate tailored questionnaire questions based on the user's intention."""

    if not intention or not intention.strip():
        raise HTTPException(status_code=400, detail="Intention cannot be empty.")

    prompt = f"""
    You are a meditation and wellness expert.
    A user wants to meditate with the intention: "{intention}"

    Generate exactly 4 short, thoughtful questions to better understand the user's 
    current emotional state and needs. Each question should have 3-4 multiple choice options.

    Return ONLY valid JSON in this exact format, no other text:
    {{
        "questions": [
            {{
                "question": "How are you feeling right now?",
                "options": ["Calm", "Anxious", "Tired", "Energized"]
            }}
        ]
    }}
    """

    data = _call_gemini(prompt, timeout=30)

    try:
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]

        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0]

        return json.loads(cleaned)["questions"]

    except (KeyError, IndexError, json.JSONDecodeError) as e:
        logger.error(f"Failed to parse Gemini questionnaire response: {e}\nRaw: {data}")
        raise HTTPException(
            status_code=502,
            detail="AI returned an unexpected response. Please try again.",
        )


def generate_script(
    intention: str,
    questionnaire_answers: dict | None = None,
    persona: str = "Supportive Friend",
    language: str = "English",
    user_name: str | None = None,
    current_mood: str | None = None,
    meditation_goal: str | None = None,
    stress_input: str | None = None,
    body_focus: str | None = None,
    audio_anchor: str | None = None,
    landscape_env: str | None = None,
) -> dict:
    """
    Generate a personalized meditation script with:
    - Three sections: meditation, suggestion, affirmation
    - Each section includes: script text with <break> tags, and voice_direction metadata
    - Voice direction includes pitch, pacing, emotion, and voice_settings for TTS

    Returns a dict with structured sections ready for TTS processing.
    """

    if not intention or not intention.strip():
        raise HTTPException(status_code=400, detail="Intention cannot be empty.")

    # Build context from questionnaire answers
    answers_context = ""
    if questionnaire_answers:
        answers_context = "\n    Additional Questionnaire responses:\n"
        for question, answer in questionnaire_answers.items():
            answers_context += f"    - {question}: {answer}\n"

    user_inputs = f"""
    User Name: {user_name or 'Not specified'}
    Current Mood: {current_mood or 'Not specified'}
    Meditation Goal: {meditation_goal or intention}
    Stressors (to leave outside): {stress_input or 'Not specified'}
    Body Focus: {body_focus or 'Not specified'}
    Audio Anchor (SFX): {audio_anchor or 'Not specified'}
    Landscape Environment: {landscape_env or 'Not specified'}
    """

    prompt = f"""
    You are a professional meditation guide for VISULARA.
    Based on the user inputs, create a script for the personalized parts of the meditation.
    Your response MUST be exclusively a valid JSON object.
    Language: German. Tone: Gentle, calm, empathetic, slow speaking style.

    User Inputs:
    {user_inputs}
    {answers_context}

    THE FLOW: Create three distinct sections that guide the user through a complete meditation journey.
    1. MEDITATION — The core guided meditation. Deep, slow, grounding. This is the main body.
    2. SUGGESTION — A powerful suggestion/visualization section. Designed so it can be looped.
    3. AFFIRMATION — A short, rhythmic affirmation. Designed for seamless looping.

    IMPORTANT RULES FOR THE SCRIPT TEXT:
    - Use <break time="1s"/>, <break time="2s"/>, <break time="3s"/> tags for pauses
      (these are the ONLY SSML tags supported by the voice engine)
    - Do NOT use <prosody>, <speak>, or any other SSML tags in the script text
    - Write naturally with embedded break tags for breathing space
    - The suggestion and affirmation MUST sound natural when repeated back-to-back (loopable)

    Return ONLY valid JSON in this exact format:
    {{
        "meditation": {{
            "script": "<break time=\\"2s\\"/> Schließe jetzt sanft deine Augen... <break time=\\"3s\\"/> Spüre, wie...",
            "voice_direction": {{
                "pitch": "Drop to chest-voice resonance, deep and grounding",
                "pacing": "Slow, around 60 words per minute with long pauses",
                "emotion": "Calm, nurturing, deeply reassuring",
                "tts_settings": {{
                    "stability": 0.85,
                    "similarity_boost": 0.70,
                    "style": 0.3
                }}
            }}
        }},
        "suggestion": {{
            "script": "Stell dir vor, du stehst an einem ruhigen Ort... <break time=\\"2s\\"/> Du spürst die Wärme...",
            "voice_direction": {{
                "pitch": "Warm, slightly lower, intimate",
                "pacing": "Slow and rhythmic, designed for seamless looping",
                "emotion": "Gentle, guiding, hypnotic",
                "tts_settings": {{
                    "stability": 0.80,
                    "similarity_boost": 0.75,
                    "style": 0.35
                }}
            }}
        }},
        "affirmation": {{
            "script": "Ich bin genug. Ich darf ruhen. Meine Energie kehrt zurück.",
            "voice_direction": {{
                "pitch": "Warm mid-range, intimate",
                "pacing": "Rhythmic and steady, designed for seamless looping",
                "emotion": "Breathier, more intimate, empowering",
                "tts_settings": {{
                    "stability": 0.90,
                    "similarity_boost": 0.80,
                    "style": 0.2
                }}
            }}
        }}
    }}

    CRITICAL: 
    - The meditation section must be substantial (full 3-5 minute guided meditation)
    - The suggestion section should be 2-4 sentences, loopable
    - The affirmation should be 1-2 short loopable sentences
    - tts_settings.stability ranges 0.0-1.0 (higher = more consistent, calmer voice)
    - tts_settings.similarity_boost ranges 0.0-1.0 
    - tts_settings.style ranges 0.0-1.0 (lower = more neutral, higher = more expressive)
    - Tailor EVERYTHING to the user's specific intention: "{intention}"
    """

    data = _call_gemini(prompt, timeout=90)

    try:
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]

        # Clean markdown code fences if present
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0]

        script = json.loads(cleaned)

        # Validate required sections
        for key in ("meditation", "suggestion", "affirmation"):
            if key not in script:
                raise ValueError(f"Missing '{key}' section in generated script.")
            if "script" not in script[key]:
                raise ValueError(f"Missing 'script' text in '{key}' section.")
            if "voice_direction" not in script[key]:
                raise ValueError(f"Missing 'voice_direction' in '{key}' section.")

        return script

    except (KeyError, IndexError, json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse Gemini script response: {e}\nRaw response: {str(data)[:500]}")
        raise HTTPException(
            status_code=502,
            detail="AI returned an unexpected response. Please try again.",
        )