from pathlib import Path

from backend.services.ffmpeg import convert_to_vertical


def render_vertical(
    video_path: str | Path,
    output_name: str
) -> Path:
    """
    Render a video to 1080x1920 vertical format.
    """

    video_path = Path(video_path)

    if not video_path.exists():
        raise FileNotFoundError(
            f"Video not found: {video_path}"
        )

    return convert_to_vertical(
        video_path=video_path,
        output_name=output_name
    )
