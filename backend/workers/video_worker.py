import asyncio

from datetime import (
    datetime,
    timezone,
)

from pathlib import Path

from backend.config import TEMP_DIR

from backend.database import (
    get_job,
    update_job,
)

from backend.services.processor import (
    inspect_video,
    prepare_audio,
)

from backend.services.transcription import (
    transcription_engine,
)

from backend.services.analyzer import (
    choose_highlight,
)

from backend.services.clipper import (
    create_highlight_clip,
)

from backend.services.narrator import (
    narrator,
)

from backend.services.tts import (
    synthesize,
)

from backend.services.subtitles import (
    create_srt,
)

from backend.services.renderer import (
    render_final,
)


def now():

    return datetime.now(
        timezone.utc
    ).isoformat()


async def process_video(
    job_id,
):

    job = get_job(job_id)

    if job is None:
        return

    input_file = Path(
        job["input_file"]
    )

    try:

        # ==========================
        # 1. INSPECT
        # ==========================

        update_job(
            job_id,
            status="PROCESSING",
            progress=5,
            message="Inspecting video...",
            updated_at=now(),
        )

        info = await asyncio.to_thread(
            inspect_video,
            input_file,
        )

        if not info["success"]:

            raise RuntimeError(
                info["error"]
            )

        duration = info[
            "duration"
        ]

        # ==========================
        # 2. AUDIO
        # ==========================

        update_job(
            job_id,
            status="TRANSCRIBING",
            progress=15,
            message="Extracting audio...",
            updated_at=now(),
        )

        audio_result = (
            await asyncio.to_thread(
                prepare_audio,
                input_file,
            )
        )

        audio_file = Path(
            audio_result[
                "audio_file"
            ]
        )

        # ==========================
        # 3. WHISPER
        # ==========================

        update_job(
            job_id,
            status="TRANSCRIBING",
            progress=30,
            message=(
                "Transcribing speech "
                "with Whisper..."
            ),
            updated_at=now(),
        )

        transcription = (
            await asyncio.to_thread(
                transcription_engine.transcribe,
                audio_file,
            )
        )

        if not transcription[
            "success"
        ]:

            raise RuntimeError(
                transcription.get(
                    "error",
                    "Transcription failed",
                )
            )

        transcript = (
            transcription["text"]
            .strip()
        )

        segments = (
            transcription[
                "segments"
            ]
        )

        # ==========================
        # 4. HIGHLIGHT
        # ==========================

        update_job(
            job_id,
            status="ANALYZING",
            progress=45,
            message=(
                "Finding the "
                "best scene..."
            ),
            updated_at=now(),
        )

        clip_duration = min(
            30.0,
            max(
                5.0,
                duration,
            ),
        )

        highlight = (
            await asyncio.to_thread(
                choose_highlight,
                input_file,
                clip_duration,
                segments,
            )
        )

        # ==========================
        # 5. CLIP
        # ==========================

        update_job(
            job_id,
            status="CLIPPING",
            progress=55,
            message=(
                "Creating "
                "highlight clip..."
            ),
            updated_at=now(),
        )

        clip_path = (
            await asyncio.to_thread(
                create_highlight_clip,
                input_file,
                highlight["start"],
                highlight["duration"],
                f"{job_id}_highlight.mp4",
            )
        )

        # ==========================
        # 6. BURMESE RECAP
        # ==========================

        update_job(
            job_id,
            status="NARRATING",
            progress=65,
            message=(
                "Creating "
                "Burmese recap..."
            ),
            updated_at=now(),
        )

        recap = (
            await asyncio.to_thread(
                narrator.create_recap,
                transcript,
            )
        )

        if not recap[
            "success"
        ]:

            raise RuntimeError(
                recap.get(
                    "error",
                    "Recap creation failed",
                )
            )

        recap_text = (
            recap["text"]
            .strip()
        )

        # ==========================
        # 7. BURMESE TTS
        # ==========================

        update_job(
            job_id,
            status="NARRATING",
            progress=72,
            message=(
                "Generating "
                "Burmese voice..."
            ),
            updated_at=now(),
        )

        narration_path = (
            TEMP_DIR /
            f"{job_id}_narration.mp3"
        )

        await synthesize(
            recap_text,
            narration_path,
        )

        # ==========================
        # 8. SUBTITLE
        # ==========================

        update_job(
            job_id,
            status="SUBTITLING",
            progress=80,
            message=(
                "Creating subtitles..."
            ),
            updated_at=now(),
        )

        subtitle_path = (
            TEMP_DIR /
            f"{job_id}.srt"
        )

        create_srt(
            segments,
            subtitle_path,
        )

        # ==========================
        # 9. FINAL 9:16
        # ==========================

        update_job(
            job_id,
            status="RENDERING",
            progress=88,
            message=(
                "Rendering final "
                "9:16 video..."
            ),
            updated_at=now(),
        )

        final_path = (
            await asyncio.to_thread(
                render_final,
                clip_path,
                narration_path,
                subtitle_path,
                f"{job_id}_final.mp4",
            )
        )

        # ==========================
        # 10. COMPLETE
        # ==========================

        update_job(
            job_id,
            status="COMPLETED",
            progress=100,
            message=(
                "Final recap "
                "created successfully."
            ),
            output_file=str(
                final_path
            ),
            recap_text=recap_text,
            language=(
                transcription.get(
                    "language"
                )
            ),
            updated_at=now(),
        )

    except Exception as error:

        update_job(
            job_id,
            status="FAILED",
            progress=0,
            message=(
                "Video processing "
                "failed."
            ),
            error=str(error),
            updated_at=now(),
        )
