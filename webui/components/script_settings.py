import os
import glob
import json
import time
import traceback
import streamlit as st
from loguru import logger

from app.config import config
from app.models.schema import VideoClipParams
from app.services import local_whisper_subtitle, script_enhancement
from app.services.subtitle_text import decode_subtitle_bytes
from app.utils import utils, check_script, script_document
from webui.tools.generate_frame_subtitle import generate_frame_subtitle_script_tool
from webui.tools.generate_script_docu import generate_script_docu
from webui.tools.generate_script_short import generate_script_short
from webui.tools.generate_short_summary import generate_script_short_sunmmary
from webui.tools.generate_video_understanding import generate_video_understanding_script_tool


MODE_FILE = "file_selection"
MODE_AUTO = "auto"
MODE_SHORT = "short"
MODE_SUMMARY = "summary"
MODE_FRAME_SUBTITLE = "frame_subtitle"
MODE_VIDEO_UNDERSTANDING = "video_understanding"
GENERATED_SCRIPT_MODES = [MODE_AUTO, MODE_SHORT, MODE_SUMMARY, MODE_FRAME_SUBTITLE, MODE_VIDEO_UNDERSTANDING]
SUBTITLE_REQUIRED_MODES = [MODE_SHORT, MODE_SUMMARY, MODE_FRAME_SUBTITLE]


def render_script_panel(tr):
    """渲染脚本配置面板"""
    with st.container(border=True):
        st.write(tr("Video Script Configuration"))
        params = VideoClipParams()

        # 渲染脚本文件选择
        render_script_file(tr, params)

        # 渲染视频文件选择
        render_video_file(tr, params)

        # 获取当前选择的脚本类型
        script_path = st.session_state.get('video_clip_json_path', '')

        # 根据脚本类型显示不同的布局
        if script_path == MODE_AUTO:
            # 画面解说
            render_video_details(tr)
        elif script_path == MODE_SHORT:
            # 短剧混剪
            render_short_generate_options(tr)
        elif script_path == MODE_SUMMARY:
            # 短剧解说
            short_drama_summary(tr)
        elif script_path == MODE_FRAME_SUBTITLE:
            # 逐帧+字幕
            render_frame_subtitle_options(tr)
        elif script_path == MODE_VIDEO_UNDERSTANDING:
            # 视频理解解说
            render_video_understanding_options(tr)
        else:
            # 默认为空
            pass

        if script_path not in [MODE_AUTO, MODE_VIDEO_UNDERSTANDING]:
            render_script_title_display(tr)

        # 渲染脚本操作按钮
        render_script_buttons(tr, params)


