import os
import uuid
import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from backend.config import (
    UPLOAD_DIR,
    MAX_FILE_SIZE,
    ALLOWED_VIDEO_EXTENSIONS,
)

router = APIRouter(prefix="/api/upload", tags=["Upload"])

CHUNK_DIR = UPLOAD_DIR / ".chunks"
CHUNK_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/init")
async def init_upload(
    filename: str = Form(...),
    file_size: int = Form(...)
):
    if file_size <= 0:
        raise HTTPException(400, "Invalid file size")

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(413, "File exceeds maximum allowed size")

    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported video format: {extension}"
        )

    upload_id = str(uuid.uuid4())

    upload_folder = CHUNK_DIR / upload_id
    upload_folder.mkdir(parents=True, exist_ok=True)

    return {
        "success": True,
        "upload_id": upload_id,
        "filename": filename,
        "file_size": file_size,
        "extension": extension
    }


@router.post("/chunk")
async def upload_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    chunk: UploadFile = File(...)
):
    upload_folder = CHUNK_DIR / upload_id

    if not upload_folder.exists():
        raise HTTPException(404, "Upload session not found")

    if chunk_index < 0:
        raise HTTPException(400, "Invalid chunk index")

    chunk_path = upload_folder / f"{chunk_index}.part"

    with open(chunk_path, "wb") as buffer:
        shutil.copyfileobj(chunk.file, buffer)

    return {
        "success": True,
        "upload_id": upload_id,
        "chunk_index": chunk_index
    }


@router.post("/complete")
async def complete_upload(
    upload_id: str = Form(...),
    filename: str = Form(...),
    total_chunks: int = Form(...)
):
    upload_folder = CHUNK_DIR / upload_id

    if not upload_folder.exists():
        raise HTTPException(404, "Upload session not found")

    if total_chunks <= 0:
        raise HTTPException(400, "Invalid total_chunks")

    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(400, "Unsupported video format")

    final_filename = f"{uuid.uuid4()}{extension}"
    final_path = UPLOAD_DIR / final_filename

    with open(final_path, "wb") as output:
        for index in range(total_chunks):
            chunk_path = upload_folder / f"{index}.part"

            if not chunk_path.exists():
                raise HTTPException(
                    400,
                    f"Missing chunk: {index}"
                )

            with open(chunk_path, "rb") as chunk_file:
                shutil.copyfileobj(chunk_file, output)

    shutil.rmtree(upload_folder, ignore_errors=True)

    file_size = final_path.stat().st_size

    return {
        "success": True,
        "upload_id": upload_id,
        "filename": final_filename,
        "path": str(final_path),
        "file_size": file_size,
        "message": "Upload completed successfully"
    }
