import time
from pathlib import Path

from faster_whisper import WhisperModel


class TranscriptionEngine:
    """
    SUN SPY RECAP multilingual speech-to-text engine.

    Goals:
    - Detect the original language automatically.
    - Keep the original language transcript.
    - Do NOT force Burmese on non-Burmese videos.
    - Produce cleaner transcripts for Gemini recap generation.
    """

    def __init__(self, model_size="small"):
        self.model_size = model_size
        self.model = None

    def load_model(self):
        if self.model is None:
            start_time = time.time()

            print(
                f"[WHISPER] Loading model: {self.model_size}",
                flush=True,
            )

            self.model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8",
                cpu_threads=2,
                num_workers=1,
            )

            elapsed = time.time() - start_time

            print(
                f"[WHISPER] Model loaded in {elapsed:.1f}s",
                flush=True,
            )

        return self.model

    def _run_transcription(
        self,
        model,
        path,
        language=None,
    ):
        print(
            f"[WHISPER] Transcription language: "
            f"{language or 'AUTO'}",
            flush=True,
        )

        segments, info = model.transcribe(
            str(path),

            # Better multilingual accuracy than beam_size=1.
            beam_size=5,

            best_of=5,

            temperature=0,

            language=language,

            # Helps remove long silent sections.
            vad_filter=True,

            # Keep context between nearby speech segments.
            condition_on_previous_text=True,

            word_timestamps=False,

            compression_ratio_threshold=2.4,

            log_prob_threshold=-1.0,

            no_speech_threshold=0.6,

            # Prevent hallucinated text during silence.
            hallucination_silence_threshold=2.0,
        )

        result_segments = []
        texts = []

        count = 0

        for segment in segments:
            text = str(segment.text or "").strip()

            if not text:
                continue

            count += 1

            result_segments.append(
                {
                    "start": float(segment.start),
                    "end": float(segment.end),
                    "text": text,
                }
            )

            texts.append(text)

            print(
                f"[WHISPER] Segment {count}: "
                f"{segment.start:.1f}s - "
                f"{segment.end:.1f}s | "
                f"{text[:160]}",
                flush=True,
            )

        transcript = " ".join(texts).strip()

        detected_language = getattr(
            info,
            "language",
            "unknown",
        )

        language_probability = float(
            getattr(
                info,
                "language_probability",
                0.0,
            )
        )

        return {
            "success": bool(transcript),
            "language": detected_language,
            "language_probability": language_probability,
            "text": transcript,
            "segments": result_segments,
            "engine": "faster-whisper",
            "model": self.model_size,
            "segment_count": count,
        }

    def _looks_burmese(self, text):
        text = str(text or "")

        if not text:
            return False

        burmese_chars = sum(
            1
            for char in text
            if "\u1000" <= char <= "\u109f"
        )

        total_letters = sum(
            1
            for char in text
            if char.isalpha()
        )

        if total_letters == 0:
            return False

        ratio = burmese_chars / total_letters

        return (
            burmese_chars >= 3
            and ratio >= 0.25
        )

    def _looks_very_poor(self, result):
        """
        Detect obviously bad Whisper output.

        We do not automatically translate it.
        We only use this to decide whether another
        transcription pass may be useful.
        """

        text = str(
            result.get("text", "")
        ).strip()

        if len(text) < 10:
            return True

        segments = result.get(
            "segments",
            [],
        )

        if not segments:
            return True

        probability = float(
            result.get(
                "language_probability",
                0.0,
            )
        )

        # Very low language confidence.
        if probability < 0.35:
            return True

        return False

    def transcribe(self, audio_path):
        path = Path(audio_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Audio file not found: {path}"
            )

        file_size = path.stat().st_size

        print(
            f"[WHISPER] Audio file: {path}",
            flush=True,
        )

        print(
            f"[WHISPER] Audio size: "
            f"{file_size / 1024 / 1024:.2f} MB",
            flush=True,
        )

        model = self.load_model()

        start_time = time.time()

        print(
            "[WHISPER] Starting automatic "
            "language detection...",
            flush=True,
        )

        # --------------------------------------------------
        # PASS 1
        # Automatic multilingual transcription
        # --------------------------------------------------

        result = self._run_transcription(
            model,
            path,
            language=None,
        )

        detected_language = result["language"]
        probability = result[
            "language_probability"
        ]

        print(
            f"[WHISPER] Auto detected language: "
            f"{detected_language}",
            flush=True,
        )

        print(
            f"[WHISPER] Language probability: "
            f"{probability:.3f}",
            flush=True,
        )

        # --------------------------------------------------
        # IMPORTANT:
        # Never force Burmese transcription for Chinese,
        # Japanese, Korean, etc.
        #
        # The old implementation could retry with
        # language='my' when Whisper detected certain
        # languages. That can damage multilingual
        # transcripts.
        # --------------------------------------------------

        if self._looks_very_poor(result):
            print(
                "[WHISPER] Transcript confidence is low.",
                flush=True,
            )

            print(
                "[WHISPER] Running one accuracy retry...",
                flush=True,
            )

            retry_result = self._run_transcription(
                model,
                path,
                language=(
                    detected_language
                    if detected_language
                    and detected_language != "unknown"
                    else None
                ),
            )

            retry_text = str(
                retry_result.get("text", "")
            ).strip()

            original_text = str(
                result.get("text", "")
            ).strip()

            # Use retry only when it is clearly better.
            if (
                len(retry_text) > len(original_text)
                and not self._looks_very_poor(
                    retry_result
                )
            ):
                print(
                    "[WHISPER] Accuracy retry selected.",
                    flush=True,
                )

                result = retry_result

            else:
                print(
                    "[WHISPER] Keeping original "
                    "automatic transcript.",
                    flush=True,
                )

        elapsed = time.time() - start_time

        if not result["text"]:
            print(
                "[WHISPER] No speech detected.",
                flush=True,
            )

            return {
                "success": False,
                "language": result["language"],
                "language_probability": (
                    result[
                        "language_probability"
                    ]
                ),
                "text": "",
                "segments": [],
                "engine": "faster-whisper",
                "model": self.model_size,
                "error": "No speech was detected.",
            }

        print(
            f"[WHISPER] Transcription completed "
            f"in {elapsed:.1f}s",
            flush=True,
        )

        print(
            f"[WHISPER] Final language: "
            f"{result['language']}",
            flush=True,
        )

        print(
            f"[WHISPER] Final probability: "
            f"{result['language_probability']:.3f}",
            flush=True,
        )

        print(
            f"[WHISPER] Segments: "
            f"{len(result['segments'])}",
            flush=True,
        )

        print(
            "[WHISPER] Transcript preview:",
            flush=True,
        )

        print(
            result["text"][:1200],
            flush=True,
        )

        return {
            "success": True,
            "language": result["language"],
            "language_probability": (
                result[
                    "language_probability"
                ]
            ),
            "text": result["text"],
            "segments": result["segments"],
            "engine": "faster-whisper",
            "model": self.model_size,
        }


# Global transcription engine.
#
# "small" gives noticeably better multilingual
# transcription than "tiny", especially for
# Chinese/Japanese/other non-Burmese speech.
#
# If Render RAM is insufficient, change this to "tiny".
transcription_engine = TranscriptionEngine(
    "small"
)
