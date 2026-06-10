import base64
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from visulara.apps.ai_services.elevenLabs_tts import generate_voice
from visulara.apps.ai_services.meditation_generator import (
    build_questionnaire,
    generate_structured_meditation,
)
from visulara.apps.meditation.archive_store import (
    create_archive_entry,
    list_archive_entries,
    list_favorite_entries,
    update_favorite_status,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class QuestionnaireRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    intention: str | None = Field(default=None, description="User's meditation intention")
    category: str | None = Field(default=None, description="Optional selected meditation category")
    name: str | None = Field(default=None, description="User name for the meditation")


class QuestionnaireResponse(BaseModel):
    intention: str
    questions: list[dict]


class MeditationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, description="User name for personalization")
    intention: str | None = Field(default=None, description="Legacy meditation intention alias")
    voice: str | None = Field(default=None, description="ElevenLabs voice ID")
    voice_id: str | None = Field(default=None, description="Legacy ElevenLabs voice ID alias")
    persona: str = Field(default="Supportive Friend", description="Voice persona style")
    language: str = Field(default="German", description="Script language")
    questionnaire_answers: dict | None = Field(
        default=None,
        description="Answers from the questionnaire, keyed by question text",
    )
    category: str | None = Field(default=None, description="Meditation category such as Relaxation or Trust")
    emotion: str | None = Field(default=None, description="Primary current emotion")
    goal: str | None = Field(default=None, description="Desired post-meditation feeling or result")
    avoid: str | None = Field(default=None, description="What should stay outside the meditation")
    duration: int | None = Field(default=None, ge=5, le=30, description="Requested meditation duration in minutes")
    duration_minutes: int | None = Field(default=None, ge=5, le=30, description="Legacy duration alias")
    experience: str | None = Field(default=None, description="Meditation experience level")
    experience_level: str | None = Field(default=None, description="Legacy experience alias")
    body_tension: list[str] = Field(default_factory=list, description="List of tense body areas")
    body_tension_areas: list[str] | None = Field(default=None, description="Legacy body tension alias")
    nature_sound: str | None = Field(default=None, description="Selected soundscape")
    landscape: str | None = Field(default=None, description="Selected visualization landscape")
    user_name: str | None = Field(default=None, description="Name of the user")
    current_mood: str | None = Field(default=None, description="How are you feeling today? (Status quo)")
    meditation_goal: str | None = Field(default=None, description="What would you like to deepen? (Goal)")
    stress_input: str | None = Field(default=None, description="What should be left outside today? (Stressors)")
    body_focus: str | None = Field(default=None, description="Body regions for relaxation")
    audio_anchor: str | None = Field(default=None, description="Acoustic relaxation anchor (SFX layer)")
    landscape_env: str | None = Field(default=None, description="Visualization environment")


class VoiceDirection(BaseModel):
    pitch: str
    pacing: str
    emotion: str


class MeditationSection(BaseModel):
    text: str
    audio_base64: str
    voice_direction: VoiceDirection


class MeditationResponse(BaseModel):
    intention: str
    persona: str
    language: str
    category: str
    summary: str
    total_duration: int
    archive_id: str
    created_at: str
    meditation: dict
    sections: dict[str, MeditationSection]


class ArchiveEntryResponse(BaseModel):
    id: str
    title: str
    category: str
    voice: str
    duration: int
    summary: str
    audio_url: str | None = None
    created_at: str
    favorite: bool
    meditation: dict
    sections: dict


class FavoriteUpdateRequest(BaseModel):
    favorite: bool = Field(..., description="Whether the meditation should be marked as favorite")


@router.post("/questionnaire", response_model=QuestionnaireResponse)
def get_questionnaire(request: QuestionnaireRequest):
    """
    Return the requirement-based meditation questionnaire.
    """
    questions = build_questionnaire(request.category or request.intention or "Relaxation")
    return QuestionnaireResponse(intention=request.intention or request.category or "Relaxation", questions=questions)


