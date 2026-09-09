import asyncio
import uuid

from datetime import (
    datetime,
    timezone,
)

from pathlib import Path

from fastapi import (
    APIRouter,
    HTTPException,
)

from pydantic import BaseModel

from backend.config import UPLOAD_DIR

from backend.database import create_job

from backend.workers.video_worker import (
    process_video,
)


router = APIRouter(
    prefix="/api",
    tags=["Recap"],
)


class RecapRequest(BaseModel):

    upload_id: str
    filename: str


@router.post("/recap")
async def create_recap(
    request: RecapRequest,
):

    filename = Path(
        request.filename
    ).name

    upload_path = (
        UPLOAD_DIR /
        filename
    )

    if not upload_path.exists():

        raise HTTPException(
            404,
            "Uploaded video not found",
        )

    job_id = str(uuid.uuid4())

    now = datetime.now(
        timezone.utc
    ).isoformat()

    create_job(
        job_id,
        request.upload_id,
        str(upload_path),
        now,
    )

    asyncio.create_task(
        process_video(job_id)
    )

    return {
        "success": True,
        "job_id": job_id,
        "status": "QUEUED",
        "message": "Recap processing started.",
    }
