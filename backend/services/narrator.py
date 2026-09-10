import json
import os
import re
import urllib.error
import urllib.request


class Narrator:
    """
    SUN SPY RECAP Burmese AI narrator.

    Pipeline:
        Original video
            ↓
        Whisper transcript
            ↓
        Gemini
            ↓
        Factual Burmese recap
            ↓
        TTS

    IMPORTANT:
    Gemini must summarize the actual transcript.
    It must NOT invent a generic description.
    """

    DEFAULT_MODEL = "gemini-3.5-flash-lite"
    DEFAULT_FALLBACK_MODEL = "gemini-3.5-flash"

    MAX_TRANSCRIPT_CHARS = 50000

    MIN_RECAP_LENGTH = 80
    MAX_RECAP_LENGTH = 1600

    def __init__(self):
        self.api_key = (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )

        self.model = (
            os.getenv("GEMINI_MODEL")
            or self.DEFAULT_MODEL
        )

        self.fallback_model = (
            os.getenv("GEMINI_FALLBACK_MODEL")
            or self.DEFAULT_FALLBACK_MODEL
        )

        self.base_url = (
            "https://generativelanguage.googleapis.com"
            "/v1beta/models"
        )

    # ---------------------------------------------------------
    # Utility
    # ---------------------------------------------------------

    def _clean_text(self, text):
        if not text:
            return ""

        text = str(text)

        # Remove markdown.
        text = re.sub(
            r"```.*?```",
            "",
            text,
            flags=re.DOTALL,
        )

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
            r"^#+\s*",
            "",
            text,
            flags=re.MULTILINE,
        )

        # Remove common AI prefixes.
        text = re.sub(
            r"^(Recap|Summary|Burmese Recap|မြန်မာအကျဉ်းချုပ်)\s*:\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        # Remove excessive whitespace.
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

    def _looks_burmese(self, text):
        if not text:
            return False

        burmese = sum(
            1
            for c in text
            if "\u1000" <= c <= "\u109f"
        )

        letters = sum(
            1
            for c in text
            if c.isalpha()
        )

        if letters == 0:
            return False

        return (
            burmese >= 10
            and (burmese / letters) >= 0.25
        )

    def _contains_generic_filler(self, text):
        """
        Detect the type of generic recap that previously
        appeared in SUN SPY RECAP.
        """

        if not text:
            return True

        generic_patterns = [
            "ဒီဗီဒီယိုလေးမှာတော့",
            "ဒီဗီဒီယိုမှာတော့",
            "ဒီဗီဒီယိုထဲမှာတော့",
            "စိတ်ဝင်စားစရာအကြောင်းအရာ",
            "စိတ်ဝင်စားဖွယ်အကြောင်းအရာ",
            "တင်ဆက်ပေးသွားမှာ",
            "အဆုံးထိကြည့်ရှုလိုက်ကြရအောင်",
            "အကြောင်းအရာတစ်ခုကို တင်ဆက်",
            "အဓိကအကြောင်းအရာကတော့",
            "လူသိပ်မသိသေးတဲ့",
            "အကြောင်းအရာများကို သဘာဝကျကျ",
            "လူမှုဘဝနဲ့ ဓလေ့ထုံးတမ်း",
        ]

        lowered = text.lower()

        matches = 0

        for phrase in generic_patterns:
            if phrase.lower() in lowered:
                matches += 1

        return matches >= 2

    def _looks_too_generic(self, text):
        """
        Additional protection against a recap that sounds
        plausible but contains almost no actual information.
        """

        if not text:
            return True

        sentences = re.split(
            r"[။!?]\s*",
            text,
        )

        sentences = [
            s.strip()
            for s in sentences
            if s.strip()
        ]

        if len(sentences) < 2:
            return True

        generic_words = [
            "ဗီဒီယို",
            "အကြောင်းအရာ",
            "တင်ဆက်",
            "စိတ်ဝင်စား",
            "ကြည့်ရှု",
            "ဖော်ပြ",
        ]

        generic_count = sum(
            1
            for word in generic_words
            if word in text
        )

        # If the text is short and mostly generic words,
        # reject it.
        if len(text) < 180 and generic_count >= 3:
            return True

        return False

    def _validate_recap(self, recap, transcript):
        """
        Validate Gemini output before sending it to TTS.
        """

        recap = self._clean_text(recap)

        if not recap:
            return False, "empty recap"

        if not self._looks_burmese(recap):
            return False, "not Burmese"

        if len(recap) < self.MIN_RECAP_LENGTH:
            return False, "recap too short"

        if len(recap) > self.MAX_RECAP_LENGTH:
            return False, "recap too long"

        if self._contains_generic_filler(recap):
            return False, "generic filler detected"

        if self._looks_too_generic(recap):
            return False, "too generic"

        # Reject obvious model meta-talk.
        forbidden_meta = [
            "AI အနေနဲ့",
            "AI အဖြစ်",
            "ဘာသာပြန်",
            "ကျွန်ုပ်သည်",
            "I cannot",
            "I can't",
            "As an AI",
            "language model",
        ]

        for phrase in forbidden_meta:
            if phrase.lower() in recap.lower():
                return False, "AI/meta text detected"

        return True, "valid"

    # ---------------------------------------------------------
    # Prompt
    # ---------------------------------------------------------

    def _build_prompt(self, transcript):
        return f"""
You are the professional recap writer for SUN SPY RECAP.

Your task is extremely important:

Read the ORIGINAL VIDEO TRANSCRIPT below and create a SHORT,
ACCURATE and NATURAL BURMESE recap.

The original video may be in ANY language:
Chinese, English, Japanese, Korean, Thai, Hindi, Burmese,
or another language.

You must UNDERSTAND the actual meaning of the transcript first.

DO NOT translate every sentence word-for-word.

Instead:
1. Identify the actual topic.
2. Identify the important events, facts, teachings, actions,
   explanations or story points.
3. Remove repetition and unimportant speech.
4. Write a coherent Burmese narration.
5. Make the recap sound like a real human narrator.
6. Keep only information supported by the transcript.

VERY IMPORTANT FACTUAL RULES:

- NEVER invent information.
- NEVER guess the country, culture, religion, people,
  location, event or subject unless the transcript supports it.
- NEVER say something is about China merely because the
  language is Chinese.
- NEVER describe the video as "social life", "culture",
  "daily life" or any other broad topic unless the transcript
  actually says so.
- If the transcript is unclear, summarize only what is clear.
- If a name is unclear, do not invent a name.
- If a number is unclear, do not invent a number.
- If the transcript contains dialogue, preserve the meaning
  of the dialogue rather than inventing new dialogue.
- Do not use information merely because it sounds plausible.

DO NOT start with generic phrases such as:

"ဒီဗီဒီယိုလေးမှာတော့..."
"ဒီဗီဒီယိုမှာတော့..."
"စိတ်ဝင်စားစရာအကြောင်းအရာတစ်ခု..."
"တင်ဆက်ပေးသွားမှာ..."
"အဆုံးထိကြည့်ရှုလိုက်ကြရအောင်..."

Start directly with the REAL subject of the video.

STYLE:

- Natural Burmese.
- Easy to understand.
- Interesting but factual.
- Suitable for TikTok / YouTube Shorts narration.
- No emojis.
- No hashtags.
- No markdown.
- No headings.
- No bullet points.
- No English explanation.
- No mention of AI.
- No mention of this prompt.
- No mention of "transcript".

LENGTH:

Write approximately 120–220 Burmese words.

STRUCTURE:

Opening:
Immediately reveal the actual subject or most interesting point.

Middle:
Explain the most important information/events.

Ending:
Finish with the main lesson, conclusion or important point
ONLY if the transcript supports one.

SOURCE TRANSCRIPT:

---------------- BEGIN TRANSCRIPT ----------------

{transcript}

----------------- END TRANSCRIPT -----------------

Return ONLY the final Burmese recap.
"""

    # ---------------------------------------------------------
    # Gemini API
    # ---------------------------------------------------------

    def _call_gemini(self, model, prompt):
        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured."
            )

        url = (
            f"{self.base_url}/{model}"
            f":generateContent?key={self.api_key}"
        )

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": prompt
                        }
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.8,
                "topK": 20,
                "maxOutputTokens": 1200,
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
                timeout=120,
            ) as response:

                raw = response.read().decode(
                    "utf-8"
                )

                return json.loads(raw)

        except urllib.error.HTTPError as error:
            body = ""

            try:
                body = error.read().decode(
                    "utf-8",
                    errors="replace",
                )
            except Exception:
                pass

            raise RuntimeError(
                f"Gemini HTTP {error.code}: {body[:2000]}"
            )

        except urllib.error.URLError as error:
            raise RuntimeError(
                f"Gemini connection error: {error}"
            )

        except Exception as error:
            raise RuntimeError(
                f"Gemini request failed: {error}"
            )

    def _extract_text(self, response):
        try:
            candidates = response.get(
                "candidates",
                [],
            )

            if not candidates:
                raise RuntimeError(
                    "Gemini returned no candidates."
                )

            parts = (
                candidates[0]
                .get("content", {})
                .get("parts", [])
            )

            texts = []

            for part in parts:
                text = part.get("text")

                if text:
                    texts.append(text)

            result = "\n".join(texts).strip()

            if not result:
                raise RuntimeError(
                    "Gemini returned empty text."
                )

            return result

        except RuntimeError:
            raise

        except Exception as error:
            raise RuntimeError(
                f"Could not parse Gemini response: {error}"
            )

    # ---------------------------------------------------------
    # Main recap
    # ---------------------------------------------------------

    def create_recap(self, transcript):
        transcript = str(
            transcript or ""
        ).strip()

        if not transcript:
            raise RuntimeError(
                "Cannot create recap: transcript is empty."
            )

        print(
            "[NARRATOR] Creating factual Burmese recap...",
            flush=True,
        )

        print(
            f"[NARRATOR] Transcript length: "
            f"{len(transcript)} characters",
            flush=True,
        )

        # Prevent extremely large requests.
        if len(transcript) > self.MAX_TRANSCRIPT_CHARS:
            print(
                "[NARRATOR] Transcript is very long; "
                "truncating for recap generation.",
                flush=True,
            )

            transcript_for_ai = transcript[
                : self.MAX_TRANSCRIPT_CHARS
            ]

        else:
            transcript_for_ai = transcript

        prompt = self._build_prompt(
            transcript_for_ai
        )

        models = []

        if self.model:
            models.append(self.model)

        if (
            self.fallback_model
            and self.fallback_model
            != self.model
        ):
            models.append(self.fallback_model)

        errors = []

        for model in models:
            try:
                print(
                    f"[NARRATOR] Trying Gemini model: "
                    f"{model}",
                    flush=True,
                )

                response = self._call_gemini(
                    model,
                    prompt,
                )

                recap = self._extract_text(
                    response
                )

                valid, reason = (
                    self._validate_recap(
                        recap,
                        transcript_for_ai,
                    )
                )

                if not valid:
                    print(
                        f"[NARRATOR] Model {model} "
                        f"produced invalid recap: "
                        f"{reason}",
                        flush=True,
                    )

                    errors.append(
                        f"{model}: {reason}"
                    )

                    continue

                print(
                    "[NARRATOR] Burmese recap "
                    "created successfully.",
                    flush=True,
                )

                print(
                    f"[NARRATOR] Recap: {recap}",
                    flush=True,
                )

                return {
                    "text": recap,
                    "engine": "gemini",
                    "model": model,
                    "language": "my",
                }

            except Exception as error:
                message = str(error)

                print(
                    f"[NARRATOR] {model} failed: "
                    f"{message}",
                    flush=True,
                )

                errors.append(
                    f"{model}: {message}"
                )

        # -----------------------------------------------------
        # IMPORTANT:
        # Do NOT return fake/generic text.
        #
        # If Gemini fails, fail the job instead.
        # This prevents the old generic recap from being
        # presented as if it were a real AI recap.
        # -----------------------------------------------------

        raise RuntimeError(
            "All Gemini recap models failed. "
            + " | ".join(errors)
        )


# Global narrator instance.
narrator = Narrator()
