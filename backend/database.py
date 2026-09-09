import sqlite3
from pathlib import Path

from backend.config import BASE_DIR


DATABASE_PATH = BASE_DIR / "sun_spy_recap.db"


def get_connection():
    connection = sqlite3.connect(
        DATABASE_PATH,
        check_same_thread=False
    )

    connection.row_factory = sqlite3.Row

    return connection


def init_database():
    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            upload_id TEXT,
            input_file TEXT,
            output_file TEXT,
            status TEXT NOT NULL,
            progress INTEGER DEFAULT 0,
            message TEXT,
            error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


def create_job(
    job_id,
    upload_id,
    input_file,
    created_at
):
    connection = get_connection()

    connection.execute(
        """
        INSERT INTO jobs (
            id,
            upload_id,
            input_file,
            status,
            progress,
            message,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_id,
            upload_id,
            input_file,
            "QUEUED",
            0,
            "Job queued",
            created_at,
            created_at
        )
    )

    connection.commit()
    connection.close()


def get_job(job_id):
    connection = get_connection()

    job = connection.execute(
        "SELECT * FROM jobs WHERE id = ?",
        (job_id,)
    ).fetchone()

    connection.close()

    return job


def update_job(
    job_id,
    status=None,
    progress=None,
    message=None,
    output_file=None,
    error=None,
    updated_at=None
):
    connection = get_connection()

    fields = []
    values = []

    if status is not None:
        fields.append("status = ?")
        values.append(status)

    if progress is not None:
        fields.append("progress = ?")
        values.append(progress)

    if message is not None:
        fields.append("message = ?")
        values.append(message)

    if output_file is not None:
        fields.append("output_file = ?")
        values.append(output_file)

    if error is not None:
        fields.append("error = ?")
        values.append(error)

    if updated_at is not None:
        fields.append("updated_at = ?")
        values.append(updated_at)

    if not fields:
        connection.close()
        return

    values.append(job_id)

    connection.execute(
        f"""
        UPDATE jobs
        SET {", ".join(fields)}
        WHERE id = ?
        """,
        values
    )

    connection.commit()
    connection.close()
