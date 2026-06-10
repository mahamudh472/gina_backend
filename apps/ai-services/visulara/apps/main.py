import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables before anything else
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from visulara.apps.meditation.meditation import router as meditation_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(
    title="Visulara API",
    description="Personalized meditation experience powered by OpenAI and ElevenLabs TTS",
    version="1.0.0",
)

# CORS — allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(base_dir, "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Register routes
app.include_router(meditation_router, prefix="/api/v1", tags=["Meditation"])


@app.get("/", tags=["UI"])
def serve_ui():
    """Serve the main UI design."""
    template_path = os.path.join(base_dir, "templates", "index.html")
    return FileResponse(template_path)

@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "app": "Visulara", "version": "1.0.0"}