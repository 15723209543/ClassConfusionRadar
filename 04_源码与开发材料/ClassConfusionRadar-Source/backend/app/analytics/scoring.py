"""
本文件的作用是：计算课堂分段困惑得分、数据完整度和各项信号解释。
"""
from collections import Counter
from typing import Optional, Union

from app.models.enums import RiskLevel


SIGNAL_RULES = [
    {
        "key": "quiz_incorrect_rate",
        "label": "测验错误率",
        "weight_ratio": 0.35,
        "weight_percent": 35.0,
        "description": "本段课堂测验中错误作答的占比。",
    },
    {
        "key": "submission_failure_rate",
        "label": "提交失败率",
        "weight_ratio": 0.35,
        "weight_percent": 35.0,
        "description": "本段编程提交中非 success 结果的占比。",
    },
    {
        "key": "error_density",
        "label": "重复错误密度",
        "weight_ratio": 0.20,
        "weight_percent": 20.0,
        "description": "本段同一学生反复出现同一错误类型的负担，避免与提交失败率简单重复计分。",
    },
    {
        "key": "interaction_silence",
        "label": "互动沉默度",
        "weight_ratio": 0.10,
        "weight_percent": 10.0,
        "description": "本段没有参与互动的学生占比。",
    },
]

SIGNAL_RULE_MAP = {item["key"]: item for item in SIGNAL_RULES}
SCORE_FORMULA_TEXT = (
    "困惑得分 = 有效数据项加权归一化得分；基础权重为：35%×测验错误率 + "
    "35%×提交失败率 + 20%×重复错误密度 + 10%×互动沉默度。"
    "缺失的数据项不按 0 拉低风险，而是降低数据完整度与可信度。"
)
RISK_LEVEL_TEXT = {
    RiskLevel.low: "低风险",
    RiskLevel.medium: "中风险",
    RiskLevel.high: "高风险",
    RiskLevel.critical: "极高风险",
}
CONFIDENCE_LEVEL_TEXT = {
    "high": "高可信",
    "medium": "中可信",
    "low": "低可信",
}


def infer_risk_level(weighted_score: float) -> RiskLevel:
    if weighted_score >= 80:
        return RiskLevel.critical
    if weighted_score >= 60:
        return RiskLevel.high
    if weighted_score >= 40:
        return RiskLevel.medium
    return RiskLevel.low


def infer_confidence_level(data_coverage_ratio: float) -> str:
    if data_coverage_ratio >= 0.80:
        return "high"
    if data_coverage_ratio >= 0.50:
        return "medium"
    return "low"


def compute_confusion_score(
    quiz_incorrect_rate: float,
    submission_failure_rate: float,
    error_density: float,
    interaction_silence: float,
    *,
    available_signals: dict[str, bool] | None = None,
) -> float:
    """只对有数据的信号做归一化，缺失项单独计入数据完整度。"""
    values = {
        "quiz_incorrect_rate": quiz_incorrect_rate,
        "submission_failure_rate": submission_failure_rate,
        "error_density": error_density,
        "interaction_silence": interaction_silence,
    }
    # 只汇总当前确实存在的数据权重，防止缺失信号被误当成零风险。
    available_signal_map = available_signals or {key: True for key in values}
    available_weight_sum = sum(
        SIGNAL_RULE_MAP[key]["weight_ratio"]
        for key, is_available in available_signal_map.items()
        if is_available and key in SIGNAL_RULE_MAP
    )
    if available_weight_sum <= 0:
        return 0.0

    weighted_score = 0.0
    for key, value in values.items():
        if available_signal_map.get(key, False):
            weighted_score += SIGNAL_RULE_MAP[key]["weight_ratio"] * max(0.0, min(1.0, value))
    return round((weighted_score / available_weight_sum) * 100, 2)


def compute_repeated_error_density(error_keys: list[tuple[int, str]], submission_total: int) -> tuple[float, int]:
    if submission_total <= 0 or not error_keys:
        return 0.0, 0

    # 同一学生第一次出现某类错误只算一次暴露，后续重复才计入重复错误密度。
    error_repeat_counts = Counter(error_keys)
    repeat_total = sum(max(0, count - 1) for count in error_repeat_counts.values())
    repeat_density = min(1.0, repeat_total / submission_total)
    return round(repeat_density, 4), repeat_total


def compute_data_coverage_ratio(available_signals: dict[str, bool]) -> float:
    # 完整度沿用基础权重计算，作为可信度证据而不直接改变困惑分。
    base_weight_total = sum(item["weight_ratio"] for item in SIGNAL_RULES)
    if base_weight_total <= 0:
        return 0.0
    available_weight_total = sum(
        SIGNAL_RULE_MAP[key]["weight_ratio"]
        for key, is_available in available_signals.items()
        if is_available and key in SIGNAL_RULE_MAP
    )
    return round(available_weight_total / base_weight_total, 4)


def summarize_errors(labels: list[str]) -> list[dict[str, Union[int, str]]]:
    return [
        {"label": label, "count": count}
        for label, count in Counter(label for label in labels if label).most_common(5)
    ]


