import time
from pathlib import Path

from faster_whisper import WhisperModel


class TranscriptionEngine:
    """
    SUN SPY RECAP multilingual speech-to-text engine.

    Optimized for Render Free / low-memory CPU environments.

    Goals:
    - Automatically detect the original language.
    - Keep the original-language transcript.
    - Never force Burmese transcription on non-Burmese videos.
    - Avoid excessive RAM usage.
    - Provide reliable transcript data for Gemini.
    """

    def __init__(self, model_size="tiny"):
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

            # Memory-friendly settings for Render Free.
            beam_size=1,
            best_of=1,
            temperature=0,

            language=language,

            # Remove long silent sections.
            vad_filter=True,

            # Keep nearby speech context.
            condition_on_previous_text=True,

            word_timestamps=False,

            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            no_speech_threshold=0.6,

            # Avoid hallucination during silence.
            hallucination_silence_threshold=2.0,
        )

        result_segments = []
        texts = []

        count = 0

        for segment in segments:
            text = str(
                segment.text or ""
            ).strip()

            if not text:
                continue

            count += 1

            result_segments.append(
                {
                    "start": float(
                        segment.start
                    ),
                    "end": float(
                        segment.end
                    ),
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

        transcript = " ".join(
            texts
        ).strip()

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

    def _looks_very_poor(self, result):
        """
        Detect obviously bad Whisper output.

        This does NOT translate or force Burmese.
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

        # ==================================================
        # PASS 1
        # Automatic multilingual transcription
        # ==================================================

        result = self._run_transcription(
            model,
            path,
            language=None,
        )

        detected_language = result[
            "language"
        ]

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

        # ==================================================
        # OPTIONAL RETRY
        # ==================================================
        #
        # Only retry if the first transcript is clearly poor.
        # Never force Burmese on another language.
        #

        if self._looks_very_poor(result):

            print(
                "[WHISPER] Transcript confidence is low.",
                flush=True,
            )

            # For low-memory environments, avoid an expensive
            # second pass unless we have a detected language.
            if (
                detected_language
                and detected_language != "unknown"
            ):

                print(
                    "[WHISPER] Running one "
                    "language-specific retry...",
                    flush=True,
                )

                retry_result = (
                    self._run_transcription(
                        model,
                        path,
                        language=detected_language,
                    )
                )

                retry_text = str(
                    retry_result.get(
                        "text",
                        "",
                    )
                ).strip()

                original_text = str(
                    result.get(
                        "text",
                        "",
                    )
                ).strip()

                if (
                    len(retry_text)
                    > len(original_text)
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

        elapsed = (
            time.time()
            - start_time
        )

        if not result.get("text"):

            print(
                "[WHISPER] No speech detected.",
                flush=True,
            )

            return {
                "success": False,
                "language": result.get(
                    "language",
                    "unknown",
                ),
                "language_probability": result.get(
                    "language_probability",
                    0.0,
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


# ============================================================
# GLOBAL TRANSCRIPTION ENGINE
# ============================================================
#
# tiny is intentionally used for Render Free because
# Whisper small can exceed the available RAM during model
# loading.
#
# Once the complete pipeline works reliably, the model can
# be upgraded if more RAM is available.
#

transcription_engine = TranscriptionEngine(
    "tiny"
)
