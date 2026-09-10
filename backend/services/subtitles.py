from pathlib import Path
import re


# ==========================================
# TIMESTAMP
# ==========================================

def format_timestamp(seconds):
    seconds = max(
        0.0,
        float(seconds),
    )

    total_ms = int(
        round(seconds * 1000)
    )

    hours, remainder = divmod(
        total_ms,
        3600000,
    )

    minutes, remainder = divmod(
        remainder,
        60000,
    )

    secs, milliseconds = divmod(
        remainder,
        1000,
    )

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d},"
        f"{milliseconds:03d}"
    )


# ==========================================
# BURMESE TEXT → SENTENCES
# ==========================================

def split_sentences(text):
    """
    Split Burmese narration into subtitle-sized
    sentences/phrases.
    """

    text = str(text or "").strip()

    if not text:
        return []

    # Burmese / English sentence endings
    parts = re.split(
        r"(?<=[။!?])\s+|(?<=[.!?])\s+",
        text,
    )

    parts = [
        part.strip()
        for part in parts
        if part.strip()
    ]

    # If AI returned one very long paragraph,
    # split it into smaller chunks.
    result = []

    for part in parts:

        if len(part) <= 55:
            result.append(part)
            continue

        words = part.split()

        current = ""

        for word in words:

            candidate = (
                f"{current} {word}"
                if current
                else word
            )

            if len(candidate) <= 55:
                current = candidate

            else:

                if current:
                    result.append(
                        current.strip()
                    )

                current = word

        if current:
            result.append(
                current.strip()
            )

    return result


# ==========================================
# CREATE BURMESE NARRATOR SRT
# ==========================================

def create_srt(
    text,
    output_path,
    duration=None,
):
    """
    Create subtitles from the Burmese narrator text.

    Parameters
    ----------
    text:
        Burmese recap/narration text.

    output_path:
        Destination .srt file.

    duration:
        Total duration of the narrator audio.

    Important:
        This does NOT use the original transcript.
        The subtitle follows the Burmese narrator.
    """

    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    text = str(
        text or ""
    ).strip()

    if not text:
        raise ValueError(
            "Subtitle text is empty."
        )

    if duration is None:
        raise ValueError(
            "Narration duration is required."
        )

    duration = max(
        0.5,
        float(duration),
    )

    sentences = split_sentences(
        text
    )

    if not sentences:
        raise ValueError(
            "Could not split subtitle text."
        )

    # ==========================================
    # Calculate duration by text length
    # ==========================================

    total_length = sum(
        max(
            1,
            len(sentence),
        )
        for sentence in sentences
    )

    blocks = []

    current_time = 0.0

    for index, sentence in enumerate(
        sentences,
        start=1,
    ):

        text_length = max(
            1,
            len(sentence),
        )

        # Give each subtitle a proportional
        # amount of narration time.
        block_duration = (
            duration
            * text_length
            / total_length
        )

        # Keep subtitles readable.
        block_duration = max(
            1.5,
            min(
                6.0,
                block_duration,
            ),
        )

        start = current_time

        # Last subtitle must end exactly
        # at the narration duration.
        if index == len(sentences):

            end = duration

        else:

            end = min(
                duration,
                start + block_duration,
            )

        if end <= start:
            continue

        blocks.append(
            f"{len(blocks) + 1}\n"
            f"{format_timestamp(start)} --> "
            f"{format_timestamp(end)}\n"
            f"{sentence}\n"
        )

        current_time = end

    # ==========================================
    # Fix gaps / overflow
    # ==========================================

    if blocks:

        # Rewrite the final subtitle end time
        # to match narration exactly.
        last_block = blocks[-1]

        lines = last_block.splitlines()

        if len(lines) >= 3:

            start_time = lines[1].split(
                " --> "
            )[0]

            lines[1] = (
                f"{start_time} --> "
                f"{format_timestamp(duration)}"
            )

            blocks[-1] = (
                "\n".join(lines)
                + "\n"
            )

    output_path.write_text(
        "\n".join(blocks),
        encoding="utf-8",
    )

    print(
        f"[SRT] Created "
        f"{len(blocks)} Burmese subtitle blocks.",
        flush=True,
    )

    print(
        f"[SRT] Narration duration: "
        f"{duration:.2f}s",
        flush=True,
    )

    print(
        f"[SRT] File: "
        f"{output_path}",
        flush=True,
    )

    return output_path
