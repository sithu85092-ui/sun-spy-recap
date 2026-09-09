from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

STORAGE_DIR = BASE_DIR / "storage"

UPLOAD_DIR = STORAGE_DIR / "uploads"
TEMP_DIR = STORAGE_DIR / "temp"
OUTPUT_DIR = STORAGE_DIR / "output"

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB

ALLOWED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
    ".avi"
}

for directory in [
    UPLOAD_DIR,
    TEMP_DIR,
    OUTPUT_DIR
]:
    directory.mkdir(parents=True, exist_ok=True)