def render_script_file(tr, params):
    """渲染脚本文件选择"""
    # 功能模式常量定义在模块顶部，方便生成流程共用。
    # 处理保存脚本后的模式切换（必须在 widget 实例化之前）
    if st.session_state.get('_switch_to_file_mode'):
        st.session_state['script_mode_selection'] = tr("Select/Upload Script")
        del st.session_state['_switch_to_file_mode']

    # 模式选项映射
    mode_options = {
        tr("Select/Upload Script"): MODE_FILE,
        tr("Auto Generate"): MODE_AUTO,
        tr("Short Generate"): MODE_SHORT,
        tr("Short Drama Summary"): MODE_SUMMARY,
        tr("Frame Subtitle Generate"): MODE_FRAME_SUBTITLE,
        tr("Video Understanding Generate"): MODE_VIDEO_UNDERSTANDING,
    }
    
    # 获取当前状态
    current_path = st.session_state.get('video_clip_json_path', '')
    
    # 确定当前选中的模式索引
    default_index = 0
    mode_keys = list(mode_options.keys())
    
    if current_path == MODE_AUTO:
        default_index = mode_keys.index(tr("Auto Generate"))
    elif current_path == MODE_SHORT:
        default_index = mode_keys.index(tr("Short Generate"))
    elif current_path == MODE_SUMMARY:
        default_index = mode_keys.index(tr("Short Drama Summary"))
    elif current_path == MODE_FRAME_SUBTITLE:
        default_index = mode_keys.index(tr("Frame Subtitle Generate"))
    elif current_path == MODE_VIDEO_UNDERSTANDING:
        default_index = mode_keys.index(tr("Video Understanding Generate"))
    else:
        default_index = mode_keys.index(tr("Select/Upload Script"))

    # 1. 渲染功能选择下拉框
    # 使用 segmented_control 替代 selectbox，提供更好的视觉体验
    default_mode_label = mode_keys[default_index]
    
    # 定义回调函数来处理状态更新
    def update_script_mode():
        # 获取当前选中的标签
        selected_label = st.session_state.script_mode_selection
        if selected_label:
            # 更新实际的 path 状态
            new_mode = mode_options[selected_label]
            st.session_state.video_clip_json_path = new_mode
            params.video_clip_json_path = new_mode
        else:
            # 如果用户取消选择（segmented_control 允许取消），恢复到默认或上一个状态
            # 这里我们强制保持当前状态，或者重置为默认
            st.session_state.script_mode_selection = default_mode_label

    # 渲染组件
    selected_mode_label = st.segmented_control(
        tr("Video Type"),
        options=mode_keys,
        default=default_mode_label,
        key="script_mode_selection",
        on_change=update_script_mode
    )
    
    # 处理未选择的情况（虽然有default，但在某些交互下可能为空）
    if not selected_mode_label:
        selected_mode_label = default_mode_label
        
    selected_mode = mode_options[selected_mode_label]

    # 2. 根据选择的模式处理逻辑
    if selected_mode == MODE_FILE:
        # --- 文件选择模式 ---
        script_list = [
            (tr("None"), ""),
            (tr("Upload Script"), "upload_script")
        ]

        # 获取已有脚本文件
        suffix = "*.json"
        script_dir = utils.script_dir()
        files = glob.glob(os.path.join(script_dir, suffix))
        file_list = []

        for file in files:
            file_list.append({
                "name": os.path.basename(file),
                "file": file,
                "ctime": os.path.getctime(file)
            })

        file_list.sort(key=lambda x: x["ctime"], reverse=True)
        for file in file_list:
            display_name = file['file'].replace(config.root_dir, "")
            script_list.append((display_name, file['file']))

        # 找到保存的脚本文件在列表中的索引
        # 如果当前path是特殊生成模式，则重置为空
        saved_script_path = current_path if current_path not in GENERATED_SCRIPT_MODES else ""
        
        selected_index = 0
        for i, (_, path) in enumerate(script_list):
            if path == saved_script_path:
                selected_index = i
                break

        # 如果找到了保存的脚本，同步更新 selectbox 的 key 状态
        if saved_script_path and selected_index > 0:
            st.session_state['script_file_selection'] = selected_index

        selected_script_index = st.selectbox(
            tr("Script Files"),
            index=selected_index,
            options=range(len(script_list)),
            format_func=lambda x: script_list[x][0],
            key="script_file_selection"
        )

        script_path = script_list[selected_script_index][1]
        # 只有当用户实际选择了脚本时才更新路径，避免覆盖已保存的路径
        if script_path:
            st.session_state['video_clip_json_path'] = script_path
            params.video_clip_json_path = script_path
        elif saved_script_path:
            # 如果用户选择了 "None" 但之前有保存的脚本，保持原有路径
            st.session_state['video_clip_json_path'] = saved_script_path
            params.video_clip_json_path = saved_script_path

        # 处理脚本上传
        if script_path == "upload_script":
            uploaded_file = st.file_uploader(
                tr("Upload Script File"),
                type=["json"],
                accept_multiple_files=False,
            )

            if uploaded_file is not None:
                try:
                    # 读取上传的JSON内容并兼容旧数组脚本/新标题脚本文档
                    script_content = uploaded_file.read().decode('utf-8')
                    json_data = json.loads(script_content)
                    document = script_document.normalize_script_payload(json_data)
                    json_data = script_document.build_script_document(document.items, document.script_title)

                    # 保存到脚本目录
                    safe_filename = os.path.basename(uploaded_file.name)
                    script_file_path = os.path.join(script_dir, safe_filename)
                    file_name, file_extension = os.path.splitext(safe_filename)

                    # 如果文件已存在,添加时间戳
                    if os.path.exists(script_file_path):
                        timestamp = time.strftime("%Y%m%d%H%M%S")
                        file_name_with_timestamp = f"{file_name}_{timestamp}"
                        script_file_path = os.path.join(script_dir, file_name_with_timestamp + file_extension)

                    # 写入文件
                    with open(script_file_path, "w", encoding='utf-8') as f:
                        json.dump(json_data, f, ensure_ascii=False, indent=2)

                    # 更新状态
                    st.success(tr("Script Uploaded Successfully"))
                    st.session_state['video_clip_json_path'] = script_file_path
                    st.session_state['video_clip_json'] = document.items
                    st.session_state['script_title'] = document.script_title
                    params.video_clip_json_path = script_file_path
                    time.sleep(1)
                    st.rerun()

                except json.JSONDecodeError:
                    st.error(tr("Invalid JSON format"))
                except Exception as e:
                    st.error(f"{tr('Upload failed')}: {str(e)}")
    else:
        # --- 功能生成模式 ---
        st.session_state['video_clip_json_path'] = selected_mode
        params.video_clip_json_path = selected_mode


