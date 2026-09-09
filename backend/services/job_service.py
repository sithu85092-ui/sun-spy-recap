from datetime import datetime

from sqlalchemy.orm import Session

from ..models import Job


def create_job(
    db: Session,
    job_id: str,
    upload_id: str,
    input_file: str,
    language: str = "my",
):
    job = Job(
        id=job_id,
        upload_id=upload_id,
        status="QUEUED",
        progress=0,
        message="Job queued.",
        input_file=input_file,
        language=language,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job


def get_job(
    db: Session,
    job_id: str,
):
    return (
        db.query(Job)
        .filter(Job.id == job_id)
        .first()
    )


def update_job(
    db: Session,
    job_id: str,
    **kwargs,
):
    job = get_job(db, job_id)

    if not job:
        return None

    for key, value in kwargs.items():
        if hasattr(job, key):
            setattr(job, key, value)

    job.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(job)

    return job


def job_to_dict(job: Job):
    if not job:
        return None

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
