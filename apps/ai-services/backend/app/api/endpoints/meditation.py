import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.meditation import NarratorVoice, MeditationSession, MeditationArtifact, MeditationStep, PlaybackTracking
from app.schemas.meditation import (
    NarratorVoiceSchema,
    GenerateMeditationRequest,
    MeditationArtifactSchema,
    FavoriteUpdateRequest,
    PlaybackTrackingUpsertRequest,
    PlaybackTrackingSchema
)
from app.constants.meditation import MEDITATION_CATEGORIES, DURATION_OPTIONS, EXPERIENCE_LEVELS
from app.services.meditation_generator import MeditationOrchestrator
from app.services.tts_generator import ElevenLabsTTSGenerator
from app.services.storage import save_audio_file

router = APIRouter()

@router.get("/voices/", response_model=List[NarratorVoiceSchema])
async def list_voices(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NarratorVoice).where(NarratorVoice.is_active == True).order_by(NarratorVoice.name))
    voices = result.scalars().all()
    return voices

@router.post("/questionnaire/")
async def questionnaire(request: GenerateMeditationRequest):
    category = request.category or "relaxation"
    questions = [
        {"key": "emotion", "question": f"What best matches your current state for {category}?", "options": ["stressed", "tired", "restless", "open"]},
        {"key": "goal", "question": "What do you want to feel after this meditation?", "options": ["lighter", "safer", "clearer", "energized"]},
        {"key": "duration", "question": "How long should the meditation be?", "options": DURATION_OPTIONS},
        {"key": "experience", "question": "What is your experience level?", "options": [level[1] for level in EXPERIENCE_LEVELS]},
        {"key": "body_tension_areas", "question": "Where do you feel tension in the body?", "options": ["neck", "shoulders", "jaw", "chest"]},
        {"key": "nature_sound", "question": "Which nature sound do you prefer?", "options": ["rain", "ocean", "wind", "silence"]},
        {"key": "landscape", "question": "Which landscape should guide the visualization?", "options": ["mountain", "beach", "forest", "temple"]},
    ]
    return {"category": category, "categories": [label for _, label in MEDITATION_CATEGORIES], "questions": questions}

@router.post("/generate/", response_model=MeditationArtifactSchema, status_code=status.HTTP_201_CREATED)
async def generate_meditation(request: GenerateMeditationRequest, db: AsyncSession = Depends(get_db)):
    # Validate Voice
    voice_id = request.voice
    if not voice_id:
        raise HTTPException(status_code=400, detail="Select a valid voice.")
        
    result = await db.execute(select(NarratorVoice).where(NarratorVoice.provider_voice_id == voice_id))
    voice = result.scalars().first()
    if not voice:
        raise HTTPException(status_code=400, detail="Select a valid voice.")

    # Create Session
    session = MeditationSession(
        user_reference=request.user_reference or request.name or request.user_name or "",
        category=request.category,
        narrator_voice_id=voice.id,
        language="German",
        emotion=request.emotion,
        goal=request.goal,
        duration_minutes=request.duration or 20,
        experience_level=request.experience or "beginner",
        body_tension_areas=request.body_tension or [],
        nature_sound=request.nature_sound or "",
        landscape=request.landscape or "",
        questionnaire_answers=request.questionnaire_answers or {},
        preferences=request.preferences or {},
        status="pending"
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    request_data = {
        "category": session.category,
        "voice_name": voice.name,
        "emotion": session.emotion,
        "goal": session.goal,
        "duration": session.duration_minutes,
        "experience": session.experience_level,
        "body_tension": session.body_tension_areas,
        "nature_sound": session.nature_sound,
        "landscape": session.landscape,
        "stress_input": request.avoid or "",
        "user_name": session.user_reference,
        "questionnaire_answers": session.questionnaire_answers,
    }

    try:
        orchestrator = MeditationOrchestrator()
        meditation_payload = await orchestrator.generate(request_data=request_data)
        
        combined_text = "\n\n".join(step["content"] for step in meditation_payload["steps"])
        
        tts_generator = ElevenLabsTTSGenerator()
        audio_bytes = await tts_generator.generate(
            text=combined_text,
            voice_id=voice.provider_voice_id,
            tts_settings=voice.default_tts_settings or None,
        )
        
        artifact = MeditationArtifact(
            session_id=session.id,
            title=meditation_payload["title"],
            summary=meditation_payload["summary"],
            total_duration_seconds=meditation_payload["total_duration"],
            script_json=meditation_payload,
            storage_metadata={}
        )
        db.add(artifact)
        await db.commit()
        await db.refresh(artifact)
        
        audio_url = await save_audio_file(artifact_id=str(artifact.id), audio_bytes=audio_bytes)
        
        artifact.audio_url = audio_url
        artifact.storage_metadata = {"provider": "filesystem", "path": audio_url}
        db.add(artifact)
        
        for index, step in enumerate(meditation_payload["steps"], start=1):
            db_step = MeditationStep(
                artifact_id=artifact.id,
                step_type=step["step_type"],
                content=step["content"],
                duration_seconds=step["duration"],
                start_time_seconds=step["start_time"],
                end_time_seconds=step["end_time"],
                sequence_order=index
            )
            db.add(db_step)
            
        session.status = "generated"
        db.add(session)
        await db.commit()
        
        # Load relationships for response
        result = await db.execute(
            select(MeditationArtifact)
            .options(
                selectinload(MeditationArtifact.steps),
                selectinload(MeditationArtifact.session).selectinload(MeditationSession.narrator_voice)
            )
            .where(MeditationArtifact.id == artifact.id)
        )
        artifact = result.scalars().first()
        
        # Construct response data manually matching MeditationArtifactSchema structure since 
        # computed fields like category_display are needed
        return {
            "id": artifact.id,
            "title": artifact.title,
            "summary": artifact.summary,
            "category": artifact.session.category,
            "category_display": artifact.session.category.replace("_", " ").title(),
            "voice": artifact.session.narrator_voice.name,
            "duration": artifact.session.duration_minutes,
            "duration_minutes": artifact.session.duration_minutes,
            "experience": artifact.session.experience_level,
            "experience_level": artifact.session.experience_level,
            "total_duration_seconds": artifact.total_duration_seconds,
            "audio_url": artifact.audio_url,
            "is_favorite": artifact.is_favorite,
            "created_at": artifact.created_at,
            "script_json": artifact.script_json,
            "steps": artifact.steps,
            "user_preferences": artifact.session.preferences
        }
            
    except Exception as exc:
        session.status = "failed"
        session.failure_reason = str(exc)
        db.add(session)
        await db.commit()
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/archive/", response_model=List[MeditationArtifactSchema])
async def list_archive(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MeditationArtifact)
        .options(
            selectinload(MeditationArtifact.steps),
            selectinload(MeditationArtifact.session).selectinload(MeditationSession.narrator_voice)
        )
        .order_by(MeditationArtifact.created_at.desc())
    )
    artifacts = result.scalars().all()
    
    response = []
    for artifact in artifacts:
        response.append({
            "id": artifact.id,
            "title": artifact.title,
            "summary": artifact.summary,
            "category": artifact.session.category,
            "category_display": artifact.session.category.replace("_", " ").title(),
            "voice": artifact.session.narrator_voice.name,
            "duration": artifact.session.duration_minutes,
            "duration_minutes": artifact.session.duration_minutes,
            "experience": artifact.session.experience_level,
            "experience_level": artifact.session.experience_level,
            "total_duration_seconds": artifact.total_duration_seconds,
            "audio_url": artifact.audio_url,
            "is_favorite": artifact.is_favorite,
            "created_at": artifact.created_at,
            "script_json": artifact.script_json,
            "steps": artifact.steps,
            "user_preferences": artifact.session.preferences
        })
    return response

