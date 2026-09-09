import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import UPLOAD_DIR
from backend.database import create_job
from backend.workers.video_worker import process_video


router = APIRouter(
    prefix="/api",
    tags=["Recap"]
)


class RecapRequest(BaseModel):
    upload_id: str
    filename: str


@router.post("/recap")
async def create_recap(request: RecapRequest):

    upload_path = UPLOAD_DIR / request.filename

    if not upload_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Uploaded video not found"
        )

    job_id = str(uuid.uuid4())

    now = datetime.now(
        timezone.utc
    ).isoformat()

    create_job(
        job_id=job_id,
        upload_id=request.upload_id,
        input_file=str(upload_path),
        created_at=now
    )

    # Start background processing
    asyncio.create_task(
        process_video(job_id)
    )

    return {
        "success": True,
        "job_id": job_id,
        "status": "QUEUED",
        "message": "Recap processing started."
    }
