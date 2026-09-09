from pathlib import Path

from backend.services.ffmpeg import (
    ffmpeg_available,
    get_duration,
    extract_audio,
)


def inspect_video(
    video_path,
):

    path = Path(video_path)

    if not path.exists():

        raise FileNotFoundError(
            f"Video not found: {path}"
        )

    if not ffmpeg_available():

        return {
            "success": False,
            "error": "FFmpeg is not installed",
        }

    duration = get_duration(
        path
    )

    return {
        "success": True,
        "filename": path.name,
        "duration": duration,
        "duration_seconds": round(
            duration,
            2,
        ),
    }


def prepare_audio(
    video_path,
):

    path = Path(video_path)

    audio_path = extract_audio(
        path,
        f"{path.stem}.wav",
    )

    return {
        "success": True,
        "audio_file": str(
            audio_path
        ),
    }
