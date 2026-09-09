from pathlib import Path

from backend.services.ffmpeg import cut_clip


def create_highlight_clip(
    video_path: str | Path,
    start: float,
    duration: float,
    output_name: str
) -> Path:

    return cut_clip(
        video_path=video_path,
        start=start,
        duration=duration,
        output_name=output_name
    )
