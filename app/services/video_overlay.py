from __future__ import annotations

from typing import Optional, Tuple


def resolve_subtitle_position(
    position: str,
    video_size: Tuple[int, int],
    clip_size: Tuple[int, int],
    custom_position: float | None = None,
) -> tuple[str, int]:
    """Resolve subtitle placement for the final composite video."""
    video_width, video_height = video_size
    _clip_width, clip_height = clip_size
    margin = max(18, int(video_height * 0.05))

    if position == "top":
        return "center", margin
    if position == "center":
        return "center", max(margin, (video_height - clip_height) // 2)
    if position == "custom":
        ratio = 0.7 if custom_position is None else max(0.0, min(float(custom_position) / 100.0, 1.0))
        top = int((video_height - clip_height) * ratio)
        max_y = max(margin, video_height - clip_height - margin)
        return "center", max(margin, min(top, max_y))

    bottom = video_height - margin - clip_height
    return "center", max(margin, bottom)


def resolve_fixed_text_overlay_position(
    kind: str,
    position: str,
    video_size: Tuple[int, int],
    clip_size: Tuple[int, int],
    subtitle_position: str = "bottom",
    custom_position: float | None = None,
    reference_position: Optional[tuple[str, int]] = None,
    reference_clip_size: Optional[Tuple[int, int]] = None,
) -> tuple[str, int]:
    """Resolve title / episode overlay positions without depending on MoviePy."""
    video_width, video_height = video_size
    _clip_width, clip_height = clip_size
    top_margin = max(20, int(video_height * 0.04))
    gap = max(8, int(video_height * 0.01))

    if kind == "episode" and position == "below_title" and reference_position and reference_clip_size:
        ref_x, ref_y = reference_position
        _ref_w, ref_h = reference_clip_size
        y = ref_y + ref_h + gap
        if subtitle_position == "bottom":
            y = min(y, int(video_height * 0.18))
        return "center", max(top_margin, y)

    if position == "center":
        return "center", max(top_margin, (video_height - clip_height) // 2)

    if position == "bottom":
        return "center", max(top_margin, video_height - clip_height - int(video_height * 0.16))

    if position == "custom":
        ratio = 0.04 if custom_position is None else max(0.0, min(float(custom_position) / 100.0, 1.0))
        y = int(video_height * ratio)
        return "center", max(top_margin, min(y, int(video_height * 0.22)))

    # Default to a top placement. The clip height is included so taller titles still stay inside the header band.
    return "center", top_margin
