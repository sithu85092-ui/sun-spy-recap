import asyncio
from datetime import datetime, timezone
from pathlib import Path

from backend.database import get_job, update_job

from backend.services.processor import (
    inspect_video,
    prepare_audio,
)

from backend.services.analyzer import (
    choose_highlight,
)

from backend.services.clipper import (
    create_highlight_clip,
)

from backend.services.transcription import (
    transcription_engine,
)


def now():
    return datetime.now(
        timezone.utc
    ).isoformat()


async def process_video(job_id: str):

    job = get_job(job_id)

    if job is None:
        return

    input_file = Path(
        job["input_file"]
    )

    try:

        # -------------------------------------------------
        # STEP 1 — Preparing
        # -------------------------------------------------

        update_job(
            job_id,
            status="PROCESSING",
            progress=5,
            message="Preparing video...",
            updated_at=now()
        )

        await asyncio.sleep(0.2)


        # -------------------------------------------------
        # STEP 2 — Inspect Video
        # -------------------------------------------------

        update_job(
            job_id,
            status="ANALYZING",
            progress=10,
            message="Inspecting video...",
            updated_at=now()
        )

        info = inspect_video(
            input_file
        )

        if not info["success"]:
            raise RuntimeError(
                info["error"]
            )

        duration = info[
            "duration"
        ]


        # -------------------------------------------------
        # STEP 3 — Extract Audio
        # -------------------------------------------------

        update_job(
            job_id,
            status="TRANSCRIBING",
            progress=20,
            message="Extracting audio...",
            updated_at=now()
        )

        audio_result = prepare_audio(
            input_file
        )

        audio_file = Path(
            audio_result["audio_file"]
        )


        # -------------------------------------------------
        # STEP 4 — Whisper STT
        # -------------------------------------------------

        update_job(
            job_id,
            status="TRANSCRIBING",
            progress=30,
            message="Transcribing speech with Whisper...",
            updated_at=now()
        )


        transcription = (
            await asyncio.to_thread(
                transcription_engine.transcribe,
                audio_file
            )
        )


        if not transcription["success"]:
            raise RuntimeError(
                transcription.get(
                    "error",
                    "Transcription failed"
                )
            )


        transcript = transcription[
            "text"
        ]

        segments = transcription[
            "segments"
        ]


        # -------------------------------------------------
        # STEP 5 — Analyze Highlight
        # -------------------------------------------------

        update_job(
            job_id,
            status="ANALYZING",
            progress=50,
            message="Finding the most interesting scene...",
            updated_at=now()
        )


        clip_duration = min(
            30.0,
            max(5.0, duration)
        )


        highlight = choose_highlight(
            input_file,
            clip_duration=clip_duration
        )


        # -------------------------------------------------
        # STEP 6 — Create Highlight
        # -------------------------------------------------

        update_job(
            job_id,
            status="CLIPPING",
            progress=60,
            message="Creating highlight clip...",
            updated_at=now()
        )


        clip_name = (
            f"{job_id}_highlight.mp4"
        )


        clip_path = (
            create_highlight_clip(
                video_path=input_file,
                start=highlight["start"],
                duration=highlight["duration"],
                output_name=clip_name
            )
        )


        # -------------------------------------------------
        # STEP 7 — Recap Preparation
        # -------------------------------------------------

        update_job(
            job_id,
            status="NARRATING",
            progress=70,
            message="Preparing Burmese recap...",
            updated_at=now()
        )


        # Temporary result.
        # Burmese AI summarization will be
        # connected in the next phase.

        recap_text = transcript[:500]


        # -------------------------------------------------
        # STEP 8 — Subtitles
        # -------------------------------------------------

        update_job(
            job_id,
            status="SUBTITLING",
            progress=80,
            message="Preparing subtitles...",
            updated_at=now()
        )


        # Subtitle generation will be connected
        # to the final rendered video later.


        # -------------------------------------------------
        # STEP 9 — Rendering
        # -------------------------------------------------

        update_job(
            job_id,
            status="RENDERING",
            progress=90,
            message="Preparing final video...",
            updated_at=now()
        )


        # Final rendering will be connected
        # in the next rendering phase.


        # -------------------------------------------------
        # STEP 10 — Completed
        # -------------------------------------------------

        update_job(
            job_id,
            status="COMPLETED",
            progress=100,
            message="Recap processing completed.",
            output_file=str(
                clip_path
            ),
            updated_at=now()
        )


    except Exception as error:

        update_job(
            job_id,
            status="FAILED",
            progress=0,
            message="Video processing failed.",
            error=str(error),
            updated_at=now()
        )
