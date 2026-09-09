import asyncio
from datetime import datetime, timezone
from pathlib import Path

from backend.database import get_job, update_job
from backend.config import TEMP_DIR

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

from backend.services.narrator import (
    narrator,
)

from backend.services.subtitles import (
    create_srt,
)

from backend.services.renderer import (
    render_vertical,
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

        # =================================================
        # 1. PREPARE
        # =================================================

        update_job(
            job_id,
            status="PROCESSING",
            progress=5,
            message="Preparing video...",
            updated_at=now()
        )

        await asyncio.sleep(0.2)


        # =================================================
        # 2. INSPECT VIDEO
        # =================================================

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


        # =================================================
        # 3. EXTRACT AUDIO
        # =================================================

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


        # =================================================
        # 4. WHISPER
        # =================================================

        update_job(
            job_id,
            status="TRANSCRIBING",
            progress=30,
            message="Transcribing speech...",
            updated_at=now()
        )

        transcription = await asyncio.to_thread(
            transcription_engine.transcribe,
            audio_file
        )

        if not transcription["success"]:
            raise RuntimeError(
                transcription.get(
                    "error",
                    "Transcription failed"
                )
            )

        transcript = (
            transcription["text"]
            or ""
        ).strip()

        segments = transcription[
            "segments"
        ]


        # =================================================
        # 5. BURMESE RECAP
        # =================================================

        update_job(
            job_id,
            status="NARRATING",
            progress=40,
            message="Creating Burmese recap...",
            updated_at=now()
        )

        recap = await asyncio.to_thread(
            narrator.create_recap,
            transcript
        )

        if not recap["success"]:
            raise RuntimeError(
                recap.get(
                    "error",
                    "Recap creation failed"
                )
            )

        recap_text = (
            recap["text"]
            or ""
        ).strip()


        # =================================================
        # 6. FIND HIGHLIGHT
        # =================================================

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


        # =================================================
        # 7. CREATE HIGHLIGHT
        # =================================================

        update_job(
            job_id,
            status="CLIPPING",
            progress=60,
            message="Creating highlight...",
            updated_at=now()
        )

        clip_name = (
            f"{job_id}_highlight.mp4"
        )

        clip_path = create_highlight_clip(
            video_path=input_file,
            start=highlight["start"],
            duration=highlight["duration"],
            output_name=clip_name
        )


        # =================================================
        # 8. CREATE SUBTITLES
        # =================================================

        update_job(
            job_id,
            status="SUBTITLING",
            progress=70,
            message="Creating subtitles...",
            updated_at=now()
        )

        subtitle_path = (
            TEMP_DIR /
            f"{job_id}.srt"
        )

        create_srt(
            segments,
            subtitle_path
        )


        # =================================================
        # 9. RENDER 9:16
        # =================================================

        update_job(
            job_id,
            status="RENDERING",
            progress=85,
            message="Rendering 9:16 vertical video...",
            updated_at=now()
        )

        final_name = (
            f"{job_id}_final.mp4"
        )

        final_path = await asyncio.to_thread(
            render_vertical,
            clip_path,
            final_name
        )


        # =================================================
        # 10. COMPLETE
        # =================================================

        update_job(
            job_id,
            status="COMPLETED",
            progress=100,
            message="Final recap created successfully.",
            output_file=str(
                final_path
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
