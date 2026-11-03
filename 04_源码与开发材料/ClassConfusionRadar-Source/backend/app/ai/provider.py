"""
本文件的作用是：实现教学建议与增强分析的生成适配逻辑。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

import httpx
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.suggestion import StructuredSuggestionContent


@dataclass
class SuggestionContext:
    segment_title: str
    knowledge_point_name: Optional[str]
    risk_level: str
    confusion_score: float
    signal_breakdown: list[dict]
    error_summary: list[dict]
    teacher_notes: Optional[str]


class SuggestionGenerationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class BaseSuggestionProvider:
    provider_label = "base"

    def generate(self, context: SuggestionContext) -> StructuredSuggestionContent:
        raise NotImplementedError

    def get_model_name(self) -> str:
        return self.provider_label


class OfflineSuggestionProvider(BaseSuggestionProvider):
    provider_label = "offline-rules-v2"

    def generate(self, context: SuggestionContext) -> StructuredSuggestionContent:
        knowledge = context.knowledge_point_name or "当前知识点"
        errors = [item["label"] for item in context.error_summary[:3]]
        error_text = "、".join(errors) if errors else "暂无明显集中错误"
        primary_key = _primary_signal_key(context.signal_breakdown)

        if primary_key == "quiz_incorrect_rate":
            first_step = f"先用一道只考“{knowledge}”核心判断的短题确认概念，不急着继续讲新内容。"
        elif primary_key == "submission_failure_rate":
            first_step = f"先把“{knowledge}”压缩成最小可运行例子，让学生现场改到能够运行。"
        elif primary_key == "error_density":
            first_step = f"把同一错误反复出现的代码拿出来对照修改，重点解释为什么会重复犯错。"
        elif primary_key == "interaction_silence":
            first_step = f"先做一次匿名选择或举手判断，确认学生对“{knowledge}”到底卡在哪一步。"
        else:
            first_step = f"先回到“{knowledge}”最基本的输入、处理和输出，确认学生是否跟上。"

        return StructuredSuggestionContent(
            diagnosis=(
                f"“{context.segment_title}”的困惑得分为 {context.confusion_score}，风险等级为 {context.risk_level}。"
                f"当前主要错误：{error_text}。建议先处理主导信号，再安排补充练习。"
            ),
            reteach_script=[
                first_step,
                "挑一个真实错误例子现场改，不只给正确答案，要把出错位置和修改理由说清楚。",
                "改完马上换一个很小的变式题，让学生独立完成，确认不是照着例子抄会了。",
            ],
            board_plan=[
                f"左侧写“{knowledge}”的判断要点。",
                f"中间保留一份错误样例，标出 {error_text}。",
                "右侧写修改后的关键语句和一条自检规则。",
            ],
            micro_exercises=[
                "修正一处关键错误并说明修改理由。",
                "更换一个边界条件，先写预期结果再运行验证。",
            ],
            followup_task=(
                f"课后再做 1 道“{knowledge}”同类型小题；下一次分析时对比该知识点的困惑得分和重复错误次数。"
            ),
        )


class OpenAICompatibleSuggestionProvider(BaseSuggestionProvider):
    provider_label = "openai-compatible"

    def generate(self, context: SuggestionContext) -> StructuredSuggestionContent:
        settings = get_settings()
        if not settings.ai_api_key:
            return OfflineSuggestionProvider().generate(context)

        prompt = (
            "你是一名面向高校编程课教师的教学分析助手。"
            "请根据课堂分段风险信息，仅输出一个 JSON 对象，不要输出 Markdown，不要输出解释性前缀。"
            "JSON 必须严格包含以下字段："
            "diagnosis(string), reteach_script(string array), board_plan(string array), "
            "micro_exercises(string array), followup_task(string)。"
            "要求：内容必须是中文、可直接给教师使用、表达具体、不能留空。"
            f"\n分段标题：{context.segment_title}"
            f"\n知识点：{context.knowledge_point_name or '未标注'}"
            f"\n风险等级：{context.risk_level}"
            f"\n困惑得分：{context.confusion_score}"
            f"\n信号拆解：{json.dumps(context.signal_breakdown, ensure_ascii=False)}"
            f"\n错误摘要：{json.dumps(context.error_summary, ensure_ascii=False)}"
            f"\n教师备注：{context.teacher_notes or '无'}"
        )

        request_payload = {
            "model": settings.ai_model,
            "messages": [
                {"role": "system", "content": "你是一名耐心、专业的编程教学督导。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }

        with httpx.Client(timeout=30.0, base_url=settings.ai_base_url) as client:
            try:
                response = client.post(
                    "/chat/completions",
                    headers={"Authorization": f"Bearer {settings.ai_api_key}"},
                    json=request_payload,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 400:
                    raise

                fallback_payload = dict(request_payload)
                fallback_payload.pop("response_format", None)
                response = client.post(
                    "/chat/completions",
                    headers={"Authorization": f"Bearer {settings.ai_api_key}"},
                    json=fallback_payload,
                )
            response.raise_for_status()
            payload = response.json()

        try:
            raw_content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise SuggestionGenerationError("模型返回格式不符合预期，无法提取结构化建议。") from exc

        try:
            suggestion_payload = _extract_json_payload(raw_content)
            return StructuredSuggestionContent.model_validate(suggestion_payload)
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
            raise SuggestionGenerationError("模型返回内容无法解析，请稍后重试；也可以切回离线建议模式。") from exc

    def get_model_name(self) -> str:
        return get_settings().ai_model


def render_structured_suggestion_markdown(content: StructuredSuggestionContent) -> str:
    lines = [
        "## 再教学建议",
        "",
        "### 困惑诊断",
        content.diagnosis,
        "",
        "### 重讲脚本",
        *[f"- {item}" for item in content.reteach_script],
        "",
        "### 板书规划",
        *[f"- {item}" for item in content.board_plan],
        "",
        "### 微练习",
        *[f"- {item}" for item in content.micro_exercises],
        "",
        "### 跟进任务",
        content.followup_task,
    ]
    return "\n".join(lines)


def get_suggestion_provider() -> BaseSuggestionProvider:
    settings = get_settings()
    if settings.ai_provider in {"openai", "openai-compatible"} and settings.ai_api_key:
        return OpenAICompatibleSuggestionProvider()
    return OfflineSuggestionProvider()


def _primary_signal_key(signal_breakdown: list[dict]) -> str | None:
    available = [item for item in signal_breakdown if item.get("is_available", True)]
    if not available:
        return None
    primary = max(available, key=lambda item: float(item.get("contribution_score", 0)))
    return str(primary.get("key"))

def _extract_json_payload(raw_content: Any) -> dict[str, Any]:
    if isinstance(raw_content, dict):
        return raw_content

    if isinstance(raw_content, list):
        text_parts = []
        for item in raw_content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(str(item.get("text", "")))
            else:
                text_parts.append(str(item))
        raw_text = "\n".join(text_parts)
    else:
        raw_text = str(raw_content)

    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:].strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start == -1 or end == -1 or start >= end:
            raise
        return json.loads(raw_text[start : end + 1])
