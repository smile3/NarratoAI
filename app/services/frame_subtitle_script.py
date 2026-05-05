import json
from typing import Any, Callable

from app.services import script_enhancement


def build_frame_subtitle_prompt(
    frame_analysis_markdown: str,
    subtitle_content: str,
    video_theme: str = "",
    custom_prompt: str = "",
) -> str:
    """Build a prompt that asks the text model to combine frame analysis and subtitles."""
    theme_line = f"视频主题：{video_theme.strip()}\n" if video_theme and video_theme.strip() else ""
    custom_line = f"补充要求：{custom_prompt.strip()}\n" if custom_prompt and custom_prompt.strip() else ""
    return f"""
你是一位专业短剧剪辑和短视频解说脚本策划。请同时参考【画面分析】和【字幕内容】，生成适合短剧推广的剪辑脚本。
{theme_line}{custom_line}
核心要求：
1. 必须把画面和字幕结合判断剧情，不要只依赖字幕，也不要只看画面；画面决定镜头是否有看点，字幕帮助理解人物关系和冲突。
2. 优先选择冲突、反转、秘密、危机、身份差、误会升级等高吸引力片段。
3. 每个片段时长要根据剧情自然变化，不要所有片段固定同一长度；短剧节奏要快，单个片段尽量短。
4. 解说文案要和画面时长匹配，短镜头少说，长镜头适当展开，不要明显超过画面可承载时长。
5. 成片尽量控制在 3 分钟左右，最多不要超过 5 分钟；可以删减无关铺垫，但前后衔接不能突兀。
6. 开头要有强钩子，结尾要留下悬念，吸引继续观看，不需要把故事讲完。
7. 只输出 JSON，不要输出解释文字。

输出格式：
{{
  "items": [
    {{
      "_id": 1,
      "timestamp": "00:00:01,000-00:00:05,000",
      "picture": "画面描述",
      "narration": "解说文案",
      "OST": 2
    }}
  ]
}}

【画面分析】
{frame_analysis_markdown}

【字幕内容】
{subtitle_content}
""".strip()


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
    generator = text_generator or _generate_text_with_config
    raw_payload = generator(
        prompt,
        "你是一位专业短剧剪辑解说脚本专家，必须输出合法 JSON。",
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
        normalized.append(
            {
                "_id": len(normalized) + 1,
                "timestamp": timestamp,
                "picture": picture,
                "narration": narration,
                "OST": 2,
            }
        )
    if not normalized:
        raise ValueError("逐帧+字幕脚本生成失败：返回片段缺少 timestamp 或 narration")
    return normalized


def _generate_text_with_config(
    prompt: str,
    system_prompt: str,
    temperature: float,
    response_format: str | None,
) -> str:
    return script_enhancement._generate_text_with_config(prompt, system_prompt, temperature, response_format)
