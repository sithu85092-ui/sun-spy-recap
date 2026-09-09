from typing import Optional


class BurmeseNarrator:

    def __init__(self):

        self.engine = "local"

    def create_recap(
        self,
        transcript: str,
        max_length: int = 500
    ) -> dict:

        transcript = (
            transcript or ""
        ).strip()

        if not transcript:

            return {
                "success": False,
                "language": "my",
                "text": "",
                "error": "Transcript is empty",
                "engine": self.engine
            }


        # -------------------------------------------------
        # Temporary Burmese recap engine
        # -------------------------------------------------
        #
        # The real local LLM summarizer will be connected
        # in the next AI-model phase.
        #
        # Keep this interface stable so the worker/API
        # does not need to change later.
        # -------------------------------------------------

        text = transcript[:max_length]


        return {
            "success": True,
            "language": "my",
            "text": text,
            "source_text": transcript,
            "engine": self.engine
        }


narrator = BurmeseNarrator()
