from pathlib import Path
import asyncio
import edge_tts

VOICES = [
    "my-MM-NilarNeural",
    "my-MM-ThihaNeural",
]


async def edge_generate(text, output_path, voice):
    communicator = edge_tts.Communicate(
        text,
        voice,
        rate="+0%",
        volume="+0%",
        pitch="+0Hz",
    )

    await communicator.save(str(output_path))

    if output_path.exists() and output_path.stat().st_size > 1000:
        return output_path

    raise RuntimeError("Edge TTS returned an empty audio file.")


def gtts_generate(text, output_path):
    from gtts import gTTS

    tts = gTTS(
        text=text,
        lang="my",
        slow=False,
    )

    tts.save(str(output_path))

    if output_path.exists() and output_path.stat().st_size > 1000:
        return output_path

    raise RuntimeError("gTTS returned an empty audio file.")


async def synthesize(text, output_path, voice=None):
    text = (text or "").strip()

    if not text:
        raise ValueError("Narration text is empty.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    voices = []

    if voice:
        voices.append(voice)

    for item in VOICES:
        if item not in voices:
            voices.append(item)

    errors = []

    # Try Microsoft Edge TTS
    for selected_voice in voices:
        for attempt in range(1, 4):
            try:
                if output_path.exists():
                    output_path.unlink()

                print(
                    f"TTS Edge: {selected_voice} attempt={attempt}",
                    flush=True,
                )

                result = await edge_generate(
                    text,
                    output_path,
                    selected_voice,
                )

                print("Edge TTS successful.", flush=True)

                return result

            except Exception as error:
                errors.append(
                    f"Edge/{selected_voice}: {error}"
                )

                print(
                    f"Edge TTS failed: {error}",
                    flush=True,
                )

                await asyncio.sleep(2)

    # Fallback to Google TTS
    for attempt in range(1, 4):
        try:
            if output_path.exists():
                output_path.unlink()

            print(
                f"TTS fallback: gTTS attempt={attempt}",
                flush=True,
            )

            result = await asyncio.to_thread(
                gtts_generate,
                text,
                output_path,
            )

            print("gTTS successful.", flush=True)

            return result

        except Exception as error:
            errors.append(f"gTTS: {error}")

            print(
                f"gTTS failed: {error}",
                flush=True,
            )

            await asyncio.sleep(2)

    raise RuntimeError(
        "Burmese AI voice generation failed. "
        "All TTS engines failed.\n"
        + "\n".join(errors[-10:])
    )
