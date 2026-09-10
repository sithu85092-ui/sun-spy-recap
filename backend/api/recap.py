import uuid

from pathlib import Path

from fastapi import (
    APIRouter,
    HTTPException,
)

from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import (
    SessionLocal,
    utcnow,
)

from backend.models import Job


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

    if not filename:
        raise HTTPException(
            400,
            "Filename is required",
        )

    # Filename returned by /upload/complete
    # is the actual B2 object filename.
    input_key = (
        f"uploads/{filename}"
    )

    job_id = str(
        uuid.uuid4()
    )

    db: Session = SessionLocal()

    try:
        job = Job(
            id=job_id,
            upload_id=request.upload_id,
            status="QUEUED",
            progress=0,
            message=(
                "Job added to worker queue."
            ),
            input_file=input_key,
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

    print(
        f"[QUEUE] Job queued: {job_id}",
        flush=True,
    )

    return {
        "success": True,
        "job_id": job_id,
        "status": "QUEUED",
        "message": (
            "Recap job added to worker queue."
        ),
    }
