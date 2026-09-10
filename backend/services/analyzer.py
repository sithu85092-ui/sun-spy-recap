import re
from pathlib import Path


def choose_highlight(
    video_path,
    clip_duration=30.0,
    transcript_segments=None,
):
    """
    Fast highlight selection for Render Free.
    Avoids running full-video FFmpeg scene detection.
    """

    path = Path(video_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Video not found: {path}"
        )

    duration = float(clip_duration)

    # Prefer transcript segments containing interesting keywords.
    if transcript_segments:

        keywords = re.compile(
            r"("
            r"important|finally|secret|best|"
            r"amazing|surprise|interesting|"
            r"အရေးကြီး|နောက်ဆုံး|လျှို့ဝှက်|"
            r"အံ့သြ|အကောင်းဆုံး|စိတ်ဝင်စား"
            r")",
            re.I,
        )

        for segment in transcript_segments:

            text = segment.get(
                "text",
                "",
            )

            if keywords.search(text):

                start = max(
                    0.0,
                    float(
                        segment.get(
                            "start",
                            0.0,
                        )
                    ) - 3.0,
                )

                return {
                    "start": start,
                    "duration": duration,
                    "score": 0.9,
                    "reason": "Transcript emphasis match",
                }

    # If no keyword is found, use the first meaningful
    # transcript segment instead of scanning the whole video.
    if transcript_segments:

        segment = transcript_segments[
            min(
                len(transcript_segments) - 1,
                len(transcript_segments) // 2,
            )
        ]

        start = max(
            0.0,
            float(
                segment.get(
                    "start",
                    0.0,
                )
            ) - 3.0,
        )

        return {
            "start": start,
            "duration": duration,
            "score": 0.5,
            "reason": "Transcript midpoint highlight",
        }

    # Final fallback.
    return {
        "start": 0.0,
        "duration": duration,
        "score": 0.2,
        "reason": "Beginning of video fallback",
    }
