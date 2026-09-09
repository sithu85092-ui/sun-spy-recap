from pathlib import Path
import asyncio
import edge_tts


DEFAULT_VOICE = "my-MM-NilarNeural"


async def synthesize(
    text,
    output_path,
    voice=DEFAULT_VOICE,
):
    text = (text or "").strip()

    if not text:
        raise ValueError("Narration text is empty")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Try Burmese voice first, then fallback voices.
    voices = [
        voice,
        "my-MM-ThihaNeural",
        "en-US-JennyNeural",
    ]

    last_error = None

    for current_voice in voices:
        for attempt in range(3):
            try:
                if output_path.exists():
                    output_path.unlink()

                communicator = edge_tts.Communicate(
                    text,
                    current_voice,
                )

                await communicator.save(
                    str(output_path)
                )

                # Make sure audio file was actually created.
                if output_path.exists() and output_path.stat().st_size > 1000:
                    return output_path

                raise RuntimeError(
                    f"TTS produced an empty audio file using {current_voice}"
                )

            except Exception as error:
                last_error = error

                # Wait before retry.
                await asyncio.sleep(2 * (attempt + 1))

    raise RuntimeError(
        f"TTS failed after retries: {last_error}"
    )
