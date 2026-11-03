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
from app.schemas.enhanced_analysis import (
    AnalysisCitation,
    EnhancedSegmentAnalysisContent,
    EnhancedSessionAnalysisContent,
    TopSegmentInsight,
)


@dataclass
class LocalCitationCandidate:
    title: str
    source_type: str
    excerpt: str
    url: Optional[str] = None


@dataclass
class EnhancedSessionContext:
    session_title: str
    course_type: str
    class_date: str
    duration_minutes: int
    notes: Optional[str]
    score_formula: str
    average_score: float
    high_risk_count: int
    critical_count: int
    total_segments: int
    top_segments: list[dict]
    transcript_excerpt: str
    slide_window_summary: str
    memory_notes: list[str]
    citation_candidates: list[LocalCitationCandidate]
    allow_web_search: bool


@dataclass
class EnhancedSegmentContext:
    segment_title: str
    knowledge_point_name: Optional[str]
    risk_level: str
    confusion_score: float
    score_formula: str
    signal_breakdown: list[dict]
    error_summary: list[dict]
    teacher_notes: Optional[str]
    transcript_excerpt: str
    slide_window_summary: str
    memory_notes: list[str]
    citation_candidates: list[LocalCitationCandidate]
    allow_web_search: bool


class EnhancedAnalysisGenerationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class BaseEnhancedAnalysisProvider:
    provider_label = "base-enhanced"

    def generate_session(self, context: EnhancedSessionContext) -> EnhancedSessionAnalysisContent:
        raise NotImplementedError

    def generate_segment(self, context: EnhancedSegmentContext) -> EnhancedSegmentAnalysisContent:
        raise NotImplementedError

    def get_model_name(self) -> str:
        return self.provider_label


class OfflineEnhancedAnalysisProvider(BaseEnhancedAnalysisProvider):
    provider_label = "offline-enhanced-v2"

    def generate_session(self, context: EnhancedSessionContext) -> EnhancedSessionAnalysisContent:
        top_segments = context.top_segments[:3]
        if not top_segments:
            top_segments = [
                {
                    "segment_score_id": 0,
                    "title": "当前课堂整体风险较低",
                    "overall_explanation": "当前没有识别出高风险分段，课堂整体表现较稳定。",
                    "primary_signal_label": "规则评分整体平稳",
                }
            ]

        insights = [
            TopSegmentInsight(
                segment_score_id=int(item.get("segment_score_id", 0)),
                segment_id=int(item.get("segment_id")) if item.get("segment_id") is not None else None,
                title=str(item.get("title", "未命名分段")),
                why_high_risk=str(item.get("overall_explanation", "该分段在规则评分中表现出较高风险。")),
                teacher_focus=(
                    f"优先复盘 {item.get('primary_signal_label') or '关键评分信号'}，并对照讲解证据重新解释该段知识点。"
                ),
            )
            for item in top_segments
        ]

        summary = (
            f"本次课堂共分析 {context.total_segments} 个分段，平均困惑得分 {context.average_score}。"
            f"其中高风险分段 {context.high_risk_count} 个，极高风险分段 {context.critical_count} 个。"
            f"教师应优先查看分数最高的 1-2 个分段，并结合课堂讲稿与 PPT 时间窗复盘讲解节奏。"
        )

        takeaways = [
            "规则评分仍然是主结果，增强分析只负责把高风险结论整理成更适合教师理解的说明。",
            f"从课堂片段看，最值得优先关注的是：{insights[0].title}。",
            "建议把高风险分段的主导信号、典型错误和讲稿证据放在同一页中讲解。",
        ]

        memory_notes = context.memory_notes[:4] + [
            f"本节课最需要优先复盘的分段是“{insights[0].title}”。",
            "后续分段增强分析应继续围绕同一组高风险原因保持解释一致。",
        ]

        return EnhancedSessionAnalysisContent(
            summary=summary,
            teacher_takeaways=_deduplicate_text(takeaways),
            top_segment_insights=insights,
            citations=_build_local_citations(context.citation_candidates, limit=4),
            memory_notes=_deduplicate_text(memory_notes)[:6],
        )

    def generate_segment(self, context: EnhancedSegmentContext) -> EnhancedSegmentAnalysisContent:
        dominant_signals = _summarize_dominant_signals(context.signal_breakdown)
        main_errors = "、".join(item["label"] for item in context.error_summary[:3]) or "暂无集中错误"
        diagnosis = (
            f"分段“{context.segment_title}”当前被判定为 {context.risk_level}，困惑得分 {context.confusion_score}。"
            f"主导风险信号为：{dominant_signals}。典型错误集中在：{main_errors}。"
        )
        evidence_story = (
            f"从讲稿片段看，该段主要围绕“{context.knowledge_point_name or context.segment_title}”展开。"
            f"{context.transcript_excerpt} 结合 PPT 时间窗：{context.slide_window_summary}，"
            "可以看出讲解重点与学生出错点之间存在明显对位关系。"
        )
        teacher_focus = _deduplicate_text(
            context.memory_notes[:3]
            + [
                f"先解释 {context.knowledge_point_name or context.segment_title} 的正确流程，再对照错误版本讲清差异。",
                "优先复盘贡献分最高的评分信号，而不是平均展开所有问题。",
                "把讲稿中的关键说明和学生常见错误放在一起对照。",
            ]
        )[:5]
        recommended_checks = [
            "检查这段讲解是否给出了足够清晰的输入、判断条件和输出结果。",
            "检查主导错误是否与课堂讲解顺序、例题难度或边界说明不足有关。",
            "复盘该分段前后的 PPT 页面，确认是否存在切换过快导致的理解断层。",
        ]

        return EnhancedSegmentAnalysisContent(
            diagnosis=diagnosis,
            evidence_story=evidence_story,
            teacher_focus=teacher_focus,
            recommended_checks=recommended_checks,
            citations=_build_local_citations(context.citation_candidates, limit=4),
            memory_notes=_deduplicate_text(
                context.memory_notes
                + [
                    f"该分段的高风险原因优先归因于：{dominant_signals}。",
                    "后续若再次生成本分段增强分析，应保持风险原因与课堂证据引用的一致表述。",
                ]
            )[:6],
        )


