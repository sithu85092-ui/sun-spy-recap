from fastapi import (
    APIRouter,
    HTTPException,
)

from backend.services.b2_storage import (
    create_download_url,
)


router = APIRouter(
    prefix="/api/files",
    tags=["Files"],
)


@router.get("/{filename}")
async def get_file(
    filename: str,
):
    if not filename:
        raise HTTPException(
            400,
            "Filename is required",
        )

    # Frontend should normally use
    # /api/status/{job_id} output_file.
    # This endpoint is kept for compatibility.

    object_key = filename

    if not object_key.startswith(
        "outputs/"
    ):
        object_key = (
            f"outputs/{filename}"
        )

    try:
        url = create_download_url(
            object_key,
            expires=3600,
        )

        return {
            "success": True,
            "url": url,
        }

    except Exception as error:
        raise HTTPException(
            404,
            f"File not found: {error}",
        )
