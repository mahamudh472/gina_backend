# 📦 Visulara Package

This directory contains the core logic for the Visulara meditation web application.

## Structure

- **apps/**: The FastAPI backend implementation.
  - **main.py**: Entry point.
  - **ai_services/**: Integration with Gemini and ElevenLabs.
  - **meditation/**: API endpoints for audio generation.
- **static/**: Frontend styling (CSS) and interactivity (JS).
- **templates/**: HTML blueprints for the UI.

## Usage

This package is intended to be run from the project root using:
```bash
python -m uvicorn visulara.apps.main:app --reload
```

For more details, please see the [main README](../README.md).
