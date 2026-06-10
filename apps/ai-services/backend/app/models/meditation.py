import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base

class TimeStampedModel(Base):
    __abstract__ = True
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class NarratorVoice(TimeStampedModel):
    __tablename__ = "narrator_voices"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    provider: Mapped[str] = mapped_column(String(50), default="elevenlabs")
    provider_voice_id: Mapped[str] = mapped_column(String(255), unique=True)
    persona: Mapped[str] = mapped_column(String(120), default="")
    language: Mapped[str] = mapped_column(String(32), default="German")
    default_tts_settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    sessions: Mapped[list["MeditationSession"]] = relationship("MeditationSession", back_populates="narrator_voice")

class MeditationSession(TimeStampedModel):
    __tablename__ = "meditation_sessions"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_reference: Mapped[str] = mapped_column(String(255), default="")
    category: Mapped[str] = mapped_column(String(32))
    narrator_voice_id: Mapped[int] = mapped_column(ForeignKey("narrator_voices.id"))
    language: Mapped[str] = mapped_column(String(32), default="German")
    emotion: Mapped[str] = mapped_column(String(255))
    goal: Mapped[str] = mapped_column(String(255))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    experience_level: Mapped[str] = mapped_column(String(32))
    body_tension_areas: Mapped[list[str]] = mapped_column(JSON, default=list)
    nature_sound: Mapped[str] = mapped_column(String(255), default="")
    landscape: Mapped[str] = mapped_column(String(255), default="")
    questionnaire_answers: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    preferences: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    failure_reason: Mapped[str] = mapped_column(String, default="")

    narrator_voice: Mapped["NarratorVoice"] = relationship("NarratorVoice", back_populates="sessions")
    artifact: Mapped["MeditationArtifact"] = relationship("MeditationArtifact", back_populates="session", uselist=False)

class MeditationArtifact(TimeStampedModel):
    __tablename__ = "meditation_artifacts"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("meditation_sessions.id"))
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(String)
    total_duration_seconds: Mapped[int] = mapped_column(Integer)
    script_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    audio_url: Mapped[str] = mapped_column(String, default="")
    storage_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)

    session: Mapped["MeditationSession"] = relationship("MeditationSession", back_populates="artifact")
    steps: Mapped[list["MeditationStep"]] = relationship("MeditationStep", back_populates="artifact", cascade="all, delete-orphan", order_by="MeditationStep.sequence_order")
    playback_events: Mapped[list["PlaybackTracking"]] = relationship("PlaybackTracking", back_populates="artifact", cascade="all, delete-orphan")

class MeditationStep(TimeStampedModel):
    __tablename__ = "meditation_steps"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    artifact_id: Mapped[str] = mapped_column(ForeignKey("meditation_artifacts.id"))
    step_type: Mapped[str] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(String)
    duration_seconds: Mapped[int] = mapped_column(Integer)
    start_time_seconds: Mapped[int] = mapped_column(Integer)
    end_time_seconds: Mapped[int] = mapped_column(Integer)
    sequence_order: Mapped[int] = mapped_column(Integer)

    artifact: Mapped["MeditationArtifact"] = relationship("MeditationArtifact", back_populates="steps")

class PlaybackTracking(TimeStampedModel):
    __tablename__ = "playback_tracking"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    artifact_id: Mapped[str] = mapped_column(ForeignKey("meditation_artifacts.id"))
    user_reference: Mapped[str] = mapped_column(String(255), default="")
    current_position_seconds: Mapped[int] = mapped_column(Integer, default=0)
    current_step_type: Mapped[str] = mapped_column(String(64), default="")
    completion_percent: Mapped[float] = mapped_column(Float, default=0.0)
    play_count: Mapped[int] = mapped_column(Integer, default=0)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    last_played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    artifact: Mapped["MeditationArtifact"] = relationship("MeditationArtifact", back_populates="playback_events")
