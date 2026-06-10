import json
from openai import AsyncOpenAI
from app.core.config import settings

class AIGenerationError(RuntimeError):
    pass

class OpenAIMeditationGenerator:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

    async def generate_json(self, prompt: str) -> dict:
        if self.client is None:
            raise AIGenerationError("OpenAI API key is not configured.")
        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You generate valid meditation JSON only."},
                    {"role": "user", "content": prompt},
                ],
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as exc:
            raise AIGenerationError("Failed to generate meditation JSON from OpenAI.") from exc