def render_video_file(tr, params):
    """渲染视频文件选择"""
    video_list = [(tr("None"), ""), (tr("Upload Local Files"), "upload_local")]

    # 获取已有视频文件
    for suffix in ["*.mp4", "*.mov", "*.avi", "*.mkv"]:
        video_files = glob.glob(os.path.join(utils.video_dir(), suffix))
        for file in video_files:
            display_name = file.replace(config.root_dir, "")
            video_list.append((display_name, file))

    saved_video_path = st.session_state.get('video_origin_path', '')
    selected_video_default = 0
    for index, (_label, candidate_path) in enumerate(video_list):
        if candidate_path == saved_video_path:
            selected_video_default = index
            break

    selected_video_index = st.selectbox(
        tr("Video File"),
        index=selected_video_default,
        options=range(len(video_list)),
        format_func=lambda x: video_list[x][0],
        key="video_file_selection",
    )

    video_path = video_list[selected_video_index][1]
    st.session_state['video_origin_path'] = video_path
    params.video_origin_path = video_path

    if video_path == "upload_local":
        uploaded_file = st.file_uploader(
            tr("Upload Local Files"),
            type=["mp4", "mov", "avi", "flv", "mkv"],
            accept_multiple_files=False,
        )

        if uploaded_file is not None:
            safe_filename = os.path.basename(uploaded_file.name)
            video_file_path = os.path.join(utils.video_dir(), safe_filename)
            file_name, file_extension = os.path.splitext(safe_filename)

            if os.path.exists(video_file_path):
                timestamp = time.strftime("%Y%m%d%H%M%S")
                file_name_with_timestamp = f"{file_name}_{timestamp}"
                video_file_path = os.path.join(utils.video_dir(), file_name_with_timestamp + file_extension)

            with open(video_file_path, "wb") as f:
                f.write(uploaded_file.read())
                st.success(tr("File Uploaded Successfully"))
                st.session_state['video_origin_path'] = video_file_path
                params.video_origin_path = video_file_path
                time.sleep(1)
                st.rerun()


def render_frame_subtitle_options(tr):
    """渲染逐帧+字幕模式选项。"""
    render_subtitle_upload(tr)
    render_video_details(tr)


def render_video_understanding_options(tr):
    """渲染视频理解解说模式选项。"""
    video_theme = st.text_input(tr("Video Theme"))

    prompt_options = script_enhancement.get_prompt_style_options()
    prompt_keys = [key for key, _label in prompt_options]
    prompt_labels = {key: label for key, label in prompt_options}
    saved_prompt_style = st.session_state.get('prompt_style', 'short_drama')
    if saved_prompt_style not in prompt_keys:
        saved_prompt_style = 'short_drama'

    if 'custom_prompt_text_area' not in st.session_state:
        st.session_state['custom_prompt_text_area'] = script_enhancement.get_prompt_template(saved_prompt_style)

    def refresh_prompt_template():
        selected_style = st.session_state.get('prompt_style', 'short_drama')
        st.session_state['custom_prompt_text_area'] = script_enhancement.get_prompt_template(selected_style)

    st.selectbox(
        tr("Prompt Style"),
        options=prompt_keys,
        format_func=lambda key: prompt_labels[key],
        index=prompt_keys.index(saved_prompt_style),
        key="prompt_style",
        on_change=refresh_prompt_template,
        help=tr("Switch default prompt templates for different narration styles"),
    )

    custom_prompt = st.text_area(
        tr("Generation Prompt"),
        key="custom_prompt_text_area",
        help=tr("Custom prompt for LLM, leave empty to use default prompt"),
        height=180,
    )

    st.session_state['video_theme'] = video_theme
    st.session_state['custom_prompt'] = custom_prompt
    return video_theme, custom_prompt


