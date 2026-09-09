import asyncio

from pathlib import Path

from backend.config import TEMP_DIR
from backend.database import (
    SessionLocal,
    utcnow,
)
from backend.models import Job

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


def update_job(
    job_id,
    *,
    status=None,
    progress=None,
    message=None,
    output_file=None,
    error=None,
    recap_text=None,
    language=None,
):

    db = SessionLocal()

    try:

        job = (
            db.query(Job)
            .filter(Job.id == job_id)
            .first()
        )

        if job is None:
            return

        if status is not None:
            job.status = status

        if progress is not None:
            job.progress = progress

        if message is not None:
            job.message = message

        if output_file is not None:
            job.output_file = output_file

        if error is not None:
            job.error = error

        if recap_text is not None:
            job.recap_text = recap_text

        if language is not None:
            job.language = language

        job.updated_at = utcnow()

        db.commit()

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()


def get_job(job_id):

    db = SessionLocal()

    try:

        job = (
            db.query(Job)
            .filter(Job.id == job_id)
            .first()
        )

        if job is None:
            return None

        return {
            "id": job.id,
            "upload_id": job.upload_id,
            "status": job.status,
            "progress": job.progress,
            "message": job.message,
            "input_file": job.input_file,
            "output_file": job.output_file,
            "error": job.error,
            "recap_text": job.recap_text,
            "language": job.language,
        }

    finally:

        db.close()


async def process_video(job_id):

    job = get_job(job_id)

    if job is None:
        return

    input_file = Path(
        job["input_file"]
    )

    try:

        # =================================
        # 1. INSPECT
        # =================================

        update_job(
            job_id,
            status="PROCESSING",
            progress=5,
            message="Inspecting video...",
        )

        info = await asyncio.to_thread(
            inspect_video,
            input_file,
        )

        if not info.get("success"):

            raise RuntimeError(
                info.get(
                    "error",
                    "Video inspection failed.",
                )
            )

        duration = float(
            info.get(
                "duration",
                0,
            )
        )

        # =================================
        # 2. AUDIO
        # =================================

        update_job(
            job_id,
            status="TRANSCRIBING",
            progress=15,
            message="Extracting audio...",
        )

        audio_result = (
            await asyncio.to_thread(
                prepare_audio,
                input_file,
            )
        )

        if not audio_result.get("success", True):

            raise RuntimeError(
                audio_result.get(
                    "error",
                    "Audio extraction failed.",
                )
            )

        audio_file = Path(
            audio_result["audio_file"]
        )

        # =================================
        # 3. WHISPER
        # =================================

        update_job(
            job_id,
            status="TRANSCRIBING",
            progress=30,
            message=(
                "Transcribing speech "
                "with Whisper..."
            ),
        )

        transcription = (
            await asyncio.to_thread(
                transcription_engine.transcribe,
                audio_file,
            )
        )

        if not transcription.get(
            "success"
        ):

            raise RuntimeError(
                transcription.get(
                    "error",
                    "Transcription failed.",
                )
            )

        transcript = (
            transcription.get(
                "text",
                "",
            )
            .strip()
        )

        segments = transcription.get(
            "segments",
            [],
        )

        if not transcript:

            raise RuntimeError(
                "No speech was detected in the video."
            )

        # =================================
        # 4. HIGHLIGHT
        # =================================

        update_job(
            job_id,
            status="ANALYZING",
            progress=45,
            message="Finding the best scene...",
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

        if not highlight:

            raise RuntimeError(
                "Could not find a suitable highlight."
            )

        # =================================
        # 5. CLIP
        # =================================

        update_job(
            job_id,
            status="CLIPPING",
            progress=55,
            message="Creating highlight clip...",
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

        # =================================
        # 6. BURMESE RECAP
        # =================================

        update_job(
            job_id,
            status="NARRATING",
            progress=65,
            message="Creating Burmese recap...",
        )

        recap = (
            await asyncio.to_thread(
                narrator.create_recap,
                transcript,
            )
        )

        if not recap.get("success"):

            raise RuntimeError(
                recap.get(
                    "error",
                    "Recap creation failed.",
                )
            )

        recap_text = (
            recap.get(
                "text",
                "",
            )
            .strip()
        )

        if not recap_text:

            raise RuntimeError(
                "AI recap returned empty text."
            )

        # =================================
        # 7. BURMESE TTS
        # =================================

        update_job(
            job_id,
            status="NARRATING",
            progress=72,
            message="Generating Burmese voice...",
        )

        narration_path = (
            TEMP_DIR /
            f"{job_id}_narration.mp3"
        )

        await synthesize(
            recap_text,
            narration_path,
        )

        # =================================
        # 8. SUBTITLES
        # =================================

        update_job(
            job_id,
            status="SUBTITLING",
            progress=80,
            message="Creating subtitles...",
        )

        subtitle_path = (
            TEMP_DIR /
            f"{job_id}.srt"
        )

        create_srt(
            segments,
            subtitle_path,
        )

        # =================================
        # 9. FINAL 9:16
        # =================================

        update_job(
            job_id,
            status="RENDERING",
            progress=88,
            message="Rendering final 9:16 video...",
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

        # =================================
        # 10. COMPLETE
        # =================================

        update_job(
            job_id,
            status="COMPLETED",
            progress=100,
            message="Final recap created successfully.",
            output_file=str(final_path),
            recap_text=recap_text,
            language=transcription.get(
                "language",
                "my",
            ),
        )

    except Exception as error:

        print(
            f"[JOB FAILED] {job_id}: {error}",
            flush=True,
        )

        update_job(
            job_id,
            status="FAILED",
            progress=0,
            message="Video processing failed.",
            error=str(error),
        )
