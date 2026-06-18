class MeditationGenerationError(RuntimeError):
    """Raised when meditation script generation cannot complete."""


class TTSGenerationError(RuntimeError):
    """Raised when meditation audio generation cannot complete."""