import asyncio
import json
import time
import traceback

import streamlit as st
from loguru import logger

from app.config import config
from app.services import frame_subtitle_script
from app.services.documentary.frame_analysis_service import DocumentaryFrameAnalysisService
from app.services.generate_narration_script import parse_frame_analysis_to_markdown
from app.services.subtitle_text import read_subtitle_text


def _normalize_progress_value(progress: float | int) -> int:
    try:
        value = float(progress)
    except (TypeError, ValueError):
        return 0
    if 0.0 <= value <= 1.0:
        value *= 100
    return max(0, min(100, int(round(value))))


def generate_frame_subtitle_script_tool(params):
    """Generate a short-drama script by combining visual frame analysis with SRT subtitles."""
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(progress: float, message: str = ""):
        normalized = _normalize_progress_value(progress)
        progress_bar.progress(normalized)
        status_text.text(f"{normalized}% - {message}" if message else f"进度: {normalized}%")

    try:
        with st.spinner("正在生成逐帧+字幕剪辑脚本..."):
            if not params.video_origin_path:
                st.error("请先选择视频文件")
                return False

            subtitle_content = str(st.session_state.get("subtitle_content") or "").strip()
            subtitle_path = st.session_state.get("subtitle_path")
            if not subtitle_content and subtitle_path:
                subtitle_content = read_subtitle_text(subtitle_path).text
            if not subtitle_content:
                st.error("字幕内容为空，请先上传字幕或使用本地 Whisper 生成字幕")
                return False

            vision_llm_provider = (
                st.session_state.get("vision_llm_provider") or config.app.get("vision_llm_provider", "openai")
            ).lower()
            vision_api_key = (
                st.session_state.get(f"vision_{vision_llm_provider}_api_key")
                or config.app.get(f"vision_{vision_llm_provider}_api_key")
            )
            vision_model = (
                st.session_state.get(f"vision_{vision_llm_provider}_model_name")
                or config.app.get(f"vision_{vision_llm_provider}_model_name")
            )
            vision_base_url = (
                st.session_state.get(f"vision_{vision_llm_provider}_base_url")
                or config.app.get(f"vision_{vision_llm_provider}_base_url", "")
            )
            if not vision_api_key or not vision_model:
                raise ValueError(
                    f"未配置 {vision_llm_provider} 的 API Key 或模型名称。"
                    f"请在设置页面配置 vision_{vision_llm_provider}_api_key 和 vision_{vision_llm_provider}_model_name"
                )

            frame_interval_input = st.session_state.get("frame_interval_input") or config.frames.get(
                "frame_interval_input", 3
            )
            vision_batch_size = st.session_state.get("vision_batch_size") or config.frames.get(
                "vision_batch_size", 10
            )
            vision_max_concurrency = st.session_state.get("vision_max_concurrency") or config.frames.get(
                "vision_max_concurrency", 2
            )

            update_progress(10, "正在逐帧分析画面...")
            service = DocumentaryFrameAnalysisService()
            analysis_result = asyncio.run(
                service.analyze_video(
                    video_path=params.video_origin_path,
                    video_theme=st.session_state.get("video_theme", ""),
                    custom_prompt=st.session_state.get("custom_prompt", ""),
                    frame_interval_input=frame_interval_input,
                    vision_batch_size=vision_batch_size,
                    vision_llm_provider=vision_llm_provider,
                    progress_callback=update_progress,
                    vision_api_key=vision_api_key,
                    vision_model_name=vision_model,
                    vision_base_url=vision_base_url,
                    max_concurrency=vision_max_concurrency,
                )
            )

            update_progress(80, "正在结合字幕生成剪辑脚本...")
            frame_markdown = parse_frame_analysis_to_markdown(analysis_result["analysis_json_path"])
            script_items = frame_subtitle_script.generate_frame_subtitle_script(
                frame_analysis_markdown=frame_markdown,
                subtitle_content=subtitle_content,
                video_theme=st.session_state.get("video_theme", ""),
                custom_prompt=st.session_state.get("custom_prompt", ""),
            )

            logger.info(f"逐帧+字幕脚本生成完成，共 {len(script_items)} 个片段")
            st.session_state["video_clip_json"] = json.loads(json.dumps(script_items, ensure_ascii=False))
            update_progress(100, "脚本生成完成")

        time.sleep(0.1)
        progress_bar.progress(100)
        status_text.text("脚本生成完成！")
        st.success("视频脚本生成成功！")
        return True

    except Exception as err:
        st.error(f"生成过程中发生错误: {str(err)}")
        logger.exception(f"生成逐帧+字幕脚本时发生错误\n{traceback.format_exc()}")
        return False
    finally:
        time.sleep(2)
        progress_bar.empty()
        status_text.empty()
