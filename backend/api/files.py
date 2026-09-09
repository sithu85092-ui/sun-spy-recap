from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.config import OUTPUT_DIR

router = APIRouter(
    prefix="/api/files",
    tags=["Files"]
)


@router.get("/{filename}")
async def get_file(filename: str):

    file_path = OUTPUT_DIR / Path(filename).name

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    return FileResponse(
        path=file_path,
        media_type="video/mp4",
        filename=file_path.name
    )
