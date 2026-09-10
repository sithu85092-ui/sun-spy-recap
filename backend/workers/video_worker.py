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
    audio_file = None

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

        input_size = input_file.stat().st_size

        if input_size < 1000:
            raise RuntimeError(
                "Downloaded video is empty."
            )

        print(
            f"[B2] Input ready: {input_file}",
            flush=True,
        )

        print(
            f"[B2] Input size: "
            f"{input_size / 1024 / 1024:.2f} MB",
            flush=True,
        )

        # ====================================================
        # IMPORTANT:
        # Gemini will receive THIS ACTUAL VIDEO FILE.
        # Do not remove or rename it before narration.
        # ====================================================

        print(
            "[GEMINI VIDEO] Actual video available for "
            "multimodal analysis.",
            flush=True,
        )

        print(
            f"[GEMINI VIDEO] Path: {input_file}",
            flush=True,
        )

        print(
            f"[GEMINI VIDEO] Exists: "
            f"{input_file.exists()}",
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

        if duration <= 0:
            raise RuntimeError(
                "Video duration could not be determined."
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

        if audio_file.stat().st_size < 1000:
            raise RuntimeError(
                "Extracted audio file is empty."
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

        if not isinstance(
            transcription,
            dict,
        ):
            raise RuntimeError(
                "Invalid transcription result."
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

        if not isinstance(
            segments,
            list,
        ):
            segments = []

        detected_language = str(
            transcription.get(
                "language",
                "unknown",
            )
        ).strip() or "unknown"

        try:
            language_probability = float(
                transcription.get(
                    "language_probability",
                    0.0,
                )
            )
        except Exception:
            language_probability = 0.0

        # ----------------------------------------------------
        # IMPORTANT:
        # We don't fail immediately when Whisper gives
        # little/no text because Gemini can understand
        # the actual video visually/audio-wise.
        # ----------------------------------------------------

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
            transcript[:2000] if transcript else
            "[NO RELIABLE TRANSCRIPT]",
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

        if not isinstance(
            analysis,
            dict,
        ):
            raise RuntimeError(
                "Video analysis returned invalid result."
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

        if not isinstance(
            scenes,
            list,
        ):
            scenes = []

        if not isinstance(
            highlight,
            dict,
        ) or not highlight:

            # If analyzer cannot produce a highlight,
            # use the complete video as fallback.
            print(
                "[ANALYZER] No highlight returned. "
                "Using full video as fallback.",
                flush=True,
            )

            highlight = {
                "start": 0.0,
                "duration": min(
                    30.0,
                    duration,
                ),
                "text": "",
            }

        try:
            highlight_start = float(
                highlight.get(
                    "start",
                    0.0,
                )
            )
        except Exception:
            highlight_start = 0.0

        try:
            highlight_duration = float(
                highlight.get(
                    "duration",
                    min(30.0, duration),
                )
            )
        except Exception:
            highlight_duration = min(
                30.0,
                duration,
            )

        # ----------------------------------------------------
        # Safety bounds
        # ----------------------------------------------------

        highlight_start = max(
            0.0,
            highlight_start,
        )

        if highlight_start >= duration:
            highlight_start = max(
                0.0,
                duration - 5.0,
            )

        highlight_duration = max(
            1.0,
            highlight_duration,
        )

        remaining = max(
            1.0,
            duration - highlight_start,
        )

        highlight_duration = min(
            highlight_duration,
            remaining,
        )

        highlight_text = str(
            highlight.get(
                "text",
                "",
            )
        ).strip()

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
            f"[ANALYZER] Highlight text: "
            f"{highlight_text[:500]}",
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
        # 6. BUILD MULTIMODAL RECAP INPUT
        # ====================================================

        update_job(
            job_id,
            status="NARRATING",
            progress=62,
            message=(
                "Understanding the actual video "
                "and creating Burmese recap..."
            ),
        )

        recap_input = {
            # ------------------------------------------------
            # Existing evidence
            # ------------------------------------------------

            "filename": input_file.name,

            "source_language": (
                detected_language
            ),

            "language_confidence": (
                language_probability
            ),

            "full_transcript": transcript,

            "relevant_context": context,

            "highlight_text": highlight_text,

            # ------------------------------------------------
            # CRITICAL NEW FIELD
            #
            # narrator.py uses this to upload the ACTUAL
            # MP4 to Gemini Files API.
            # ------------------------------------------------

            "video_path": str(input_file),

            # ------------------------------------------------
            # Additional useful metadata
            # ------------------------------------------------

            "video_duration": duration,

            "highlight_start": highlight_start,

            "highlight_duration": highlight_duration,

            "scenes": scenes,
        }

        print(
            "================================================",
            flush=True,
        )

        print(
            "[NARRATOR] Sending ACTUAL VIDEO + "
            "transcript evidence to Gemini...",
            flush=True,
        )

        print(
            f"[NARRATOR] Video path: "
            f"{input_file}",
            flush=True,
        )

        print(
            f"[NARRATOR] Video exists: "
            f"{input_file.exists()}",
            flush=True,
        )

        print(
            f"[NARRATOR] Video size: "
            f"{input_file.stat().st_size / 1024 / 1024:.2f} MB",
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

        print(
            f"[NARRATOR] Highlight text: "
            f"{len(highlight_text)} chars",
            flush=True,
        )

        print(
            "================================================",
            flush=True,
        )

        # ====================================================
        # 7. GEMINI BURMESE MULTIMODAL RECAP
        # ====================================================

        recap_result = await asyncio.to_thread(
            narrator.create_recap,
            recap_input,
        )

        if not isinstance(
            recap_result,
            dict,
        ):
            raise RuntimeError(
                "Narrator returned invalid result."
            )

        recap_text = str(
            recap_result.get(
                "text",
                "",
            )
        ).strip()

        recap_engine = str(
            recap_result.get(
                "engine",
                "unknown",
            )
        )

        recap_model = str(
            recap_result.get(
                "model",
                "unknown",
            )
        )

        recap_language = str(
            recap_result.get(
                "language",
                "my",
            )
        )

        if not recap_text:
            raise RuntimeError(
                "AI recap returned empty text."
            )

        # ====================================================
        # 7A. WORKER-LEVEL QUALITY CHECK
        # ====================================================

        forbidden_generic = [
            "ဒီဗီဒီယိုလေးမှာတော့",
            "ဒီဗီဒီယိုမှာတော့",
            "ဒီဗီဒီယိုထဲမှာတော့",
            "ဒီဗီဒီယိုကတော့",
            "အဆုံးထိကြည့်ရှုလိုက်ကြရအောင်",
            "စိတ်ဝင်စားစရာအကြောင်းအရာ",
            "စိတ်ဝင်စားဖွယ်အကြောင်းအရာ",
            "လူမှုဘဝနဲ့ ဓလေ့ထုံးတမ်း",
            "လူမှုဘဝနှင့် ဓလေ့ထုံးတမ်း",
            "အဖြစ်အပျက်တစ်ခုကို မြင်တွေ့ရပါတယ်",
            "အော်ဟစ်တောင်းပန်သံတွေ",
            "စိုးရိမ်ပူပန်သံတွေ",
        ]

        generic_matches = 0

        recap_lower = recap_text.lower()

        for phrase in forbidden_generic:

            if phrase.lower() in recap_lower:
                generic_matches += 1

        if generic_matches >= 2:
            raise RuntimeError(
                "AI returned a generic/unrelated recap. "
                "The result was rejected."
            )

        # ----------------------------------------------------
        # Reject very short useless responses.
        # ----------------------------------------------------

        if len(recap_text) < 30:
            raise RuntimeError(
                "AI recap is too short to be useful."
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
            f"[NARRATOR] Language: "
            f"{recap_language}",
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

        if narration_duration <= 0:
            raise RuntimeError(
                "Narration duration could not be determined."
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
            audio_file,
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
