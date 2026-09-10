import re
from pathlib import Path


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

            text = segment.get("text", "")

            if keywords.search(text):

                start = max(
                    0.0,
                    float(
                        segment.get("start", 0.0)
                    ) - 3.0,
                )

                return {
                    "start": start,
                    "duration": clip_duration,
                    "score": 0.9,
                    "reason": "Transcript emphasis match",
                }

        # Use a middle transcript segment
        # when no keyword is found.
        segment = transcript_segments[
            len(transcript_segments) // 2
        ]

        start = max(
            0.0,
            float(
                segment.get("start", 0.0)
            ) - 3.0,
        )

        return {
            "start": start,
            "duration": clip_duration,
            "score": 0.5,
            "reason": "Transcript midpoint highlight",
        }

    return {
        "start": 0.0,
        "duration": clip_duration,
        "score": 0.2,
        "reason": "Beginning fallback",
    }
