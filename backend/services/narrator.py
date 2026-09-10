import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests


class Narrator:
    """
    SUN SPY RECAP
    Multimodal Gemini narrator.

    Evidence:
      1. Actual video
      2. Whisper transcript
      3. Selected transcript context

    Output:
      Natural Burmese recap only.
    """

    DEFAULT_MODEL = "gemini-3.5-flash-lite"
    DEFAULT_FALLBACK_MODEL = "gemini-3.5-flash"

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    UPLOAD_URL = "https://generativelanguage.googleapis.com/upload/v1beta/files"

    REQUEST_TIMEOUT = 180
    PROCESS_TIMEOUT = 300
    POLL_SECONDS = 5

    MAX_TRANSCRIPT_CHARS = 30000
    MAX_CONTEXT_CHARS = 12000
    MAX_HIGHLIGHT_CHARS = 6000

    MIN_RECAP_LENGTH = 40
    MAX_RECAP_LENGTH = 1800

    GENERIC_PHRASES = [
        "SUN SPY RECAP မှ တင်ဆက်ပေးလိုက်ပါတယ်",
        "ဒီဗီဒီယိုလေးမှာတော့",
        "ဒီဗီဒီယိုမှာတော့",
        "ဒီဗီဒီယိုထဲမှာတော့",
        "ဒီဗီဒီယိုကတော့",
        "စိတ်ဝင်စားစရာအကြောင်းအရာ",
        "စိတ်ဝင်စားဖွယ်အကြောင်းအရာ",
        "အဆုံးထိကြည့်ရှုလိုက်ကြရအောင်",
        "တင်ဆက်ပေးသွားမှာ",
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

        if not self.api_key:
            print(
                "[NARRATOR] ERROR: GEMINI_API_KEY is missing.",
                flush=True,
            )

        print(
            f"[NARRATOR] Engine: gemini-multimodal",
            flush=True,
        )
        print(
            f"[NARRATOR] Model: {self.model}",
            flush=True,
        )
        print(
            f"[NARRATOR] Fallback: {self.fallback_model}",
            flush=True,
        )

    # ---------------------------------------------------------
    # BASIC HELPERS
    # ---------------------------------------------------------

    @staticmethod
    def _clean_text(value: Any) -> str:
        if value is None:
            return ""

        text = str(value)

        text = text.replace("\x00", " ")
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    @staticmethod
    def _looks_burmese(text: str) -> bool:
        burmese_chars = re.findall(
            r"[\u1000-\u109F]",
            text,
        )

        return len(burmese_chars) >= 10

    def _contains_generic(self, text: str) -> bool:
        lowered = text.lower()

        hits = 0

        for phrase in self.GENERIC_PHRASES:
            if phrase.lower() in lowered:
                hits += 1

        return hits >= 1

    def _validate_recap(self, text: str) -> str:
        text = self._clean_text(text)

        text = re.sub(
            r"```(?:text|burmese|my)?",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = text.replace("```", "").strip()

        if not text:
            raise RuntimeError(
                "Gemini returned empty recap."
            )

        if not self._looks_burmese(text):
            raise RuntimeError(
                "Gemini did not return Burmese."
            )

        if len(text) < self.MIN_RECAP_LENGTH:
            raise RuntimeError(
                "Gemini recap is too short."
            )

        if self._contains_generic(text):
            raise RuntimeError(
                "Gemini returned generic introduction."
            )

        if len(text) > self.MAX_RECAP_LENGTH:
            text = text[:self.MAX_RECAP_LENGTH].rstrip()

        return text

    def _normalize_input(self, data: Any) -> Dict[str, str]:

        if isinstance(data, str):
            return {
                "filename": "",
                "source_language": "unknown",
                "language_confidence": "",
                "full_transcript": self._clean_text(data),
                "relevant_context": "",
                "highlight_text": "",
                "video_path": "",
            }

        if not isinstance(data, dict):
            raise TypeError(
                "create_recap expects dict or string."
            )

        return {
            "filename": self._clean_text(
                data.get("filename", "")
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

            "full_transcript": self._clean_text(
                data.get(
                    "full_transcript",
                    data.get(
                        "transcript",
                        "",
                    ),
                )
            ),

            "relevant_context": self._clean_text(
                data.get(
                    "relevant_context",
                    data.get(
                        "context",
                        "",
                    ),
                )
            ),

            "highlight_text": self._clean_text(
                data.get(
                    "highlight_text",
                    data.get(
                        "highlight",
                        "",
                    ),
                )
            ),

            "video_path": self._clean_text(
                data.get(
                    "video_path",
                    "",
                )
            ),
        }

    # ---------------------------------------------------------
    # GEMINI FILE API
    # ---------------------------------------------------------

    def _upload_video(
        self,
        video_path: str,
    ) -> Dict[str, Any]:

        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured."
            )

        path = Path(video_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Video not found: {path}"
            )

        file_size = path.stat().st_size

        mime_type = "video/mp4"

        print(
            "================================================",
            flush=True,
        )

        print(
            "[GEMINI VIDEO] Uploading actual video...",
            flush=True,
        )

        print(
            f"[GEMINI VIDEO] File: {path.name}",
            flush=True,
        )

        print(
            f"[GEMINI VIDEO] Size: "
            f"{file_size / 1024 / 1024:.2f} MB",
            flush=True,
        )

        # -----------------------------------------------------
        # STEP 1
        # Start resumable upload
        # -----------------------------------------------------

        headers = {
            "x-goog-api-key": self.api_key,
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(
                file_size
            ),
            "X-Goog-Upload-Header-Content-Type": mime_type,
            "Content-Type": "application/json",
        }

        metadata = {
            "file": {
                "display_name": path.name,
            }
        }

        response = requests.post(
            self.UPLOAD_URL,
            headers=headers,
            json=metadata,
            timeout=60,
        )

        if response.status_code not in (200, 201):
            raise RuntimeError(
                "Gemini upload initialization failed: "
                f"HTTP {response.status_code}: "
                f"{response.text[:3000]}"
            )

        upload_url = (
            response.headers.get(
                "x-goog-upload-url"
            )
            or response.headers.get(
                "X-Goog-Upload-URL"
            )
        )

        if not upload_url:
            raise RuntimeError(
                "Gemini did not return upload URL."
            )

        print(
            "[GEMINI VIDEO] Resumable upload session created.",
            flush=True,
        )

        # -----------------------------------------------------
        # STEP 2
        # Upload and finalize
        # -----------------------------------------------------

        with open(path, "rb") as file_handle:

            upload_headers = {
                "Content-Length": str(file_size),
                "X-Goog-Upload-Offset": "0",
                "X-Goog-Upload-Command": (
                    "upload, finalize"
                ),
            }

            upload_response = requests.post(
                upload_url,
                headers=upload_headers,
                data=file_handle,
                timeout=self.REQUEST_TIMEOUT,
            )

        if upload_response.status_code not in (200, 201):
            raise RuntimeError(
                "Gemini video upload failed: "
                f"HTTP {upload_response.status_code}: "
                f"{upload_response.text[:3000]}"
            )

        try:
            result = upload_response.json()
        except Exception as exc:
            raise RuntimeError(
                f"Invalid Gemini upload response: {exc}"
            )

        file_info = result.get(
            "file",
            result,
        )

        file_name = file_info.get("name")
        file_uri = file_info.get("uri")

        file_mime = (
            file_info.get("mimeType")
            or mime_type
        )

        state = file_info.get("state")

        if not file_uri:
            raise RuntimeError(
                "Gemini upload returned no file URI."
            )

        print(
            f"[GEMINI VIDEO] File name: {file_name}",
            flush=True,
        )

        print(
            f"[GEMINI VIDEO] File URI: {file_uri}",
            flush=True,
        )

        print(
            f"[GEMINI VIDEO] Initial state: {state}",
            flush=True,
        )

        return {
            "name": file_name,
            "uri": file_uri,
            "mime_type": file_mime,
            "state": state,
        }

    def _get_file(
        self,
        file_name: str,
    ) -> Dict[str, Any]:

        url = (
            f"{self.BASE_URL}/{file_name}"
        )

        response = requests.get(
            url,
            params={
                "key": self.api_key,
            },
            timeout=30,
        )

        if response.status_code != 200:
            raise RuntimeError(
                "Gemini file status failed: "
                f"HTTP {response.status_code}: "
                f"{response.text[:2000]}"
            )

        data = response.json()

        return data.get(
            "file",
            data,
        )

    def _wait_for_video(
        self,
        file_name: str,
    ) -> Dict[str, Any]:

        if not file_name:
            raise RuntimeError(
                "Gemini file name is missing."
            )

        started = time.time()

        print(
            "[GEMINI VIDEO] Waiting for processing...",
            flush=True,
        )

        while True:

            elapsed = time.time() - started

            if elapsed > self.PROCESS_TIMEOUT:
                raise RuntimeError(
                    "Gemini video processing timed out."
                )

            info = self._get_file(
                file_name
            )

            state = info.get("state")

            print(
                f"[GEMINI VIDEO] State: {state}",
                flush=True,
            )

            if state == "ACTIVE":
                print(
                    "[GEMINI VIDEO] Video is ACTIVE and ready.",
                    flush=True,
                )

                return info

            if state == "FAILED":
                raise RuntimeError(
                    "Gemini failed to process video."
                )

            time.sleep(
                self.POLL_SECONDS
            )

    def _delete_video(
        self,
        file_name: Optional[str],
    ):

        if not file_name:
            return

        try:

            url = (
                f"{self.BASE_URL}/{file_name}"
            )

            response = requests.delete(
                url,
                params={
                    "key": self.api_key,
                },
                timeout=30,
            )

            print(
                "[GEMINI VIDEO] Temporary file deleted "
                f"(HTTP {response.status_code}).",
                flush=True,
            )

        except Exception as exc:

            print(
                "[GEMINI VIDEO] Cleanup warning: "
                f"{exc}",
                flush=True,
            )

    # ---------------------------------------------------------
    # PROMPT
    # ---------------------------------------------------------

    def _build_prompt(
        self,
        data: Dict[str, str],
    ) -> str:

        transcript = (
            data["full_transcript"]
            [:self.MAX_TRANSCRIPT_CHARS]
        )

        context = (
            data["relevant_context"]
            [:self.MAX_CONTEXT_CHARS]
        )

        highlight = (
            data["highlight_text"]
            [:self.MAX_HIGHLIGHT_CHARS]
        )

        return f"""
You are the professional AI narrator for SUN SPY RECAP.

Your job is to create ONE accurate Burmese recap of the
ACTUAL uploaded video.

IMPORTANT:
You have access to the REAL VIDEO FILE.

You MUST watch/analyze the actual video.

Do not rely only on the transcript.

==================================================
VIDEO EVIDENCE
==================================================

Analyze:

- what people are doing
- what people are saying
- who is speaking
- important objects
- locations that are actually visible
- actions
- expressions
- important visual events
- religious objects
- Buddha statues
- lamps
- ceremonies
- signs or text visible in the video
- important sounds
- dialogue
- narration
- sequence of events

Only state things that are actually supported by
the video or clearly supported by the speech.

==================================================
WHISPER TRANSCRIPT
==================================================

The following transcript was generated automatically.

It may contain recognition errors.

Therefore:

VIDEO > CLEAR SPEECH > TRANSCRIPT

If the transcript conflicts with clearly audible speech
or visible video, trust the actual video.

Transcript:

{transcript}

==================================================
SELECTED CONTEXT
==================================================

{context}

==================================================
SELECTED HIGHLIGHT
==================================================

{highlight}

==================================================
SOURCE LANGUAGE
==================================================

Detected language:
{data["source_language"]}

Confidence:
{data["language_confidence"]}

The source language does NOT determine the topic.

==================================================
CRITICAL ANTI-HALLUCINATION RULES
==================================================

DO NOT invent:

- names
- locations
- countries
- dates
- historical facts
- relationships
- religious teachings
- motives
- events
- emotions

unless the video clearly supports them.

Do not interpret ordinary conversation as violence,
threats, pleading, recording, fighting, or abuse unless
those things are actually clear from the video.

Do not turn uncertain Whisper words into facts.

If speech is unclear, describe the clearly visible events.

If visuals are unclear, use clearly audible speech.

If both are clear, combine them.

==================================================
BURMESE OUTPUT
==================================================

Write natural spoken Burmese.

The recap should sound like a human Burmese narrator,
not an AI disclaimer.

Do NOT begin with:

"ဒီဗီဒီယိုလေးမှာတော့"
"ဒီဗီဒီယိုမှာတော့"
"ဒီဗီဒီယိုထဲမှာတော့"
"SUN SPY RECAP မှ တင်ဆက်ပေးလိုက်ပါတယ်"

Do NOT say:

"အဆုံးထိကြည့်ရှုလိုက်ကြရအောင်"

Do NOT explain your analysis.

Do NOT mention Whisper.

Do NOT mention Gemini.

Do NOT mention AI.

Do NOT say that information is insufficient unless
the actual video genuinely contains almost no usable
information.

Instead, describe what is actually happening.

Length:
approximately 100–220 Burmese words.

Return ONLY the Burmese narration.

No title.
No headings.
No bullets.
No hashtags.
No emojis.
No markdown.
""".strip()

    # ---------------------------------------------------------
    # GEMINI GENERATE
    # ---------------------------------------------------------

    @staticmethod
    def _extract_text(
        data: Dict[str, Any],
    ) -> str:

        candidates = data.get(
            "candidates",
            [],
        )

        if not candidates:
            return ""

        content = candidates[0].get(
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

    def _call_gemini(
        self,
        model: str,
        prompt: str,
        video: Dict[str, Any],
    ) -> str:

        url = (
            f"{self.BASE_URL}/models/"
            f"{model}:generateContent"
        )

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": prompt,
                        },
                        {
                            "file_data": {
                                "mime_type": (
                                    video["mime_type"]
                                ),
                                "file_uri": (
                                    video["uri"]
                                ),
                            }
                        },
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
            "================================================",
            flush=True,
        )

        print(
            "[GEMINI] Sending ACTUAL VIDEO + transcript...",
            flush=True,
        )

        print(
            f"[GEMINI] Model: {model}",
            flush=True,
        )

        response = requests.post(
            url,
            params={
                "key": self.api_key,
            },
            json=payload,
            timeout=self.REQUEST_TIMEOUT,
        )

        if response.status_code != 200:

            raise RuntimeError(
                f"Gemini API HTTP "
                f"{response.status_code}: "
                f"{response.text[:5000]}"
            )

        data = response.json()

        text = self._extract_text(
            data
        )

        if not text:

            raise RuntimeError(
                "Gemini returned no text."
            )

        return text

    # ---------------------------------------------------------
    # PUBLIC
    # ---------------------------------------------------------

    def create_recap(
        self,
        data: Any,
    ) -> Dict[str, str]:

        normalized = self._normalize_input(
            data
        )

        video_path = normalized[
            "video_path"
        ]

        if not video_path:
            raise RuntimeError(
                "video_path is required for "
                "multimodal recap."
            )

        if not Path(video_path).exists():
            raise RuntimeError(
                f"Video does not exist: "
                f"{video_path}"
            )

        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured."
            )

        prompt = self._build_prompt(
            normalized
        )

        models = list(
            dict.fromkeys(
                [
                    self.model,
                    self.fallback_model,
                ]
            )
        )

        uploaded = None
        errors = []

        try:

            # Upload actual video
            uploaded = self._upload_video(
                video_path
            )

            # Wait until Gemini can analyze it
            active_file = self._wait_for_video(
                uploaded["name"]
            )

            # Refresh URI if available
            uploaded["uri"] = (
                active_file.get("uri")
                or uploaded["uri"]
            )

            uploaded["mime_type"] = (
                active_file.get("mimeType")
                or uploaded["mime_type"]
            )

            for model in models:

                try:

                    raw = self._call_gemini(
                        model=model,
                        prompt=prompt,
                        video=uploaded,
                    )

                    recap = self._validate_recap(
                        raw
                    )

                    print(
                        "================================================",
                        flush=True,
                    )

                    print(
                        "[NARRATOR] FINAL BURMESE RECAP:",
                        flush=True,
                    )

                    print(
                        recap,
                        flush=True,
                    )

                    print(
                        "================================================",
                        flush=True,
                    )

                    return {
                        "text": recap,
                        "engine": (
                            "gemini-multimodal"
                        ),
                        "model": model,
                        "language": "my",
                    }

                except Exception as exc:

                    message = (
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    )

                    errors.append(
                        f"{model} -> {message}"
                    )

                    print(
                        f"[NARRATOR] {model} failed: "
                        f"{message}",
                        flush=True,
                    )

        finally:

            if uploaded:

                self._delete_video(
                    uploaded.get(
                        "name"
                    )
                )

        raise RuntimeError(
            "All Gemini multimodal recap attempts "
            "failed. "
            + " | ".join(errors)
        )


narrator = Narrator()


def create_recap(data):
    return narrator.create_recap(data)
