from pathlib import Path


def create_srt(
    segments: list,
    output_path: str | Path
) -> Path:

    output_path = Path(output_path)

    lines = []

    for index, segment in enumerate(
        segments,
        start=1
    ):
        start = segment.get("start", 0)
        end = segment.get("end", start + 2)
        text = segment.get("text", "").strip()

        if not text:
            continue

        lines.append(
            f"{index}\n"
            f"{format_timestamp(start)} --> "
            f"{format_timestamp(end)}\n"
            f"{text}\n"
        )

    output_path.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    return output_path


def format_timestamp(seconds: float) -> str:

    seconds = max(0, float(seconds))

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int(
        round((seconds - int(seconds)) * 1000)
    )

    if milliseconds >= 1000:
        milliseconds = 999

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d},"
        f"{milliseconds:03d}"
    )
