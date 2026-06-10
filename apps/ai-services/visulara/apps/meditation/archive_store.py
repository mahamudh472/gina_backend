import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4


ARCHIVE_PATH = Path(__file__).resolve().parent.parent.parent / "media" / "meditation_archive.json"
ARCHIVE_PATH.parent.mkdir(parents=True, exist_ok=True)

_LOCK = Lock()


def _read_archive() -> list[dict]:
    if not ARCHIVE_PATH.exists():
        return []
    raw = ARCHIVE_PATH.read_text(encoding="utf-8-sig").strip()
    if not raw:
        return []
    return json.loads(raw)


def _write_archive(entries: list[dict]) -> None:
    ARCHIVE_PATH.write_text(
        json.dumps(entries, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def create_archive_entry(
    *,
    title: str,
    category: str,
    voice_id: str,
    duration: int,
    summary: str,
    meditation: dict,
    sections: dict,
) -> dict:
    entry = {
        "id": str(uuid4()),
        "title": title,
        "category": category,
        "voice": voice_id,
        "duration": duration,
        "summary": summary,
        "audio_url": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "favorite": False,
        "meditation": meditation,
        "sections": sections,
    }

    with _LOCK:
        entries = _read_archive()
        entries.append(entry)
        _write_archive(entries)

    return entry


def list_archive_entries() -> list[dict]:
    with _LOCK:
        entries = _read_archive()
    return sorted(entries, key=lambda item: item["created_at"], reverse=True)


def list_favorite_entries() -> list[dict]:
    return [entry for entry in list_archive_entries() if entry.get("favorite")]


def update_favorite_status(entry_id: str, favorite: bool) -> dict | None:
    with _LOCK:
        entries = _read_archive()
        updated = None
        for entry in entries:
            if entry["id"] == entry_id:
                entry["favorite"] = favorite
                updated = entry
                break
        if updated is None:
            return None
        _write_archive(entries)
        return updated
