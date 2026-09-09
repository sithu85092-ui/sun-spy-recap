import asyncio
import os

from ..database import SessionLocal
from ..services.job_service import (
    get_job,
    update_job,
)


def update_progress(
    job_id,
    progress,
    message,
    status="PROCESSING",
):
    db = SessionLocal()

    try:
        update_job(
            db,
            job_id,
            progress=progress,
            message=message,
            status=status,
        )
    finally:
        db.close()


async def process_video(job_id: str):

    db = SessionLocal()

    try:
        job = get_job(db, job_id)

        if not job:
            return

        input_file = job.input_file

        update_job(
            db,
            job_id,
            status="PROCESSING",
            progress=5,
            message="Inspecting video...",
        )

        # Import existing services here
        from ..services.extractor import extract_audio
        from ..services.whisper_service import transcribe
        from ..services.analyzer import choose_highlight
        from ..services.clipper import create_clip
        from ..services.recap_service import generate_recap
        from ..services.tts import synthesize
        from ..services.subtitle import create_subtitles
        from ..services.renderer import render_vertical

        # --------------------------------
        # 1. Extract audio
        # --------------------------------

        update_progress(
            job_id,
            15,
            "Extracting audio...",
        )

        audio_file = await asyncio.to_thread(
            extract_audio,
            input_file,
        )

        # --------------------------------
        # 2. Whisper
        # --------------------------------

        update_progress(
            job_id,
            30,
            "Transcribing audio...",
        )

        transcript = await asyncio.to_thread(
            transcribe,
            audio_file,
        )

        # --------------------------------
        # 3. Find highlight
        # --------------------------------

        update_progress(
            job_id,
            45,
            "Finding the best scene...",
        )

        highlight = await asyncio.to_thread(
            choose_highlight,
            transcript,
        )

        # --------------------------------
        # 4. Clip
        # --------------------------------

        update_progress(
            job_id,
            55,
            "Creating highlight clip...",
        )

        clip_file = await asyncio.to_thread(
            create_clip,
            input_file,
            highlight,
        )

        # --------------------------------
        # 5. Burmese recap
        # --------------------------------

        update_progress(
            job_id,
            65,
            "Creating Burmese recap...",
        )

        recap_text = await asyncio.to_thread(
            generate_recap,
            transcript,
        )

        # --------------------------------
        # 6. TTS
        # --------------------------------

        update_progress(
            job_id,
            72,
            "Generating Burmese narration...",
        )

        tts_file = await synthesize(
            recap_text,
            "data/narration.mp3",
        )

        # --------------------------------
        # 7. Subtitles
        # --------------------------------

        update_progress(
            job_id,
            80,
            "Creating subtitles...",
        )

        subtitle_file = await asyncio.to_thread(
            create_subtitles,
            recap_text,
        )

        # --------------------------------
        # 8. Render 9:16
        # --------------------------------

        update_progress(
            job_id,
            88,
            "Rendering 9:16 video...",
        )

        output_file = await asyncio.to_thread(
            render_vertical,
            clip_file,
            tts_file,
            subtitle_file,
        )

        # --------------------------------
        # 9. Complete
        # --------------------------------

        db = SessionLocal()

        try:
            update_job(
                db,
                job_id,
                status="COMPLETED",
                progress=100,
                message="Video processing completed.",
                output_file=str(output_file),
                recap_text=recap_text,
            )
        finally:
            db.close()

    except Exception as error:

        db = SessionLocal()

        try:
            update_job(
                db,
                job_id,
                status="FAILED",
                progress=0,
                message="Video processing failed.",
                error=str(error),
            )
        finally:
            db.close()
