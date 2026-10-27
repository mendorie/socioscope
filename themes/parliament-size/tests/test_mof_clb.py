"""財務省 予算書 PDF と 内閣法制局 HTML の純粋変換（実ファイルのテキスト様式を縮約した合成）。"""

import pytest

from theme_parliament_size import clb, mof

ROWS = [
    (101, 114),
    (1300, 1315),
    (3310, 3352),
    (163, 163),
    (1115, 1215),
    (50671, 52768),
    (47865, 49894),  # 内閣本府等（内閣府の内訳）
    (2806, 2875),  # 警察庁（内閣府の内訳）
    (4964, 4752),
    (182107, 193861),
    (7405, 7436),
    (7257, 7448),
    (282777, 294031),
    (53384, 55094),
    (338191, 343064),
    (20933, 20957),
    (8695, 8506),
    (60965, 60719),
    (3207, 3096),
    (79172, 86691),
    (10000, None),
    (10000, 7395),
]


def budget_page(total: tuple[int, int] = (1125717, 1151978)) -> list[str]:
    lines = ["前年度予算額 令 和 ７ 年 度 予 算 額 比較増△減額", "％"]
    for a, b in ROWS:
        bs = "－" if b is None else f"{b:,}"
        lines.append(f"{a:,} {bs} 1 1.0")
        if a == 182107:
            lines.append("( 177,863 ) ( 188,728 ) ( 10,865 ) ( 6.1 )")
    lines.append(f"{total[0]:,} {total[1]:,} 26,262 2.3合　　  　計")
    lines += [
        "環境省",
        "令和７年度一般会計歳出予算（衆議院修正＋参議院修正後）所管別内訳",
        "皇室費",
        "国会",
        "裁判所",
        "防衛省",
        "予備費",
        "－ 2 －",
    ]
    return ["page 0 (歳入歳出)", "\n".join(lines), "page 2"]


def test_mof_parse_assigns_organs_in_order_and_checks_the_total() -> None:
    out = mof.parse(budget_page())
    kokkai = [r for r in out if r["organ"] == "国会"]
    assert [(r["fy"], r["stage"], r["amount"]) for r in kokkai] == [
        (2024, "initial", 1300.0),
        (2025, "revised", 1315.0),
    ]
    assert [r for r in out if r["organ"] == "合計"][1]["amount"] == 1151978.0
    sub = next(r for r in out if r["organ"] == "内閣府_警察庁")
    assert sub["in_total"] is False
    reserve = [r for r in out if r["organ"] == "予備費_物価高騰対策等"]
    assert reserve[1]["amount"] is None
    mart = mof.build_mart(out)
    assert mart[0]["iso3"] == "JPN" and {r["fy"] for r in mart} == {2024, 2025}


def test_mof_parse_is_fail_closed() -> None:
    with pytest.raises(ValueError, match="page with 所管別内訳 not found"):
        mof.parse(["nothing"])
    with pytest.raises(ValueError, match="!= total"):
        mof.parse(budget_page(total=(1125717, 1000000)))
    page = budget_page()
    page[1] = page[1].replace("皇室費\n", "")
    with pytest.raises(ValueError, match="lacks the label"):
        mof.parse(page)
    page = budget_page()
    page[1] = page[1].replace("3,310 3,352 1 1.0\n", "")
    with pytest.raises(ValueError, match="expected 22 organ rows"):
        mof.parse(page)


def _cell(carried: int, n: int) -> str:
    return f"<td>（継続{carried}件） {n}件</td>"


def clb_html(sessions: int = 12, broken: bool = False) -> bytes:
    rows = []
    for i in range(sessions):
        s = 221 - i
        tot_sub = 64 + 59 if not broken else 1
        rows.append(
            f"<tr><td>第{s}回（特別会） 令和8年2月18日～7月25日</td>"
            + _cell(0, 64)
            + _cell(0, 64)
            + _cell(0, 59)
            + _cell(0, 14)
            + _cell(0, tot_sub)
            + _cell(0, 78)
            + "</tr>"
        )
    html = (
        "<html><body><table><tr><th>区分</th><th>閣法 提出</th></tr>"
        + "".join(rows)
        + "</table><p>※継続審査件数は外数</p></body></html>"
    )
    return html.encode("utf-8")


def test_clb_parse_reads_sessions_and_checks_totals() -> None:
    out = clb.parse(clb_html())
    assert len(out) == 12
    first = out[0]
    assert (first["session"], first["kind"], first["start_date"]) == (210, "特別会", "2026-02-18")
    assert (first["cabinet_submitted"], first["member_enacted"]) == (64, 14)
    mart = clb.build_mart(out)
    assert mart[-1]["session"] == 221 and mart[-1]["year"] == 2026
    assert mart[-1]["member_share_of_enacted"] == pytest.approx(14 / 78)
    with pytest.raises(ValueError, match="totals do not add up"):
        clb.parse(clb_html(broken=True))
    with pytest.raises(ValueError, match=">= 10 rows"):
        clb.parse(clb_html(sessions=3))


def test_clb_wareki_conversion() -> None:
    assert clb._wareki("平成25年1月28日～6月26日") == "2013-01-28"
    assert clb._wareki("令和元年10月4日") == "2019-10-04"
    assert clb._wareki("no date") == ""
