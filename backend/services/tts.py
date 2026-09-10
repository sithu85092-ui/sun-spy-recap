from pathlib import Path
import asyncio
import re

import edge_tts


# ==========================================
# BURMESE MICROSOFT VOICES
# ==========================================

VOICES = [
    "my-MM-NilarNeural",
    "my-MM-ThihaNeural",
]


# ==========================================
# BURMESE VALIDATION
# ==========================================

def has_burmese(text):
    return any(
        "\u1000" <= char <= "\u109f"
        for char in str(text or "")
    )


def clean_text(text):
    text = str(
        text or ""
    ).strip()

    # Remove markdown accidentally returned
    # by an AI model.
    text = re.sub(
        r"\*\*|\*|__|_",
        "",
        text,
    )

    text = text.replace(
        "```",
        "",
    )

    # Remove excessive spaces
    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text


# ==========================================
# EDGE TTS
# ==========================================

async def edge_generate(
    text,
    output_path,
    voice,
):
    communicator = edge_tts.Communicate(
        text,
        voice,
        rate="+0%",
        volume="+0%",
        pitch="+0Hz",
    )

    await communicator.save(
        str(output_path)
    )

    if (
        output_path.exists()
        and output_path.stat().st_size > 1000
    ):
        return output_path

    raise RuntimeError(
        "Edge TTS returned an empty audio file."
    )


# ==========================================
# GOOGLE TTS FALLBACK
# ==========================================

def gtts_generate(
    text,
    output_path,
):
    from gtts import gTTS

    tts = gTTS(
        text=text,
        lang="my",
        slow=False,
    )

    tts.save(
        str(output_path)
    )

    if (
        output_path.exists()
        and output_path.stat().st_size > 1000
    ):
        return output_path

    raise RuntimeError(
        "gTTS returned an empty audio file."
    )


# ==========================================
# MAIN TTS FUNCTION
# ==========================================

async def synthesize(
    text,
    output_path,
    voice=None,
):
    text = clean_text(
        text
    )

    if not text:
        raise ValueError(
            "Narration text is empty."
        )

    # ==========================================
    # IMPORTANT:
    # TTS should only receive Burmese narration.
    # ==========================================

    if not has_burmese(text):

        raise ValueError(
            "TTS refused non-Burmese narration. "
            "Narrator must return Burmese text."
        )

    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Delete old output
    if output_path.exists():

        try:
            output_path.unlink()
        except Exception:
            pass

    voices = []

    if voice:
        voices.append(
            voice
        )

    for item in VOICES:

        if item not in voices:
            voices.append(
                item
            )

    errors = []

    # ==========================================
    # 1. MICROSOFT EDGE TTS
    # ==========================================

    for selected_voice in voices:

        # Only 2 attempts per voice.
        for attempt in range(1, 3):

            try:

                if output_path.exists():
                    output_path.unlink()

                print(
                    f"[TTS] Edge "
                    f"{selected_voice} "
                    f"attempt={attempt}",
                    flush=True,
                )

                result = await edge_generate(
                    text,
                    output_path,
                    selected_voice,
                )

                print(
                    f"[TTS] Edge successful: "
                    f"{selected_voice}",
                    flush=True,
                )

                print(
                    f"[TTS] Audio size: "
                    f"{result.stat().st_size} bytes",
                    flush=True,
                )

                return result

            except Exception as error:

                errors.append(
                    f"Edge/{selected_voice}: "
                    f"{error}"
                )

                print(
                    f"[TTS] Edge failed: "
                    f"{error}",
                    flush=True,
                )

                # Small retry delay
                await asyncio.sleep(
                    1.5
                )

    # ==========================================
    # 2. GOOGLE TTS FALLBACK
    # ==========================================

    for attempt in range(1, 3):

        try:

            if output_path.exists():
                output_path.unlink()

            print(
                f"[TTS] gTTS fallback "
                f"attempt={attempt}",
                flush=True,
            )

            result = await asyncio.to_thread(
                gtts_generate,
                text,
                output_path,
            )

            print(
                "[TTS] gTTS successful.",
                flush=True,
            )

            print(
                f"[TTS] Audio size: "
                f"{result.stat().st_size} bytes",
                flush=True,
            )

            return result

        except Exception as error:

            errors.append(
                f"gTTS: {error}"
            )

            print(
                f"[TTS] gTTS failed: "
                f"{error}",
                flush=True,
            )

            await asyncio.sleep(
                1.5
            )

    # ==========================================
    # ALL TTS FAILED
    # ==========================================

    raise RuntimeError(
        "Myanmar narrator voice generation failed.\n"
        + "\n".join(
            errors[-8:]
        )
    )
