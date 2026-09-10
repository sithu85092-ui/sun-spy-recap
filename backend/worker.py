import asyncio
import signal
import time

from backend.database import (
    SessionLocal,
    utcnow,
)

from backend.models import Job

from backend.workers.video_worker import (
    process_video,
)


POLL_INTERVAL = 5


running = True


def stop_worker(
    signum,
    frame,
):
    global running

    print(
        "[WORKER] Shutdown signal received.",
        flush=True,
    )

    running = False


signal.signal(
    signal.SIGTERM,
    stop_worker,
)

signal.signal(
    signal.SIGINT,
    stop_worker,
)


def recover_interrupted_jobs():
    """
    Jobs that were PROCESSING when the service
    restarted are returned to QUEUED state.
    """

    db = SessionLocal()

    try:

        jobs = (
            db.query(Job)
            .filter(
                Job.status.in_([
                    "PROCESSING",
                    "TRANSCRIBING",
                    "ANALYZING",
                    "CLIPPING",
                    "NARRATING",
                    "SUBTITLING",
                    "RENDERING",
                ])
            )
            .all()
        )

        recovered = 0

        for job in jobs:

            job.status = "QUEUED"
            job.progress = 0
            job.message = (
                "Job recovered after worker restart."
            )
            job.error = None
            job.updated_at = utcnow()

            recovered += 1

        db.commit()

        if recovered:

            print(
                f"[WORKER] Recovered "
                f"{recovered} interrupted job(s).",
                flush=True,
            )

    except Exception as error:

        db.rollback()

        print(
            "[WORKER] Recovery failed:",
            error,
            flush=True,
        )

    finally:

        db.close()


def get_next_job():

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
            .first()
        )

        if job is None:
            return None

        job.status = "PROCESSING"
        job.progress = max(
            int(job.progress or 0),
            1,
        )
        job.message = (
            "Worker started processing..."
        )
        job.updated_at = utcnow()

        db.commit()

        return job.id

    except Exception as error:

        db.rollback()

        print(
            "[WORKER] Failed to get job:",
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

    recover_interrupted_jobs()

    while running:

        try:

            job_id = get_next_job()

            if job_id is None:

                await asyncio.sleep(
                    POLL_INTERVAL
                )

                continue

            print(
                f"[WORKER] Processing job: "
                f"{job_id}",
                flush=True,
            )

            try:

                await process_video(
                    job_id
                )

            except Exception as error:

                print(
                    f"[WORKER] Job {job_id} "
                    f"failed: {error}",
                    flush=True,
                )

        except Exception as error:

            print(
                "[WORKER] Main loop error:",
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
