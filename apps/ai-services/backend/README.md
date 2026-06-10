# Production Backend

This Django REST Framework backend is the production-oriented implementation for the meditation generation flow.

## Features

- PostgreSQL-ready domain models for sessions, artifacts, steps, favorites, and playback tracking
- OpenAI-based structured meditation generation
- ElevenLabs-based TTS generation
- JSON Schema validation for AI output
- S3-ready audio storage through `django-storages`
- Archive, favorites, voices, questionnaire, and playback APIs

## Setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py loaddata apps/meditation/fixtures/default_voices.json
python manage.py runserver
```

## API

- `GET /api/v1/voices/`
- `POST /api/v1/questionnaire/`
- `POST /api/v1/meditations/generate/`
- `GET /api/v1/meditations/archive/`
- `GET /api/v1/meditations/favorites/`
- `POST /api/v1/meditations/{artifact_id}/favorite/`
- `POST /api/v1/meditations/{artifact_id}/playback/`

## Notes

- When `DATABASE_URL` is missing, the project falls back to SQLite for local development only.
- When S3 credentials are configured, generated audio is stored using the configured default storage backend.



### Runserver
```
python -m uvicorn visulara.apps.main:app --reload
```