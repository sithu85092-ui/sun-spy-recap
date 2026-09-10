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
        raise RuntimeError("ffprobe is not installed")

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

    duration = data.get("format", {}).get("duration")

    if duration is None:
        raise RuntimeError(
            f"Could not determine media duration: {video_path}"
        )

    return float(duration)


def extract_audio(
    video_path,
    output_name,
):
    if not ffmpeg_available():
        raise RuntimeError("FFmpeg is not installed")

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

        # Original video audio -> Whisper
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

    print(
        f"[AUDIO OK] {output_path}",
        flush=True,
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

        # Intermediate clip only.
        # Original audio can exist here because
        # final render will NOT map it.
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
    """
    Final SUN SPY RECAP renderer.

    IMPORTANT:
    - Original video audio is NEVER mapped.
    - Only Burmese narration audio is mapped.
    - Burmese SRT is burned into the video.
    - Output is 720x1280 (9:16).
    """

    if not ffmpeg_available():
        raise RuntimeError(
            "FFmpeg is not installed"
        )

    video_path = Path(video_path)
    narration_path = Path(narration_path)

    if not video_path.exists():
        raise FileNotFoundError(
            f"Video not found: {video_path}"
        )

    if not narration_path.exists():
        raise FileNotFoundError(
            f"Narration audio not found: {narration_path}"
        )

    if narration_path.stat().st_size < 1000:
        raise RuntimeError(
            "Narration audio file is empty."
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = OUTPUT_DIR / output_name

    # ---------------------------------------
    # 9:16 VIDEO
    # ---------------------------------------

    vertical_filter = (
        "scale=720:1280:"
        "force_original_aspect_ratio=decrease,"
        "pad=720:1280:"
        "(ow-iw)/2:"
        "(oh-ih)/2:black"
    )

    # ---------------------------------------
    # INPUTS
    #
    # Input 0 = video
    # Input 1 = Burmese narration
    # ---------------------------------------

    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",

        "-threads",
        "1",

        # Video input
        "-i",
        str(video_path),

        # Narrator input
        "-i",
        str(narration_path),
    ]

    # ---------------------------------------
    # BURMESE SUBTITLE
    # ---------------------------------------

    subtitle_exists = (
        subtitle_path
        and Path(subtitle_path).exists()
        and Path(subtitle_path).stat().st_size > 0
    )

    if subtitle_exists:
        subtitle_file = (
            Path(subtitle_path)
            .resolve()
            .as_posix()
            .replace(":", r"\:")
            .replace("'", r"\'")
        )

        video_filter = (
            f"{vertical_filter},"
            f"subtitles='{subtitle_file}'"
        )

        print(
            f"[SUBTITLE] Burmese SRT found: {subtitle_path}",
            flush=True,
        )

    else:
        video_filter = vertical_filter

        print(
            "[SUBTITLE] No subtitle file found. "
            "Rendering without subtitles.",
            flush=True,
        )

    # ---------------------------------------
    # STREAM MAPPING
    # ---------------------------------------

    command.extend([
        "-vf",
        video_filter,

        # ONLY video from original video
        "-map",
        "0:v:0",

        # ONLY narration from input 1
        "-map",
        "1:a:0",

        # Ignore original video audio completely.
        # This is the important part.
        "-map_metadata",
        "-1",

        # -----------------------------------
        # VIDEO
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
        # AUDIO
        # -----------------------------------

        "-c:a",
        "aac",

        "-b:a",
        "96k",

        "-ac",
        "2",

        # -----------------------------------
        # AUDIO/VISUAL SYNC
        # -----------------------------------

        "-shortest",

        # -----------------------------------
        # MP4
        # -----------------------------------

        "-movflags",
        "+faststart",

        str(output_path),
    ])

    print(
        "[FINAL RENDER] "
        "9:16 + Burmese Narrator + Burmese Subtitle...",
        flush=True,
    )

    _run(command)

    # ---------------------------------------
    # VERIFY OUTPUT
    # ---------------------------------------

    if not output_path.exists():
        raise RuntimeError(
            "Final video was not created."
        )

    if output_path.stat().st_size < 1000:
        raise RuntimeError(
            "Final video is empty."
        )

    # Verify final streams
    try:
        verify = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_streams",
                str(output_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True,
        )

        stream_data = json.loads(
            verify.stdout
        )

        streams = stream_data.get(
            "streams",
            [],
        )

        video_streams = [
            stream
            for stream in streams
            if stream.get("codec_type") == "video"
        ]

        audio_streams = [
            stream
            for stream in streams
            if stream.get("codec_type") == "audio"
        ]

        if not video_streams:
            raise RuntimeError(
                "Final video has no video stream."
            )

        if not audio_streams:
            raise RuntimeError(
                "Final video has NO audio stream. "
                "Narrator audio was not included."
            )

        print(
            "[VERIFY] Final video stream: OK",
            flush=True,
        )

        print(
            "[VERIFY] Final narration audio: OK",
            flush=True,
        )

        print(
            f"[VERIFY] Audio streams: "
            f"{len(audio_streams)}",
            flush=True,
        )

    except RuntimeError:
        raise

    except Exception as error:
        print(
            f"[VERIFY] Stream check skipped: {error}",
            flush=True,
        )

    print(
        f"[FINAL VIDEO OK] {output_path}",
        flush=True,
    )

    print(
        f"[FINAL VIDEO SIZE] "
        f"{output_path.stat().st_size} bytes",
        flush=True,
    )

    return output_path
