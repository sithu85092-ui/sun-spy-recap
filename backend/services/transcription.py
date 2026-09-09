from pathlib import Path

from faster_whisper import WhisperModel


class TranscriptionEngine:

    def __init__(self, model_size="tiny"):

        self.model_size = model_size
        self.model = None


    def load_model(self):

        if self.model is None:

            self.model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8",
                cpu_threads=2,
                num_workers=1,
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


        model = self.load_model()


        segments, info = model.transcribe(
            str(path),

            beam_size=1,

            best_of=1,

            temperature=0,

            vad_filter=True,

            condition_on_previous_text=False,

            language=None,
        )


        result_segments = []
        texts = []


        for segment in segments:

            text = segment.text.strip()

            if not text:
                continue


            result_segments.append({

                "start":
                    float(segment.start),

                "end":
                    float(segment.end),

                "text":
                    text,

            })


            texts.append(text)


        return {

            "success": True,

            "language":
                info.language,

            "language_probability":
                float(
                    info.language_probability
                ),

            "text":
                " ".join(texts),

            "segments":
                result_segments,

            "engine":
                "faster-whisper",

            "model":
                self.model_size,

        }


transcription_engine = (
    TranscriptionEngine("tiny")
)
