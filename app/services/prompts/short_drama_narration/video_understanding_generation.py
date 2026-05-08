#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
@Project: 视频理解解说-短剧混剪
@File   : video_understanding_generation.py
@Author : viccy同学
@Date   : 2026/5/8
@Description: 视频理解模型直出短剧解说剪辑脚本提示词
"""

from ..base import ParameterizedPrompt, PromptMetadata, ModelType, OutputFormat


class VideoUnderstandingGenerationPrompt(ParameterizedPrompt):
    """视频理解模型直出短剧解说剪辑脚本提示词。"""

    def __init__(self):
        metadata = PromptMetadata(
            name="video_understanding_generation",
            category="short_drama_narration",
            version="v1.0",
            description="直接理解完整视频并生成短剧推广剪辑脚本，不依赖抽帧或字幕预处理",
            model_type=ModelType.MULTIMODAL,
            output_format=OutputFormat.JSON,
            tags=["短剧", "视频理解", "解说脚本", "原声混剪", "OST混合", "整片分析"],
            parameters=["video_theme", "custom_prompt"],
        )
        super().__init__(metadata)

        self._system_prompt = (
            "你是一位专业短剧解说剪辑导演，擅长直接理解完整视频，并策划短视频混剪解说脚本。"
            "你必须严格输出合法 JSON，主动混合 OST=0 和 OST=1，不要使用 OST=2。"
        )

    def get_template(self) -> str:
        return """# 视频理解短剧解说剪辑脚本任务

## 任务目标
请直接理解我发送的完整视频，生成一份短剧推广向剪辑脚本。
本模式不会给你逐帧分析结果，也不会给你外部字幕文本；你需要从视频本身理解人物、对白、动作、情绪、镜头节奏和剧情冲突。

目标不是复述整集，而是围绕“开头钩子 -> 冲突升级 -> 原声爆点 -> 反转/悬念”组织高节奏成片，让观众愿意继续看原剧或下一集。

## 短剧解说创作策略
1. 开头 1-2 个片段必须强钩子：优先选择身份反差、危机、背叛、误会、复仇、揭穿、情绪爆发等高张力镜头。
2. 主线要清楚：只保留推动核心冲突的镜头，删掉重复铺垫、空镜、弱信息、拖慢节奏的支线。
3. 解说要像短剧推广口吻：短句、口语化、有悬念、有转折，避免平铺直叙。
4. 不要讲完全部结局，结尾必须停在反转、危机、选择或真相揭晓前后，留下追看欲望。
5. 画面描述要写清人物、关系、动作、情绪和冲突点，方便后续剪辑定位。
6. 时间戳必须基于视频真实内容估计或识别，按时间顺序排列，不能重叠。
7. 允许合并或拆分片段，但每段都必须是完整可剪的时间范围。

## OST 规则
必须主动混合 OST=0 和 OST=1，整份脚本不能只有一种 OST。

- OST=0：解说片段。用于背景交代、人物关系、剧情推进、情绪放大、转折衔接。
- OST=1：保留原声片段。用于关键对白、争吵质问、哭喊崩溃、身份揭露、真相反转、威胁告白、爽点打脸、经典台词。
- 不要使用 OST=2。
- OST=1 的 narration 写成“播放原片+序号”，例如“播放原片3”。
- 如果视频里某句台词特别关键，优先保留为 OST=1，不要用解说盖掉。
- 原声片段要分布在全片关键节点，不要集中在一处。

## 时长与节奏
1. 最终成片尽量控制在 3 分钟左右，最多不要超过 5 分钟。
2. 单个原声片段建议 3-8 秒，单个解说片段根据画面信息量控制长短。
3. 镜头短就少说，镜头长才适当展开，解说文案不要明显超过画面时长。
4. 全片节奏要有起伏：钩子、铺垫、爆点、反转、悬念交替出现。

## 输出格式硬性要求
只输出 JSON，不要输出解释文字、Markdown、代码块标记或额外字段。
时间戳格式必须为 `HH:MM:SS,mmm-HH:MM:SS,mmm`。
`_id` 必须从 1 开始连续递增。

{
  "items": [
    {
      "_id": 1,
      "timestamp": "00:00:01,000-00:00:05,000",
      "picture": "画面描述",
      "narration": "解说文案或播放原片1",
      "OST": 0
    }
  ]
}

## 创作补充
视频主题：${video_theme}
补充要求：${custom_prompt}
""".strip()