@router.get("/favorites/", response_model=List[MeditationArtifactSchema])
async def list_favorites(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MeditationArtifact)
        .where(MeditationArtifact.is_favorite == True)
        .options(
            selectinload(MeditationArtifact.steps),
            selectinload(MeditationArtifact.session).selectinload(MeditationSession.narrator_voice)
        )
        .order_by(MeditationArtifact.created_at.desc())
    )
    artifacts = result.scalars().all()
    
    response = []
    for artifact in artifacts:
        response.append({
            "id": artifact.id,
            "title": artifact.title,
            "summary": artifact.summary,
            "category": artifact.session.category,
            "category_display": artifact.session.category.replace("_", " ").title(),
            "voice": artifact.session.narrator_voice.name,
            "duration": artifact.session.duration_minutes,
            "duration_minutes": artifact.session.duration_minutes,
            "experience": artifact.session.experience_level,
            "experience_level": artifact.session.experience_level,
            "total_duration_seconds": artifact.total_duration_seconds,
            "audio_url": artifact.audio_url,
            "is_favorite": artifact.is_favorite,
            "created_at": artifact.created_at,
            "script_json": artifact.script_json,
            "steps": artifact.steps,
            "user_preferences": artifact.session.preferences
        })
    return response

@router.post("/{artifact_id}/favorite/", response_model=MeditationArtifactSchema)
async def update_favorite(artifact_id: str, request: FavoriteUpdateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MeditationArtifact)
        .options(
            selectinload(MeditationArtifact.steps),
            selectinload(MeditationArtifact.session).selectinload(MeditationSession.narrator_voice)
        )
        .where(MeditationArtifact.id == artifact_id)
    )
    artifact = result.scalars().first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
        
    artifact.is_favorite = request.is_favorite
    db.add(artifact)
    await db.commit()
    
    return {
        "id": artifact.id,
        "title": artifact.title,
        "summary": artifact.summary,
        "category": artifact.session.category,
        "category_display": artifact.session.category.replace("_", " ").title(),
        "voice": artifact.session.narrator_voice.name,
        "duration": artifact.session.duration_minutes,
        "duration_minutes": artifact.session.duration_minutes,
        "experience": artifact.session.experience_level,
        "experience_level": artifact.session.experience_level,
        "total_duration_seconds": artifact.total_duration_seconds,
        "audio_url": artifact.audio_url,
        "is_favorite": artifact.is_favorite,
        "created_at": artifact.created_at,
        "script_json": artifact.script_json,
        "steps": artifact.steps,
        "user_preferences": artifact.session.preferences
    }

@router.post("/{artifact_id}/playback/", response_model=PlaybackTrackingSchema)
async def tracking_playback(artifact_id: str, request: PlaybackTrackingUpsertRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MeditationArtifact).where(MeditationArtifact.id == artifact_id))
    artifact = result.scalars().first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
        
    result = await db.execute(
        select(PlaybackTracking)
        .where(PlaybackTracking.artifact_id == artifact_id, PlaybackTracking.user_reference == request.user_reference)
    )
    tracking = result.scalars().first()
    
    if not tracking:
        tracking = PlaybackTracking(
            artifact_id=artifact_id,
            user_reference=request.user_reference
        )
        
    tracking.current_position_seconds = request.current_position_seconds
    if request.current_step_type is not None:
        tracking.current_step_type = request.current_step_type
    tracking.completion_percent = request.completion_percent
    if request.play_count is not None:
        tracking.play_count = request.play_count
    if request.is_completed is not None:
        tracking.is_completed = request.is_completed
    tracking.last_played_at = datetime.now(timezone.utc)
    
    db.add(tracking)
    await db.commit()
    await db.refresh(tracking)
    
    return tracking
