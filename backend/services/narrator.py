import re


class BurmeseNarrator:

    def __init__(self):

        self.engine = (
            "extractive-local"
        )

    def create_recap(
        self,
        transcript,
        max_length=700,
    ):

        text = (
            transcript or ""
        ).strip()

        if not text:

            return {
                "success": False,
                "language": "my",
                "text": "",
                "error": (
                    "Transcript is empty"
                ),
                "engine": self.engine,
            }

        sentences = re.split(
            r"(?<=[.!?။])\s+",
            text,
        )

        sentences = [
            sentence.strip()
            for sentence in sentences
            if sentence.strip()
        ]

        selected = sentences[:8]

        recap = " ".join(
            selected
        )

        if len(recap) > max_length:

            recap = (
                recap[:max_length]
                .rsplit(" ", 1)[0]
                .strip()
                + "…"
            )

        has_burmese = any(
            "\u1000" <= char <= "\u109f"
            for char in recap
        )

        return {
            "success": True,
            "language": (
                "my"
                if has_burmese
                else "auto"
            ),
            "text": recap,
            "source_text": text,
            "engine": self.engine,
        }


narrator = BurmeseNarrator()
