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
    analyze_video,
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


# ============================================================
# JOB DATABASE HELPERS
# ============================================================

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


# ============================================================
# MAIN VIDEO PROCESSING
# ============================================================

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

    clip_path = None
    narration_path = None
    subtitle_path = None
    final_path = None

    try:

        TEMP_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ====================================================
        # 0. DOWNLOAD VIDEO
        # ====================================================

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

        # ====================================================
        # 1. INSPECT VIDEO
        # ====================================================

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

        print(
            f"[JOB] Video duration: "
            f"{duration:.2f}s",
            flush=True,
        )

        print(
            f"[JOB] Filename: "
            f"{input_file.name}",
            flush=True,
        )

        # ====================================================
        # 2. EXTRACT AUDIO
        # ====================================================

        update_job(
            job_id,
            status="TRANSCRIBING",
            progress=12,
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

        if not audio_file.exists():
            raise RuntimeError(
                "Extracted audio file does not exist."
            )

        # ====================================================
        # 3. WHISPER TRANSCRIPTION
        # ====================================================

        update_job(
            job_id,
            status="TRANSCRIBING",
            progress=25,
            message=(
                "Detecting original language "
                "and transcribing..."
            ),
        )

        print(
            "[WHISPER] Starting transcription...",
            flush=True,
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

        transcript = str(
            transcription.get(
                "text",
                "",
            )
        ).strip()

        segments = transcription.get(
            "segments",
            [],
        )

        detected_language = str(
            transcription.get(
                "language",
                "unknown",
            )
        )

        language_probability = float(
            transcription.get(
                "language_probability",
                0.0,
            )
        )

        if not transcript:
            raise RuntimeError(
                "No speech was detected in the video."
            )

        print(
            "================================================",
            flush=True,
        )

        print(
            f"[WHISPER] Detected language: "
            f"{detected_language}",
            flush=True,
        )

        print(
            f"[WHISPER] Language confidence: "
            f"{language_probability:.3f}",
            flush=True,
        )

        print(
            f"[WHISPER] Segment count: "
            f"{len(segments)}",
            flush=True,
        )

        print(
            "[WHISPER] Transcript preview:",
            flush=True,
        )

        print(
            transcript[:2000],
            flush=True,
        )

        print(
            "================================================",
            flush=True,
        )

        # ====================================================
        # 4. VIDEO + TRANSCRIPT ANALYSIS
        # ====================================================

        update_job(
            job_id,
            status="ANALYZING",
            progress=42,
            message=(
                "Analyzing scenes and important "
                "video content..."
            ),
        )

        print(
            "[ANALYZER] Starting video analysis...",
            flush=True,
        )

        analysis = await asyncio.to_thread(
            analyze_video,
            input_file,
            segments,
            duration,
        )

        if not analysis:
            raise RuntimeError(
                "Video analysis returned no result."
            )

        highlight = analysis.get(
            "highlight",
            {},
        )

        context = str(
            analysis.get(
                "context",
                "",
            )
        ).strip()

        scenes = analysis.get(
            "scenes",
            [],
        )

        if not highlight:
            raise RuntimeError(
                "Could not find a suitable highlight."
            )

        highlight_start = float(
            highlight.get(
                "start",
                0.0,
            )
        )

        highlight_duration = float(
            highlight.get(
                "duration",
                min(30.0, duration),
            )
        )

        # Never exceed source video.
        if duration > 0:
            remaining = max(
                1.0,
                duration - highlight_start,
            )

            highlight_duration = min(
                highlight_duration,
                remaining,
            )

        print(
            f"[ANALYZER] Scene changes: "
            f"{len(scenes)}",
            flush=True,
        )

        print(
            f"[ANALYZER] Highlight start: "
            f"{highlight_start:.2f}s",
            flush=True,
        )

        print(
            f"[ANALYZER] Highlight duration: "
            f"{highlight_duration:.2f}s",
            flush=True,
        )

        print(
            f"[ANALYZER] Context length: "
            f"{len(context)} chars",
            flush=True,
        )

        # ====================================================
        # 5. CREATE HIGHLIGHT CLIP
        # ====================================================

        update_job(
            job_id,
            status="CLIPPING",
            progress=52,
            message="Creating the best scene clip...",
        )

        clip_path = await asyncio.to_thread(
            create_highlight_clip,
            input_file,
            highlight_start,
            highlight_duration,
            f"{job_id}_highlight.mp4",
        )

        clip_path = Path(
            clip_path
        )

        if not clip_path.exists():
            raise RuntimeError(
                "Highlight clip was not created."
            )

        if clip_path.stat().st_size < 1000:
            raise RuntimeError(
                "Highlight clip is empty."
            )

        print(
            f"[CLIPPER] Highlight created: "
            f"{clip_path}",
            flush=True,
        )

        # ====================================================
        # 6. BUILD RECAP SOURCE
        # ====================================================
        #
        # The important change:
        #
        # Gemini receives:
        #   - detected language
        #   - video filename
        #   - full transcript
        #   - relevant context
        #   - selected highlight text
        #
        # This gives the AI more evidence and reduces
        # generic / invented recaps.
        # ====================================================

        update_job(
            job_id,
            status="NARRATING",
            progress=62,
            message="Understanding the video and creating Burmese recap...",
        )

        highlight_text = str(
            highlight.get(
                "text",
                "",
            )
        ).strip()

        recap_input = {
            "filename": input_file.name,
            "source_language": detected_language,
            "language_confidence": language_probability,
            "full_transcript": transcript,
            "relevant_context": context,
            "highlight_text": highlight_text,
        }

        print(
            "[NARRATOR] Sending video evidence to Gemini...",
            flush=True,
        )

        print(
            f"[NARRATOR] Source language: "
            f"{detected_language}",
            flush=True,
        )

        print(
            f"[NARRATOR] Full transcript: "
            f"{len(transcript)} chars",
            flush=True,
        )

        print(
            f"[NARRATOR] Relevant context: "
            f"{len(context)} chars",
            flush=True,
        )

        # ====================================================
        # 7. GEMINI BURMESE RECAP
        # ====================================================

        # New narrator versions may accept a dictionary.
        # Keep a safe compatibility fallback for older
        # narrator implementations.
        try:

            recap_result = await asyncio.to_thread(
                narrator.create_recap,
                recap_input,
            )

        except TypeError:

            print(
                "[NARRATOR] Structured input is not "
                "supported by current narrator; "
                "using transcript fallback.",
                flush=True,
            )

            recap_result = await asyncio.to_thread(
                narrator.create_recap,
                transcript,
            )

        # ----------------------------------------------------
        # Normalize narrator result
        # ----------------------------------------------------

        if isinstance(
            recap_result,
            dict,
        ):

            recap_text = str(
                recap_result.get(
                    "text",
                    "",
                )
            ).strip()

            recap_engine = recap_result.get(
                "engine",
                "unknown",
            )

            recap_model = recap_result.get(
                "model",
                "unknown",
            )

        else:

            recap_text = str(
                recap_result or ""
            ).strip()

            recap_engine = "unknown"
            recap_model = "unknown"

        if not recap_text:
            raise RuntimeError(
                "AI recap returned empty text."
            )

        # ----------------------------------------------------
        # Reject known generic fallback.
        # ----------------------------------------------------

        forbidden_generic = [
            "ဒီဗီဒီယိုလေးမှာတော့",
            "ဒီဗီဒီယိုမှာတော့ လူသိပ်မသိသေးတဲ့",
            "စိတ်ဝင်စားစရာ အကြောင်းအရာတစ်ခုကို",
            "အစကနေ အဆုံးထိ အသေအချာ",
        ]

        recap_lower = recap_text.lower()

        for phrase in forbidden_generic:

            if phrase.lower() in recap_lower:

                raise RuntimeError(
                    "AI returned a generic recap. "
                    "The result was rejected instead "
                    "of publishing unrelated content."
                )

        print(
            "================================================",
            flush=True,
        )

        print(
            f"[NARRATOR] Engine: "
            f"{recap_engine}",
            flush=True,
        )

        print(
            f"[NARRATOR] Model: "
            f"{recap_model}",
            flush=True,
        )

        print(
            "[NARRATOR] FINAL BURMESE RECAP:",
            flush=True,
        )

        print(
            recap_text,
            flush=True,
        )

        print(
            "================================================",
            flush=True,
        )

        # ====================================================
        # 8. BURMESE TTS
        # ====================================================

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

        narration_duration = (
            await asyncio.to_thread(
                get_duration,
                narration_path,
            )
        )

        print(
            f"[TTS] Myanmar narrator audio: "
            f"{narration_duration:.2f}s",
            flush=True,
        )

        # ====================================================
        # 9. BURMESE SUBTITLE
        # ====================================================

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
            f"[SRT] Burmese subtitles ready: "
            f"{subtitle_path}",
            flush=True,
        )

        # ====================================================
        # 10. RENDER FINAL 9:16
        # ====================================================

        update_job(
            job_id,
            status="RENDERING",
            progress=88,
            message="Rendering final 9:16 video...",
        )

        final_path = await asyncio.to_thread(
            render_final,
            clip_path,
            narration_path,
            subtitle_path,
            f"{job_id}_final.mp4",
        )

        final_path = Path(
            final_path
        )

        if not final_path.exists():
            raise RuntimeError(
                "Final video was not created."
            )

        if final_path.stat().st_size < 1000:
            raise RuntimeError(
                "Final video is empty."
            )

        print(
            f"[RENDER] Final video: "
            f"{final_path}",
            flush=True,
        )

        # ====================================================
        # 11. UPLOAD FINAL VIDEO
        # ====================================================

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
            f"[B2] Uploading: {final_key}",
            flush=True,
        )

        await asyncio.to_thread(
            upload_file,
            final_path,
            final_key,
        )

        print(
            "[B2] Upload complete.",
            flush=True,
        )

        # ====================================================
        # 12. COMPLETE
        # ====================================================

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

        # ====================================================
        # CLEANUP
        # ====================================================

        cleanup_files = [
            input_file,
            clip_path,
            narration_path,
            subtitle_path,
            final_path,
        ]

        for path in cleanup_files:

            try:

                if path is not None:

                    path = Path(path)

                    if path.exists():

                        path.unlink()

                        print(
                            f"[CLEANUP] Removed: "
                            f"{path.name}",
                            flush=True,
                        )

            except Exception as cleanup_error:

                print(
                    "[CLEANUP] Failed: "
                    f"{cleanup_error}",
                    flush=True,
                )
