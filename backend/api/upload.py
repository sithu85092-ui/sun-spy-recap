import shutil
import uuid

from pathlib import Path

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
)

from backend.config import (
    UPLOAD_DIR,
    MAX_FILE_SIZE,
    ALLOWED_VIDEO_EXTENSIONS,
)


router = APIRouter(
    prefix="/api/upload",
    tags=["Upload"],
)


CHUNK_DIR = UPLOAD_DIR / ".chunks"

CHUNK_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


@router.post("/init")
async def init_upload(
    filename: str = Form(...),
    file_size: int = Form(...),
):

    if file_size <= 0:
        raise HTTPException(
            400,
            "Invalid file size",
        )

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            413,
            "File exceeds maximum allowed size",
        )

    filename = Path(filename).name

    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported video format: {extension}",
        )

    upload_id = str(uuid.uuid4())

    folder = CHUNK_DIR / upload_id

    folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    return {
        "success": True,
        "upload_id": upload_id,
        "filename": filename,
        "file_size": file_size,
        "extension": extension,
    }


@router.post("/chunk")
async def upload_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    chunk: UploadFile = File(...),
):

    folder = CHUNK_DIR / upload_id

    if not folder.exists():
        raise HTTPException(
            404,
            "Upload session not found",
        )

    if chunk_index < 0:
        raise HTTPException(
            400,
            "Invalid chunk index",
        )

    chunk_path = (
        folder /
        f"{chunk_index}.part"
    )

    with chunk_path.open("wb") as buffer:

        shutil.copyfileobj(
            chunk.file,
            buffer,
        )

    return {
        "success": True,
        "upload_id": upload_id,
        "chunk_index": chunk_index,
    }


@router.post("/complete")
async def complete_upload(
    upload_id: str = Form(...),
    filename: str = Form(...),
    total_chunks: int = Form(...),
):

    folder = CHUNK_DIR / upload_id

    if not folder.exists():
        raise HTTPException(
            404,
            "Upload session not found",
        )

    if total_chunks <= 0:
        raise HTTPException(
            400,
            "Invalid total_chunks",
        )

    filename = Path(filename).name

    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            400,
            "Unsupported video format",
        )

    final_path = (
        UPLOAD_DIR /
        f"{uuid.uuid4()}{extension}"
    )

    try:

        with final_path.open("wb") as output:

            for index in range(total_chunks):

                part = (
                    folder /
                    f"{index}.part"
                )

                if not part.exists():
                    raise HTTPException(
                        400,
                        f"Missing chunk: {index}",
                    )

                with part.open("rb") as source:

                    shutil.copyfileobj(
                        source,
                        output,
                    )

    except Exception:

        final_path.unlink(
            missing_ok=True
        )

        raise

    file_size = final_path.stat().st_size

    shutil.rmtree(
        folder,
        ignore_errors=True,
    )

    if file_size > MAX_FILE_SIZE:

        final_path.unlink(
            missing_ok=True
        )

        raise HTTPException(
            413,
            "Uploaded file exceeds maximum size",
        )

    return {
        "success": True,
        "upload_id": upload_id,
        "filename": final_path.name,
        "path": str(final_path),
        "file_size": file_size,
    }