def render_short_generate_options(tr):
    """
    渲染Short Generate模式下的特殊选项
    在Short Generate模式下，替换原有的输入框为自定义片段选项
    """
    short_drama_summary(tr)
    # 显示自定义片段数量选择器
    custom_clips = st.number_input(
        tr("自定义片段"),
        min_value=1,
        max_value=20,
        value=st.session_state.get('custom_clips', 5),
        help=tr("设置需要生成的短视频片段数量"),
        key="custom_clips_input"
    )
    st.session_state['custom_clips'] = custom_clips


def render_video_details(tr):
    """画面解说 渲染视频主题和提示词"""
    video_theme = st.text_input(tr("Video Theme"))
    st.checkbox(
        tr("Auto Generate Script Title"),
        value=st.session_state.get('auto_generate_script_title', True),
        key="auto_generate_script_title",
        help=tr("Automatically generate a promotional title after visual narration script generation"),
    )

    prompt_options = script_enhancement.get_prompt_style_options()
    prompt_keys = [key for key, _label in prompt_options]
    prompt_labels = {key: label for key, label in prompt_options}
    saved_prompt_style = st.session_state.get('prompt_style', 'default')
    if saved_prompt_style not in prompt_keys:
        saved_prompt_style = 'default'

    if 'custom_prompt_text_area' not in st.session_state:
        st.session_state['custom_prompt_text_area'] = script_enhancement.get_prompt_template(saved_prompt_style)

    def refresh_prompt_template():
        selected_style = st.session_state.get('prompt_style', 'default')
        st.session_state['custom_prompt_text_area'] = script_enhancement.get_prompt_template(selected_style)

    selected_style = st.selectbox(
        tr("Prompt Style"),
        options=prompt_keys,
        format_func=lambda key: prompt_labels[key],
        index=prompt_keys.index(saved_prompt_style),
        key="prompt_style",
        on_change=refresh_prompt_template,
        help=tr("Switch default prompt templates for different narration styles"),
    )

    custom_prompt = st.text_area(
        tr("Generation Prompt"),
        key="custom_prompt_text_area",
        help=tr("Custom prompt for LLM, leave empty to use default prompt"),
        height=180
    )
    # 非短视频模式下显示原有的三个输入框
    input_cols = st.columns(2)

    with input_cols[0]:
        st.number_input(
            tr("Frame Interval (seconds)"),
            min_value=0,
            value=st.session_state.get('frame_interval_input', config.frames.get('frame_interval_input', 3)),
            help=tr("Frame Interval (seconds) (More keyframes consume more tokens)"),
            key="frame_interval_input"
        )

    with input_cols[1]:
        st.number_input(
            tr("Batch Size"),
            min_value=0,
            value=st.session_state.get('vision_batch_size', config.frames.get('vision_batch_size', 10)),
            help=tr("Batch Size (More keyframes consume more tokens)"),
            key="vision_batch_size"
        )
    st.session_state['video_theme'] = video_theme
    st.session_state['custom_prompt'] = custom_prompt
    return video_theme, custom_prompt


def render_script_title_display(tr):
    """在非逐帧模式下显示当前脚本标题。"""
    pending_title = st.session_state.pop('_generated_script_title_pending', None)
    if pending_title is not None:
        st.session_state['script_title'] = pending_title

    script_title = st.session_state.get('script_title', '')
    if script_title:
        st.text_input(tr("Script Title"), value=script_title, disabled=True)


