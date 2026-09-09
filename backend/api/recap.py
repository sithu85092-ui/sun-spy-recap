import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.job_service import (
    create_job,
)
from ..workers.video_worker import process_video


router = APIRouter(
    prefix="/api",
    tags=["Recap"],
)


class RecapRequest(BaseModel):
    upload_id: str
    filename: str
    language: str = "my"


@router.post("/recap")
async def create_recap(
    request: RecapRequest,
    db: Session = Depends(get_db),
):
    job_id = str(uuid.uuid4())

    job = create_job(
        db=db,
        job_id=job_id,
        upload_id=request.upload_id,
        input_file=request.filename,
        language=request.language,
    )

    asyncio.create_task(
        process_video(job_id)
    )

    return {
        "success": True,
        "job_id": job.id,
        "status": job.status,
        "message": "Video processing started.",
    }
