from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.job_service import (
    get_job,
    job_to_dict,
)


router = APIRouter(
    prefix="/api",
    tags=["Jobs"],
)


@router.get("/status/{job_id}")
def status(
    job_id: str,
    db: Session = Depends(get_db),
):
    job = get_job(db, job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    return {
        "success": True,
        "job": job_to_dict(job),
    }