def render_subtitle_upload(tr):
    """渲染字幕上传入口；没有上传时生成按钮会自动使用本地 Whisper。"""
    if 'subtitle_file_processed' not in st.session_state:
        st.session_state['subtitle_file_processed'] = False

    subtitle_file = st.file_uploader(
        tr("上传字幕文件"),
        type=["srt"],
        accept_multiple_files=False,
        key="subtitle_file_uploader"
    )

    if st.session_state.get('subtitle_path'):
        st.info(f"{tr('Current Subtitle')}: {os.path.basename(st.session_state['subtitle_path'])}")
        if st.button(tr("清除已上传字幕")):
            st.session_state['subtitle_path'] = None
            st.session_state['subtitle_content'] = None
            st.session_state['subtitle_file_processed'] = False
            st.rerun()

    if subtitle_file is None or st.session_state['subtitle_file_processed']:
        return

    try:
        safe_filename = os.path.basename(subtitle_file.name)
        decoded = decode_subtitle_bytes(subtitle_file.getvalue())
        script_content = decoded.text
        detected_encoding = decoded.encoding

        if not script_content:
            st.error(tr("无法读取字幕文件，请检查文件编码（支持 UTF-8、UTF-16、GBK、GB2312）"))
            st.stop()

        if len(script_content.strip()) < 10:
            st.warning(tr("字幕文件内容似乎为空，请检查文件"))

        script_file_path = os.path.join(utils.subtitle_dir(), safe_filename)
        file_name, file_extension = os.path.splitext(safe_filename)
        if os.path.exists(script_file_path):
            timestamp = time.strftime("%Y%m%d%H%M%S")
            script_file_path = os.path.join(utils.subtitle_dir(), f"{file_name}_{timestamp}{file_extension}")

        with open(script_file_path, "w", encoding='utf-8') as f:
            f.write(script_content)

        st.success(
            f"{tr('字幕上传成功')} "
            f"(编码: {detected_encoding.upper()}, "
            f"大小: {len(script_content)} 字符)"
        )
        st.session_state['subtitle_path'] = script_file_path
        st.session_state['subtitle_content'] = script_content
        st.session_state['subtitle_file_processed'] = True

    except Exception as e:
        st.error(f"{tr('Upload failed')}: {str(e)}")


def short_drama_summary(tr):
    """短剧解说 渲染字幕、短剧名称和温度。"""
    render_subtitle_upload(tr)

    video_theme = st.text_input(tr("短剧名称"))
    st.session_state['video_theme'] = video_theme
    temperature = st.slider("temperature", 0.0, 2.0, 0.7)
    st.session_state['temperature'] = temperature
    return video_theme


def ensure_subtitle_for_current_video(tr, params=None):
    """Return an existing subtitle path or generate one from the current video with local Whisper."""
    subtitle_path = st.session_state.get('subtitle_path')
    if subtitle_path and os.path.exists(str(subtitle_path)):
        if not st.session_state.get('subtitle_content'):
            with open(subtitle_path, "r", encoding="utf-8") as handle:
                st.session_state['subtitle_content'] = handle.read()
        st.session_state['subtitle_file_processed'] = True
        return subtitle_path

    video_path = getattr(params, "video_origin_path", None) if params is not None else None
    video_path = video_path or st.session_state.get('video_origin_path')
    if not video_path or video_path == "upload_local" or not os.path.exists(str(video_path)):
        st.error(tr("Please select a video before generating subtitles"))
        return ""

    try:
        output_path = local_whisper_subtitle.default_subtitle_path_for_media(str(video_path))
        with st.spinner(tr("Generating Local Whisper Subtitles")):
            generated_path = local_whisper_subtitle.create_with_local_whisper(str(video_path), output_path)
        with open(generated_path, "r", encoding="utf-8") as handle:
            subtitle_content = handle.read()
        st.session_state['subtitle_path'] = generated_path
        st.session_state['subtitle_content'] = subtitle_content
        st.session_state['subtitle_file_processed'] = True
        st.success(f"{tr('Local Whisper subtitles generated')}: {os.path.basename(generated_path)}")
        return generated_path
    except Exception as err:
        logger.error(f"本地 Whisper 字幕生成失败: {traceback.format_exc()}")
        st.error(f"{tr('Failed to generate local subtitles')}: {str(err)}")
        return ""



