# Main Endpoints

Back to index: [ENDPOINT_LIST.md](../ENDPOINT_LIST.md)

## Endpoint Inventory

- `GET /api/v1/charecter-voice/`
- `GET /api/v1/nature-sounds/`
- `GET /api/v1/background-image/`
- `POST /api/v1/meditation/generate/`
- `GET /api/v1/meditation/archive/`
- `GET /api/v1/meditation/<id>/`

---

## `GET /api/v1/meditation/archive/`

### Description

Retrieve a paginated list of all meditations created by the authenticated user, ordered by newest first. Includes aggregated fields such as the overall total duration of all meditations and a flat array of all meditation IDs.

### Auth

- `Required`

### Query Parameters

- `page` (optional): Page number (default 1)
- `page_size` (optional): Number of results per page (default 10)

### Request Payload Reference

N/A

### Response Payload Reference

Success example.

```json
{
  "all_meditation_ids": [24, 23, 21],
  "overall_total_duration": 1800.0,
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 24,
      "banner_url": "http://127.0.0.1:8000/static/Cover/Cover_Entspannung.jpg",
      "category": "relaxation",
      "category_name": "Entspannung",
      "created_at": "2026-05-19T11:49:52Z",
      "total_duration": 600.0
    },
    {
      "id": 23,
      "banner_url": "http://127.0.0.1:8000/static/Cover/Cover_Energie.jpg",
      "category": "energy",
      "category_name": "Energie",
      "created_at": "2026-05-18T09:20:10Z",
      "total_duration": 600.0
    }
  ]
}
```

---

## `GET /api/v1/meditation/<id>/`

### Description

Retrieve detailed data for a specific meditation by its ID, including all generated steps. This endpoint will only return the meditation if it was created by the currently authenticated user.

### Auth

- `Required`

### Request Payload Reference

N/A

### Response Payload Reference

Success example.

```json
{
  "id": 24,
  "title": "Tiefenentspannung für Anna",
  "banner_url": "http://127.0.0.1:8000/static/Cover/Cover_Entspannung.jpg",
  "background_image": {
    "id": 2,
    "name": "Cosmic Sky",
    "file": "http://127.0.0.1:8000/media/uploads/images/cosmic_bg.jpg"
  },
  "charecter_voice": {
    "id": 1,
    "name": "Aura",
    "avatar_url": "http://127.0.0.1:8000/media/uploads/characters/aura.png",
    "short_description": "A soothing and calm female voice.",
    "tags": "calm, soothing",
    "file": "http://127.0.0.1:8000/media/uploads/audio/aura.mp3"
  },
  "nature_sound": {
    "id": 1,
    "name": "Ocean Waves",
    "file": "http://127.0.0.1:8000/media/uploads/audio/ocean_waves.mp3"
  },
  "experience_question_answer": {
    "name": "Anna",
    "goal": "Tiefenentspannung nach der Arbeit"
  },
  "category": "relaxation",
  "created_at": "2026-05-19T11:49:52Z",
  "steps": [
    {
      "id": 162,
      "step_type": "greeting",
      "content": "Willkommen Anna zu deiner heutigen Meditationsreise für tiefe Entspannung. Schön, dass du hier bist.",
      "audio_file": "http://127.0.0.1:8000/media/uploads/audio/aura.mp3",
      "duration": "00:00:45",
      "duration_percentage": 7.5,
      "created_at": "2026-05-19T11:49:52Z"
    }
  ],
  "total_duration": 600.0
}
```

Error example (Unauthorized or Not Found).

```json
{
  "detail": "Not found."
}
```

---

## `GET /api/v1/charecter-voice/`

### Description

Retrieve a list of all active character voices available for meditation generation.

### Auth

- `Not required`

### Request Payload Reference

N/A

### Response Payload Reference

Success example.

```json
[
  {
    "id": 1,
    "name": "Aura",
    "avatar_url": "http://127.0.0.1:8000/media/uploads/characters/aura.png",
    "short_description": "A soothing and calm female voice.",
    "tags": "calm, soothing",
    "file": "http://127.0.0.1:8000/media/uploads/audio/aura.mp3"
  }
]
```

---

## `GET /api/v1/nature-sounds/`

### Description

Retrieve a list of all active nature sounds.

### Auth

- `Not required`

### Request Payload Reference

N/A

### Response Payload Reference

Success example.

```json
[
  {
    "id": 1,
    "name": "Ocean Waves",
    "file": "http://127.0.0.1:8000/media/uploads/audio/ocean_waves.mp3"
  }
]
```

---

## `GET /api/v1/background-image/`

### Description

Retrieve a list of all active background images.

### Auth

- `Not required`

### Request Payload Reference

N/A

### Response Payload Reference

Success example.

```json
[
  {
    "id": 1,
    "name": "Cosmic Sky",
    "file": "http://127.0.0.1:8000/media/uploads/images/cosmic_bg.jpg"
  }
]
```

---

## `POST /api/v1/meditation/generate/`

### Description

Generate a personalized meditation sequence. The response strictly returns the generation IDs, total time, and the structured sequence of steps with dynamically calculated percentage duration. The actual meditation text content will later be generated via AI integration.

### Auth

- `Required`

### Request Payload Reference

Use this shape as request body. Note that `nature_sound_name` and `background_image_id` are optional.

```json
{
  "category": "relaxation",
  "charecter_voice_id": 1,
  "experience_question_answers": {
    "name": "Anna",
    "goal": "Tiefenentspannung nach der Arbeit"
  },
  "nature_sound_name": "Ocean Waves",
  "background_image_id": 2
}
```

Categories available: `relaxation`, `self_love`, `focus_clarity`, `gratitude`, `trust`, `energy`, `transformation`, `inner_peace`.

### Response Payload Reference

Success example.

```json
{
  "id": 24,
  "meditation_id": 24,
  "total_duration": 600.0,
  "steps": [
    {
      "id": 162,
      "step_type": "greeting",
      "content": "Willkommen Anna zu deiner heutigen Meditationsreise für tiefe Entspannung. Schön, dass du hier bist.",
      "audio_file": "http://127.0.0.1:8000/media/uploads/audio/aura.mp3",
      "duration": "00:00:45",
      "duration_percentage": 7.5,
      "created_at": "2026-05-19T11:49:52Z"
    },
    {
      "id": 163,
      "step_type": "personal",
      "content": "Nimm dir einen Moment Zeit, um ganz bei dir anzukommen. Du darfst jetzt alles loslassen.",
      "audio_file": "http://127.0.0.1:8000/media/uploads/audio/aura.mp3",
      "duration": "00:01:00",
      "duration_percentage": 10.0,
      "created_at": "2026-05-19T11:49:52Z"
    }
  ]
}
```

Error example (Missing required fields or invalid ID).

```json
{
  "charecter_voice_id": [
    "Character voice does not exist."
  ],
  "category": [
    "\"invalid_cat\" is not a valid choice."
  ]
}
```

### Related Tests

- `apps/main/tests.py`
