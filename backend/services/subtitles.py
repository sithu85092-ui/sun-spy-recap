from pathlib import Path


def format_timestamp(
    seconds,
):

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


def create_srt(
    segments,
    output_path,
):

    output_path = Path(
        output_path
    )

    blocks = []

    number = 1

    for segment in segments:

        text = (
            segment
            .get("text", "")
            .strip()
        )

        if not text:
            continue

        start = float(
            segment.get(
                "start",
                0,
            )
        )

        end = max(
            start + 0.5,
            float(
                segment.get(
                    "end",
                    start + 2,
                )
            ),
        )

        blocks.append(
            f"{number}\n"
            f"{format_timestamp(start)} --> "
            f"{format_timestamp(end)}\n"
            f"{text}\n"
        )

        number += 1

    output_path.write_text(
        "\n".join(blocks),
        encoding="utf-8",
    )

    return output_path
