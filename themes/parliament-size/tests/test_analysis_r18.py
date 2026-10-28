import math

import pytest

from theme_parliament_size.analysis.a20261030_r18_distrust_and_cuts import (
    enacted_rate,
    is_distrust_or_cost,
    judge_h17a,
    judge_h17c,
    period_mean,
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


def test_period_mean_is_inclusive_and_nan_when_empty() -> None:
    series = {91: 31.0, 92: 27.0, 97: 30.0, 98: 35.0}
    assert period_mean(series, (91, 97)) == pytest.approx((31 + 27 + 30) / 3)
    assert period_mean(series, (98, 103)) == 35.0
    assert math.isnan(period_mean(series, (104, 105)))