class OpenAICompatibleEnhancedAnalysisProvider(BaseEnhancedAnalysisProvider):
    provider_label = "openai-compatible-enhanced"

    def generate_session(self, context: EnhancedSessionContext) -> EnhancedSessionAnalysisContent:
        prompt = (
            "你是一名面向高校编程课教师的课堂分析助手。"
            "请基于现有规则评分结果，输出一个严格 JSON 对象，不要输出 Markdown，不要输出额外说明。"
            "JSON 必须包含字段：summary(string), teacher_takeaways(string[]), "
            "top_segment_insights([{segment_score_id:number,segment_id:number|null,title:string,why_high_risk:string,teacher_focus:string}]), "
            "citations([{title:string,url:string|null,source_type:string,excerpt:string}]), "
            "memory_notes(string[])。"
            "要求：中文、教师可直接使用、强调规则评分是主结果，增强分析只是解释补充。"
            f"\n课堂标题：{context.session_title}"
            f"\n课程类型：{context.course_type}"
            f"\n日期：{context.class_date}"
            f"\n时长：{context.duration_minutes}"
            f"\n课堂备注：{context.notes or '无'}"
            f"\n评分公式：{context.score_formula}"
            f"\n平均困惑得分：{context.average_score}"
            f"\n高风险分段数：{context.high_risk_count}"
            f"\n极高风险分段数：{context.critical_count}"
            f"\n高风险分段：{json.dumps(context.top_segments, ensure_ascii=False)}"
            f"\n讲稿摘录：{context.transcript_excerpt}"
            f"\nSlide 窗口摘要：{context.slide_window_summary}"
            f"\n已有课堂内记忆：{json.dumps(context.memory_notes, ensure_ascii=False)}"
            f"\n可引用的本地证据：{json.dumps([candidate.__dict__ for candidate in context.citation_candidates], ensure_ascii=False)}"
        )
        payload = self._generate_json_payload(prompt, allow_web_search=context.allow_web_search)
        try:
            return EnhancedSessionAnalysisContent.model_validate(payload)
        except ValidationError as exc:
            raise EnhancedAnalysisGenerationError("模型返回了无法解析的课堂增强总览，请稍后重试。") from exc

    def generate_segment(self, context: EnhancedSegmentContext) -> EnhancedSegmentAnalysisContent:
        prompt = (
            "你是一名面向高校编程课教师的课堂分析助手。"
            "请基于现有规则评分结果，为单个高风险分段输出严格 JSON 对象，不要输出 Markdown，不要输出额外说明。"
            "JSON 必须包含字段：diagnosis(string), evidence_story(string), teacher_focus(string[]), "
            "recommended_checks(string[]), citations([{title:string,url:string|null,source_type:string,excerpt:string}]), "
            "memory_notes(string[])。"
            "要求：中文、教师可直接用于课堂复盘；规则评分结论必须保持不变。"
            f"\n分段标题：{context.segment_title}"
            f"\n知识点：{context.knowledge_point_name or '未标注'}"
            f"\n风险等级：{context.risk_level}"
            f"\n困惑得分：{context.confusion_score}"
            f"\n评分公式：{context.score_formula}"
            f"\n信号拆解：{json.dumps(context.signal_breakdown, ensure_ascii=False)}"
            f"\n错误摘要：{json.dumps(context.error_summary, ensure_ascii=False)}"
            f"\n教师备注：{context.teacher_notes or '无'}"
            f"\n讲稿摘录：{context.transcript_excerpt}"
            f"\nSlide 窗口摘要：{context.slide_window_summary}"
            f"\n已有课堂内记忆：{json.dumps(context.memory_notes, ensure_ascii=False)}"
            f"\n可引用的本地证据：{json.dumps([candidate.__dict__ for candidate in context.citation_candidates], ensure_ascii=False)}"
        )
        payload = self._generate_json_payload(prompt, allow_web_search=context.allow_web_search)
        try:
            return EnhancedSegmentAnalysisContent.model_validate(payload)
        except ValidationError as exc:
            raise EnhancedAnalysisGenerationError("模型返回了无法解析的分段增强分析，请稍后重试。") from exc

    def get_model_name(self) -> str:
        return get_settings().ai_model

    def _generate_json_payload(self, prompt: str, allow_web_search: bool) -> dict[str, Any]:
        settings = get_settings()
        if not settings.ai_api_key:
            raise EnhancedAnalysisGenerationError("未配置 AI_API_KEY，无法调用增强分析服务。")

        if allow_web_search:
            payload = self._try_responses_api(prompt)
            if payload is not None:
                return payload

        return self._chat_completion_json(prompt)

    def _try_responses_api(self, prompt: str) -> Optional[dict[str, Any]]:
        settings = get_settings()
        request_payloads = [
            {
                "model": settings.ai_model,
                "input": prompt,
                "tools": [{"type": "web_search"}],
            },
            {
                "model": settings.ai_model,
                "input": prompt,
                "tools": [{"type": "web_search_preview"}],
            },
        ]

        with httpx.Client(timeout=45.0, base_url=settings.ai_base_url) as client:
            for request_payload in request_payloads:
                try:
                    response = client.post(
                        "/responses",
                        headers={"Authorization": f"Bearer {settings.ai_api_key}"},
                        json=request_payload,
                    )
                    response.raise_for_status()
                except httpx.HTTPError:
                    continue

                payload = response.json()
                raw_content = payload.get("output_text")
                if not raw_content:
                    raw_content = _extract_responses_output_text(payload)
                if not raw_content:
                    continue

                try:
                    return _extract_json_payload(raw_content)
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue

        return None

    def _chat_completion_json(self, prompt: str) -> dict[str, Any]:
        settings = get_settings()
        request_payload = {
            "model": settings.ai_model,
            "messages": [
                {"role": "system", "content": "你是一名严谨、耐心的课堂分析助手。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        with httpx.Client(timeout=45.0, base_url=settings.ai_base_url) as client:
            try:
                response = client.post(
                    "/chat/completions",
                    headers={"Authorization": f"Bearer {settings.ai_api_key}"},
                    json=request_payload,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 400:
                    raise EnhancedAnalysisGenerationError(f"增强分析服务异常：{exc}") from exc

                fallback_payload = dict(request_payload)
                fallback_payload.pop("response_format", None)
                response = client.post(
                    "/chat/completions",
                    headers={"Authorization": f"Bearer {settings.ai_api_key}"},
                    json=fallback_payload,
                )
                try:
                    response.raise_for_status()
                except httpx.HTTPError as fallback_exc:
                    raise EnhancedAnalysisGenerationError(f"增强分析服务异常：{fallback_exc}") from fallback_exc
            except httpx.HTTPError as exc:
                raise EnhancedAnalysisGenerationError(f"增强分析服务异常：{exc}") from exc

        payload = response.json()
        try:
            raw_content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise EnhancedAnalysisGenerationError("模型返回格式不符合预期，无法提取增强分析结果。") from exc

        try:
            return _extract_json_payload(raw_content)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise EnhancedAnalysisGenerationError("模型返回了无法解析的增强分析 JSON，请稍后重试。") from exc


def get_enhanced_analysis_provider() -> BaseEnhancedAnalysisProvider:
    settings = get_settings()
    if settings.ai_provider in {"openai", "openai-compatible"} and settings.ai_api_key:
        return OpenAICompatibleEnhancedAnalysisProvider()
    return OfflineEnhancedAnalysisProvider()


def _build_local_citations(candidates: list[LocalCitationCandidate], limit: int) -> list[AnalysisCitation]:
    citations: list[AnalysisCitation] = []
    for candidate in candidates[:limit]:
        citations.append(
            AnalysisCitation(
                title=candidate.title,
                url=candidate.url,
                source_type=candidate.source_type,
                excerpt=candidate.excerpt,
            )
        )
    return citations


def _deduplicate_text(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def _summarize_dominant_signals(signal_breakdown: list[dict]) -> str:
    if not signal_breakdown:
        return "暂无明显主导信号"

    dominant_items = sorted(
        signal_breakdown,
        key=lambda item: float(item.get("contribution_score", 0)),
        reverse=True,
    )[:2]
    return "，".join(
        f"{item.get('label', '未知信号')} {item.get('value_percent', 0)}%"
        for item in dominant_items
    )


def _extract_responses_output_text(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for output_item in payload.get("output", []):
        for content_item in output_item.get("content", []):
            text_value = content_item.get("text")
            if isinstance(text_value, str) and text_value.strip():
                parts.append(text_value)
    return "\n".join(parts).strip()


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
