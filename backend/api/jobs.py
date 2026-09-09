from fastapi import (
    APIRouter,
    HTTPException,
)

from backend.database import get_job


router = APIRouter(
    prefix="/api",
    tags=["Jobs"],
)


@router.get("/status/{job_id}")
async def get_job_status(
    job_id: str,
):

    job = get_job(job_id)

    if job is None:
        raise HTTPException(
            404,
            "Job not found",
        )

    return {
        "success": True,
        "job": {
            "id": job["id"],
            "upload_id": job["upload_id"],
            "status": job["status"],
            "progress": job["progress"],
            "message": job["message"],
            "input_file": job["input_file"],
            "output_file": job["output_file"],
            "error": job["error"],
            "recap_text": job["recap_text"],
            "language": job["language"],
            "created_at": job["created_at"],
            "updated_at": job["updated_at"],
        },
    }
