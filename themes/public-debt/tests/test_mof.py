import pytest

from theme_public_debt import mof

PAGE = """国債等の保有者別内訳
（令和８年６月末（速報））
国債
合計 1,006兆5,235億円
国庫短期証券（T-Bill）
合計 135兆4,990億円
国債及び国庫短期証券（T-Bill）
合計 1,142兆225億円
（単位：億円）
出所：日本銀行「資金循環統計」（令和８年９月17日公表）
(注１)「国債」は「財投債」を含む。
一般政府
（除く公的年金）
37,388
0.4%
日本銀行
4,700,401
46.7%
銀行等
1,573,121
15.6%
生損保等
1,520,591
15.1%
公的年金
766,164
7.6%
年金基金
322,110
3.2%
海外
799,111
7.9%
家計
219,434
2.2%
その他
126,915
1.3%
 一般政府
（除く公的年金）
161,000
11.9%
財政融資資金
22,000
1.6%
銀行等
454,400
33.5%
海外
699,656
51.6%
"""


def test_parse_reads_the_jgb_block_only_and_checks_totals() -> None:
    rows = mof.parse([PAGE])

    assert rows[0]["asof_year"] == 2026 and rows[0]["asof_month"] == 6
    holders = [r["holder"] for r in rows]
    assert holders == [
        "一般政府（除く公的年金）",
        "日本銀行",
        "銀行等",
        "生損保等",
        "公的年金",
        "年金基金",
        "海外",
        "家計",
        "その他",
    ]
    boj = next(r for r in rows if r["holder"] == "日本銀行")
    assert boj["amount_oku_yen"] == 4_700_401.0 and boj["share_pct"] == 46.7
    assert all(r["instrument"] == "jgb" and r["source"] == "mof_holdings" for r in rows)


def test_parse_fails_closed_when_holders_do_not_add_up() -> None:
    bad = PAGE.replace("4,700,401", "1,000")
    with pytest.raises(ValueError, match="do not add up"):
        mof.parse([bad])


def test_parse_fails_closed_without_date_or_boj() -> None:
    with pytest.raises(ValueError, match="as-of date"):
        mof.parse(["国債\n合計 1兆0億円\n日本銀行\n1\n100%"])
    with pytest.raises(ValueError, match="日本銀行"):
        mof.parse(["（令和８年６月末）\n合計 1兆0億円\n銀行等\n10,000\n100%"])


def test_build_mart_emits_shares_for_japan() -> None:
    rows = mof.parse([PAGE])
    out = mof.build_mart(rows)
    got = {r["metric"]: r["value"] for r in out}

    assert got["share_boj"] == 46.7 and got["share_foreign"] == 7.9
    assert all(r["iso3"] == "JPN" and r["year"] == 2026 and r["unit"] == "jgb_holders" for r in out)
