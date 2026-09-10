import asyncio
import signal
import time

from sqlalchemy import or_

from backend.database import SessionLocal, utcnow
from backend.models import Job
from backend.workers.video_worker import process_video


POLL_INTERVAL = 5
STALE_JOB_SECONDS = 1800

running = True


def handle_shutdown(signum, frame):
    global running

    print(
        "[WORKER] Shutdown signal received.",
        flush=True,
    )

    running = False


signal.signal(
    signal.SIGTERM,
    handle_shutdown,
)

signal.signal(
    signal.SIGINT,
    handle_shutdown,
)


def recover_stale_jobs():
    """
    Return interrupted jobs to QUEUED.

    This allows a job to continue after the
    worker/server is restarted.
    """

    db = SessionLocal()

    try:
        now = utcnow()

        stale_before = (
            now.timestamp()
            - STALE_JOB_SECONDS
        )

        statuses = [
            "PROCESSING",
            "TRANSCRIBING",
            "ANALYZING",
            "CLIPPING",
            "NARRATING",
            "SUBTITLING",
            "RENDERING",
        ]

        jobs = (
            db.query(Job)
            .filter(
                Job.status.in_(statuses)
            )
            .all()
        )

        recovered = 0

        for job in jobs:

            updated = job.updated_at

            if updated is None:
                is_stale = True
            else:
                is_stale = (
                    updated.timestamp()
                    < stale_before
                )

            if not is_stale:
                continue

            job.status = "QUEUED"
            job.progress = 0
            job.message = (
                "Job re-queued after worker restart."
            )
            job.error = None
            job.updated_at = now

            recovered += 1

        if recovered:
            db.commit()

        print(
            f"[WORKER] Recovered "
            f"{recovered} stale job(s).",
            flush=True,
        )

    except Exception as error:

        db.rollback()

        print(
            "[WORKER] Recovery error:",
            error,
            flush=True,
        )

    finally:

        db.close()


def claim_next_job():
    """
    Find one QUEUED job and mark it PROCESSING.

    PostgreSQL row locking prevents two worker
    loops from claiming the same job.
    """

    db = SessionLocal()

    try:

        job = (
            db.query(Job)
            .filter(
                Job.status == "QUEUED"
            )
            .order_by(
                Job.created_at.asc()
            )
            .with_for_update(
                skip_locked=True
            )
            .first()
        )

        if job is None:
            db.rollback()
            return None

        job.status = "PROCESSING"
        job.progress = 1
        job.message = (
            "Worker claimed job."
        )
        job.error = None
        job.updated_at = utcnow()

        db.commit()

        print(
            f"[WORKER] Claimed job: "
            f"{job.id}",
            flush=True,
        )

        return job.id

    except Exception as error:

        db.rollback()

        print(
            "[WORKER] Claim error:",
            error,
            flush=True,
        )

        return None

    finally:

        db.close()


async def worker_loop():

    print(
        "[WORKER] SUN SPY RECAP worker started.",
        flush=True,
    )

    recover_stale_jobs()

    last_recovery = time.time()

    while running:

        try:

            # Periodically recover jobs that became
            # stale while the worker was running.
            if (
                time.time()
                - last_recovery
                > 300
            ):

                recover_stale_jobs()

                last_recovery = time.time()

            job_id = claim_next_job()

            if job_id is None:

                await asyncio.sleep(
                    POLL_INTERVAL
                )

                continue

            print(
                f"[WORKER] Starting job "
                f"{job_id}",
                flush=True,
            )

            try:

                await process_video(
                    job_id
                )

            except Exception as error:

                print(
                    f"[WORKER] Unhandled job "
                    f"error {job_id}: "
                    f"{error}",
                    flush=True,
                )

        except Exception as error:

            print(
                "[WORKER] Loop error:",
                error,
                flush=True,
            )

            await asyncio.sleep(
                POLL_INTERVAL
            )

    print(
        "[WORKER] Worker stopped.",
        flush=True,
    )


def main():

    try:

        asyncio.run(
            worker_loop()
        )

    except KeyboardInterrupt:

        print(
            "[WORKER] Keyboard interrupt.",
            flush=True,
        )


if __name__ == "__main__":
    main()
