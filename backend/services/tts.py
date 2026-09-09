from pathlib import Path

import edge_tts


DEFAULT_VOICE = (
    "my-MM-NilarNeural"
)


async def synthesize(
    text,
    output_path,
    voice=DEFAULT_VOICE,
):

    text = (
        text or ""
    ).strip()

    if not text:

        raise ValueError(
            "Narration text is empty"
        )

    output_path = Path(
        output_path
    )

    communicator = (
        edge_tts.Communicate(
            text,
            voice,
        )
    )

    await communicator.save(
        str(output_path)
    )

    return output_path
