"""H7: 人口転換開始年の純粋関数（I/O なし・決定的）。

定義（`design/themes/growth-fertility.md` H7 で事前固定）:
`pre_window` 内の TFR 最大値（peak）が `min_peak` 以上の国を対象とし、
peak から `drop` 割だけ下回り、その後観測されたどの年も閾値を上回らない最初の年を開始年とする。
`smooth` は判定前に当てる中心移動平均の幅（奇数、1 = 生値）。欠損年は補完せず飛ばす。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

Series = Mapping[int, float | None] | Iterable[tuple[int, float | None]]


def _observed(series: Series) -> list[tuple[int, float]]:
    items = series.items() if isinstance(series, Mapping) else series
    return sorted((int(y), float(v)) for y, v in items if v is not None)


def _smoothed(obs: list[tuple[int, float]], smooth: int) -> list[tuple[int, float]]:
    """観測年だけで作る中心移動平均（幅 smooth、両端は窓を縮める）。"""
    if smooth == 1:
        return obs
    half = smooth // 2
    values = [v for _, v in obs]
    out = []
    for i, (year, _) in enumerate(obs):
        window = values[max(0, i - half) : i + half + 1]
        out.append((year, sum(window) / len(window)))
    return out


def _peak(obs: list[tuple[int, float]], pre_window: tuple[int, int]) -> tuple[float, int] | None:
    lo, hi = pre_window
    candidates = [(v, -y) for y, v in obs if lo <= y <= hi]
    if not candidates:
        return None
    v, neg_year = max(candidates)
    return v, -neg_year


def transition_onset(
    series: Series,
    *,
    pre_window: tuple[int, int] = (1960, 1975),
    min_peak: float = 4.5,
    drop: float = 0.10,
    smooth: int = 1,
) -> int | None:
    """TFR 系列（year → tfr、None は欠損）から転換開始年を返す。対象外・未特定は None。"""
    if smooth < 1 or smooth % 2 == 0:
        raise ValueError(f"smooth must be a positive odd integer, got {smooth}")
    obs = _smoothed(_observed(series), smooth)
    peak = _peak(obs, pre_window)
    if peak is None or peak[0] < min_peak:
        return None
    threshold = (1.0 - drop) * peak[0]
    onset: int | None = None
    for year, value in obs:
        if year < pre_window[0]:
            continue
        if value <= threshold:
            if onset is None:
                onset = year
        else:
            onset = None
    return onset


def onset_table(
    panel_rows: Iterable[Mapping[str, Any]],
    *,
    pre_window: tuple[int, int] = (1960, 1975),
    min_peak: float = 4.5,
    drop: float = 0.10,
    smooth: int = 1,
) -> list[dict[str, Any]]:
    """mart 行（iso3, year, tfr）→ 国ごとの peak / peak_year / onset_year / eligible（iso3 順）。"""
    by_iso: dict[str, dict[int, float | None]] = {}
    for row in panel_rows:
        by_iso.setdefault(str(row["iso3"]), {})[int(row["year"])] = row.get("tfr")
    table = []
    for iso3 in sorted(by_iso):
        series = by_iso[iso3]
        peak = _peak(_observed(series), pre_window)
        onset = transition_onset(
            series, pre_window=pre_window, min_peak=min_peak, drop=drop, smooth=smooth
        )
        table.append(
            {
                "iso3": iso3,
                "peak": None if peak is None else peak[0],
                "peak_year": None if peak is None else peak[1],
                "onset_year": onset,
                "eligible": peak is not None and peak[0] >= min_peak,
            }
        )
    return table
