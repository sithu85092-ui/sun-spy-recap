import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .database import (
    init_db,
    SessionLocal,
)

from .models import Job

from .api import (
    jobs,
    recap,
    upload,
    files,
)


app = FastAPI(
    title="SUN SPY RECAP API",
    version="4.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():

    init_db()

    print(
        "SUN SPY RECAP PostgreSQL backend started.",
        flush=True,
    )

    # Check database connection
    db = SessionLocal()

    try:

        db.execute(
            text("SELECT 1")
        )

        print(
            "PostgreSQL connection OK.",
            flush=True,
        )

    finally:

        db.close()


@app.get("/")
def root():

    return {
        "ok": True,
        "service": "SUN SPY RECAP API",
        "version": "4.0.0",
        "database": "PostgreSQL",
        "pipeline": [
            "upload",
            "whisper",
            "highlight",
            "recap",
            "tts",
            "subtitles",
            "9:16 render",
        ],
    }


@app.get("/api/health")
def health():

    db = SessionLocal()

    try:

        db.execute(
            text("SELECT 1")
        )

        database_status = "connected"

    except Exception as error:

        database_status = (
            f"error: {error}"
        )

    finally:

        db.close()

    return {
        "status": "ok",
        "service": "SUN SPY RECAP API",
        "version": "4.0.0",
        "database": "postgresql",
        "database_status": database_status,
    }


app.include_router(
    upload.router
)

app.include_router(
    recap.router
)

app.include_router(
    jobs.router
)

app.include_router(
    files.router
)
