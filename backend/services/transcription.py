from pathlib import Path


class TranscriptionEngine:
    """
    Speech-to-text engine.

    The actual Whisper/open-source model can be
    connected here later without changing the API.
    """

    def __init__(self):
        self.model = None

    def transcribe(
        self,
        audio_path: str | Path
    ) -> dict:

        audio_path = Path(audio_path)

        if not audio_path.exists():
            raise FileNotFoundError(
                f"Audio file not found: {audio_path}"
            )

        # Model integration will be added here.
        # Keep the response format stable.

        return {
            "success": True,
            "language": "unknown",
            "text": "",
            "segments": [],
            "engine": "whisper-compatible"
        }


transcription_engine = TranscriptionEngine()
