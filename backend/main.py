from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_database

from backend.api.upload import router as upload_router
from backend.api.jobs import router as jobs_router
from backend.api.recap import router as recap_router
from backend.api.files import router as files_router


@asynccontextmanager
async def lifespan(app: FastAPI):

    init_database()

    yield


app = FastAPI(
    title="SUN SPY RECAP API",
    version="1.0.0",
    description="Professional AI Video Recap API",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Routers

app.include_router(upload_router)

app.include_router(jobs_router)

app.include_router(recap_router)

app.include_router(files_router)


@app.get("/")
async def root():

    return {
        "name": "SUN SPY RECAP",
        "version": "1.0.0",
        "message": "Upload • Discover • Recap",
    }


@app.get("/api/health")
async def health():

    return {
        "status": "ok",
        "service": "SUN SPY RECAP API",
        "version": "1.0.0",
    }
