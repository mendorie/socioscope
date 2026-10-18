"""H12: 結婚が外れた背景（a20261018_h12_why_marriage_left）の純粋ヘルパのテスト。"""

import polars as pl
import pytest

from theme_growth_fertility.analysis import a20261018_h12_why_marriage_left as h12


def test_ci_overlap() -> None:
    assert h12.ci_overlap((93.2, 95.2), (95.0, 96.0))
    assert not h12.ci_overlap((82.7, 85.9), (93.2, 95.2))


def test_k1_needs_both_sexes_10pt_and_disjoint_ci() -> None:
    ok = {"male": h12.Change(95.9, 81.4, False), "female": h12.Change(94.2, 83.0, False)}
    assert h12.k1_type(ok)
    short = {"male": h12.Change(95.9, 81.4, False), "female": h12.Change(94.2, 84.3, False)}
    assert not h12.k1_type(short)  # female −9.9
    overl = {"male": h12.Change(95.9, 81.4, False), "female": h12.Change(94.2, 80.0, True)}
    assert not h12.k1_type(overl)


def test_k2_needs_both_sexes_10pt_rise_and_top_reason() -> None:
    assert h12.k2_type({"male": 35.3, "female": 34.1}, {"male": True, "female": True})
    assert not h12.k2_type({"male": 35.3, "female": 9.0}, {"male": True, "female": True})
    assert not h12.k2_type({"male": 35.3, "female": 34.1}, {"male": True, "female": False})


def test_k3_either_condition_and_unmeasurable_gap() -> None:
    assert h12.k3_type(adv_gap=5.0, econ_f_change=3.0)
    assert h12.k3_type(adv_gap=None, econ_f_change=-10.0)
    assert not h12.k3_type(adv_gap=None, econ_f_change=14.0)
    assert not h12.k3_type(adv_gap=4.9, econ_f_change=-9.9)


def test_top_item() -> None:
    assert h12.top_item({"a": 10.0, "b": 48.1, "c": None}) == "b"


def test_period_mean_half_weights_endpoints() -> None:
    vals = {2018: 10.0, 2019: 20.0, 2020: 30.0, 2021: 40.0}
    # July 2018 – June 2021: half of 2018 and 2021, all of 2019 and 2020, over 3 years
    assert h12.period_mean(vals, 2018, 2021) == pytest.approx((5 + 20 + 30 + 20) / 3)
    with pytest.raises(KeyError):
        h12.period_mean({2018: 1.0}, 2018, 2019)


def test_fill_rate_and_upper_bound() -> None:
    f = h12.fill(lost0=0.5, lost1=0.3, net1=0.1, n0=1000.0, n1=500.0)
    assert f.loss == pytest.approx(500 - 150)
    assert f.filled == pytest.approx(50)
    assert f.rate == pytest.approx(50 / 350)
    # moving c from the lost channels to the filler raises both terms by c
    u = h12.fill(lost0=0.5, lost1=0.3, net1=0.1, n0=1000.0, n1=500.0, moved1=0.08)
    assert u.loss == pytest.approx(350 + 40)
    assert u.filled == pytest.approx(50 + 40)
    assert u.rate > f.rate


def test_k4_verdict_thresholds() -> None:
    assert h12.k4_verdict(0.5) == "補われている"
    assert h12.k4_verdict(0.1999) == "補われていない"
    assert h12.k4_verdict(0.2) == "部分的"


def test_rank_and_final_stance() -> None:
    ranked = h12.rank_types({"reach": 34.1, "will": 14.5}, {"reach", "will"})
    assert [k for k, _ in ranked] == ["reach", "will"]
    s = h12.final_stance(h12.rank_types({"reach": 34.1, "will": 9.9}, {"reach"}), 0.27)
    assert s.startswith("結婚が外れた背景は到達の失敗が主で（変化幅 34.1 ポイント）")
    assert "意思の低下・女性側の評価の低下は従である" in s
    assert s.endswith("ネット経由が補ったのは約 3 割である")
    none = h12.final_stance([], 0.1)
    assert none.startswith("意思も到達も評価も、測った指標では大きく動いていない")


def test_pooled_share() -> None:
    df = pl.DataFrame({"count": [80.0, 60.0], "denominator": [100.0, 100.0]})
    p, lo, hi = h12.pooled(df)
    assert p == pytest.approx(70.0)
    assert lo < 70 < hi
