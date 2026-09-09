from backend.services.ffmpeg import (
    render_vertical_with_audio,
)


def render_final(
    video_path,
    narration_path,
    subtitle_path,
    output_name,
):

    return render_vertical_with_audio(
        video_path,
        narration_path,
        subtitle_path,
        output_name,
    )
