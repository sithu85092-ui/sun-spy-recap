from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Job


router = APIRouter(
    prefix="/api",
    tags=["Jobs"],
)


def serialize_job(job: Job):

    return {
        "id": job.id,
        "upload_id": job.upload_id,
        "status": job.status,
        "progress": job.progress,
        "message": job.message,
        "input_file": job.input_file,
        "output_file": job.output_file,
        "error": job.error,
        "recap_text": job.recap_text,
        "language": job.language,
        "created_at": (
            job.created_at.isoformat()
            if job.created_at
            else None
        ),
        "updated_at": (
            job.updated_at.isoformat()
            if job.updated_at
            else None
        ),
    }


@router.get("/status/{job_id}")
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
):

    job = (
        db.query(Job)
        .filter(Job.id == job_id)
        .first()
    )

    if job is None:

        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    return {
        "success": True,
        "job": serialize_job(job),
    }
