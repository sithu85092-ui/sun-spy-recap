import json
import os
import re
import urllib.error
import urllib.request


class Narrator:

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model = os.getenv(
            "GEMINI_MODEL",
            "gemini-2.5-flash-lite",
        ).strip()

        self.endpoint = (
            "https://generativelanguage.googleapis.com"
            f"/v1beta/models/{self.model}:generateContent"
        )

    # ---------------------------------------------------------
    # Burmese detection
    # ---------------------------------------------------------

    def _has_burmese(self, text):
        text = str(text or "")

        burmese_chars = sum(
            1
            for char in text
            if "\u1000" <= char <= "\u109f"
        )

        return burmese_chars >= 3

    # ---------------------------------------------------------
    # Clean Gemini response
    # ---------------------------------------------------------

    def _clean_text(self, text):
        text = str(text or "").strip()

        # Remove markdown formatting
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
        text = re.sub(r"\*(.*?)\*", r"\1", text)
        text = re.sub(r"__(.*?)__", r"\1", text)
        text = re.sub(r"_(.*?)_", r"\1", text)

        # Remove code fences
        text = text.replace("```text", "")
        text = text.replace("```", "")

        # Remove common AI prefixes
        text = re.sub(
            r"^(မြန်မာဘာသာဖြင့်|အနှစ်ချုပ်|အကျဉ်းချုပ်|"
            r"Recap|Summary)\s*[:：-]?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    # ---------------------------------------------------------
    # Build Gemini prompt
    # ---------------------------------------------------------

    def _build_prompt(self, transcript):
        return f"""
You are the Burmese narrator for SUN SPY RECAP.

The source video can be in ANY language.

Your task:

1. Understand the meaning of the source transcript.
2. Identify the most important, interesting, useful, surprising,
   emotional, educational, or entertaining information.
3. Create a SHORT Burmese-language recap suitable for a short video.
4. The final narration MUST be natural Myanmar Burmese.
5. Do NOT translate word-for-word.
6. Do NOT mention that you are an AI.
7. Do NOT mention the source language.
8. Do NOT use markdown.
9. Do NOT use emojis.
10. Do NOT use English unless absolutely necessary for a proper name.
11. Write like a natural human Burmese video narrator.
12. Keep the narration concise and engaging.
13. Start with an interesting hook.
14. Explain the key point clearly.
15. End naturally without saying "ကျေးဇူးတင်ပါတယ်" or
    "ဗီဒီယိုကို Like and Follow လုပ်ပါ" unless it is genuinely
    appropriate.

IMPORTANT:
Return ONLY the final Burmese narration.
Do not provide analysis.
Do not provide explanations.
Do not provide multiple versions.

SOURCE TRANSCRIPT:

{transcript}
""".strip()

    # ---------------------------------------------------------
    # Gemini API request
    # ---------------------------------------------------------

    def _call_gemini(self, prompt):

        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured."
            )

        url = (
            f"{self.endpoint}"
            f"?key={self.api_key}"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "topP": 0.9,
                "maxOutputTokens": 500,
            }
        }

        data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:

            with urllib.request.urlopen(
                request,
                timeout=90,
            ) as response:

                raw = response.read().decode(
                    "utf-8"
                )

                return json.loads(raw)

        except urllib.error.HTTPError as error:

            try:
                error_body = error.read().decode(
                    "utf-8",
                    errors="replace",
                )
            except Exception:
                error_body = str(error)

            print(
                f"[GEMINI API ERROR] HTTP {error.code}: "
                f"{error_body}",
                flush=True,
            )

            raise RuntimeError(
                f"Gemini API HTTP {error.code}: "
                f"{error_body}"
            )

        except urllib.error.URLError as error:

            print(
                f"[GEMINI NETWORK ERROR] {error}",
                flush=True,
            )

            raise RuntimeError(
                f"Gemini API network error: {error}"
            )

        except Exception as error:

            print(
                f"[GEMINI REQUEST ERROR] {error}",
                flush=True,
            )

            raise RuntimeError(
                f"Gemini API request failed: {error}"
            )

    # ---------------------------------------------------------
    # Extract generated text
    # ---------------------------------------------------------

    def _extract_text(self, response):

        candidates = response.get(
            "candidates",
            [],
        )

        if not candidates:
            raise RuntimeError(
                "Gemini returned no candidates."
            )

        candidate = candidates[0]

        content = candidate.get(
            "content",
            {},
        )

        parts = content.get(
            "parts",
            [],
        )

        texts = []

        for part in parts:

            text = part.get(
                "text",
                "",
            )

            if text:
                texts.append(text)

        result = "\n".join(texts).strip()

        if not result:
            raise RuntimeError(
                "Gemini returned empty narration."
            )

        return result

    # ---------------------------------------------------------
    # Validate Burmese narration
    # ---------------------------------------------------------

    def _validate_burmese(self, text):

        text = self._clean_text(text)

        if not text:
            raise RuntimeError(
                "Gemini narration is empty."
            )

        if not self._has_burmese(text):

            raise RuntimeError(
                "Gemini did not return Burmese narration."
            )

        # Prevent extremely long output
        if len(text) > 3000:
            text = text[:3000].rstrip()

        return text

    # ---------------------------------------------------------
    # Main recap generator
    # ---------------------------------------------------------

    def create_recap(self, transcript):

        transcript = str(
            transcript or ""
        ).strip()

        if not transcript:
            raise ValueError(
                "Transcript is empty."
            )

        print(
            "[NARRATOR] Creating Burmese recap "
            "with Gemini...",
            flush=True,
        )

        print(
            f"[NARRATOR] Gemini model: "
            f"{self.model}",
            flush=True,
        )

        # -----------------------------------------------------
        # Gemini path
        # -----------------------------------------------------

        if self.api_key:

            try:

                prompt = self._build_prompt(
                    transcript
                )

                response = self._call_gemini(
                    prompt
                )

                generated = self._extract_text(
                    response
                )

                recap = self._validate_burmese(
                    generated
                )

                print(
                    "[NARRATOR] Gemini Burmese recap "
                    "created successfully.",
                    flush=True,
                )

                print(
                    f"[NARRATOR] Recap: "
                    f"{recap[:500]}",
                    flush=True,
                )

                return {
                    "success": True,
                    "language": "my",
                    "text": recap,
                    "source_text": transcript,
                    "engine": "gemini",
                    "model": self.model,
                }

            except Exception as error:

                print(
                    f"[NARRATOR] Gemini failed: "
                    f"{error}",
                    flush=True,
                )

                raise RuntimeError(
                    "Could not create Burmese recap "
                    "with Gemini API. "
                    f"{error}"
                )

        # -----------------------------------------------------
        # Local fallback
        #
        # This only works when the transcript itself
        # is already Burmese.
        # -----------------------------------------------------

        print(
            "[NARRATOR] GEMINI_API_KEY not found. "
            "Checking local Burmese fallback...",
            flush=True,
        )

        if self._has_burmese(transcript):

            recap = self._clean_text(
                transcript
            )

            print(
                "[NARRATOR] Using local Burmese "
                "transcript fallback.",
                flush=True,
            )

            return {
                "success": True,
                "language": "my",
                "text": recap,
                "source_text": transcript,
                "engine": "local-burmese",
                "model": "none",
            }

        raise RuntimeError(
            "Could not create Burmese recap. "
            "Set GEMINI_API_KEY for automatic "
            "translation and summarization from "
            "other languages."
        )


# -------------------------------------------------------------
# Global narrator instance
# -------------------------------------------------------------

narrator = Narrator()
