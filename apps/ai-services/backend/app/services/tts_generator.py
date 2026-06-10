from app.core.config import settings
import httpx

class TTSGenerationError(RuntimeError):
    pass

class ElevenLabsTTSGenerator:
    async def generate(self, *, text: str, voice_id: str, tts_settings: dict | None = None) -> bytes:
        payload = {
            "text": text,
            "model_id": settings.ELEVEN_TTS_MODEL,
            "voice_settings": tts_settings or {
                "stability": 0.8,
                "similarity_boost": 0.75,
                "style": 0.25,
                "use_speaker_boost": True,
            },
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={"xi-api-key": settings.ELEVEN_API_KEY, "Content-Type": "application/json"},
                json=payload,
            )
            
            if response.status_code != 200:
                raise TTSGenerationError(f"TTS provider returned {response.status_code}.")
                
            return response.content
