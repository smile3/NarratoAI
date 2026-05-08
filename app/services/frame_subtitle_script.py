from loguru import logger
from typing import Any, Callable

from app.services import script_enhancement
from app.services.prompts import PromptManager


FRAME_SUBTITLE_PROMPT_CATEGORY = "short_drama_narration"
FRAME_SUBTITLE_PROMPT_NAME = "frame_subtitle_generation"


def build_frame_subtitle_prompt(
    frame_analysis_markdown: str,
    subtitle_content: str,
    video_theme: str = "",
    custom_prompt: str = "",
) -> str:
    """Build a prompt that asks the text model to combine frame analysis and subtitles."""
    return PromptManager.get_prompt(
        category=FRAME_SUBTITLE_PROMPT_CATEGORY,
        name=FRAME_SUBTITLE_PROMPT_NAME,
        parameters={
            "frame_analysis_markdown": frame_analysis_markdown,
            "subtitle_content": subtitle_content,
            "video_theme": video_theme,
            "custom_prompt": custom_prompt,
        },
    )


def generate_frame_subtitle_script(
    frame_analysis_markdown: str,
    subtitle_content: str,
    video_theme: str = "",
    custom_prompt: str = "",
    text_generator: Callable[[str, str, float, str | None], str] | None = None,
) -> list[dict[str, Any]]:
    """Generate normalized script items from visual frame analysis plus subtitles."""
    prompt = build_frame_subtitle_prompt(
        frame_analysis_markdown=frame_analysis_markdown,
        subtitle_content=subtitle_content,
        video_theme=video_theme,
        custom_prompt=custom_prompt,
    )
    system_prompt = (
        PromptManager.get_prompt_object(
            category=FRAME_SUBTITLE_PROMPT_CATEGORY,
            name=FRAME_SUBTITLE_PROMPT_NAME,
        ).get_system_prompt()
        or "你是一位专业短剧剪辑解说脚本专家，必须输出合法 JSON。"
    )
    generator = text_generator or _generate_text_with_config
    raw_payload = generator(
        prompt,
        system_prompt,
        0.8,
        "json",
    )
    items = script_enhancement.parse_script_items_payload(raw_payload)
    if not items:
        raise ValueError("逐帧+字幕脚本生成失败：模型没有返回有效的 items JSON")
    return normalize_frame_subtitle_items(items)


def normalize_frame_subtitle_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        timestamp = str(item.get("timestamp", "") or "").strip()
        picture = str(item.get("picture", "") or "").strip()
        narration = str(item.get("narration", "") or "").strip()
        if not timestamp or not narration:
            continue
        ost = _normalize_ost_value(item.get("OST"), narration=narration)
        normalized.append(
            {
                "_id": len(normalized) + 1,
                "timestamp": timestamp,
                "picture": picture,
                "narration": narration,
                "OST": ost,
            }
        )
    if not normalized:
        raise ValueError("逐帧+字幕脚本生成失败：返回片段缺少 timestamp 或 narration")

    normalized = _ensure_mixed_ost_beats(normalized)

    return normalized


def _normalize_ost_value(raw_ost: Any, *, narration: str) -> int:
    try:
        ost = int(raw_ost)
    except (TypeError, ValueError):
        ost = -1

    if ost in (0, 1):
        return ost

    if _looks_like_original_audio_segment(narration):
        return 1
    return 0


def _looks_like_original_audio_segment(text: str) -> bool:
    text = (text or "").strip()
    if not text:
        return False

    original_audio_keywords = (
        "播放原片",
        "原声",
        "原音",
        "原台词",
    )
    return any(keyword in text for keyword in original_audio_keywords)


def _ensure_mixed_ost_beats(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ensure the mixed short-drama mode keeps both narration and original-audio beats."""
    has_narration = any(item.get("OST") == 0 for item in items)
    has_original_audio = any(item.get("OST") == 1 for item in items)
    if has_narration and has_original_audio:
        return items
    if len(items) < 2:
        logger.warning("逐帧+字幕脚本未混合 OST=0/1，且片段数量不足，无法自动补齐混合结构")
        return items

    if not has_original_audio:
        candidate = max(items, key=_original_audio_candidate_score)
        candidate["OST"] = 1
        candidate["narration"] = f"播放原片{candidate.get('_id', '')}".strip()
        logger.warning(f"逐帧+字幕脚本未生成 OST=1，已将片段 {candidate.get('_id')} 设为原声片段")

    if not has_narration:
        candidate = min(items, key=_original_audio_candidate_score)
        candidate["OST"] = 0
        if _looks_like_original_audio_segment(candidate.get("narration", "")):
            candidate["narration"] = _fallback_narration_from_picture(candidate)
        logger.warning(f"逐帧+字幕脚本未生成 OST=0，已将片段 {candidate.get('_id')} 设为解说片段")

    return items


def _original_audio_candidate_score(item: dict[str, Any]) -> int:
    text = f"{item.get('picture', '')} {item.get('narration', '')}"
    high_tension_keywords = (
        "质问",
        "争吵",
        "对峙",
        "怒吼",
        "哭喊",
        "告白",
        "揭穿",
        "威胁",
        "崩溃",
        "反转",
        "真相",
        "身份",
        "秘密",
        "危机",
        "爆发",
        "惊呼",
        "台词",
        "对白",
    )
    score = sum(3 for keyword in high_tension_keywords if keyword in text)
    score += min(len(str(item.get("picture", ""))), 80) // 20
    return score


def _fallback_narration_from_picture(item: dict[str, Any]) -> str:
    picture = str(item.get("picture", "") or "").strip()
    if picture:
        return f"真正的转折，就藏在这一幕里：{picture}"
    return "真正的转折，就从这一刻开始。"


def _generate_text_with_config(
    prompt: str,
    system_prompt: str,
    temperature: float,
    response_format: str | None,
) -> str:
    return script_enhancement._generate_text_with_config(prompt, system_prompt, temperature, response_format)
