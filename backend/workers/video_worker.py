import asyncio
from pathlib import Path

from backend.config import TEMP_DIR
from backend.database import SessionLocal, utcnow
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

from backend.services.ffmpeg import (
    get_duration,
)

from backend.services.b2_storage import (
    download_file,
    upload_file,
)


# ==========================================
# JOB DATABASE HELPERS
# ==========================================

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


# ==========================================
# MAIN VIDEO PROCESSING
# ==========================================

async def process_video(job_id):

    print(
        f"[JOB START] {job_id}",
        flush=True,
    )

    job = get_job(job_id)

    if job is None:
        print(
            f"[JOB] Not found: {job_id}",
            flush=True,
        )
        return

    input_key = job["input_file"]

    if not input_key:
        raise RuntimeError(
            "Job has no input file."
        )

    input_file = (
        TEMP_DIR /
        f"{job_id}_input.mp4"
    )

    try:

        TEMP_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ==========================================
        # 0. DOWNLOAD INPUT FROM B2
        # ==========================================

        update_job(
            job_id,
            status="PROCESSING",
            progress=2,
            message="Downloading video from storage...",
        )

        print(
            f"[B2] Downloading input: {input_key}",
            flush=True,
        )

        await asyncio.to_thread(
            download_file,
            input_key,
            input_file,
        )

        if not input_file.exists():
            raise FileNotFoundError(
                f"B2 download failed: {input_key}"
            )

        if input_file.stat().st_size < 1000:
            raise RuntimeError(
                "Downloaded video is empty."
            )

        print(
            f"[B2] Input ready: {input_file}",
            flush=True,
        )

        # ==========================================
        # 1. INSPECT VIDEO
        # ==========================================

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
            info.get("duration", 0)
        )

        print(
            f"[JOB] Video duration: {duration:.2f}s",
            flush=True,
        )

        # ==========================================
        # 2. EXTRACT AUDIO
        # ==========================================

        update_job(
            job_id,
            status="TRANSCRIBING",
            progress=15,
            message="Extracting audio...",
        )

        audio_result = await asyncio.to_thread(
            prepare_audio,
            input_file,
        )

        if not audio_result.get(
            "success",
            True,
        ):
            raise RuntimeError(
                audio_result.get(
                    "error",
                    "Audio extraction failed.",
                )
            )

        audio_file = Path(
            audio_result["audio_file"]
        )

        # ==========================================
        # 3. TRANSCRIBE ANY LANGUAGE
        # ==========================================

        update_job(
            job_id,
            status="TRANSCRIBING",
            progress=30,
            message=(
                "Detecting language and "
                "transcribing speech..."
            ),
        )

        transcription = await asyncio.to_thread(
            transcription_engine.transcribe,
            audio_file,
        )

        if not transcription.get("success"):
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

        detected_language = (
            transcription.get(
                "language",
                "unknown",
            )
        )

        if not transcript:
            raise RuntimeError(
                "No speech was detected in the video."
            )

        print(
            f"[WHISPER] Detected language: "
            f"{detected_language}",
            flush=True,
        )

        print(
            "[JOB] Whisper completed.",
            flush=True,
        )

        # ==========================================
        # 4. FIND BEST / INTERESTING SCENE
        # ==========================================

        update_job(
            job_id,
            status="ANALYZING",
            progress=45,
            message="Finding the most interesting scene...",
        )

        clip_duration = min(
            30.0,
            max(
                5.0,
                duration,
            ),
        )

        highlight = await asyncio.to_thread(
            choose_highlight,
            input_file,
            clip_duration,
            segments,
        )

        if not highlight:
            raise RuntimeError(
                "Could not find a suitable highlight."
            )

        highlight_start = float(
            highlight.get(
                "start",
                0,
            )
        )

        highlight_duration = float(
            highlight.get(
                "duration",
                clip_duration,
            )
        )

        print(
            f"[JOB] Highlight selected: "
            f"start={highlight_start:.2f}s "
            f"duration={highlight_duration:.2f}s "
            f"score={highlight.get('score')}",
            flush=True,
        )

        # ==========================================
        # 5. CREATE HIGHLIGHT CLIP
        # ==========================================

        update_job(
            job_id,
            status="CLIPPING",
            progress=55,
            message="Creating the best scene clip...",
        )

        clip_path = await asyncio.to_thread(
            create_highlight_clip,
            input_file,
            highlight_start,
            highlight_duration,
            f"{job_id}_highlight.mp4",
        )

        clip_path = Path(clip_path)

        if not clip_path.exists():
            raise RuntimeError(
                "Highlight clip was not created."
            )

        if clip_path.stat().st_size < 1000:
            raise RuntimeError(
                "Highlight clip is empty."
            )

        print(
            f"[JOB] Highlight clip created: "
            f"{clip_path}",
            flush=True,
        )

        # ==========================================
        # 6. CREATE BURMESE RECAP
        # ==========================================

        update_job(
            job_id,
            status="NARRATING",
            progress=65,
            message="Creating Burmese recap...",
        )

        recap = await asyncio.to_thread(
            narrator.create_recap,
            transcript,
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

        print(
            "[NARRATOR] Burmese recap created.",
            flush=True,
        )

        print(
            f"[NARRATOR] {recap_text}",
            flush=True,
        )

        # ==========================================
        # 7. BURMESE NARRATOR VOICE
        # ==========================================

        update_job(
            job_id,
            status="NARRATING",
            progress=72,
            message="Generating Myanmar narrator voice...",
        )

        narration_path = (
            TEMP_DIR /
            f"{job_id}_narration.mp3"
        )

        await synthesize(
            recap_text,
            narration_path,
        )

        if not narration_path.exists():
            raise RuntimeError(
                "Narration audio was not created."
            )

        if narration_path.stat().st_size < 1000:
            raise RuntimeError(
                "Narration audio is empty."
            )

        narration_duration = await asyncio.to_thread(
            get_duration,
            narration_path,
        )

        print(
            f"[TTS] Myanmar narrator audio: "
            f"{narration_duration:.2f}s",
            flush=True,
        )

        # ==========================================
        # 8. BURMESE SUBTITLE
        # ==========================================

        update_job(
            job_id,
            status="SUBTITLING",
            progress=80,
            message="Creating Burmese subtitles...",
        )

        subtitle_path = (
            TEMP_DIR /
            f"{job_id}.srt"
        )

        # IMPORTANT:
        # Subtitle = Burmese recap/narration,
        # NOT the original-language transcript.
        create_srt(
            recap_text,
            subtitle_path,
            duration=narration_duration,
        )

        if not subtitle_path.exists():
            raise RuntimeError(
                "Subtitle file was not created."
            )

        if subtitle_path.stat().st_size < 10:
            raise RuntimeError(
                "Subtitle file is empty."
            )

        print(
            f"[SRT] Burmese narrator subtitles ready: "
            f"{subtitle_path}",
            flush=True,
        )

        # ==========================================
        # 9. FINAL 9:16 VIDEO
        # ==========================================

        update_job(
            job_id,
            status="RENDERING",
            progress=88,
            message="Rendering final 9:16 video...",
        )

        # renderer.py / ffmpeg.py maps ONLY
        # narration audio.
        #
        # Therefore:
        # Original video audio = REMOVED
        # Myanmar narrator = FINAL AUDIO
        #

        final_path = await asyncio.to_thread(
            render_final,
            clip_path,
            narration_path,
            subtitle_path,
            f"{job_id}_final.mp4",
        )

        final_path = Path(final_path)

        if not final_path.exists():
            raise RuntimeError(
                "Final video was not created."
            )

        if final_path.stat().st_size < 1000:
            raise RuntimeError(
                "Final video is empty."
            )

        print(
            f"[JOB] Final video rendered: "
            f"{final_path}",
            flush=True,
        )

        # ==========================================
        # 9.5. UPLOAD FINAL TO B2
        # ==========================================

        update_job(
            job_id,
            status="RENDERING",
            progress=94,
            message="Uploading final video...",
        )

        final_key = (
            f"outputs/{job_id}_final.mp4"
        )

        print(
            f"[B2] Uploading final: "
            f"{final_key}",
            flush=True,
        )

        await asyncio.to_thread(
            upload_file,
            final_path,
            final_key,
        )

        print(
            f"[B2] Final upload complete: "
            f"{final_key}",
            flush=True,
        )

        # ==========================================
        # 10. COMPLETE
        # ==========================================

        update_job(
            job_id,
            status="COMPLETED",
            progress=100,
            message=(
                "Burmese AI recap created successfully."
            ),
            output_file=final_key,
            recap_text=recap_text,
            language="my",
        )

        print(
            f"[JOB COMPLETE] {job_id}",
            flush=True,
        )

    except Exception as error:

        print(
            f"[JOB FAILED] {job_id}: {error}",
            flush=True,
        )

        try:
            update_job(
                job_id,
                status="FAILED",
                progress=0,
                message="Video processing failed.",
                error=str(error),
            )

        except Exception as update_error:

            print(
                "[JOB] Failed to update failure status: "
                f"{update_error}",
                flush=True,
            )

    finally:

        # ==========================================
        # CLEAN INPUT
        # ==========================================

        try:

            if input_file.exists():

                input_file.unlink()

                print(
                    "[CLEANUP] Temporary input removed.",
                    flush=True,
                )

        except Exception as cleanup_error:

            print(
                "[CLEANUP] Input cleanup failed: "
                f"{cleanup_error}",
                flush=True,
            )
