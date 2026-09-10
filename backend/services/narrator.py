import json
import os
import re
import urllib.error
import urllib.request


class Narrator:
    """
    SUN SPY RECAP Burmese AI Narrator

    Flow:
        Any-language transcript
                ↓
        Gemini understands content
                ↓
        Natural Burmese recap
                ↓
        Burmese TTS

    IMPORTANT:
    This service NEVER creates a fake generic recap when Gemini fails.
    """

    def __init__(self):
        self.api_key = os.getenv(
            "GEMINI_API_KEY",
            "",
        ).strip()

        # Current stable Gemini model.
        # Can be overridden with GEMINI_MODEL.
        self.model = os.getenv(
            "GEMINI_MODEL",
            "gemini-2.5-flash",
        ).strip()

        # Optional fallback model.
        self.fallback_model = os.getenv(
            "GEMINI_FALLBACK_MODEL",
            "gemini-2.5-flash-lite",
        ).strip()

        self.timeout = int(
            os.getenv(
                "GEMINI_TIMEOUT",
                "120",
            )
        )

    # =========================================================
    # BURMESE DETECTION
    # =========================================================

    def _has_burmese(self, text):
        text = str(text or "")

        burmese_chars = sum(
            1
            for char in text
            if "\u1000" <= char <= "\u109f"
        )

        return burmese_chars >= 5

    # =========================================================
    # GENERIC FALLBACK DETECTION
    # =========================================================

    def _looks_generic(self, text):
        """
        Detect old/fake generic narration such as:

        "ဒီဗီဒီယိုလေးမှာတော့ လူသိပ်မသိသေးတဲ့..."
        """

        text = str(text or "").strip()

        if not text:
            return True

        generic_patterns = [
            "ဒီဗီဒီယိုလေးမှာတော့",
            "ဒီဗီဒီယိုမှာတော့",
            "လူသိပ်မသိသေးတဲ့ စိတ်ဝင်စားစရာ အကြောင်းအရာ",
            "စိတ်ဝင်စားစရာ အကြောင်းအရာတစ်ခုကို",
            "အစကနေ အဆုံးထိ အသေအချာ ကြည့်ရှု",
            "ဗီဒီယိုလေးကို အဆုံးထိ",
            "ဒီနေ့မှာတော့ လူသိပ်မသိသေးတဲ့",
            "အကြောင်းအရာတစ်ခုကို တင်ဆက်",
        ]

        lower_text = text.lower()

        matches = 0

        for pattern in generic_patterns:
            if pattern.lower() in lower_text:
                matches += 1

        # If a known generic phrase exists, reject it.
        if matches >= 1:
            return True

        # Very short recap is suspicious.
        if len(text) < 80:
            return True

        return False

    # =========================================================
    # CLEAN GEMINI RESPONSE
    # =========================================================

    def _clean_text(self, text):
        text = str(text or "").strip()

        # Remove markdown
        text = re.sub(
            r"\*\*(.*?)\*\*",
            r"\1",
            text,
        )

        text = re.sub(
            r"\*(.*?)\*",
            r"\1",
            text,
        )

        text = re.sub(
            r"__(.*?)__",
            r"\1",
            text,
        )

        text = re.sub(
            r"_(.*?)_",
            r"\1",
            text,
        )

        # Remove code fences
        text = text.replace(
            "```text",
            "",
        )

        text = text.replace(
            "```",
            "",
        )

        # Remove common AI prefixes
        text = re.sub(
            r"^(မြန်မာဘာသာဖြင့်|"
            r"မြန်မာဘာသာနဲ့|"
            r"အနှစ်ချုပ်|"
            r"အကျဉ်းချုပ်|"
            r"Recap|"
            r"Summary)"
            r"\s*[:：-]?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        # Normalize whitespace
        text = re.sub(
            r"[ \t]+",
            " ",
            text,
        )

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text,
        )

        return text.strip()

    # =========================================================
    # BUILD GEMINI PROMPT
    # =========================================================

    def _build_prompt(self, transcript):
        return f"""
You are the main Burmese recap writer for SUN SPY RECAP.

The source video can be spoken in ANY language.

Your job is to deeply understand the transcript and create a
short, accurate, natural Burmese narration for a social-media
video recap.

STRICT RULES:

1. Understand the actual meaning of the transcript.
2. Identify the MAIN topic of the video.
3. Identify the most important facts, events, explanation,
   lesson, story, or message.
4. Write the final narration ONLY in natural Myanmar Burmese.
5. Do NOT translate word-for-word.
6. Do NOT invent facts.
7. Do NOT add facts that are not supported by the transcript.
8. Do NOT use a generic introduction.
9. Do NOT write:
   "ဒီဗီဒီယိုလေးမှာတော့ လူသိပ်မသိသေးတဲ့..."
10. Do NOT write:
   "စိတ်ဝင်စားစရာ အကြောင်းအရာတစ်ခုကို..."
11. The first sentence must reveal the actual topic or create
    a topic-specific hook.
12. Make the narration sound like a real Burmese narrator.
13. Keep it concise but informative.
14. Prefer approximately 120-220 Burmese words.
15. Do not use markdown.
16. Do not use emojis.
17. Do not mention AI.
18. Do not mention Gemini.
19. Do not mention the source language.
20. Do not say "watch until the end".
21. Do not add Like/Follow requests unless the source content
    itself contains them.
22. If the source is a story, explain the actual story.
23. If the source is educational, explain the actual lesson.
24. If the source is religious/Dhamma content, preserve the
    meaning faithfully and do not invent doctrine.
25. If the source contains names, places, numbers, or important
    terminology, preserve them when relevant.
26. The result MUST clearly relate to the supplied transcript.

QUALITY TEST:

A person reading only your Burmese recap should be able to
understand what the original video is actually about.

Return ONLY the final Burmese narration.

SOURCE TRANSCRIPT:
--------------------
{transcript}
--------------------
""".strip()

    # =========================================================
    # GEMINI REQUEST
    # =========================================================

    def _call_gemini(
        self,
        prompt,
        model,
    ):
        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured."
            )

        endpoint = (
            "https://generativelanguage.googleapis.com"
            f"/v1beta/models/{model}:generateContent"
        )

        url = (
            f"{endpoint}"
            f"?key={self.api_key}"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt,
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.45,
                "topP": 0.9,
                "maxOutputTokens": 700,
            },
        }

        data = json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8")

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
                timeout=self.timeout,
            ) as response:

                raw = response.read().decode(
                    "utf-8"
                )

                return json.loads(raw)

        except urllib.error.HTTPError as error:

            try:
                error_body = (
                    error.read()
                    .decode(
                        "utf-8",
                        errors="replace",
                    )
                )
            except Exception:
                error_body = str(error)

            print(
                f"[GEMINI API ERROR] "
                f"model={model} "
                f"HTTP {error.code}: "
                f"{error_body}",
                flush=True,
            )

            raise RuntimeError(
                f"Gemini API HTTP {error.code}: "
                f"{error_body}"
            )

        except urllib.error.URLError as error:

            print(
                f"[GEMINI NETWORK ERROR] "
                f"{error}",
                flush=True,
            )

            raise RuntimeError(
                f"Gemini network error: {error}"
            )

        except Exception as error:

            print(
                f"[GEMINI REQUEST ERROR] "
                f"{error}",
                flush=True,
            )

            raise RuntimeError(
                f"Gemini request failed: {error}"
            )

    # =========================================================
    # EXTRACT GEMINI TEXT
    # =========================================================

    def _extract_text(self, response):

        if not isinstance(
            response,
            dict,
        ):
            raise RuntimeError(
                "Invalid Gemini response."
            )

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

            if not isinstance(
                part,
                dict,
            ):
                continue

            text = part.get(
                "text",
                "",
            )

            if text:
                texts.append(
                    str(text)
                )

        result = "\n".join(
            texts
        ).strip()

        if not result:
            raise RuntimeError(
                "Gemini returned empty narration."
            )

        return result

    # =========================================================
    # VALIDATE BURMESE
    # =========================================================

    def _validate_burmese(
        self,
        text,
        transcript,
    ):

        text = self._clean_text(
            text
        )

        if not text:
            raise RuntimeError(
                "Gemini narration is empty."
            )

        if not self._has_burmese(
            text
        ):
            raise RuntimeError(
                "Gemini did not return Burmese narration."
            )

        # Prevent extremely long output.
        if len(text) > 3500:
            text = text[:3500].rstrip()

        # Reject the old generic fallback.
        if self._looks_generic(
            text
        ):
            raise RuntimeError(
                "Gemini returned a generic narration "
                "instead of a transcript-based recap."
            )

        # Make sure recap isn't suspiciously close
        # to an empty/trivial result.
        if len(text) < 80:
            raise RuntimeError(
                "Gemini recap is too short."
            )

        return text

    # =========================================================
    # CREATE RECAP
    # =========================================================

    def create_recap(
        self,
        transcript,
    ):

        transcript = str(
            transcript or ""
        ).strip()

        if not transcript:
            raise ValueError(
                "Transcript is empty."
            )

        if len(transcript) < 20:
            raise ValueError(
                "Transcript is too short to create a reliable recap."
            )

        print(
            "[NARRATOR] Creating Burmese recap "
            "from transcript...",
            flush=True,
        )

        print(
            f"[NARRATOR] Primary model: "
            f"{self.model}",
            flush=True,
        )

        if self.fallback_model:
            print(
                f"[NARRATOR] Fallback model: "
                f"{self.fallback_model}",
                flush=True,
            )

        # =====================================================
        # GEMINI REQUIRED FOR AUTOMATIC RECAP
        # =====================================================

        if not self.api_key:

            raise RuntimeError(
                "GEMINI_API_KEY is not configured. "
                "SUN SPY RECAP requires Gemini to create "
                "an accurate Burmese recap from any language."
            )

        prompt = self._build_prompt(
            transcript
        )

        models_to_try = []

        if self.model:
            models_to_try.append(
                self.model
            )

        if (
            self.fallback_model
            and self.fallback_model
            not in models_to_try
        ):
            models_to_try.append(
                self.fallback_model
            )

        last_error = None

        for model in models_to_try:

            try:

                print(
                    f"[NARRATOR] Trying Gemini "
                    f"model: {model}",
                    flush=True,
                )

                response = self._call_gemini(
                    prompt,
                    model,
                )

                generated = self._extract_text(
                    response
                )

                recap = self._validate_burmese(
                    generated,
                    transcript,
                )

                print(
                    "[NARRATOR] Burmese recap "
                    "created successfully.",
                    flush=True,
                )

                print(
                    f"[NARRATOR] Recap: "
                    f"{recap[:1000]}",
                    flush=True,
                )

                return {
                    "success": True,
                    "language": "my",
                    "text": recap,
                    "source_text": transcript,
                    "engine": "gemini",
                    "model": model,
                }

            except Exception as error:

                last_error = error

                print(
                    f"[NARRATOR] Model "
                    f"{model} failed: "
                    f"{error}",
                    flush=True,
                )

                continue

        # =====================================================
        # IMPORTANT:
        # NEVER RETURN A FAKE GENERIC RECAP
        # =====================================================

        raise RuntimeError(
            "Could not create Burmese recap "
            "with Gemini API. "
            f"Models tried: {', '.join(models_to_try)}. "
            f"Last error: {last_error}"
        )


# =============================================================
# GLOBAL NARRATOR INSTANCE
# =============================================================

narrator = Narrator()
