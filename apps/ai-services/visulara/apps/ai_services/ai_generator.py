import json
import os
import time
import logging
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIStatusError, APIConnectionError

env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Primary model and fallbacks to handle rate limit and temporary errors
OPENAI_MODELS = [OPENAI_MODEL]
for fallback in ["gpt-4o-mini", "gpt-4o"]:
    if fallback not in OPENAI_MODELS:
        OPENAI_MODELS.append(fallback)

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def generate_script(prompt: str) -> dict:
    if client is None:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    last_error = "Unknown error"

    for model in OPENAI_MODELS:
        for attempt in range(2):
            try:
                logger.info(f"Calling OpenAI model {model} (attempt {attempt + 1}/2)...")
                response = client.chat.completions.create(
                    model=model,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": "You are a world-class meditation teacher. Generate valid meditation JSON only according to the specified schema."},
                        {"role": "user", "content": prompt},
                    ],
                    timeout=60,
                )
                content = response.choices[0].message.content
                return json.loads(content)
            except (RateLimitError, APIStatusError) as e:
                status_code = getattr(e, "status_code", None)
                if status_code in (429, 500, 502, 503, 504) or isinstance(e, RateLimitError):
                    delay = 5 * (attempt + 1)
                    logger.warning(
                        f"OpenAI {model} returned error ({e}). "
                        f"Attempt {attempt + 1}/2. Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    last_error = str(e)
                    continue
                else:
                    logger.error(f"OpenAI {model} returned non-retryable error: {e}")
                    last_error = str(e)
                    break
            except APIConnectionError as e:
                logger.warning(f"Connection error calling OpenAI {model}: {e}. Retrying...")
                time.sleep(2)
                last_error = str(e)
                continue
            except Exception as e:
                logger.error(f"Unexpected error calling OpenAI {model}: {e}")
                last_error = str(e)
                break

    raise RuntimeError(f"All OpenAI models and attempts failed. Last error: {last_error}")