import re
import subprocess
from pathlib import Path


class VideoAnalyzer:
    """
    SUN SPY RECAP video analyzer.

    Responsibilities:
    - Detect scene changes.
    - Analyze transcript segments.
    - Find the most informative section.
    - Avoid selecting silence / empty sections.
    - Keep enough context around the selected highlight.
    """

    def __init__(self):
        self.scene_threshold = 0.30

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    def _safe_float(self, value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    def _clean_text(self, text):
        text = str(text or "")

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    def _segment_text(self, segment):
        if isinstance(segment, dict):
            return self._clean_text(
                segment.get("text", "")
            )

        return self._clean_text(
            getattr(segment, "text", "")
        )

    def _segment_start(self, segment):
        if isinstance(segment, dict):
            return self._safe_float(
                segment.get("start", 0)
            )

        return self._safe_float(
            getattr(segment, "start", 0)
        )

    def _segment_end(self, segment):
        if isinstance(segment, dict):
            return self._safe_float(
                segment.get("end", 0)
            )

        return self._safe_float(
            getattr(segment, "end", 0)
        )

    # ---------------------------------------------------------
    # Scene detection
    # ---------------------------------------------------------

    def detect_scenes(self, video_path):
        """
        Detect visual scene changes using FFmpeg.

        Returns:
            list[float]
        """

        video_path = Path(video_path)

        if not video_path.exists():
            print(
                f"[ANALYZER] Video not found: "
                f"{video_path}",
                flush=True,
            )

            return []

        print(
            "[ANALYZER] Detecting scene changes...",
            flush=True,
        )

        filter_expr = (
            f"select='gt(scene,"
            f"{self.scene_threshold})',"
            "showinfo"
        )

        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "info",
            "-i",
            str(video_path),
            "-vf",
            filter_expr,
            "-f",
            "null",
            "-",
        ]

        try:
            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300,
            )

            output = process.stderr or ""

            scenes = []

            for line in output.splitlines():
                match = re.search(
                    r"pts_time:([0-9.]+)",
                    line,
                )

                if not match:
                    continue

                timestamp = self._safe_float(
                    match.group(1)
                )

                if timestamp >= 0:
                    scenes.append(timestamp)

            # Remove duplicates / nearly identical timestamps.
            cleaned = []

            for timestamp in scenes:
                if not cleaned:
                    cleaned.append(timestamp)
                    continue

                if abs(timestamp - cleaned[-1]) >= 1.0:
                    cleaned.append(timestamp)

            print(
                f"[ANALYZER] Detected "
                f"{len(cleaned)} scene changes.",
                flush=True,
            )

            return cleaned

        except subprocess.TimeoutExpired:
            print(
                "[ANALYZER] Scene detection timed out.",
                flush=True,
            )

            return []

        except Exception as error:
            print(
                f"[ANALYZER] Scene detection failed: "
                f"{error}",
                flush=True,
            )

            return []

    # ---------------------------------------------------------
    # Transcript scoring
    # ---------------------------------------------------------

    def _score_segment(self, segment, index, total):
        """
        Give a segment an information score.

        We intentionally do NOT assume the video topic.
        Keywords are only weak signals.
        """

        text = self._segment_text(segment)

        if not text:
            return 0.0

        score = 0.0

        length = len(text)

        # More content usually means more information.
        if length >= 30:
            score += 1.0

        if length >= 60:
            score += 1.0

        if length >= 100:
            score += 1.0

        # Sentences / punctuation can indicate explanatory speech.
        punctuation_count = sum(
            text.count(mark)
            for mark in [
                "。",
                "，",
                "。",
                "၊",
                ".",
                ",",
                "!",
                "?",
                "！",
                "？",
            ]
        )

        score += min(
            punctuation_count * 0.15,
            1.0,
        )

        # Weak informational signals.
        informational_patterns = [
            r"because",
            r"therefore",
            r"finally",
            r"important",
            r"reason",
            r"means",
            r"called",
            r"first",
            r"second",
            r"then",
            r"after",
            r"before",

            r"အကြောင်း",
            r"အရေးကြီး",
            r"အဓိပ္ပာယ်",
            r"အကျိုး",
            r"အကြောင်းရင်း",
            r"နောက်ဆုံး",
            r"ပထမ",
            r"ပြီးတော့",
            r"ထို့ကြောင့်",
            r"ဆိုလို",
            r"ခေါ်ဆို",
            r"ဖြစ်ရခြင်း",
        ]

        lowered = text.lower()

        for pattern in informational_patterns:
            try:
                if re.search(
                    pattern,
                    lowered,
                    flags=re.IGNORECASE,
                ):
                    score += 0.5
            except Exception:
                pass

        # Penalize extremely short conversational fragments.
        if length < 12:
            score -= 1.0

        # Slight preference for middle content, but NOT
        # enough to override actual transcript information.
        if total > 1:
            position = index / (total - 1)

            distance_from_middle = abs(
                position - 0.5
            )

            score += max(
                0,
                0.3 - distance_from_middle * 0.3,
            )

        return score

    # ---------------------------------------------------------
    # Highlight selection
    # ---------------------------------------------------------

    def choose_highlight(
        self,
        segments,
        video_duration=None,
        clip_duration=30,
    ):
        """
        Select the most informative transcript region.

        Returns:
            {
                "start": float,
                "duration": float,
                "text": str
            }
        """

        if not segments:
            print(
                "[ANALYZER] No transcript segments.",
                flush=True,
            )

            return {
                "start": 0.0,
                "duration": float(clip_duration),
                "text": "",
            }

        print(
            f"[ANALYZER] Analyzing "
            f"{len(segments)} transcript segments...",
            flush=True,
        )

        scored = []

        total = len(segments)

        for index, segment in enumerate(segments):
            text = self._segment_text(segment)

            if not text:
                continue

            score = self._score_segment(
                segment,
                index,
                total,
            )

            scored.append(
                (
                    score,
                    index,
                    segment,
                )
            )

        if not scored:
            first = segments[0]

            start = max(
                0.0,
                self._segment_start(first),
            )

            return {
                "start": start,
                "duration": float(clip_duration),
                "text": self._segment_text(first),
            }

        # Highest score first.
        scored.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        best_score, best_index, best_segment = (
            scored[0]
        )

        best_start = self._segment_start(
            best_segment
        )

        best_end = self._segment_end(
            best_segment
        )

        # Give context before the important segment.
        start = max(
            0.0,
            best_start - 5.0,
        )

        # If the selected speech itself is long,
        # include it rather than blindly using 30 seconds.
        natural_duration = max(
            0.0,
            best_end - start,
        )

        duration = max(
            float(clip_duration),
            natural_duration,
        )

        # Don't exceed video duration.
        if video_duration:
            remaining = max(
                1.0,
                float(video_duration) - start,
            )

            duration = min(
                duration,
                remaining,
            )

        selected_text = self._segment_text(
            best_segment
        )

        print(
            f"[ANALYZER] Best transcript segment: "
            f"index={best_index}, "
            f"score={best_score:.2f}",
            flush=True,
        )

        print(
            f"[ANALYZER] Highlight start: "
            f"{start:.2f}s",
            flush=True,
        )

        print(
            f"[ANALYZER] Highlight duration: "
            f"{duration:.2f}s",
            flush=True,
        )

        print(
            f"[ANALYZER] Highlight text: "
            f"{selected_text[:500]}",
            flush=True,
        )

        return {
            "start": start,
            "duration": duration,
            "text": selected_text,
        }

    # ---------------------------------------------------------
    # Context extraction
    # ---------------------------------------------------------

    def build_context_window(
        self,
        segments,
        center_start,
        window_seconds=60,
    ):
        """
        Return transcript around a selected point.

        This is useful when the selected sentence needs
        surrounding context.
        """

        if not segments:
            return ""

        center_start = self._safe_float(
            center_start
        )

        half_window = (
            float(window_seconds) / 2.0
        )

        window_start = max(
            0.0,
            center_start - half_window,
        )

        window_end = (
            center_start + half_window
        )

        texts = []

        for segment in segments:
            start = self._segment_start(
                segment
            )

            end = self._segment_end(
                segment
            )

            # Include segments overlapping the window.
            if end < window_start:
                continue

            if start > window_end:
                continue

            text = self._segment_text(
                segment
            )

            if text:
                texts.append(text)

        context = " ".join(texts).strip()

        print(
            f"[ANALYZER] Context window: "
            f"{len(context)} characters",
            flush=True,
        )

        return context

    # ---------------------------------------------------------
    # Public analysis method
    # ---------------------------------------------------------

    def analyze(
        self,
        video_path,
        transcript_segments,
        video_duration=None,
    ):
        """
        Complete analysis helper.
        """

        scenes = self.detect_scenes(
            video_path
        )

        highlight = self.choose_highlight(
            transcript_segments,
            video_duration=video_duration,
        )

        context = self.build_context_window(
            transcript_segments,
            highlight["start"],
            window_seconds=90,
        )

        return {
            "scenes": scenes,
            "highlight": highlight,
            "context": context,
        }


# Global analyzer instance.
analyzer = VideoAnalyzer()


# -------------------------------------------------------------
# Backward-compatible helper functions
# -------------------------------------------------------------
#
# These functions are kept so existing video_worker.py code
# that imports detect_scenes() / choose_highlight() continues
# to work without modification.
# -------------------------------------------------------------


def detect_scenes(video_path):
    return analyzer.detect_scenes(
        video_path
    )


def choose_highlight(
    segments,
    video_duration=None,
    clip_duration=30,
):
    return analyzer.choose_highlight(
        segments,
        video_duration=video_duration,
        clip_duration=clip_duration,
    )


def analyze_video(
    video_path,
    transcript_segments,
    video_duration=None,
):
    return analyzer.analyze(
        video_path,
        transcript_segments,
        video_duration=video_duration,
    )
