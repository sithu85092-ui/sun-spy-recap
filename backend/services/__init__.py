import json
import shutil
import subprocess
from pathlib import Path

from backend.config import TEMP_DIR, OUTPUT_DIR


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def ffprobe_available() -> bool:
    return shutil.which("ffprobe") is not None


def _run(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )


def get_duration(video_path: str | Path) -> float:
    if not ffprobe_available():
        raise RuntimeError("ffprobe is not installed")

    result = _run([
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        str(video_path),
    ])

    data = json.loads(result.stdout)

    return float(data["format"]["duration"])


def extract_audio(
    video_path: str | Path,
    output_name: str
) -> Path:

    if not ffmpeg_available():
        raise RuntimeError("FFmpeg is not installed")

    output_path = TEMP_DIR / output_name

    _run([
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        str(output_path),
    ])

    return output_path


def cut_clip(
    video_path: str | Path,
    start: float,
    duration: float,
    output_name: str
) -> Path:

    if not ffmpeg_available():
        raise RuntimeError("FFmpeg is not installed")

    output_path = OUTPUT_DIR / output_name

    _run([
        "ffmpeg",
        "-y",
        "-ss", str(start),
        "-i", str(video_path),
        "-t", str(duration),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-movflags", "+faststart",
        str(output_path),
    ])

    return output_path


def convert_to_vertical(
    video_path: str | Path,
    output_name: str
) -> Path:

    if not ffmpeg_available():
        raise RuntimeError("FFmpeg is not installed")

    output_path = OUTPUT_DIR / output_name

    _run([
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vf",
        (
            "scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
        ),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-movflags", "+faststart",
        str(output_path),
    ])

    return output_path
