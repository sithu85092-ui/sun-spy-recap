import json
import shutil
import subprocess

from pathlib import Path

from backend.config import (
    TEMP_DIR,
    OUTPUT_DIR,
)


def ffmpeg_available():
    return shutil.which("ffmpeg") is not None


def ffprobe_available():
    return shutil.which("ffprobe") is not None


def _run(command):
    print(
        "[FFMPEG]",
        " ".join(map(str, command)),
        flush=True,
    )

    result = subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=None,
        text=True,
        check=True,
    )

    return result


def get_duration(video_path):

    if not ffprobe_available():
        raise RuntimeError(
            "ffprobe is not installed"
        )

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            str(video_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=True,
    )

    data = json.loads(result.stdout)

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

    TEMP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = TEMP_DIR / output_name

    _run([
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-threads",
        "1",
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

    if not output_path.exists():
        raise RuntimeError(
            "Audio extraction failed."
        )

    if output_path.stat().st_size < 1000:
        raise RuntimeError(
            "Extracted audio is empty."
        )

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

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = OUTPUT_DIR / output_name

    start = max(
        0.0,
        float(start),
    )

    duration = max(
        1.0,
        float(duration),
    )

    _run([
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        str(start),
        "-i",
        str(video_path),
        "-t",
        str(duration),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c",
        "copy",
        "-avoid_negative_ts",
        "make_zero",
        "-movflags",
        "+faststart",
        str(output_path),
    ])

    if not output_path.exists():
        raise RuntimeError(
            "Highlight clip was not created."
        )

    if output_path.stat().st_size < 1000:
        raise RuntimeError(
            "Highlight clip is empty."
        )

    print(
        f"[CLIP OK] {output_path}",
        flush=True,
    )

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

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = OUTPUT_DIR / output_name

    # ---------------------------------------
    # FAST 9:16 RENDER
    # Render Free instance အတွက် 720x1280
    # ---------------------------------------

    vertical_filter = (
        "scale=720:1280:"
        "force_original_aspect_ratio=decrease,"
        "pad=720:1280:"
        "(ow-iw)/2:"
        "(oh-ih)/2:black"
    )

    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",

        # Keep CPU usage predictable
        "-threads",
        "1",

        # Input video
        "-i",
        str(video_path),

        # Burmese narration
        "-i",
        str(narration_path),
    ]

    # ---------------------------------------
    # SUBTITLE
    # ---------------------------------------

    if (
        subtitle_path
        and Path(subtitle_path).exists()
    ):

        subtitle_file = (
            Path(subtitle_path)
            .resolve()
            .as_posix()
            .replace(":", r"\:")
        )

        video_filter = (
            f"{vertical_filter},"
            f"subtitles={subtitle_file}"
        )

    else:

        video_filter = vertical_filter

    command.extend([
        "-vf",
        video_filter,

        # Video
        "-map",
        "0:v:0",

        # Narration
        "-map",
        "1:a:0",

        # Stop when shortest stream ends
        "-shortest",

        # -----------------------------------
        # FAST H.264
        # -----------------------------------

        "-c:v",
        "libx264",

        "-preset",
        "ultrafast",

        "-crf",
        "30",

        "-pix_fmt",
        "yuv420p",

        # -----------------------------------
        # Audio
        # -----------------------------------

        "-c:a",
        "aac",

        "-b:a",
        "96k",

        # -----------------------------------
        # MP4
        # -----------------------------------

        "-movflags",
        "+faststart",

        str(output_path),
    ])

    print(
        "[FINAL RENDER] Fast TikTok 9:16 render started...",
        flush=True,
    )

    _run(command)

    if not output_path.exists():
        raise RuntimeError(
            "Final video was not created."
        )

    if output_path.stat().st_size < 1000:
        raise RuntimeError(
            "Final video is empty."
        )

    print(
        f"[FINAL VIDEO OK] {output_path}",
        flush=True,
    )

    return output_path
