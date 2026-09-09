from pathlib import Path

from fastapi import (
    APIRouter,
    HTTPException,
)

from fastapi.responses import FileResponse

from backend.config import OUTPUT_DIR


router = APIRouter(
    prefix="/api/files",
    tags=["Files"],
)


@router.get("/{filename}")
async def get_file(
    filename: str,
):

    safe_name = Path(
        filename
    ).name

    file_path = (
        OUTPUT_DIR /
        safe_name
    )

    if (
        not file_path.exists()
        or not file_path.is_file()
    ):
        raise HTTPException(
            404,
            "File not found",
        )

    return FileResponse(
        path=file_path,
        media_type="video/mp4",
        filename=file_path.name,
    )
