import re
import subprocess

from pathlib import Path


def detect_scenes(
    video_path,
):

    path = Path(video_path)

    result = subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(path),
            "-vf",
            "select='gt(scene,0.30)',showinfo",
            "-an",
            "-f",
            "null",
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    timestamps = []

    for line in result.stderr.splitlines():

        if "pts_time:" not in line:
            continue

        try:

            value = (
                line
                .split("pts_time:")[1]
                .split()[0]
            )

            timestamps.append({
                "time": float(value)
            })

        except (
            ValueError,
            IndexError,
        ):
            continue

    return timestamps


def choose_highlight(
    video_path,
    clip_duration=30.0,
    transcript_segments=None,
):

    path = Path(video_path)

    if not path.exists():

        raise FileNotFoundError(
            f"Video not found: {path}"
        )

    scenes = detect_scenes(
        path
    )

    if transcript_segments:

        keywords = re.compile(
            r"("
            r"important|finally|secret|best|"
            r"amazing|surprise|"
            r"အရေးကြီး|နောက်ဆုံး|"
            r"လျှို့ဝှက်|အံ့သြ|"
            r"အကောင်းဆုံး"
            r")",
            re.I,
        )

        for segment in transcript_segments:

            if keywords.search(
                segment.get(
                    "text",
                    "",
                )
            ):

                start = max(
                    0.0,
                    float(
                        segment["start"]
                    ) - 5.0,
                )

                return {
                    "start": start,
                    "duration": clip_duration,
                    "score": 0.9,
                    "reason": (
                        "Transcript "
                        "emphasis match"
                    ),
                }

    if scenes:

        middle_index = (
            len(scenes) // 2
        )

        candidate = scenes[
            min(
                len(scenes) - 1,
                middle_index,
            )
        ]

        start = max(
            0.0,
            candidate["time"]
            - clip_duration / 2,
        )

        return {
            "start": start,
            "duration": clip_duration,
            "score": 0.6,
            "reason": (
                "Scene-change "
                "highlight"
            ),
        }

    return {
        "start": 0.0,
        "duration": clip_duration,
        "score": 0.2,
        "reason": (
            "Fallback beginning "
            "of video"
        ),
    }
