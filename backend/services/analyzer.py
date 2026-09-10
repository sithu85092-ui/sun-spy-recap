import re
from pathlib import Path


KEYWORDS = re.compile(
    r"""
    (
        important|interesting|amazing|surprise|secret|
        finally|suddenly|danger|problem|solution|
        best|worst|crazy|shocking|revealed|
        အရေးကြီး|စိတ်ဝင်စား|အံ့သြ|အံ့ဩ|လျှို့ဝှက်|
        နောက်ဆုံး|ရုတ်တရက်|အန္တရာယ်|ပြဿနာ|ဖြေရှင်း|
        အကောင်းဆုံး|အဆိုးဆုံး|ထိတ်လန့်|ဖော်ပြ
    )
    """,
    re.I | re.X,
)


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _score_segment(segment, index, total):
    text = str(segment.get("text", "")).strip()

    if not text:
        return -1.0

    start = _safe_float(segment.get("start"))
    end = _safe_float(segment.get("end"), start + 1)
    duration = max(0.1, end - start)

    score = 0.0

    # 1. Meaningful dialogue
    words = len(text.split())

    if words >= 5:
        score += 15

    if words >= 10:
        score += 10

    # 2. Interesting keywords
    keyword_matches = len(KEYWORDS.findall(text))
    score += min(keyword_matches * 20, 40)

    # 3. Longer meaningful speech
    if duration >= 2:
        score += 5

    if duration >= 4:
        score += 5

    # 4. Avoid choosing only the very beginning
    if total > 1:
        position = index / max(1, total - 1)

        if 0.15 <= position <= 0.85:
            score += 10

        if 0.25 <= position <= 0.75:
            score += 5

    # 5. Avoid extremely short filler
    filler = re.compile(
        r"^(ဟုတ်|အင်း|အော်|oh|ok|okay|yes|no|嗯|啊|哦)$",
        re.I,
    )

    if filler.fullmatch(text.strip()):
        score -= 30

    return score


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

    clip_duration = max(
        5.0,
        float(clip_duration),
    )

    segments = transcript_segments or []

    if not segments:
        return {
            "start": 0.0,
            "duration": clip_duration,
            "score": 0.0,
            "reason": "No transcript segments available",
        }

    # --------------------------------
    # Score every transcript segment
    # --------------------------------

    scored = []

    total = len(segments)

    for index, segment in enumerate(segments):
        score = _score_segment(
            segment,
            index,
            total,
        )

        if score < 0:
            continue

        start = _safe_float(
            segment.get("start")
        )

        scored.append({
            "index": index,
            "start": start,
            "score": score,
            "text": str(
                segment.get("text", "")
            ).strip(),
        })

    if not scored:
        return {
            "start": 0.0,
            "duration": clip_duration,
            "score": 0.0,
            "reason": "Transcript contains no usable speech",
        }

    # --------------------------------
    # Best segment
    # --------------------------------

    best = max(
        scored,
        key=lambda item: item["score"],
    )

    # Start slightly before important speech
    start = max(
        0.0,
        best["start"] - 3.0,
    )

    # --------------------------------
    # Prevent clip from exceeding video
    # --------------------------------

    try:
        from backend.services.ffmpeg import get_duration

        video_duration = float(
            get_duration(path)
        )

        if video_duration > 0:
            if start + clip_duration > video_duration:
                start = max(
                    0.0,
                    video_duration - clip_duration,
                )

            clip_duration = min(
                clip_duration,
                video_duration,
            )

    except Exception as error:
        print(
            f"[ANALYZER] Duration check skipped: {error}",
            flush=True,
        )

    result = {
        "start": round(start, 3),
        "duration": round(
            clip_duration,
            3,
        ),
        "score": round(
            best["score"],
            2,
        ),
        "reason": (
            "Highest-scoring transcript "
            "highlight"
        ),
        "text": best["text"],
    }

    print(
        "[ANALYZER] Selected highlight:",
        result,
        flush=True,
    )

    return result
