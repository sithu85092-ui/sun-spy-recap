from pathlib import Path

from backend.services.ffmpeg import (
    ffmpeg_available,
    get_duration,
    extract_audio,
)


def inspect_video(video_path: str | Path) -> dict:

    video_path = Path(video_path)

    if not video_path.exists():
        raise FileNotFoundError(
            f"Video not found: {video_path}"
        )

    if not ffmpeg_available():
        return {
            "success": False,
            "error": "FFmpeg is not installed"
        }

    duration = get_duration(video_path)

    return {
        "success": True,
        "filename": video_path.name,
        "duration": duration,
        "duration_seconds": round(duration, 2),
    }


def prepare_audio(video_path: str | Path) -> dict:

    video_path = Path(video_path)

    audio_name = f"{video_path.stem}.wav"

    audio_path = extract_audio(
        video_path,
        audio_name
    )

    return {
        "success": True,
        "audio_file": str(audio_path)
    }
