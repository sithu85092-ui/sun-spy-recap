import asyncio
import uuid

from pathlib import Path

from fastapi import (
    APIRouter,
    HTTPException,
)

from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import UPLOAD_DIR
from backend.database import SessionLocal, utcnow
from backend.models import Job
from backend.workers.video_worker import process_video


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
        UPLOAD_DIR / filename
    )

    if not upload_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Uploaded video not found",
        )

    job_id = str(uuid.uuid4())

    db: Session = SessionLocal()

    try:

        job = Job(
            id=job_id,
            upload_id=request.upload_id,
            status="QUEUED",
            progress=0,
            message="Job queued",
            input_file=str(upload_path),
            output_file=None,
            error=None,
            recap_text=None,
            language="my",
            created_at=utcnow(),
            updated_at=utcnow(),
        )

        db.add(job)
        db.commit()

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()

    # Start processing in background.
    asyncio.create_task(
        process_video(job_id)
    )

    return {
        "success": True,
        "job_id": job_id,
        "status": "QUEUED",
        "message": "Recap processing started.",
    }
