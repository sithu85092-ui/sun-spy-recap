import json
import shutil
import subprocess

from pathlib import Path

from backend.config import (
    TEMP_DIR,
    OUTPUT_DIR,
)


def ffmpeg_available():

    return shutil.which(
        "ffmpeg"
    ) is not None


def ffprobe_available():

    return shutil.which(
        "ffprobe"
    ) is not None


def _run(command):

    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )


def get_duration(
    video_path,
):

    if not ffprobe_available():

        raise RuntimeError(
            "ffprobe is not installed"
        )

    result = _run([
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        str(video_path),
    ])

    data = json.loads(
        result.stdout
    )

    return float(
        data["format"]["duration"]
    )


def extract_audio(
    video_path,
    output_name,
):

    if not ffmpeg_available():

        raise RuntimeError(
            "FFmpeg is not installed"
        )

    output_path = (
        TEMP_DIR /
        output_name
    )

    _run([
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ])

    return output_path


def cut_clip(
    video_path,
    start,
    duration,
    output_name,
):

    if not ffmpeg_available():

        raise RuntimeError(
            "FFmpeg is not installed"
        )

    output_path = (
        OUTPUT_DIR /
        output_name
    )

    _run([
        "ffmpeg",
        "-y",
        "-ss",
        str(max(0, start)),
        "-i",
        str(video_path),
        "-t",
        str(max(1, duration)),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(output_path),
    ])

    return output_path


def render_vertical_with_audio(
    video_path,
    narration_path,
    subtitle_path,
    output_name,
):

    if not ffmpeg_available():

        raise RuntimeError(
            "FFmpeg is not installed"
        )

    output_path = (
        OUTPUT_DIR /
        output_name
    )

    vertical_filter = (
        "scale=1080:1920:"
        "force_original_aspect_ratio=decrease,"
        "pad=1080:1920:"
        "(ow-iw)/2:"
        "(oh-ih)/2:black"
    )

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(narration_path),
    ]

    if (
        subtitle_path
        and Path(subtitle_path).exists()
    ):

        subtitle_file = (
            Path(subtitle_path)
            .as_posix()
            .replace(":", r"\:")
        )

        video_filter = (
            f"{vertical_filter},"
            f"subtitles={subtitle_file}"
        )

        command.extend([
            "-vf",
            video_filter,
        ])

    else:

        command.extend([
            "-vf",
            vertical_filter,
        ])

    command.extend([
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-shortest",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(output_path),
    ])

    _run(command)

    return output_path
