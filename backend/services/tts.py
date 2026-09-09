from pathlib import Path
import asyncio
import edge_tts


VOICES = [
    "my-MM-NilarNeural",
    "my-MM-ThihaNeural",
    "en-US-JennyNeural",
]


async def synthesize(
    text,
    output_path,
    voice=None,
):
    text = (text or "").strip()

    if not text:
        raise ValueError(
            "Narration text is empty"
        )

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # If a specific voice was requested,
    # try it first.
    voices = []

    if voice:
        voices.append(voice)

    for item in VOICES:
        if item not in voices:
            voices.append(item)

    last_error = None

    for selected_voice in voices:

        for attempt in range(1, 4):

            try:

                # Remove broken previous output
                if output_path.exists():
                    output_path.unlink()

                communicator = (
                    edge_tts.Communicate(
                        text,
                        selected_voice
                    )
                )

                await communicator.save(
                    str(output_path)
                )

                # Validate generated audio
                if (
                    output_path.exists()
                    and output_path.stat().st_size > 1000
                ):
                    return output_path

                raise RuntimeError(
                    "Generated audio file is empty."
                )

            except Exception as error:

                last_error = error

                print(
                    f"TTS failed: "
                    f"voice={selected_voice}, "
                    f"attempt={attempt}, "
                    f"error={error}"
                )

                await asyncio.sleep(2)

    raise RuntimeError(
        "Burmese AI voice generation failed. "
        f"Last error: {last_error}"
    )
