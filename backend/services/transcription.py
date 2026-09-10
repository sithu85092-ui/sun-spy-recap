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
            "[WHISPER] Starting transcription...",
            flush=True,
        )

        segments, info = model.transcribe(
            str(path),

            beam_size=1,

            best_of=1,

            temperature=0,

            language=None,

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
                "start": float(
                    segment.start
                ),

                "end": float(
                    segment.end
                ),

                "text": text,
            })

            texts.append(text)

            print(
                f"[WHISPER] Segment {count}: "
                f"{segment.start:.1f}s - "
                f"{segment.end:.1f}s",
                flush=True,
            )

        elapsed = time.time() - start_time

        transcript = " ".join(
            texts
        ).strip()

        if not transcript:

            print(
                "[WHISPER] No speech detected.",
                flush=True,
            )

            return {
                "success": False,

                "language": getattr(
                    info,
                    "language",
                    "unknown",
                ),

                "language_probability": float(
                    getattr(
                        info,
                        "language_probability",
                        0.0,
                    )
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
            f"[WHISPER] Language: "
            f"{info.language}",
            flush=True,
        )

        print(
            f"[WHISPER] Segments: "
            f"{count}",
            flush=True,
        )

        return {
            "success": True,

            "language": info.language,

            "language_probability": float(
                info.language_probability
            ),

            "text": transcript,

            "segments": result_segments,

            "engine": "faster-whisper",

            "model": self.model_size,
        }


transcription_engine = (
    TranscriptionEngine("tiny")
)
