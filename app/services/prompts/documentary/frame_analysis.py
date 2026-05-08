#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
@Project: 逐帧解说-画面分析
@File   : frame_analysis.py
@Author : viccy同学
@Date   : 2025/1/7
@Description: 纪录片视频帧分析提示词
"""

from ..base import VisionPrompt, PromptMetadata, ModelType, OutputFormat


class FrameAnalysisPrompt(VisionPrompt):
    """纪录片视频帧分析提示词"""
    
    def __init__(self):
        metadata = PromptMetadata(
            name="frame_analysis",
            category="documentary",
            version="v1.0",
            description="分析视频关键帧，提取画面内容、场景描述和短剧情绪冲突信息",
            model_type=ModelType.VISION,
            output_format=OutputFormat.JSON,
            tags=["纪录片", "短剧", "视频分析", "关键帧", "画面描述", "冲突识别"],
            parameters=["video_theme", "custom_instructions"]
        )
        super().__init__(metadata)
        
        self._system_prompt = "你是一名专业的视频内容分析师，擅长分析关键帧内容，提取画面信息、人物关系、情绪冲突和可剪辑爆点。"
        
    def get_template(self) -> str:
        return """请仔细分析这些视频关键帧图片，我需要你提供详细的画面分析。

    视频主题：${video_theme}

分析要求：
1. 按时间顺序分析每一帧画面
    2. 详细描述画面中的主要内容、人物、物体、环境
    3. 注意人物关系、情绪状态、冲突升级、身份差、误会、反转、危机等短剧关键信息
    4. 注意画面的构图、色彩、光线等视觉元素
    5. 识别画面中的关键动作、表情变化或可能需要保留原声的对白场面
    6. 提供准确的时间戳信息

${custom_instructions}

请按照以下JSON格式输出分析结果：

{
  "analysis": [
    {
      "timestamp": "00:00:05,390",
          "picture": "详细的画面描述，包括场景、人物、物体、动作、表情和冲突点等",
          "scene_type": "场景类型（如：建造、准备、完成等）",
          "key_elements": ["关键元素1", "关键元素2"],
          "drama_signals": ["人物关系/情绪冲突/原声爆点等短剧信号"],
          "visual_quality": "画面质量描述（构图、光线、色彩等）"
    }
  ],
  "summary": "整体视频内容概述",
  "total_frames": "分析的帧数"
}

重要要求：
1. 只输出JSON格式，不要添加任何其他文字或代码块标记
2. 画面描述要详细准确，为后续解说文案生成提供充分信息
3. 时间戳必须准确对应视频帧
4. 严禁虚构不存在的内容"""
