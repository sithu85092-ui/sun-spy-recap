import asyncio
from datetime import datetime, timezone
from pathlib import Path

from backend.database import get_job, update_job
from backend.services.processor import inspect_video
from backend.services.analyzer import choose_highlight
from backend.services.clipper import create_highlight_clip


def now():
    return datetime.now(timezone.utc).isoformat()


async def process_video(job_id: str):

    job = get_job(job_id)

    if job is None:
        return

    input_file = Path(job["input_file"])

    try:

        # ==========================
        # 1. PROCESSING
        # ==========================

        update_job(
            job_id,
            status="PROCESSING",
            progress=5,
            message="Preparing video...",
            updated_at=now()
        )

        await asyncio.sleep(0.3)

        # ==========================
        # 2. VIDEO INSPECTION
        # ==========================

        update_job(
            job_id,
            status="ANALYZING",
            progress=15,
            message="Inspecting video...",
            updated_at=now()
        )

        info = inspect_video(input_file)

        if not info["success"]:
            raise RuntimeError(info["error"])

        duration = info["duration"]

        # ==========================
        # 3. HIGHLIGHT DETECTION
        # ==========================

        update_job(
            job_id,
            status="ANALYZING",
            progress=30,
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

        # ==========================
        # 4. AUTO CLIP
        # ==========================

        update_job(
            job_id,
            status="CLIPPING",
            progress=45,
            message="Creating highlight clip...",
            updated_at=now()
        )

        clip_name = f"{job_id}_highlight.mp4"

        clip_path = create_highlight_clip(
            video_path=input_file,
            start=highlight["start"],
            duration=highlight["duration"],
            output_name=clip_name
        )

        # ==========================
        # 5. NARRATION
        # ==========================

        update_job(
            job_id,
            status="NARRATING",
            progress=60,
            message="Creating Burmese recap...",
            updated_at=now()
        )

        await asyncio.sleep(0.5)

        # ==========================
        # 6. SUBTITLES
        # ==========================

        update_job(
            job_id,
            status="SUBTITLING",
            progress=75,
            message="Preparing subtitles...",
            updated_at=now()
        )

        await asyncio.sleep(0.5)

        # ==========================
        # 7. RENDERING
        # ==========================

        update_job(
            job_id,
            status="RENDERING",
            progress=90,
            message="Rendering final video...",
            updated_at=now()
        )

        await asyncio.sleep(0.5)

        # ==========================
        # 8. COMPLETED
        # ==========================

        update_job(
            job_id,
            status="COMPLETED",
            progress=100,
            message="Highlight created successfully.",
            output_file=str(clip_path),
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
