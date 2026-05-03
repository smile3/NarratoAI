import asyncio
import concurrent.futures
import copy
import json
import re
from typing import Any, Callable


PROMPT_STYLE_TEMPLATES: dict[str, dict[str, str]] = {
    "default": {
        "label": "默认（原本风格）",
        "prompt": """
请根据画面信息生成自然、连贯、口语化的短视频解说文案。
要求：
1. 严格贴合画面，不虚构没有出现的人物、动作和结果。
2. 保持时间戳和剪辑顺序不变。
3. 文案短句优先，节奏清楚，适合配音朗读。
4. 开头快速说明看点，中段顺畅推进，结尾保留记忆点。
""".strip(),
    },
    "short_drama": {
        "label": "短剧（悬念吸引）",
        "prompt": """
请按短剧推广解说风格生成文案，重点制造悬念、冲突和继续观看的欲望。
要求：
1. 开头 3 秒必须有钩子，例如反转、危机、秘密、身份差。
2. 每个片段都要推进疑问：他为什么这样做、她接下来会怎样、真相是否反转。
3. 语言口语化、有节奏，避免长句和书面腔。
4. 不改变时间戳，不虚构画面，只强化已有剧情张力。
""".strip(),
    },
    "movie": {
        "label": "电影（沉浸叙事）",
        "prompt": """
请按电影解说风格生成文案，突出人物动机、情绪铺垫、镜头氛围和剧情转折。
要求：
1. 语言有画面感，但不过度煽情。
2. 用简洁句子讲清人物处境和关键选择。
3. 在转折处制造期待，让观众想知道后续。
4. 不改变时间戳，不虚构画面和剧情结论。
""".strip(),
    },
    "variety": {
        "label": "综艺（轻松吐槽）",
        "prompt": """
请按综艺解说风格生成文案，语气轻松、有梗、有互动感。
要求：
1. 适度吐槽画面中的反差和笑点，但不要喧宾夺主。
2. 节奏明快，适合短视频连续观看。
3. 可以使用轻微反问和调侃制造娱乐感。
4. 不改变时间戳，不虚构画面。
""".strip(),
    },
    "science": {
        "label": "科普（清晰有趣）",
        "prompt": """
请按科普解说风格生成文案，把画面中的现象讲得清楚、有趣、可信。
要求：
1. 开头用问题或反常识点吸引注意。
2. 解释要准确，不夸大，不编造专业结论。
3. 多用类比和短句，让普通观众容易理解。
4. 不改变时间戳，不虚构画面。
""".strip(),
    },
}


def get_prompt_style_options() -> list[tuple[str, str]]:
    """Return prompt style options as (key, label)."""
    return [(key, value["label"]) for key, value in PROMPT_STYLE_TEMPLATES.items()]


def get_prompt_template(style: str | None) -> str:
    """Return the editable default prompt for a selected narration style."""
    normalized = style if style in PROMPT_STYLE_TEMPLATES else "default"
    return PROMPT_STYLE_TEMPLATES[normalized]["prompt"]


