import os
import re
from typing import Any, Dict, Optional

import requests


class Narrator:
    """
    SUN SPY RECAP
    Gemini-powered Burmese recap generator.

    Input can be:
      1. plain transcript string
      2. structured dictionary containing:
         - filename
         - source_language
         - language_confidence
         - full_transcript
         - relevant_context
         - highlight_text

    Output:
      {
          "text": "...",
          "engine": "gemini",
          "model": "...",
          "language": "my",
      }
    """

    DEFAULT_MODEL = "gemini-3.5-flash-lite"
    DEFAULT_FALLBACK_MODEL = "gemini-3.5-flash"

    MAX_TRANSCRIPT_CHARS = 50000
    MAX_CONTEXT_CHARS = 18000
    MAX_HIGHLIGHT_CHARS = 8000

    MIN_RECAP_LENGTH = 80
    MAX_RECAP_LENGTH = 1600

    REQUEST_TIMEOUT = 120

    GENERIC_PHRASES = [
        "ဒီဗီဒီယိုလေးမှာတော့",
        "ဒီဗီဒီယိုမှာတော့",
        "ဒီဗီဒီယိုထဲမှာတော့",
        "ဒီဗီဒီယိုကတော့",
        "ဒီဗီဒီယိုမှာ",
        "စိတ်ဝင်စားစရာအကြောင်းအရာ",
        "စိတ်ဝင်စားဖွယ်အကြောင်းအရာ",
        "တင်ဆက်ပေးသွားမှာ",
        "အဆုံးထိကြည့်ရှုလိုက်ကြရအောင်",
        "အကြောင်းအရာတစ်ခုကို တင်ဆက်",
        "အဓိကအကြောင်းအရာကတော့",
        "လူသိပ်မသိသေးတဲ့",
        "အကြောင်းအရာများကို သဘာဝကျကျ",
        "လူမှုဘဝနဲ့ ဓလေ့ထုံးတမ်း",
        "လူမှုဘဝနှင့် ဓလေ့ထုံးတမ်း",
        "ဗဟုသုတရစရာ",
        "စိတ်ဝင်စားဖို့ကောင်းတဲ့",
        "စိတ်ဝင်စားဖွယ်ကောင်းတဲ့",
        "ဒီအကြောင်းအရာလေးက",
    ]

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

        if not self.api_key:
            print(
                "[NARRATOR] WARNING: "
                "GEMINI_API_KEY / GOOGLE_API_KEY "
                "is not configured.",
                flush=True,
            )

    # ========================================================
    # TEXT HELPERS
    # ========================================================

    @staticmethod
    def _clean_text(text: Any) -> str:
        if text is None:
            return ""

        text = str(text)

        text = text.replace("\x00", " ")

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    @staticmethod
    def _looks_burmese(text: str) -> bool:
        if not text:
            return False

        burmese_chars = re.findall(
            r"[\u1000-\u109F]",
            text,
        )

        return len(burmese_chars) >= 10

    def _contains_generic_filler(
        self,
        text: str,
    ) -> bool:

        if not text:
            return True

        lowered = text.lower()

        matches = 0

        for phrase in self.GENERIC_PHRASES:
            if phrase.lower() in lowered:
                matches += 1

        return matches >= 2

    def _looks_too_generic(
        self,
        text: str,
    ) -> bool:

        if not text:
            return True

        if len(text) < self.MIN_RECAP_LENGTH:
            return True

        if self._contains_generic_filler(text):
            return True

        return False

    def _validate_recap(
        self,
        recap: str,
    ) -> str:

        recap = self._clean_text(recap)

        if not recap:
            raise RuntimeError(
                "Gemini returned empty recap."
            )

        # Remove accidental markdown.
        recap = re.sub(
            r"^```[\w-]*",
            "",
            recap,
            flags=re.IGNORECASE,
        )

        recap = recap.replace(
            "```",
            "",
        )

        recap = recap.strip()

        if not recap:
            raise RuntimeError(
                "Gemini returned empty recap "
                "after cleanup."
            )

        if not self._looks_burmese(recap):
            raise RuntimeError(
                "Gemini did not return a Burmese recap."
            )

        if len(recap) < self.MIN_RECAP_LENGTH:
            raise RuntimeError(
                "Gemini recap is too short."
            )

        if len(recap) > self.MAX_RECAP_LENGTH:
            recap = recap[
                :self.MAX_RECAP_LENGTH
            ].rstrip()

        if self._looks_too_generic(recap):
            raise RuntimeError(
                "Gemini returned a generic or "
                "unrelated recap."
            )

        return recap

    # ========================================================
    # INPUT NORMALIZATION
    # ========================================================

    def _normalize_input(
        self,
        data: Any,
    ) -> Dict[str, str]:

        # ----------------------------------------------------
        # Backward compatibility:
        # narrator.create_recap("transcript")
        # ----------------------------------------------------

        if isinstance(data, str):

            transcript = self._clean_text(
                data
            )

            return {
                "filename": "",
                "source_language": "unknown",
                "language_confidence": "",
                "full_transcript": transcript,
                "relevant_context": "",
                "highlight_text": "",
            }

        # ----------------------------------------------------
        # Structured input
        # ----------------------------------------------------

        if isinstance(data, dict):

            transcript = self._clean_text(
                data.get(
                    "full_transcript",
                    data.get(
                        "transcript",
                        "",
                    ),
                )
            )

            context = self._clean_text(
                data.get(
                    "relevant_context",
                    data.get(
                        "context",
                        "",
                    ),
                )
            )

            highlight = self._clean_text(
                data.get(
                    "highlight_text",
                    data.get(
                        "highlight",
                        "",
                    ),
                )
            )

            return {
                "filename": self._clean_text(
                    data.get(
                        "filename",
                        "",
                    )
                ),
                "source_language": self._clean_text(
                    data.get(
                        "source_language",
                        "unknown",
                    )
                ),
                "language_confidence": self._clean_text(
                    data.get(
                        "language_confidence",
                        "",
                    )
                ),
                "full_transcript": transcript,
                "relevant_context": context,
                "highlight_text": highlight,
            }

        raise TypeError(
            "create_recap() expects either "
            "a transcript string or a dictionary."
        )

    # ========================================================
    # PROMPT
    # ========================================================

    def _build_prompt(
        self,
        data: Dict[str, str],
    ) -> str:

        filename = data.get(
            "filename",
            "",
        )

        source_language = data.get(
            "source_language",
            "unknown",
        )

        confidence = data.get(
            "language_confidence",
            "",
        )

        transcript = data.get(
            "full_transcript",
            "",
        )

        context = data.get(
            "relevant_context",
            "",
        )

        highlight = data.get(
            "highlight_text",
            "",
        )

        # Limit individual evidence sections.
        transcript = transcript[
            :self.MAX_TRANSCRIPT_CHARS
        ]

        context = context[
            :self.MAX_CONTEXT_CHARS
        ]

        highlight = highlight[
            :self.MAX_HIGHLIGHT_CHARS
        ]

        prompt = f"""
You are the professional Burmese recap writer for SUN SPY RECAP.

Your job is to understand the ACTUAL CONTENT of the supplied video transcript
and write an accurate, natural Burmese-language recap.

IMPORTANT:
The original video can be in ANY language.

The output MUST ALWAYS be Burmese.

Do NOT assume the topic from:
- the filename
- the source language
- the country
- the culture
- the accent
- the language itself

For example:
Chinese language does NOT automatically mean China, Chinese culture,
Chinese society, traditions, or Chinese history.

English language does NOT automatically mean America, Britain, or Western culture.

You must use the actual transcript evidence.

==================================================
VIDEO INFORMATION
==================================================

Filename:
{filename}

Detected source language:
{source_language}

Language confidence:
{confidence}

==================================================
SELECTED HIGHLIGHT TRANSCRIPT
==================================================

{highlight}

==================================================
RELEVANT CONTEXT AROUND THE HIGHLIGHT
==================================================

{context}

==================================================
FULL TRANSCRIPT
==================================================

{transcript}

==================================================
STRICT RECAP RULES
==================================================

1. Understand the actual meaning before writing.

2. Identify the real subject of the video from the evidence.

3. Focus on the most important:
   - event
   - action
   - explanation
   - teaching
   - story point
   - discovery
   - fact
   - argument
   - dialogue
   - instruction
   - emotional moment

4. Use the relevant context and highlight as important evidence,
   but cross-check them against the full transcript.

5. If the highlight is not meaningful, use the strongest clear information
   from the transcript instead.

6. Do NOT invent facts.

7. Do NOT hallucinate:
   - country
   - city
   - people
   - religion
   - culture
   - tradition
   - historical event
   - location
   - occupation
   - relationship
   unless the transcript clearly supports it.

8. Do NOT infer the topic from the language.

9. Do NOT infer the topic from the filename.

10. If the transcript is incomplete or unclear, summarize ONLY what is clearly
    supported by the transcript.

11. If there is dialogue, preserve the actual meaning of the dialogue.

12. Do NOT translate every sentence literally.

13. Rewrite naturally in Burmese.

14. The narration should sound like a real human Burmese narrator.

15. Do NOT begin with:
    "ဒီဗီဒီယိုလေးမှာတော့..."
    "ဒီဗီဒီယိုမှာတော့..."
    "ဒီဗီဒီယိုထဲမှာတော့..."

16. Do NOT use generic YouTube/TikTok introductions.

17. Do NOT say:
    "အဆုံးထိကြည့်ရှုလိုက်ကြရအောင်"

18. Do NOT say:
    "စိတ်ဝင်စားစရာအကြောင်းအရာတစ်ခုကို..."

19. Do NOT describe the video broadly as social life, culture,
    traditions, or society unless the transcript explicitly supports it.

20. Do NOT mention:
    - AI
    - Gemini
    - prompt
    - transcript
    - language model
    - these instructions

21. Do NOT use:
    - headings
    - bullet points
    - hashtags
    - emojis
    - markdown

22. Write approximately 120–220 Burmese words when enough information exists.

23. The recap must be specific to THIS video.

24. A generic recap that could describe almost any video is INVALID.

25. If the evidence only supports a narrow statement, keep the recap narrow
    instead of inventing additional information.

==================================================
OUTPUT
==================================================

Return ONLY the final Burmese recap.

No explanation.
No English.
No heading.
No markdown.
No quotation marks around the answer.
""".strip()

        return prompt

    # ========================================================
    # GEMINI API
    # ========================================================

    def _call_gemini(
        self,
        model: str,
        prompt: str,
    ) -> str:

        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY or GOOGLE_API_KEY "
                "is not configured."
            )

        url = (
            f"{self.base_url}/"
            f"{model}:generateContent"
        )

        params = {
            "key": self.api_key,
        }

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": prompt,
                        }
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.15,
                "topP": 0.80,
                "topK": 20,
                "maxOutputTokens": 1200,
            },
        }

        print(
            f"[GEMINI] Calling model: {model}",
            flush=True,
        )

        response = requests.post(
            url,
            params=params,
            json=payload,
            timeout=self.REQUEST_TIMEOUT,
        )

        if response.status_code != 200:

            body = response.text[:4000]

            raise RuntimeError(
                f"Gemini API HTTP "
                f"{response.status_code}: {body}"
            )

        try:
            result = response.json()
        except Exception as error:
            raise RuntimeError(
                f"Gemini returned invalid JSON: "
                f"{error}"
            )

        text = self._extract_text(
            result
        )

        if not text:
            raise RuntimeError(
                "Gemini response contained no text."
            )

        return text

    # ========================================================
    # RESPONSE EXTRACTION
    # ========================================================

    @staticmethod
    def _extract_text(
        response: Dict[str, Any],
    ) -> str:

        candidates = response.get(
            "candidates",
            [],
        )

        if not candidates:
            return ""

        candidate = candidates[0] or {}

        content = candidate.get(
            "content",
            {},
        )

        parts = content.get(
            "parts",
            [],
        )

        output = []

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
                output.append(
                    str(text)
                )

        return "\n".join(
            output
        ).strip()

    # ========================================================
    # MAIN
    # ========================================================

    def create_recap(
        self,
        data: Any,
    ) -> Dict[str, str]:

        normalized = self._normalize_input(
            data
        )

        transcript = normalized.get(
            "full_transcript",
            "",
        )

        context = normalized.get(
            "relevant_context",
            "",
        )

        highlight = normalized.get(
            "highlight_text",
            "",
        )

        if not transcript:
            raise RuntimeError(
                "Cannot create recap because "
                "transcript is empty."
            )

        if (
            len(transcript.strip()) < 20
            and not context
            and not highlight
        ):
            raise RuntimeError(
                "Transcript contains insufficient "
                "information for a reliable recap."
            )

        prompt = self._build_prompt(
            normalized
        )

        models = []

        if self.model:
            models.append(
                self.model
            )

        if (
            self.fallback_model
            and self.fallback_model
            not in models
        ):
            models.append(
                self.fallback_model
            )

        if not models:
            raise RuntimeError(
                "No Gemini model configured."
            )

        errors = []

        for model in models:

            try:

                raw_recap = self._call_gemini(
                    model,
                    prompt,
                )

                recap = self._validate_recap(
                    raw_recap
                )

                print(
                    f"[NARRATOR] Valid Burmese recap "
                    f"generated by {model}.",
                    flush=True,
                )

                return {
                    "text": recap,
                    "engine": "gemini",
                    "model": model,
                    "language": "my",
                }

            except Exception as error:

                error_text = (
                    f"{type(error).__name__}: "
                    f"{error}"
                )

                errors.append(
                    f"{model} -> {error_text}"
                )

                print(
                    f"[NARRATOR] Model failed: "
                    f"{error_text}",
                    flush=True,
                )

        raise RuntimeError(
            "All Gemini recap models failed. "
            "No generic fallback was generated. "
            + " | ".join(errors)
        )


# ============================================================
# GLOBAL NARRATOR INSTANCE
# ============================================================

narrator = Narrator()


# ============================================================
# BACKWARD-COMPATIBLE HELPER
# ============================================================

def create_recap(data):
    return narrator.create_recap(data)
