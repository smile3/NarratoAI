from __future__ import annotations

import base64
import mimetypes
import re
from pathlib import Path
from typing import Any, Callable

from loguru import logger

from app.config import config
from app.config.defaults import normalize_openai_compatible_model_name
from app.services import script_enhancement
from app.services.prompts import PromptManager


VIDEO_UNDERSTANDING_PROMPT_CATEGORY = "short_drama_narration"
VIDEO_UNDERSTANDING_PROMPT_NAME = "video_understanding_generation"

VideoGenerator = Callable[[str, str, str, float, str | None], str]


def build_video_understanding_prompt(video_theme: str = "", custom_prompt: str = "") -> str:
    """Build the prompt used by the direct video-understanding script mode."""
    return PromptManager.get_prompt(
        category=VIDEO_UNDERSTANDING_PROMPT_CATEGORY,
        name=VIDEO_UNDERSTANDING_PROMPT_NAME,
        parameters={
            "video_theme": video_theme,
            "custom_prompt": custom_prompt,
        },
    )


def generate_video_understanding_script(
    video_path: str,
    video_theme: str = "",
    custom_prompt: str = "",
    video_generator: VideoGenerator | None = None,
) -> list[dict[str, Any]]:
    """Generate normalized script items by sending the whole video to a video model."""
    video_file = Path(video_path or "")
    if not video_file.is_file():
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    prompt = build_video_understanding_prompt(video_theme=video_theme, custom_prompt=custom_prompt)
    system_prompt = (
        PromptManager.get_prompt_object(
            category=VIDEO_UNDERSTANDING_PROMPT_CATEGORY,
            name=VIDEO_UNDERSTANDING_PROMPT_NAME,
        ).get_system_prompt()
        or "你是一位专业短剧解说剪辑导演，必须输出合法 JSON。"
    )

    generator = video_generator or _generate_with_openai_compatible_video_model
    raw_payload = generator(str(video_file), prompt, system_prompt, 0.7, "json")
    items = script_enhancement.parse_script_items_payload(raw_payload)
    if not items:
        raise ValueError("视频理解脚本生成失败：模型没有返回有效的 items JSON")
    return normalize_video_understanding_items(items)


def normalize_video_understanding_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize model output into the editor's script item schema."""
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        timestamp = _normalize_timestamp_range(item.get("timestamp"))
        picture = str(item.get("picture", "") or "").strip()
        narration = str(item.get("narration", "") or "").strip()
        if not timestamp or not narration:
            continue

        ost = _normalize_ost_value(item.get("OST"), narration=narration)
        normalized.append(
            {
                "_id": len(normalized) + 1,
                "timestamp": timestamp,
                "picture": picture or "视频理解模型识别到的关键剧情画面",
                "narration": narration,
                "OST": ost,
            }
        )

    if not normalized:
        raise ValueError("视频理解脚本生成失败：返回片段缺少 timestamp 或 narration")

    return _ensure_mixed_ost_beats(normalized)


def _generate_with_openai_compatible_video_model(
    video_path: str,
    prompt: str,
    system_prompt: str,
    temperature: float,
    response_format: str | None,
) -> str:
    from openai import BadRequestError, OpenAI

    provider = str(config.app.get("video_understanding_llm_provider", "openai") or "openai").lower()
    api_key = config.app.get(f"video_understanding_{provider}_api_key")
    model_name = config.app.get(f"video_understanding_{provider}_model_name")
    base_url = config.app.get(f"video_understanding_{provider}_base_url")

    if not api_key or not model_name:
        raise ValueError(
            f"未配置视频理解模型的 API Key 或模型名称。请在基础设置中配置 "
            f"video_understanding_{provider}_api_key 和 video_understanding_{provider}_model_name"
        )

    model_name = normalize_openai_compatible_model_name(str(model_name), provider=provider)
    client = OpenAI(
        api_key=api_key,
        base_url=base_url or None,
        timeout=float(config.app.get("llm_video_timeout", 300)),
        max_retries=int(config.app.get("llm_max_retries", 3)),
    )

    completion_kwargs: dict[str, Any] = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "video_url", "video_url": {"url": _video_to_data_url(video_path)}},
                ],
            },
        ],
        "temperature": temperature,
    }

    max_tokens = config.app.get("video_understanding_max_tokens")
    if max_tokens:
        completion_kwargs["max_tokens"] = int(max_tokens)
    if response_format == "json":
        completion_kwargs["response_format"] = {"type": "json_object"}

    try:
        response = client.chat.completions.create(**completion_kwargs)
    except BadRequestError as exc:
        error_msg = str(exc)
        if response_format == "json" and "response_format" in error_msg.lower():
            logger.warning("视频理解模型网关不支持 response_format，回退为提示词约束 JSON 输出")
            completion_kwargs.pop("response_format", None)
            response = client.chat.completions.create(**completion_kwargs)
        elif _looks_like_video_content_error(error_msg):
            raise ValueError(
                "当前视频理解模型或网关不支持 OpenAI-compatible video_url 视频输入。"
                "请更换支持视频理解的模型/网关，或确认该网关的视频内容块格式。"
            ) from exc
        else:
            raise

    content = _extract_chat_completion_text(response)
    if not content:
        raise ValueError("视频理解模型返回空响应")
    return content