def render_script_buttons(tr, params):
    """渲染脚本操作按钮"""
    # 获取当前选择的脚本类型
    script_path = st.session_state.get('video_clip_json_path', '')

    # 生成/加载按钮
    if script_path == MODE_AUTO:
        button_name = tr("Generate Video Script")
    elif script_path == MODE_SHORT:
        button_name = tr("Generate Short Video Script")
    elif script_path == MODE_SUMMARY:
        button_name = tr("生成短剧解说脚本")
    elif script_path == MODE_FRAME_SUBTITLE:
        button_name = tr("Generate Frame Subtitle Script")
    elif script_path == MODE_VIDEO_UNDERSTANDING:
        button_name = tr("Generate Video Understanding Script")
    elif script_path.endswith("json"):
        button_name = tr("Load Video Script")
    else:
        button_name = tr("Please Select Script File")

    if script_path in GENERATED_SCRIPT_MODES and script_path != MODE_VIDEO_UNDERSTANDING:
        st.checkbox(
            tr("Enable Script Polishing"),
            value=st.session_state.get('enable_script_polishing', False),
            key="enable_script_polishing",
            help=tr("Polish generated narration without changing timestamps"),
        )

    if script_path == MODE_AUTO:
        action_cols = st.columns(2)
        with action_cols[0]:
            if st.button(button_name, key="script_action", disabled=not script_path, use_container_width=True):
                run_script_action(tr, params, script_path)
        with action_cols[1]:
            if st.button(
                tr("Generate Script Save and Create Video"),
                key="script_action_save_video",
                disabled=not script_path,
                use_container_width=True,
                type="primary",
            ):
                if run_script_action(tr, params, script_path):
                    save_current_script_and_schedule_video(tr)
    else:
        if st.button(button_name, key="script_action", disabled=not script_path):
            run_script_action(tr, params, script_path)

    # 视频脚本编辑区
    video_clip_json_details = st.text_area(
        tr("Video Script"),
        value=format_script_editor_value(),
        height=500
    )

    if is_file_script_mode(script_path):
        if st.button(tr("AI Polish Short Drama Script"), key="polish_loaded_script", use_container_width=True):
            polish_loaded_script_as_short_drama(tr, video_clip_json_details)

    # 操作按钮行 - 合并格式检查和保存功能
    if st.button(tr("Save Script"), key="save_script", use_container_width=True):
        save_script_with_validation(tr, video_clip_json_details)


def format_script_editor_value():
    """Format current script for editing, including the persisted title when present."""
    script_items = st.session_state.get('video_clip_json', [])
    script_title = st.session_state.get('script_title', '')
    if script_title:
        return script_document.dumps_script_document(script_items, script_title, indent=2)
    return json.dumps(script_items, indent=2, ensure_ascii=False)


def is_file_script_mode(script_path: str) -> bool:
    """判断当前是否为选择/上传脚本模式下的真实脚本文件。"""
    return bool(script_path) and script_path not in [*GENERATED_SCRIPT_MODES, "upload_script"]


def run_script_action(tr, params, script_path):
    """执行当前脚本动作，并在需要时进行二次加工。"""
    if script_path == MODE_AUTO:
        success = generate_script_docu(params)
        if not success:
            return False
        if not maybe_polish_generated_script(tr):
            return False
        if not maybe_generate_script_title_after_generation(tr):
            return False
        return bool(st.session_state.get('video_clip_json'))
    elif script_path == MODE_SHORT:
        if not ensure_subtitle_for_current_video(tr, params):
            return False
        custom_clips = st.session_state.get('custom_clips')
        success = generate_script_short(tr, params, custom_clips)
        return bool(success and maybe_polish_generated_script(tr) and st.session_state.get('video_clip_json'))
    elif script_path == MODE_SUMMARY:
        subtitle_path = ensure_subtitle_for_current_video(tr, params)
        if not subtitle_path:
            return False
        video_theme = st.session_state.get('video_theme')
        temperature = st.session_state.get('temperature')
        success = generate_script_short_sunmmary(params, subtitle_path, video_theme, temperature)
        return bool(success and maybe_polish_generated_script(tr) and st.session_state.get('video_clip_json'))
    elif script_path == MODE_FRAME_SUBTITLE:
        if not ensure_subtitle_for_current_video(tr, params):
            return False
        success = generate_frame_subtitle_script_tool(params)
        if not success:
            return False
        if not maybe_polish_generated_script(tr):
            return False
        if st.session_state.get('auto_generate_script_title', True) and not maybe_generate_script_title_after_generation(tr):
            return False
        return bool(st.session_state.get('video_clip_json'))
    elif script_path == MODE_VIDEO_UNDERSTANDING:
        success = generate_video_understanding_script_tool(params)
        if not success:
            return False
        st.session_state['script_title'] = ''
        return bool(st.session_state.get('video_clip_json'))
    else:
        load_script(tr, script_path)
        return False


