# 🌿 Visulara - Personalized Meditation Experience

Visulara is a state-of-the-art meditation web application that crafts deeply personal journeys for your mind and soul. By leveraging the power of **OpenAI** and **ElevenLabs Text-to-Speech**, Visulara generates unique scripts and immersive audio tailored specifically to your intentions, mood, and environment.

## ✨ Key Features

- **Personalized Script Generation**: Uses OpenAI to create three-part meditations (Guided, Suggestion, Affirmation) based on your unique intentions.
- **Ultra-Realistic AI Voices**: Integration with ElevenLabs professional voices (Frederik, Jil, Kerstin, Brian) for a human-like, soothing experience.
- **Intelligent Fallback System**: Automatically handles high-demand spikes in AI services by falling back to alternative models (gpt-4o-mini, gpt-4o) and retrying requests.
- **Dynamic Audio Layering**: Combines AI-generated guidance with background "anchors" like rain, wind, or ocean waves.
- **Seamless User Flow**: Interactive questionnaire to capture your current state, followed by a beautiful, glassmorphic meditation player.

## 📁 Project Structure

```text
meditation_web_app/
├── .env                    # Environment variables (API Keys)
├── requirements.txt        # Python dependencies
├── visulara/               # Core application package
│   ├── apps/               # Backend logic
│   │   ├── main.py         # FastAPI application entry point
│   │   ├── ai_services/    # AI Integration layer
│   │   │   ├── ai_generator.py # OpenAI script generator & fallbacks
│   │   │   └── elevenLabs_tts.py # ElevenLabs TTS & resilience
│   │   └── meditation/     # Domain-specific routes
│   │       └── meditation.py # Audio generation & orchestrator
│   ├── static/             # Frontend assets (CSS, JS)
│   └── templates/          # HTML templates
└── docs/                   # Project documentation
```

## 🚀 Getting Started

### 1. Environment Setup
Create a `.env` file in the project root with your API keys:

```env
OPENAI_API_KEY=your_openai_api_key
ELEVEN_API_KEY=your_elevenlabs_key
```

### 2. Installation
We recommend using a virtual environment:

```powershell
# Create virtual environment
python -m venv myenv

# Activate (Windows)
myenv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Running the Application
Start the development server from the root directory:

```powershell
python -m uvicorn visulara.apps.main:app --reload
```

The app will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000).

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python)
- **AI**: OpenAI (LLM), ElevenLabs (TTS)
- **Frontend**: Vanilla JavaScript, CSS (Modern Glassmorphic UI)
- **Design**: Premium aesthetics with dynamic animations and responsive layouts.

---
*Created with care for mental well-being.*