def _video_to_data_url(video_path: str) -> str:
    file_path = Path(video_path)
    mime_type = mimetypes.guess_type(file_path.name)[0] or "video/mp4"
    encoded = base64.b64encode(file_path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def _extract_chat_completion_text(response: Any) -> str:
    if not getattr(response, "choices", None):
        return ""
    message = response.choices[0].message
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "\n".join(str(part.get("text", "")) for part in content if isinstance(part, dict)).strip()
    return str(content or "").strip()


def _normalize_timestamp_range(raw_timestamp: Any) -> str:
    text = str(raw_timestamp or "").strip()
    if not text:
        return ""

    text = text.replace("-->", "-").replace("—", "-").replace("–", "-")
    match = re.search(
        r"(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})\s*-\s*(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})",
        text,
    )
    if not match:
        return text
    return f"{_normalize_timecode(match.group(1))}-{_normalize_timecode(match.group(2))}"


def _normalize_timecode(raw_timecode: str) -> str:
    timecode = raw_timecode.strip().replace(".", ",")
    hhmmss, millis = timecode.split(",", 1)
    parts = hhmmss.split(":")
    parts[0] = parts[0].zfill(2)
    millis = millis[:3].ljust(3, "0")
    return f"{':'.join(parts)},{millis}"


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
    original_audio_keywords = ("播放原片", "原声", "原音", "原台词")
    return any(keyword in text for keyword in original_audio_keywords)


def _ensure_mixed_ost_beats(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    has_narration = any(item.get("OST") == 0 for item in items)
    has_original_audio = any(item.get("OST") == 1 for item in items)
    if has_narration and has_original_audio:
        return items
    if len(items) < 2:
        logger.warning("视频理解脚本未混合 OST=0/1，且片段数量不足，无法自动补齐混合结构")
        return items

    if not has_original_audio:
        candidate = max(items, key=_original_audio_candidate_score)
        candidate["OST"] = 1
        candidate["narration"] = f"播放原片{candidate.get('_id', '')}".strip()
        logger.warning(f"视频理解脚本未生成 OST=1，已将片段 {candidate.get('_id')} 设为原声片段")

    if not has_narration:
        candidate = min(items, key=_original_audio_candidate_score)
        candidate["OST"] = 0
        if _looks_like_original_audio_segment(candidate.get("narration", "")):
            candidate["narration"] = _fallback_narration_from_picture(candidate)
        logger.warning(f"视频理解脚本未生成 OST=0，已将片段 {candidate.get('_id')} 设为解说片段")

    return items


def _original_audio_candidate_score(item: dict[str, Any]) -> int:
    text = f"{item.get('picture', '')} {item.get('narration', '')}"
    keywords = (
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
        "台词",
        "对白",
    )
    score = sum(3 for keyword in keywords if keyword in text)
    score += min(len(str(item.get("picture", ""))), 80) // 20
    return score


def _fallback_narration_from_picture(item: dict[str, Any]) -> str:
    picture = str(item.get("picture", "") or "").strip()
    if picture:
        return f"真正的转折，就藏在这一幕里：{picture}"
    return "真正的转折，就从这一刻开始。"


def _looks_like_video_content_error(message: str) -> bool:
    lowered = (message or "").lower()
    return "video_url" in lowered or "video" in lowered or "content type" in lowered