def build_signal_item(
    key: str,
    raw_value: float,
    samples: int,
    evidence_summary: str,
    *,
    is_available: bool = True,
    available_weight_sum: float | None = None,
) -> dict[str, Union[str, float, int, bool]]:
    rule = SIGNAL_RULE_MAP[key]
    base_weight_percent = float(rule["weight_percent"])
    effective_weight_percent = (
        round((float(rule["weight_ratio"]) / available_weight_sum) * 100, 2)
        if is_available and available_weight_sum and available_weight_sum > 0
        else 0.0
    )
    return {
        "key": key,
        "label": rule["label"],
        "weight_percent": base_weight_percent,
        "effective_weight_percent": effective_weight_percent,
        "raw_value": round(raw_value, 4),
        "value_percent": round(raw_value * 100, 2),
        "contribution_score": round(raw_value * effective_weight_percent, 2) if is_available else 0.0,
        "samples": samples,
        "is_available": is_available,
        "description": rule["description"],
        "evidence_summary": evidence_summary,
    }


ERROR_LABEL_TEXT = {
    "SegmentationFault": "内存访问错误",
    "SyntaxError": "语法错误",
    "InfiniteLoop": "死循环",
    "OffByOne": "循环边界差一",
    "StateUpdate": "状态更新错误",
    "BoundaryCondition": "边界条件错误",
    "IndexError": "下标越界",
    "ArrayIndexOutOfBounds": "数组越界",
    "NullPointer": "空指针错误",
    "NullPointerException": "空指针错误",
    "TypeError": "类型错误",
    "NameError": "变量名错误",
    "ValueError": "数值格式错误",
    "KeyError": "键值不存在",
    "ZeroDivisionError": "除零错误",
    "StackOverflow": "递归过深",
    "StackOverflowError": "递归过深",
    "Timeout": "运行超时",
    "TLE": "运行超时",
    "WrongAnswer": "答案错误",
    "WA": "答案错误",
    "RuntimeError": "运行错误",
    "RE": "运行错误",
    "CompileError": "编译错误",
    "CompilationError": "编译错误",
    "CE": "编译错误",
    "MemoryLimitExceeded": "内存超限",
    "MLE": "内存超限",
    "LogicError": "逻辑错误",
    "ScopeError": "变量作用域错误",
    "QueueBoundary": "循环队列边界错误",
    "BoundaryUpdate": "边界更新错误",
    "MissingBaseCase": "缺少递归终止条件",
    "VirtualDispatch": "虚函数调用错误",
    "JoinCondition": "数据库连接条件错误",
    "AsyncOrder": "异步执行顺序错误",
    "ConcurrentModification": "并发修改错误",
    "RaceCondition": "竞态条件错误",
    "SequenceMismatch": "序列号不匹配",
    "IsolationViolation": "事务隔离异常",
    "DependencyInversion": "依赖倒置问题",
    "HeuristicError": "启发函数错误",
    "Overfitting": "模型过拟合",
    "EffectDependency": "副作用依赖错误",
    "SignatureMismatch": "数字签名不匹配",
    "InterruptConflict": "中断冲突",
    "unknown": "未知错误",
    "wrong_answer": "答案错误",
}


def readable_error_label(label: str) -> str:
    return ERROR_LABEL_TEXT.get(label, label)


def readable_error_text(text: str) -> str:
    result = text
    for code, label in ERROR_LABEL_TEXT.items():
        result = result.replace(code, label)
    return result


def build_main_error_summary(error_summary: list[dict[str, Union[int, str]]]) -> str:
    if not error_summary:
        return "暂无明显提交错误。"
    return "；".join(
        f"{readable_error_label(str(item['label']))}（{item['count']} 次）"
        for item in error_summary
    )


def build_overall_explanation(
    confusion_score: float,
    risk_level: RiskLevel,
    signal_breakdown: list[dict[str, Union[str, float, int, bool]]],
    main_error_summary: str,
    *,
    data_coverage_percent: float | None = None,
    confidence_level: str | None = None,
) -> str:
    sorted_signals = sorted(
        [item for item in signal_breakdown if bool(item.get("is_available", True))],
        key=lambda item: float(item["contribution_score"]),
        reverse=True,
    )
    dominant_signals = [item for item in sorted_signals if float(item["contribution_score"]) > 0][:2]

    if dominant_signals:
        reason_text = "，主要由 " + "、".join(
            f"{item['label']} {item['value_percent']}%（有效贡献 {item['contribution_score']} 分）"
            for item in dominant_signals
        ) + " 拉高。"
    else:
        reason_text = "，当前可用信号贡献都较低。"

    coverage_text = ""
    if data_coverage_percent is not None and confidence_level is not None:
        coverage_text = f" 数据完整度 {round(data_coverage_percent, 2)}%，可信度为{CONFIDENCE_LEVEL_TEXT.get(confidence_level, confidence_level)}。"

    missing_signals = [str(item["label"]) for item in signal_breakdown if not bool(item.get("is_available", True))]
    missing_text = f" 缺失信号：{'、'.join(missing_signals)}。" if missing_signals else ""
    error_text = "" if main_error_summary == "暂无明显提交错误。" else f" 主要错误：{main_error_summary}"
    return (
        f"该分段困惑得分为 {confusion_score}，判定为{RISK_LEVEL_TEXT[risk_level]}{reason_text}"
        f"{coverage_text}{missing_text}{error_text}"
    )


def get_primary_signal(signal_breakdown: list[dict[str, Union[str, float, int, bool]]]) -> Optional[dict[str, Union[str, float, int, bool]]]:
    available_items = [item for item in signal_breakdown if bool(item.get("is_available", True))]
    if not available_items:
        return None
    return max(available_items, key=lambda item: float(item["contribution_score"]))
