from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .api import jobs
from .api import recap
from .api import upload


app = FastAPI(
    title="SUN SPY RECAP API",
    version="3.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {
        "ok": True,
        "service": "SUN SPY RECAP API",
        "version": "3.0.0",
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
    return {
        "status": "ok",
        "service": "SUN SPY RECAP API",
        "version": "3.0.0",
        "database": "postgresql",
    }


app.include_router(upload.router)
app.include_router(recap.router)
app.include_router(jobs.router)
