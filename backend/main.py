from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="SUN SPY RECAP API",
    version="1.0.0",
    description="AI Video Recap API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "SUN SPY RECAP API",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    return {
        "name": "SUN SPY RECAP",
        "message": "Upload • Discover • Recap"
    }
