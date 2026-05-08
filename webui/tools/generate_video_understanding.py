import json
import time
import traceback

import streamlit as st
from loguru import logger

from app.services import video_understanding_script


def generate_video_understanding_script_tool(params):
    """Generate a short-drama script by sending the whole video to a video model."""
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(progress: int, message: str = ""):
        progress_bar.progress(max(0, min(100, progress)))
        status_text.text(f"{progress}% - {message}" if message else f"进度: {progress}%")

    try:
        with st.spinner("正在使用视频理解模型生成剪辑脚本..."):
            if not params.video_origin_path:
                st.error("请先选择视频文件")
                return False

            update_progress(10, "正在发送完整视频给视频理解模型...")
            script_items = video_understanding_script.generate_video_understanding_script(
                video_path=params.video_origin_path,
                video_theme=st.session_state.get("video_theme", ""),
                custom_prompt=st.session_state.get("custom_prompt", ""),
            )

            logger.info(f"视频理解脚本生成完成，共 {len(script_items)} 个片段")
            st.session_state["video_clip_json"] = json.loads(json.dumps(script_items, ensure_ascii=False))
            update_progress(100, "脚本生成完成")

        time.sleep(0.1)
        progress_bar.progress(100)
        status_text.text("脚本生成完成！")
        st.success("视频理解解说脚本生成成功！")
        return True

    except Exception as err:
        st.error(f"生成过程中发生错误: {str(err)}")
        logger.exception(f"生成视频理解解说脚本时发生错误\n{traceback.format_exc()}")
        return False
    finally:
        time.sleep(2)
        progress_bar.empty()
        status_text.empty()
