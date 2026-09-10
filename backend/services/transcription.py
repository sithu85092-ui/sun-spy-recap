import time
from pathlib import Path

from faster_whisper import WhisperModel


class TranscriptionEngine:

    def __init__(self, model_size="tiny"):
        self.model_size = model_size
        self.model = None

    def load_model(self):

        if self.model is None:

            start_time = time.time()

            print(
                "[WHISPER] Loading model...",
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
                f"[WHISPER] Model loaded "
                f"in {elapsed:.1f}s",
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

            beam_size=1,

            best_of=1,

            temperature=0,

            language=language,

            vad_filter=True,

            condition_on_previous_text=False,

            word_timestamps=False,

            compression_ratio_threshold=2.4,

            log_prob_threshold=-1.0,

            no_speech_threshold=0.6,
        )

        result_segments = []
        texts = []

        count = 0

        for segment in segments:

            text = segment.text.strip()

            if not text:
                continue

            count += 1

            result_segments.append({
                "start": float(segment.start),
                "end": float(segment.end),
                "text": text,
            })

            texts.append(text)

            print(
                f"[WHISPER] Segment {count}: "
                f"{segment.start:.1f}s - "
                f"{segment.end:.1f}s",
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

    def transcribe(
        self,
        audio_path,
    ):

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
        # STEP 1
        # Normal automatic transcription
        # --------------------------------------------------

        result = self._run_transcription(
            model,
            path,
            language=None,
        )

        detected_language = result["language"]
        probability = result["language_probability"]
        transcript = result["text"]

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
        # STEP 2
        # Detect possible Burmese misclassification
        #
        # If Whisper says Chinese/Japanese/etc. with weak
        # confidence, retry using Burmese.
        # --------------------------------------------------

        retry_burmese = False

        suspicious_languages = {
            "zh",
            "ja",
            "ko",
            "th",
            "vi",
            "lo",
            "km",
            "unknown",
        }

        if detected_language in suspicious_languages:

            retry_burmese = True

        elif probability < 0.70:

            retry_burmese = True

        if retry_burmese:

            print(
                "[WHISPER] Possible language "
                "misclassification detected.",
                flush=True,
            )

            print(
                "[WHISPER] Retrying transcription "
                "with Burmese language='my'...",
                flush=True,
            )

            burmese_result = self._run_transcription(
                model,
                path,
                language="my",
            )

            burmese_text = burmese_result["text"]

            # --------------------------------------------------
            # Choose Burmese result only when it actually
            # contains Burmese script.
            # Otherwise keep the original auto-detected
            # transcription for multilingual support.
            # --------------------------------------------------

            if self._looks_burmese(
                burmese_text
            ):

                print(
                    "[WHISPER] Burmese transcript "
                    "confirmed.",
                    flush=True,
                )

                result = burmese_result

            else:

                print(
                    "[WHISPER] Burmese retry did not "
                    "produce reliable Burmese text.",
                    flush=True,
                )

                print(
                    "[WHISPER] Keeping automatic "
                    "transcription.",
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

                "error": (
                    "No speech was detected."
                ),
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
            f"[WHISPER] Transcript: "
            f"{result['text'][:500]}",
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


transcription_engine = (
    TranscriptionEngine("tiny")
)