def maybe_generate_script_title_after_generation(tr):
    """逐帧解说生成成功后，按勾选项自动生成标题。"""
    if not st.session_state.get('auto_generate_script_title', True):
        st.session_state['script_title'] = ''
        return True

    script_items = st.session_state.get('video_clip_json', [])
    if not script_items:
        return False

    try:
        with st.spinner(tr("Generating Script Title")):
            generated_title = script_enhancement.generate_script_title(
                script_items,
                video_theme=st.session_state.get('video_theme', ''),
            )
        st.session_state['script_title'] = generated_title
        st.success(tr("Script title generated"))
        return True
    except Exception as err:
        logger.error(f"生成脚本标题失败: {traceback.format_exc()}")
        st.error(f"{tr('Failed to generate script title')}: {str(err)}")
        return False


def polish_loaded_script_as_short_drama(tr, video_clip_json_details):
    """对选择/上传脚本页面里的脚本按短剧推广方向进行二次加工。"""
    script_content = get_script_content_for_polishing(video_clip_json_details)
    if not script_content:
        st.error(tr("Please generate or load a script first"))
        return False

    validation = check_script.check_format(script_content)
    if not validation.get('success'):
        st.error(f"{tr('Script format check failed')}: {validation.get('message', '')}")
        details = validation.get('details')
        if details:
            st.error(details)
        return False

    try:
        document = script_document.loads_script_document(script_content)
        script_items = document.items
        if document.script_title:
            st.session_state['script_title'] = document.script_title
        with st.spinner(tr("Polishing Loaded Script")):
            polished = script_enhancement.optimize_script_narrations(
                script_items,
                style="short_drama",
                custom_instruction="",
            )
            generated_title = script_enhancement.generate_script_title(
                polished,
                video_theme=st.session_state.get('video_theme', ''),
            )

        st.session_state['video_clip_json'] = polished
        st.session_state['script_title'] = generated_title
        st.success(tr("Loaded script polished successfully"))
        st.rerun()
        return True
    except Exception as err:
        logger.error(f"选择/上传脚本二次加工失败: {traceback.format_exc()}")
        st.error(f"{tr('Failed to polish loaded script')}: {str(err)}")
        return False


def get_script_content_for_polishing(video_clip_json_details):
    """获取当前要二次加工的脚本文本，优先使用编辑区，其次使用已选脚本文件。"""
    content = str(video_clip_json_details or "").strip()
    if content and content != "[]":
        return content

    script_path = st.session_state.get('video_clip_json_path', '')
    if script_path and script_path.endswith(".json") and os.path.exists(script_path):
        with open(script_path, "r", encoding="utf-8") as f:
            return utils.clean_model_output(f.read()).strip()

    return content


def maybe_polish_generated_script(tr):
    """根据选项对已生成脚本做二次加工。"""
    if not st.session_state.get('enable_script_polishing'):
        return True

    script_items = st.session_state.get('video_clip_json', [])
    if not script_items:
        return False

    try:
        with st.spinner(tr("Polishing Script")):
            polished = script_enhancement.optimize_script_narrations(
                script_items,
                style=st.session_state.get('prompt_style', 'short_drama'),
                custom_instruction=st.session_state.get('custom_prompt', ''),
            )
        st.session_state['video_clip_json'] = polished
        st.success(tr("Script polished successfully"))
        return True
    except Exception as err:
        logger.error(f"二次加工脚本失败: {traceback.format_exc()}")
        st.error(f"{tr('Failed to polish script')}: {str(err)}")
        return False


def save_current_script_and_schedule_video(tr):
    """保存当前脚本并标记下一次渲染自动生成视频。"""
    script_items = st.session_state.get('video_clip_json', [])
    if not script_items:
        st.error(tr("Please generate or load a script first"))
        return

    script_content = script_document.dumps_script_document(
        script_items,
        st.session_state.get('script_title', ''),
        indent=2,
    )
    save_path = save_script_with_validation(tr, script_content, rerun=False)
    if save_path:
        st.session_state['_auto_generate_video_after_script_save'] = True
        st.session_state['_switch_to_file_mode'] = True
        st.success(tr("Script saved. Video generation will start now."))
        time.sleep(0.5)
        st.rerun()


