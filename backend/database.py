import sqlite3

from backend.config import BASE_DIR


DATABASE_PATH = BASE_DIR / "sun_spy_recap.db"


def get_connection():
    connection = sqlite3.connect(
        DATABASE_PATH,
        check_same_thread=False,
    )

    connection.row_factory = sqlite3.Row

    return connection


def init_database():
    connection = get_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            upload_id TEXT NOT NULL,
            input_file TEXT NOT NULL,
            output_file TEXT,
            status TEXT NOT NULL,
            progress INTEGER DEFAULT 0,
            message TEXT,
            error TEXT,
            recap_text TEXT,
            language TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    connection.commit()
    connection.close()


def create_job(
    job_id,
    upload_id,
    input_file,
    created_at,
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
        VALUES (
            ?,
            ?,
            ?,
            'QUEUED',
            0,
            'Job queued',
            ?,
            ?
        )
        """,
        (
            job_id,
            upload_id,
            input_file,
            created_at,
            created_at,
        ),
    )

    connection.commit()
    connection.close()


def get_job(job_id):
    connection = get_connection()

    job = connection.execute(
        """
        SELECT *
        FROM jobs
        WHERE id = ?
        """,
        (job_id,),
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
    recap_text=None,
    language=None,
    updated_at=None,
):
    fields = []
    values = []

    updates = {
        "status": status,
        "progress": progress,
        "message": message,
        "output_file": output_file,
        "error": error,
        "recap_text": recap_text,
        "language": language,
        "updated_at": updated_at,
    }

    for field, value in updates.items():

        if value is not None:
            fields.append(
                f"{field} = ?"
            )

            values.append(value)

    if not fields:
        return

    values.append(job_id)

    connection = get_connection()

    connection.execute(
        f"""
        UPDATE jobs
        SET {", ".join(fields)}
        WHERE id = ?
        """,
        values,
    )

    connection.commit()
    connection.close()
