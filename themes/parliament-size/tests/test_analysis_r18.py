import math

from theme_parliament_size.analysis.a20261030_r18_distrust_and_cuts import (
    enacted_rate,
    is_distrust_or_cost,
    judge_h17a,
    judge_h17c,
)


def test_reason_classification_and_enacted_rate() -> None:
    assert is_distrust_or_cost("不信・費用") and is_distrust_or_cost("費用・効率")
    assert not is_distrust_or_cost("効率・制度改革")
    rows = [{"status": "enacted"}, {"status": "repealed"}, {"status": "proposed"}]
    assert enacted_rate(rows) == (1, 3)
    assert enacted_rate([]) == (0, 0)


def test_judgements_follow_the_pre_registered_cutoffs() -> None:
    assert judge_h17a(-5.0).startswith("整合") and judge_h17a(-4.9).startswith("不支持")
    assert judge_h17a(5.0).startswith("逆") and judge_h17a(math.nan) == "判定不能"
    assert judge_h17c(5.0).startswith("整合") and judge_h17c(0.0) == "不支持"
    assert judge_h17c(-5.0).startswith("逆")
