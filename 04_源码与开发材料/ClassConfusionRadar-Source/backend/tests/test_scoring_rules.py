"""
本文件的作用是：验证困惑评分规则相关功能在典型与异常场景下的行为。
"""
from app.analytics.scoring import (
    compute_confusion_score,
    compute_data_coverage_ratio,
    compute_repeated_error_density,
    infer_confidence_level,
    infer_risk_level,
)
from app.models.enums import RiskLevel


def test_missing_signals_are_normalized_instead_of_counted_as_zero():
    score = compute_confusion_score(
        quiz_incorrect_rate=0,
        submission_failure_rate=0.8,
        error_density=0.4,
        interaction_silence=0,
        available_signals={
            "quiz_incorrect_rate": False,
            "submission_failure_rate": True,
            "error_density": True,
            "interaction_silence": False,
        },
    )
    assert score == 65.45


def test_repeated_error_density_ignores_first_occurrence():
    density, repeated = compute_repeated_error_density([(1, "SyntaxError"), (2, "SyntaxError")], 4)
    assert density == 0
    assert repeated == 0


def test_repeated_error_density_counts_same_students_repeating_same_error():
    density, repeated = compute_repeated_error_density(
        [(1, "SyntaxError"), (1, "SyntaxError"), (1, "SyntaxError"), (2, "Timeout"), (2, "Timeout")],
        6,
    )
    assert density == 0.5
    assert repeated == 3


def test_data_coverage_uses_base_signal_weights():
    ratio = compute_data_coverage_ratio(
        {
            "quiz_incorrect_rate": False,
            "submission_failure_rate": True,
            "error_density": True,
            "interaction_silence": False,
        }
    )
    assert ratio == 0.55
    assert infer_confidence_level(ratio) == "medium"


def test_risk_thresholds_are_stable():
    assert infer_risk_level(39.99) == RiskLevel.low
    assert infer_risk_level(40) == RiskLevel.medium
    assert infer_risk_level(60) == RiskLevel.high
    assert infer_risk_level(80) == RiskLevel.critical
