from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Any, Dict, List
from datetime import datetime
import uuid

class NarratorVoiceSchema(BaseModel):
    id: int
    name: str
    slug: str
    provider: str
    provider_voice_id: str
    persona: str
    language: str
    default_tts_settings: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)

class GenerateMeditationRequest(BaseModel):
    user_reference: Optional[str] = ""
    name: Optional[str] = ""
    category: str
    voice: Optional[str] = None
    emotion: str
    goal: str
    duration: Optional[int] = None
    experience: Optional[str] = None
    body_tension: Optional[List[str]] = Field(default_factory=list)
    nature_sound: Optional[str] = ""
    landscape: Optional[str] = ""
    avoid: Optional[str] = ""
    user_name: Optional[str] = ""
    questionnaire_answers: Optional[Dict[str, Any]] = Field(default_factory=dict)
    preferences: Optional[Dict[str, Any]] = Field(default_factory=dict)

class MeditationStepSchema(BaseModel):
    step_type: str
    content: str
    duration: int = Field(alias="duration_seconds")
    start_time: int = Field(alias="start_time_seconds")
    end_time: int = Field(alias="end_time_seconds")
    sequence_order: int

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class MeditationArtifactSchema(BaseModel):
    id: str
    title: str
    summary: str
    category: str
    category_display: str
    voice: str
    duration: int
    duration_minutes: int
    experience: str
    experience_level: str
    total_duration_seconds: int
    audio_url: str
    is_favorite: bool
    created_at: datetime
    script_json: Dict[str, Any]
    steps: List[MeditationStepSchema]
    user_preferences: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)

class FavoriteUpdateRequest(BaseModel):
    is_favorite: bool

class PlaybackTrackingUpsertRequest(BaseModel):
    user_reference: Optional[str] = ""
    current_position_seconds: int = Field(ge=0)
    current_step_type: Optional[str] = ""
    completion_percent: float = Field(ge=0, le=100)
    play_count: Optional[int] = None
    is_completed: Optional[bool] = None

class PlaybackTrackingSchema(BaseModel):
    id: str
    artifact_id: str
    user_reference: str
    current_position_seconds: int
    current_step_type: str
    completion_percent: float
    play_count: int
    is_completed: bool
    last_played_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
