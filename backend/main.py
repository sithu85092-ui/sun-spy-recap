from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.upload import router as upload_router

app = FastAPI(
    title="SUN SPY RECAP API",
    version="1.0.0",
    description="Professional AI Video Recap API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)


@app.get("/")
async def root():
    return {
        "name": "SUN SPY RECAP",
        "version": "1.0.0",
        "message": "Upload • Discover • Recap"
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "SUN SPY RECAP API",
        "version": "1.0.0"
    }