def load_script(tr, script_path):
    """加载脚本文件"""
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            script = f.read()
            script = utils.clean_model_output(script)
            document = script_document.loads_script_document(script)
            st.session_state['video_clip_json'] = document.items
            st.session_state['script_title'] = document.script_title
            st.success(tr("Script loaded successfully"))
            st.rerun()
    except Exception as e:
        logger.error(f"加载脚本文件时发生错误\n{traceback.format_exc()}")
        st.error(f"{tr('Failed to load script')}: {str(e)}")


def save_script_with_validation(tr, video_clip_json_details, *, rerun=True):
    """保存视频脚本（包含格式验证）"""
    if not video_clip_json_details:
        st.error(tr("请输入视频脚本"))
        st.stop()

    # 第一步：格式验证
    with st.spinner("正在验证脚本格式..."):
        try:
            result = check_script.check_format(video_clip_json_details)
            if not result.get('success'):
                # 格式验证失败，显示详细错误信息
                error_message = result.get('message', '未知错误')
                error_details = result.get('details', '')

                st.error(f"**脚本格式验证失败**")
                st.error(f"**错误信息：** {error_message}")
                if error_details:
                    st.error(f"**详细说明：** {error_details}")

                # 显示正确格式示例
                st.info("**正确的脚本格式示例：**")
                example_script = [
                    {
                        "_id": 1,
                        "timestamp": "00:00:00,600-00:00:07,559",
                        "picture": "工地上，蔡晓艳奋力救人，场面混乱",
                        "narration": "灾后重建，工地上险象环生！泼辣女工蔡晓艳挺身而出，救人第一！",
                        "OST": 0
                    },
                    {
                        "_id": 2,
                        "timestamp": "00:00:08,240-00:00:12,359",
                        "picture": "领导视察，蔡晓艳不屑一顾",
                        "narration": "播放原片4",
                        "OST": 1
                    }
                ]
                st.code(json.dumps(example_script, ensure_ascii=False, indent=2), language='json')
                st.stop()

        except Exception as e:
            st.error(f"格式验证过程中发生错误: {str(e)}")
            st.stop()

    # 第二步：保存脚本
    with st.spinner(tr("Save Script")):
        script_dir = utils.script_dir()
        timestamp = time.strftime("%Y-%m%d-%H%M%S")
        save_path = os.path.join(script_dir, f"{timestamp}.json")

        try:
            document = script_document.loads_script_document(video_clip_json_details)
            script_title = document.script_title or st.session_state.get('script_title', '')
            data = script_document.build_script_document(document.items, script_title)
            with open(save_path, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
                st.session_state['video_clip_json'] = document.items
                st.session_state['script_title'] = script_title
                st.session_state['video_clip_json_path'] = save_path
                
                # 标记需要切换到文件选择模式（在下次渲染前处理）
                st.session_state['_switch_to_file_mode'] = True

                # 更新配置
                config.app["video_clip_json_path"] = save_path

                st.success("✅ 脚本格式验证通过，保存成功！")

                if rerun:
                    time.sleep(0.5)  # 给一点时间让用户看到成功消息
                    st.rerun()
                return save_path

        except Exception as err:
            st.error(f"{tr('Failed to save script')}: {str(err)}")
            st.stop()


# crop_video函数已移除 - 现在使用统一裁剪策略，不再需要预裁剪步骤


def get_script_params():
    """获取脚本参数"""
    script_path = st.session_state.get('video_clip_json_path', '')
    script_title = st.session_state.get('script_title', '')
    if not script_title and script_path and script_path.endswith('.json') and os.path.exists(script_path):
        try:
            script_title = script_document.load_script_document(script_path).script_title
            st.session_state['script_title'] = script_title
        except Exception:
            logger.warning(f"读取脚本标题失败: {script_path}")
    return {
        'video_language': st.session_state.get('video_language', ''),
        'video_clip_json_path': script_path,
        'video_origin_path': st.session_state.get('video_origin_path', ''),
        'video_name': st.session_state.get('video_name', ''),
        'video_plot': st.session_state.get('video_plot', ''),
        'script_title': script_title,
    }
