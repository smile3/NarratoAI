#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
@Project: 逐帧解说-短剧混剪
@File   : frame_subtitle_generation.py
@Author : viccy同学
@Date   : 2026/5/8
@Description: 逐帧+字幕短剧混剪提示词 - 优化版本
"""

from ..base import ParameterizedPrompt, PromptMetadata, ModelType, OutputFormat


class FrameSubtitleGenerationPrompt(ParameterizedPrompt):
    """逐帧+字幕短剧混剪提示词"""

    def __init__(self):
        metadata = PromptMetadata(
            name="frame_subtitle_generation",
            category="short_drama_narration",
            version="v1.0",
            description="结合画面分析和字幕内容，生成短剧推广剪辑脚本，并主动混合解说与原声片段",
            model_type=ModelType.TEXT,
            output_format=OutputFormat.JSON,
            tags=["短剧", "逐帧分析", "字幕融合", "解说脚本", "原声混剪", "OST混合"],
            parameters=["frame_analysis_markdown", "subtitle_content", "video_theme", "custom_prompt"],
        )
        super().__init__(metadata)

        self._system_prompt = (
            "你是一位专业的短剧解说剪辑策划，擅长把画面分析和字幕内容融合成高节奏混剪脚本。"
            "你必须严格输出合法 JSON，并主动混合 OST=0 和 OST=1，不要使用 OST=2。"
        )

    def get_template(self) -> str:
        return """# 逐帧+字幕短剧混剪任务

## 任务目标
请同时参考【画面分析】和【字幕内容】，生成适合短剧推广的剪辑脚本。
目标不是平均覆盖所有镜头，而是围绕“开头钩子 -> 冲突升级 -> 原声爆点 -> 反转/悬念”组织片段。

## 核心要求
1. 必须主动混合 OST=0 和 OST=1，整份脚本不能只有一种 OST。
2. OST=0 用于解说推进、背景交代、过渡、信息补充和情节串联。
3. OST=1 用于必须保留原声的关键对白、情绪爆发、身份揭露、质问、争吵、反转、真相、经典台词。
4. 不要使用 OST=2。
5. 如果某段原声更有张力，优先把它标为 OST=1，并让 narration 写成简短原声标记，例如“播放原片3”或“原声：关键对白”。
6. 如果某段更适合讲解，就使用 OST=0，写成短剧解说口吻，尽量带有悬念、转折和推进感。
7. 开头前 1-2 个片段要有钩子，结尾留下悬念，不要把故事讲完。
8. 片段长度要根据剧情自然变化，短镜头少说，长镜头适当展开，不要所有片段固定同一长度。
9. 时间戳必须来自字幕/画面分析，允许合并或拆分，但不能重叠，必须按时间顺序排列。
10. 成片尽量控制在 3 分钟左右，最多不要超过 5 分钟。
11. 画面描述要兼顾人物关系、情绪状态、动作和冲突点，便于后续剪辑。
12. 只输出 JSON，不要输出解释文字。

## 输出格式
{
  "items": [
    {
      "_id": 1,
      "timestamp": "00:00:01,000-00:00:05,000",
      "picture": "画面描述",
      "narration": "解说文案或原声标记",
      "OST": 0
    }
  ]
}

## 画面分析
${frame_analysis_markdown}

## 字幕内容
${subtitle_content}

## 创作补充
视频主题：${video_theme}
补充要求：${custom_prompt}
""".strip()
