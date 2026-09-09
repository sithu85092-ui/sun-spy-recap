import subprocess
from pathlib import Path


def detect_scenes(video_path: str | Path) -> list[dict]:
    """
    Detect scene boundaries using FFmpeg.
    Returns a list of scene timestamps.
    """

    video_path = Path(video_path)

    if not video_path.exists():
        raise FileNotFoundError(
            f"Video not found: {video_path}"
        )

    command = [
        "ffmpeg",
        "-i",
        str(video_path),
        "-vf",
        "select='gt(scene,0.35)',showinfo",
        "-an",
        "-f",
        "null",
        "-"
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    timestamps = []

    for line in result.stderr.splitlines():

        if "pts_time:" not in line:
            continue

        try:
            value = line.split("pts_time:")[1]
            timestamp = float(value.split()[0])

            timestamps.append({
                "time": timestamp
            })

        except (ValueError, IndexError):
            continue

    return timestamps


def choose_highlight(
    video_path: str | Path,
    clip_duration: float = 30.0
) -> dict:
    """
    Choose a highlight region from detected scenes.
    """

    scenes = detect_scenes(video_path)

    if not scenes:
        return {
            "start": 0.0,
            "duration": clip_duration,
            "score": 0.0,
            "reason": "No scene changes detected"
        }

    # Simple first-stage scoring.
    # Later this will be replaced by AI scoring.
    best_scene = scenes[0]

    start = max(
        0.0,
        best_scene["time"] - clip_duration / 2
    )

    return {
        "start": round(start, 2),
        "duration": clip_duration,
        "score": 0.5,
        "reason": "Scene-change based highlight detection"
    }
