from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ScriptDocument:
    items: list[dict[str, Any]]
    script_title: str = ""


class ScriptDocumentError(ValueError):
    pass


def build_script_document(items: list[dict[str, Any]], script_title: str = "") -> dict[str, Any]:
    """Build the persisted script payload with a top-level title."""
    return {
        "script_title": str(script_title or "").strip(),
        "items": items,
    }


def normalize_script_payload(payload: Any) -> ScriptDocument:
    """Normalize legacy array scripts and titled script documents."""
    if isinstance(payload, list):
        return ScriptDocument(items=payload, script_title="")

    if isinstance(payload, dict):
        items = payload.get("items")
        if items is None:
            items = payload.get("video_clip_json")
        if not isinstance(items, list):
            raise ScriptDocumentError("脚本对象必须包含 items 数组字段")
        title = payload.get("script_title")
        if title is None:
            title = payload.get("title", "")
        return ScriptDocument(items=items, script_title=str(title or "").strip())

    raise ScriptDocumentError("脚本必须是 JSON 数组，或包含 script_title 和 items 的 JSON 对象")


def loads_script_document(script_content: str) -> ScriptDocument:
    try:
        payload = json.loads(script_content)
    except json.JSONDecodeError:
        raise
    return normalize_script_payload(payload)


def load_script_document(script_path: str | Path) -> ScriptDocument:
    return loads_script_document(Path(script_path).read_text(encoding="utf-8"))


def dumps_script_document(items: list[dict[str, Any]], script_title: str = "", *, indent: int = 2) -> str:
    return json.dumps(
        build_script_document(items, script_title),
        ensure_ascii=False,
        indent=indent,
    )
