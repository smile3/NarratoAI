import os
from typing import Any, Callable, Iterable

from loguru import logger

from app.config import config
from app.utils import utils


_model = None


def format_srt_timestamp(seconds: float | int | None) -> str:
    """Format seconds as an SRT timestamp."""
    try:
        total_ms = int(round(max(0.0, float(seconds or 0)) * 1000))
    except (TypeError, ValueError):
        total_ms = 0

    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _segment_value(segment: Any, key: str, default: Any = None) -> Any:
    if isinstance(segment, dict):
        return segment.get(key, default)
    return getattr(segment, key, default)


def segments_to_srt(segments: Iterable[Any]) -> str:
    """Convert faster-whisper segments or dict-like segments into SRT text."""
    blocks: list[str] = []
    for index, segment in enumerate(segments, 1):
        text = str(_segment_value(segment, "text", "") or "").strip()
        if not text:
            continue

        start = _segment_value(segment, "start", 0)
        end = _segment_value(segment, "end", start)
        try:
            if float(end) <= float(start):
                end = float(start) + 0.001
        except (TypeError, ValueError):
            end = start

        blocks.append(
            "\n".join(
                [
                    str(len(blocks) + 1),
                    f"{format_srt_timestamp(start)} --> {format_srt_timestamp(end)}",
                    text,
                ]
            )
        )

    return "\n\n".join(blocks) + ("\n" if blocks else "")


def default_subtitle_path_for_media(media_path: str) -> str:
    """Return the default generated SRT path for a media file."""
    base_name = os.path.splitext(os.path.basename(str(media_path or "media")))[0]
    return os.path.join(utils.subtitle_dir(), f"{base_name}_whisper.srt")


def create_with_local_whisper(
    media_file: str,
    subtitle_file: str = "",
    transcriber: Callable[[str], Any] | None = None,
) -> str:
    """Generate an SRT subtitle file from a local media file using faster-whisper.

    A test or another service can inject ``transcriber`` to avoid loading a model. The
    transcriber may return either an iterable of segments or ``(segments, info)``.
    """
    if not media_file or not os.path.exists(media_file):
        raise FileNotFoundError(f"媒体文件不存在: {media_file}")

    output_path = subtitle_file or default_subtitle_path_for_media(media_file)
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    segment_result = transcriber(media_file) if transcriber else _transcribe_with_faster_whisper(media_file)
    segments = segment_result[0] if isinstance(segment_result, tuple) else segment_result
    srt_text = segments_to_srt(segments or [])
    if not srt_text.strip():
        raise RuntimeError("本地 Whisper 没有识别出有效字幕内容")

    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(srt_text)

    logger.info(f"本地 Whisper 字幕生成完成: {output_path}")
    return output_path


def _transcribe_with_faster_whisper(media_file: str) -> Any:
    model = _load_model()
    return model.transcribe(
        media_file,
        beam_size=int(config.whisper.get("beam_size", 5) or 5),
        vad_filter=bool(config.whisper.get("vad_filter", True)),
        vad_parameters={"min_silence_duration_ms": int(config.whisper.get("min_silence_duration_ms", 500) or 500)},
        initial_prompt=config.whisper.get("initial_prompt", "以下是普通话的句子"),
    )


def _load_model() -> Any:
    global _model
    if _model is not None:
        return _model

    try:
        from faster_whisper import WhisperModel
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "未安装 faster-whisper，无法使用本地 Whisper 生成字幕。"
            "请先安装 requirements.txt 中的 faster-whisper 依赖。"
        ) from exc

    configured_model = (
        config.whisper.get("model_path")
        or config.whisper.get("model_size")
        or config.whisper.get("model_size_or_path")
    )
    bundled_model_path = os.path.join(utils.root_dir(), "app", "models", "faster-whisper-large-v3")
    model_size_or_path = configured_model or (bundled_model_path if os.path.isdir(bundled_model_path) else "large-v3")

    local_files_only = config.whisper.get("local_files_only")
    if local_files_only is None:
        local_files_only = os.path.isdir(str(model_size_or_path))

    device = config.whisper.get("device", "cpu")
    compute_type = config.whisper.get("compute_type", "int8")
    logger.info(f"加载本地 Whisper 模型: {model_size_or_path}, device={device}, compute_type={compute_type}")
    _model = WhisperModel(
        model_size_or_path=str(model_size_or_path),
        device=device,
        compute_type=compute_type,
        local_files_only=bool(local_files_only),
    )
    return _model
