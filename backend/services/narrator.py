import os
import re
import json
import urllib.request
import urllib.error


class BurmeseNarrator:

    def __init__(self):

        self.engine = "ai-burmese"

        self.api_key = os.getenv(
            "OPENAI_API_KEY"
        )

        self.model = os.getenv(
            "NARRATOR_MODEL",
            "gpt-4o-mini"
        )

    # ==========================================
    # OPENAI REQUEST
    # ==========================================

    def _call_ai(self, transcript):

        if not self.api_key:
            return None

        prompt = f"""
You are the Burmese narrator and recap writer
for SUN SPY RECAP.

The input transcript may be in ANY language.

Your job:

1. Understand the meaning of the transcript.
2. Identify the most important and interesting information.
3. Create a short, natural Burmese recap.
4. The FINAL OUTPUT MUST BE IN BURMESE.
5. NEVER return Chinese, English, Japanese, Korean,
   or the original transcript language.
6. Do not translate word-for-word.
7. Make it sound like a real human Burmese narrator.
8. Keep the recap engaging and easy to understand.
9. Do not add information that is not supported
   by the transcript.
10. Do not use markdown.
11. Do not use emojis.
12. Return ONLY the Burmese narration text.

The narration will be used for Myanmar TTS,
so write natural spoken Burmese.

Transcript:
{transcript}
"""

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a professional Burmese "
                        "documentary narrator."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.4,
            "max_tokens": 700,
        }

        data = json.dumps(
            payload
        ).encode("utf-8")

        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": (
                    f"Bearer {self.api_key}"
                ),
            },
            method="POST",
        )

        try:

            with urllib.request.urlopen(
                request,
                timeout=90,
            ) as response:

                result = json.loads(
                    response.read().decode(
                        "utf-8"
                    )
                )

            choices = result.get(
                "choices",
                []
            )

            if not choices:
                return None

            message = choices[0].get(
                "message",
                {}
            )

            content = message.get(
                "content",
                ""
            )

            if isinstance(
                content,
                list,
            ):

                content = "".join(
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict)
                )

            return str(
                content or ""
            ).strip()

        except urllib.error.HTTPError as error:

            try:
                body = error.read().decode(
                    "utf-8",
                    errors="ignore",
                )
            except Exception:
                body = ""

            print(
                f"[NARRATOR AI ERROR] "
                f"HTTP {error.code}: {body}",
                flush=True,
            )

            return None

        except Exception as error:

            print(
                f"[NARRATOR AI ERROR] "
                f"{error}",
                flush=True,
            )

            return None

    # ==========================================
    # BURMESE CHECK
    # ==========================================

    def _has_burmese(self, text):

        return any(
            "\u1000" <= char <= "\u109f"
            for char in str(text or "")
        )

    # ==========================================
    # CLEAN AI OUTPUT
    # ==========================================

    def _clean_text(self, text):

        text = str(
            text or ""
        ).strip()

        # Remove markdown
        text = re.sub(
            r"\*\*|\*|__|_",
            "",
            text,
        )

        text = re.sub(
            r"^```.*?$",
            "",
            text,
            flags=re.MULTILINE,
        )

        text = text.replace(
            "```",
            "",
        )

        # Remove accidental labels
        text = re.sub(
            r"^(Burmese|မြန်မာ|Narration|Recap)\s*:\s*",
            "",
            text,
            flags=re.I,
        )

        # Remove excessive whitespace
        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        return text

    # ==========================================
    # LOCAL FALLBACK
    # ==========================================

    def _local_fallback(self, transcript):

        """
        This fallback is NOT a real translation engine.

        It only returns Burmese text when the transcript
        is already Burmese.

        For Chinese/English/etc. an AI API is required
        for reliable Burmese translation.
        """

        text = str(
            transcript or ""
        ).strip()

        if not text:
            return ""

        if self._has_burmese(text):

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

            return " ".join(
                selected
            ).strip()

        return ""

    # ==========================================
    # MAIN RECAP
    # ==========================================

    def create_recap(
        self,
        transcript,
        max_length=700,
    ):

        text = str(
            transcript or ""
        ).strip()

        if not text:

            return {
                "success": False,
                "language": "my",
                "text": "",
                "error": "Transcript is empty",
                "engine": self.engine,
            }

        print(
            "[NARRATOR] Creating Burmese recap...",
            flush=True,
        )

        # ==========================================
        # 1. AI BURMESE RECAP
        # ==========================================

        recap = self._call_ai(
            text
        )

        if recap:

            recap = self._clean_text(
                recap
            )

            # IMPORTANT:
            # Never accept non-Burmese AI output.
            if not self._has_burmese(
                recap
            ):

                print(
                    "[NARRATOR] AI returned "
                    "non-Burmese text. "
                    "Rejecting output.",
                    flush=True,
                )

                recap = ""

        # ==========================================
        # 2. LOCAL BURMESE FALLBACK
        # ==========================================

        if not recap:

            recap = self._local_fallback(
                text
            )

        # ==========================================
        # 3. FINAL VALIDATION
        # ==========================================

        if not recap:

            return {
                "success": False,
                "language": "my",
                "text": "",
                "source_text": text,
                "error": (
                    "Could not create Burmese recap. "
                    "Set OPENAI_API_KEY for automatic "
                    "translation from other languages."
                ),
                "engine": self.engine,
            }

        # ==========================================
        # 4. LENGTH LIMIT
        # ==========================================

        if len(recap) > max_length:

            shortened = (
                recap[:max_length]
                .rsplit(" ", 1)[0]
                .strip()
            )

            if shortened:

                recap = (
                    shortened
                    + "…"
                )

            else:

                recap = (
                    recap[:max_length]
                    + "…"
                )

        print(
            "[NARRATOR] Burmese recap ready.",
            flush=True,
        )

        print(
            f"[NARRATOR] {recap}",
            flush=True,
        )

        return {
            "success": True,
            "language": "my",
            "text": recap,
            "source_text": text,
            "engine": self.engine,
        }


narrator = BurmeseNarrator()
