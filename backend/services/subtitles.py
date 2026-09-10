from pathlib import Path


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


def create_srt(
    segments,
    output_path,
    clip_start=0.0,
    clip_duration=None,
):
    """
    Create subtitles for the selected highlight clip.

    Important:
    - Original transcript timestamps are converted
      to timestamps relative to the highlight clip.
    - Only subtitles that overlap the selected clip
      are included.
    - This prevents subtitles from appearing outside
      the final video.
    """

    output_path = Path(output_path)

    clip_start = max(
        0.0,
        float(clip_start),
    )

    if clip_duration is not None:
        clip_duration = max(
            0.5,
            float(clip_duration),
        )

    clip_end = None

    if clip_duration is not None:
        clip_end = (
            clip_start
            + clip_duration
        )

    blocks = []

    number = 1

    for segment in segments or []:

        text = str(
            segment.get(
                "text",
                "",
            )
        ).strip()

        if not text:
            continue

        original_start = max(
            0.0,
            float(
                segment.get(
                    "start",
                    0,
                )
            ),
        )

        original_end = max(
            original_start + 0.5,
            float(
                segment.get(
                    "end",
                    original_start + 2,
                )
            ),
        )

        # Ignore segments completely before clip
        if (
            clip_end is not None
            and original_end <= clip_start
        ):
            continue

        # Ignore segments completely after clip
        if (
            clip_end is not None
            and original_start >= clip_end
        ):
            continue

        # Convert original timestamps
        # to highlight-relative timestamps.
        start = max(
            0.0,
            original_start - clip_start,
        )

        end = max(
            start + 0.5,
            original_end - clip_start,
        )

        # Never allow subtitle beyond clip
        if clip_duration is not None:

            start = min(
                start,
                clip_duration,
            )

            end = min(
                end,
                clip_duration,
            )

        if end <= start:
            continue

        blocks.append(
            f"{number}\n"
            f"{format_timestamp(start)} --> "
            f"{format_timestamp(end)}\n"
            f"{text}\n"
        )

        number += 1

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        "\n".join(blocks),
        encoding="utf-8",
    )

    print(
        f"[SRT] Created {number - 1} subtitle blocks: "
        f"{output_path}",
        flush=True,
    )

    return output_path
