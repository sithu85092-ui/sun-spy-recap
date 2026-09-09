from backend.services.ffmpeg import (
    cut_clip,
)


def create_highlight_clip(
    video_path,
    start,
    duration,
    output_name,
):

    return cut_clip(
        video_path=video_path,
        start=start,
        duration=duration,
        output_name=output_name,
    )
