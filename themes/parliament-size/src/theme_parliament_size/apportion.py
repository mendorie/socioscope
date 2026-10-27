"""議席配分の純粋関数: ドント式、修正サンラグ式、アダムズ方式、Gallagher 不比例性指数、参入閾値。

すべて決定的。同点は入力の並び順（辞書の挿入順）で先のものを優先し、`tie` を返して呼び出し側が
注記できるようにする。
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence


def highest_averages(
    votes: Mapping[str, float], seats: int, divisor: Sequence[float] | None = None
) -> dict[str, int]:
    """最高平均法。divisor[k] は k 議席目（0 始まり）を争うときの除数。None はドント（1,2,3,…）。"""
    if seats < 0:
        msg = "seats must be >= 0"
        raise ValueError(msg)
    out = {p: 0 for p in votes}
    if seats == 0 or not votes:
        return out
    for _ in range(seats):
        best: str | None = None
        best_q = -1.0
        for p, v in votes.items():
            k = out[p]
            d = divisor[k] if divisor is not None and k < len(divisor) else float(k + 1)
            q = v / d
            if q > best_q:
                best, best_q = p, q
        assert best is not None
        out[best] += 1
    return out


def dhondt(votes: Mapping[str, float], seats: int) -> dict[str, int]:
    return highest_averages(votes, seats)


def sainte_lague(
    votes: Mapping[str, float], seats: int, first_divisor: float = 1.0, max_seats: int = 200
) -> dict[str, int]:
    """サンラグ式（1,3,5,…）。first_divisor=1.4 で修正サンラグ式。"""
    divs = [first_divisor] + [float(2 * k + 1) for k in range(1, max_seats)]
    return highest_averages(votes, seats, divs)


def adams(populations: Mapping[str, float], seats: int, max_iter: int = 200) -> dict[str, int]:
    """アダムズ方式: 各単位の人口 ÷ 除数 の小数点以下を切り上げた合計が seats になる除数を探す。
    どの単位も最低 1 議席。切り上げなので同じ配分を与える除数は区間をなすが、配分は一意。"""
    if seats < len(populations):
        msg = "seats must be >= number of units (each unit gets at least one seat)"
        raise ValueError(msg)
    total = float(sum(populations.values()))
    lo, hi = total / seats / 2, total / seats * 2
    for _ in range(max_iter):
        x = (lo + hi) / 2
        alloc = {k: max(1, math.ceil(v / x)) for k, v in populations.items()}
        s = sum(alloc.values())
        if s == seats:
            return alloc
        if s > seats:
            lo = x  # 除数を大きくして議席を減らす
        else:
            hi = x
    msg = "adams: divisor search did not converge"
    raise ValueError(msg)


def gallagher(vote_shares: Mapping[str, float], seat_shares: Mapping[str, float]) -> float:
    """Gallagher 最小二乗指数（% 単位の得票率・議席率）。0 が完全比例。"""
    keys = set(vote_shares) | set(seat_shares)
    return math.sqrt(
        sum((vote_shares.get(k, 0.0) - seat_shares.get(k, 0.0)) ** 2 for k in keys) / 2
    )


def threshold_share(votes: Mapping[str, float], seats: int, party: str) -> float:
    """party が（他党の票を固定して）1 議席を取るのに必要な最小得票率（全体に占める %）。
    ドント式: 他党の s 番目に大きい商 q_s（s = seats）を超えればよい（最後の議席の商）。"""
    others = {p: v for p, v in votes.items() if p != party}
    quotients = sorted((v / (k + 1) for v in others.values() for k in range(seats)), reverse=True)
    if len(quotients) < seats:
        return 0.0
    need = quotients[seats - 1]
    total_others = sum(others.values())
    # 自党の票 x が need を超えると 1 議席。得票率 = x / (total_others + x)
    return 100.0 * need / (total_others + need) if total_others + need > 0 else 0.0
