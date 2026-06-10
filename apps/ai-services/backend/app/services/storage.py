import os
from app.core.config import settings

async def save_audio_file(*, artifact_id: str, audio_bytes: bytes) -> str:
    media_root = os.path.join(os.getcwd(), "media")
    folder_path = os.path.join(media_root, settings.MEDITATION_AUDIO_FOLDER)
    os.makedirs(folder_path, exist_ok=True)
    
    file_path = os.path.join(folder_path, f"{artifact_id}.mp3")
    
    # Write async if needed, but for simplicity a blocking write is fast enough for small files
    with open(file_path, "wb") as f:
        f.write(audio_bytes)
        
    return f"/media/{settings.MEDITATION_AUDIO_FOLDER}/{artifact_id}.mp3"
