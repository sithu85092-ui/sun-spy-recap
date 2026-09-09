import asyncio
from datetime import datetime, timezone
from pathlib import Path

from backend.database import get_job, update_job
from backend.services.processor import inspect_video


def now():
    return datetime.now(timezone.utc).isoformat()


async def process_video(job_id: str):

    job = get_job(job_id)

    if job is None:
        return

    input_file = Path(job["input_file"])

    try:
        update_job(
            job_id,
            status="PROCESSING",
            progress=5,
            message="Preparing video...",
            updated_at=now()
        )

        await asyncio.sleep(0.5)

        # --------------------------------
        # STEP 1: Inspect Video
        # --------------------------------

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

        await asyncio.sleep(0.5)

        # --------------------------------
        # STEP 2: AI Analysis
        # --------------------------------

        update_job(
            job_id,
            status="ANALYZING",
            progress=30,
            message="Analyzing video...",
            updated_at=now()
        )

        # AI analyzer will be connected here.
        await asyncio.sleep(1)

        # --------------------------------
        # STEP 3: Highlight Detection
        # --------------------------------

        update_job(
            job_id,
            status="CLIPPING",
            progress=45,
            message="Finding the best scene...",
            updated_at=now()
        )

        # Highlight engine will be connected here.
        await asyncio.sleep(1)

        # --------------------------------
        # STEP 4: Narration
        # --------------------------------

        update_job(
            job_id,
            status="NARRATING",
            progress=60,
            message="Creating Burmese recap...",
            updated_at=now()
        )

        # Burmese AI narration will be connected here.
        await asyncio.sleep(1)

        # --------------------------------
        # STEP 5: Subtitles
        # --------------------------------

        update_job(
            job_id,
            status="SUBTITLING",
            progress=75,
            message="Creating subtitles...",
            updated_at=now()
        )

        # Subtitle engine will be connected here.
        await asyncio.sleep(1)

        # --------------------------------
        # STEP 6: Rendering
        # --------------------------------

        update_job(
            job_id,
            status="RENDERING",
            progress=90,
            message="Rendering 9:16 video...",
            updated_at=now()
        )

        # Final renderer will be connected here.
        await asyncio.sleep(1)

        # --------------------------------
        # COMPLETE
        # --------------------------------

        update_job(
            job_id,
            status="COMPLETED",
            progress=100,
            message="Recap completed successfully.",
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