@router.post("/generate-meditation", response_model=MeditationResponse)
@router.post("/meditations/generate", response_model=MeditationResponse, include_in_schema=False)
def generate_meditation(request: MeditationRequest):
    """
    Generate a personalized meditation structure and render the required audio sections.
    """
    logger.info(
        "Generating meditation - name: '%s', persona: '%s', language: '%s'",
        request.name or request.intention or request.goal,
        request.persona,
        request.language,
    )

    voice_id = request.voice or request.voice_id
    if not voice_id:
        raise HTTPException(status_code=422, detail="voice is required")

    duration = request.duration or request.duration_minutes or 20
    experience = request.experience or request.experience_level or "beginner"

    generation_request = request.model_dump()
    generation_request["voice"] = voice_id
    generation_request["duration"] = duration
    generation_request["experience"] = experience
    generation_request["name"] = request.name or request.intention or request.goal or "Not specified"
    generation_request["user_name"] = generation_request["name"]
    generation_request["stress_input"] = request.avoid or request.stress_input or "Not specified"
    generation_request["body_tension"] = request.body_tension or request.body_tension_areas or []

    generation_result = generate_structured_meditation(generation_request)
    structured_meditation = generation_result["meditation"]
    script_sections = generation_result["sections"]

    sections = {}
    for section_name in ("meditation", "suggestion", "affirmation"):
        section_data = script_sections[section_name]
        section_text = section_data["script"]
        voice_direction = section_data.get("voice_direction", {})
        tts_settings = voice_direction.get("tts_settings")

        logger.info(
            "Generating TTS for '%s' - %s chars",
            section_name,
            len(section_text),
        )

        audio_bytes = generate_voice(
            text=section_text,
            voice_id=voice_id,
            tts_settings=tts_settings,
        )

        sections[section_name] = MeditationSection(
            text=section_text,
            audio_base64=base64.b64encode(audio_bytes).decode("utf-8"),
            voice_direction=VoiceDirection(
                pitch=voice_direction.get("pitch", "Natural"),
                pacing=voice_direction.get("pacing", "Moderate"),
                emotion=voice_direction.get("emotion", "Calm"),
            ),
        )

    logger.info("Meditation generation complete - structured meditation and audio are ready.")

    archive_payload = {
        name: {
            "text": section.text,
            "audio_base64": section.audio_base64,
            "voice_direction": section.voice_direction.model_dump(),
        }
        for name, section in sections.items()
    }
    archive_entry = create_archive_entry(
        title=structured_meditation["title"],
        category=generation_result["normalized_request"]["category"],
        voice_id=voice_id,
        duration=duration,
        summary=structured_meditation.get("summary", ""),
        meditation=structured_meditation,
        sections=archive_payload,
    )

    return MeditationResponse(
        intention=request.name or request.intention or request.goal or request.category or "Guided meditation",
        persona=request.persona,
        language=request.language,
        category=generation_result["normalized_request"]["category"],
        summary=structured_meditation.get("summary", ""),
        total_duration=structured_meditation["total_duration"],
        archive_id=archive_entry["id"],
        created_at=archive_entry["created_at"],
        meditation=structured_meditation,
        sections=sections,
    )


@router.get("/archive", response_model=list[ArchiveEntryResponse])
def get_archive():
    """
    Return saved meditations for archive and replay screens.
    """
    return list_archive_entries()


@router.get("/favorites", response_model=list[ArchiveEntryResponse])
def get_favorites():
    """
    Return meditations marked as favorite.
    """
    return list_favorite_entries()


@router.post("/archive/{entry_id}/favorite", response_model=ArchiveEntryResponse)
def set_favorite(entry_id: str, request: FavoriteUpdateRequest):
    """
    Mark or unmark an archived meditation as favorite.
    """
    updated = update_favorite_status(entry_id, request.favorite)
    if updated is None:
        raise HTTPException(status_code=404, detail="Meditation archive entry not found.")
    return updated


class SimpleTTSRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Script text to read")
    voice_id: str = Field(..., min_length=1, description="ElevenLabs voice ID")


@router.post("/simple-tts")
def generate_simple_tts(request: SimpleTTSRequest):
    """
    Generate voice directly from plain text for frontend testing.
    """
    from fastapi.responses import Response

    logger.info(
        "Generating simple TTS - voice: '%s', text len: %s",
        request.voice_id,
        len(request.text),
    )

    audio_bytes = generate_voice(
        text=request.text,
        voice_id=request.voice_id,
        tts_settings=None,
    )

    return Response(content=audio_bytes, media_type="audio/mpeg")