def parse_script_items_payload(payload: Any) -> list[dict[str, Any]]:
    """Parse model JSON output and return a list of script item dictionaries."""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if isinstance(payload, dict):
        raw_items = payload.get("items", payload.get("script", payload.get("data", [])))
        return raw_items if isinstance(raw_items, list) else []

    text = str(payload or "").strip()
    if not text:
        return []

    candidates = [text, _strip_code_fence(text), text.replace("{{", "{").replace("}}", "}")]

    json_block = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if json_block:
        candidates.append(json_block.group(1).strip())

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidates.append(text[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        return parse_script_items_payload(parsed)

    return []


def parse_script_optimization_payload(payload: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Parse an optimization response with a hook object and rewritten items."""
    parsed = _parse_json_object_payload(payload)
    if isinstance(parsed, dict):
        hook = parsed.get("hook") if isinstance(parsed.get("hook"), dict) else {}
        items = parse_script_items_payload(parsed)
        return hook, items

    return {}, parse_script_items_payload(payload)


def merge_optimized_narrations(
    original_items: list[dict[str, Any]],
    optimized_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Apply optimized narration text while preserving timing and all non-narration fields."""
    merged = copy.deepcopy(original_items)
    optimized_by_id = {
        item.get("_id"): item
        for item in optimized_items
        if isinstance(item, dict) and item.get("_id") is not None
    }

    for index, original_item in enumerate(merged):
        optimized_item = optimized_by_id.get(original_item.get("_id"))
        if optimized_item is None and index < len(optimized_items):
            candidate = optimized_items[index]
            optimized_item = candidate if isinstance(candidate, dict) else None
        if optimized_item is None:
            continue

        narration = str(optimized_item.get("narration", "") or "").strip()
        if narration:
            original_item["narration"] = narration

    return merged


def apply_script_optimization(
    original_items: list[dict[str, Any]],
    optimized_items: list[dict[str, Any]],
    hook: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Rewrite narration and prepend a duplicated core-shot hook at the beginning."""
    merged = merge_optimized_narrations(original_items, optimized_items)
    if not merged:
        return merged

    hook_item = _build_hook_item(merged, hook or {})
    with_hook = [hook_item, *copy.deepcopy(merged)]
    for index, item in enumerate(with_hook, 1):
        item["_id"] = index
    return with_hook


def clean_generated_title(raw_title: str, max_length: int = 24) -> str:
    """Clean a model-generated promotional title down to a single display line."""
    cleaned = _strip_code_fence(str(raw_title or "")).strip()
    cleaned = re.sub(r"^(脚本标题|标题|片名|视频标题|title)\s*[:：]\s*", "", cleaned, flags=re.IGNORECASE)

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    cleaned = lines[0] if lines else ""
    cleaned = cleaned.strip(" \t\r\n'\"`，,。；;：:")
    cleaned = re.sub(r"^[《<【\[]\s*", "", cleaned)
    cleaned = re.sub(r"\s*[》>】\]]$", "", cleaned)
    cleaned = re.sub(r"\s+", "", cleaned)
    return cleaned[:max_length]


def build_title_prompt(script_items: list[dict[str, Any]], video_theme: str = "", max_length: int = 24) -> str:
    script_digest = _build_script_digest(script_items)
    theme_line = f"视频主题：{video_theme.strip()}\n" if video_theme and video_theme.strip() else ""
    return f"""
请为下面的视频解说脚本生成 1 个适合短视频推广的中文标题。
{theme_line}要求：
1. 必须吸引眼球，有悬念或冲突感。
2. 不要标题党到脱离内容，不要虚构脚本没有的信息。
3. 不要输出解释，不要加引号，不要加书名号。
4. 标题不超过 {max_length} 个中文字符。

脚本摘要：
{script_digest}
""".strip()


def build_script_optimization_prompt(
    script_items: list[dict[str, Any]],
    style: str = "short_drama",
    custom_instruction: str = "",
) -> str:
    style_prompt = custom_instruction.strip() or get_prompt_template(style)
    slim_items = [
        {
            "_id": item.get("_id", index + 1),
            "timestamp": item.get("timestamp", ""),
            "picture": item.get("picture", ""),
            "narration": item.get("narration", ""),
            "OST": item.get("OST", 0),
        }
        for index, item in enumerate(script_items)
        if isinstance(item, dict)
    ]

    return f"""
请对下面已经生成的视频解说脚本做二次加工。

创作风格要求：
{style_prompt}

硬性规则：
1. 先判断哪一个片段是最核心、最能吸引观众注意力的镜头。
2. 为这个核心镜头单独写一段开场钩子文案，放在 hook 字段里；后续系统会把这个镜头复制到视频最开始播放一次。
3. items 里只优化原片段 narration 字段，让语言更自然、更有悬念、更吸引人注意。
4. 严禁修改原片段 timestamp、_id、OST、picture，也不要改变原片段数量和顺序。
5. 不要新增不存在的情节，不要改变剪辑时间。
6. 只输出 JSON，不要输出解释文字。

输出格式：
{{
  "hook": {{
    "source_id": 2,
    "narration": "复制到视频最开始的核心镜头开场钩子文案"
  }},
  "items": [
    {{"_id": 1, "narration": "优化后的解说文案"}}
  ]
}}

原始脚本：
{json.dumps(slim_items, ensure_ascii=False, indent=2)}
""".strip()


def generate_script_title(
    script_items: list[dict[str, Any]],
    video_theme: str = "",
    max_length: int = 24,
    text_generator: Callable[[str, str, float, str | None], str] | None = None,
) -> str:
    """Generate and clean a promotional title from script items."""
    generator = text_generator or _generate_text_with_config
    raw_title = generator(
        build_title_prompt(script_items, video_theme=video_theme, max_length=max_length),
        "你是一位短视频爆款标题策划。",
        0.9,
        None,
    )
    return clean_generated_title(raw_title, max_length=max_length)


def optimize_script_narrations(
    script_items: list[dict[str, Any]],
    style: str = "short_drama",
    custom_instruction: str = "",
    text_generator: Callable[[str, str, float, str | None], str] | None = None,
) -> list[dict[str, Any]]:
    """Use an LLM to rewrite narration text and preserve original timing metadata."""
    generator = text_generator or _generate_text_with_config
    raw_payload = generator(
        build_script_optimization_prompt(script_items, style=style, custom_instruction=custom_instruction),
        "你是一位专业短视频解说文案编辑，只改文案，不改时间轴。",
        0.8,
        "json",
    )
    hook, optimized_items = parse_script_optimization_payload(raw_payload)
    if not optimized_items:
        raise ValueError("二次加工失败：模型没有返回有效的 items JSON")
    return apply_script_optimization(script_items, optimized_items, hook)


def _strip_code_fence(text: str) -> str:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _parse_json_object_payload(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        return payload

    text = str(payload or "").strip()
    if not text:
        return None

    candidates = [text, _strip_code_fence(text), text.replace("{{", "{").replace("}}", "}")]

    json_block = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if json_block:
        candidates.append(json_block.group(1).strip())

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidates.append(text[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _build_hook_item(script_items: list[dict[str, Any]], hook: dict[str, Any]) -> dict[str, Any]:
    source_id = hook.get("source_id", hook.get("_id"))
    source_index = hook.get("source_index")
    source_item = _find_hook_source_item(script_items, source_id=source_id, source_index=source_index)

    hook_item = copy.deepcopy(source_item)
    hook_narration = str(hook.get("narration", "") or "").strip()
    if not hook_narration:
        hook_narration = _fallback_hook_narration(source_item)
    hook_item["narration"] = hook_narration
    # The hook is a replay of the chosen visual moment with narration, so keep the original timestamp/picture
    # but make it a TTS segment even if the source was an OST-only beat.
    hook_item["OST"] = 2 if hook_item.get("OST") == 1 else hook_item.get("OST", 2)
    return hook_item


def _find_hook_source_item(
    script_items: list[dict[str, Any]],
    *,
    source_id: Any,
    source_index: Any,
) -> dict[str, Any]:
    if source_id is not None:
        for item in script_items:
            if item.get("_id") == source_id or str(item.get("_id")) == str(source_id):
                return item

    if source_index is not None:
        try:
            index = int(source_index)
            if 0 <= index < len(script_items):
                return script_items[index]
            if 1 <= index <= len(script_items):
                return script_items[index - 1]
        except Exception:
            pass

    return max(script_items, key=lambda item: len(str(item.get("picture", ""))) + len(str(item.get("narration", ""))))


def _fallback_hook_narration(source_item: dict[str, Any]) -> str:
    picture = str(source_item.get("picture", "") or "").strip()
    if picture:
        return f"先别眨眼，最关键的一幕就藏在这里：{picture}"
    narration = str(source_item.get("narration", "") or "").strip()
    if narration:
        return f"先看这一幕，后面的反转都从这里开始：{narration}"
    return "先别眨眼，真正吸引人的反转马上开始。"


def _build_script_digest(script_items: list[dict[str, Any]], max_chars: int = 2400) -> str:
    lines = []
    for item in script_items:
        if not isinstance(item, dict):
            continue
        line = " | ".join(
            part
            for part in [
                str(item.get("timestamp", "") or "").strip(),
                str(item.get("picture", "") or "").strip(),
                str(item.get("narration", "") or "").strip(),
            ]
            if part
        )
        if line:
            lines.append(line)
        if sum(len(existing) for existing in lines) >= max_chars:
            break
    return "\n".join(lines)[:max_chars]


def _run_async_safely(coro_func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    def run_in_new_loop() -> Any:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro_func(*args, **kwargs))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return run_in_new_loop()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(run_in_new_loop).result()


def _generate_text_with_config(
    prompt: str,
    system_prompt: str,
    temperature: float,
    response_format: str | None,
) -> str:
    from app.config import config
    from app.services.llm.manager import LLMServiceManager
    from app.services.llm.unified_service import UnifiedLLMService

    if not LLMServiceManager.is_registered():
        from app.services.llm.providers import register_all_providers

        register_all_providers()

    provider = str(config.app.get("text_llm_provider", "openai") or "openai").lower()
    api_key = config.app.get(f"text_{provider}_api_key")
    model_name = config.app.get(f"text_{provider}_model_name")
    base_url = config.app.get(f"text_{provider}_base_url")
    if not api_key or not model_name:
        raise ValueError(f"未配置 {provider} 的文本模型 API Key 或模型名称")

    result = _run_async_safely(
        UnifiedLLMService.generate_text,
        prompt=prompt,
        system_prompt=system_prompt,
        provider=provider,
        temperature=temperature,
        response_format=response_format,
        api_key=api_key,
        api_base=base_url,
    )
    return result if isinstance(result, str) else str(result)
