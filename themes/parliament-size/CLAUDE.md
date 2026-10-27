# themes/parliament-size
設計（問い・事前登録仮説 H1〜H6・指標・採用順）: `design/themes/parliament-size.md`。規約: root `CLAUDE.md`、`.claude/rules/themes.md`。
データソースの調査記録: `design/data-sources.md`（候補表の parliament-size 行、採用記録「IPU Parline API」）。

## 構成
```
src/theme_parliament_size/
  pipeline.py   fetch / stage / mart（Port 経由。I/O はここだけ）。ソースごとに `# ---- <source>` ブロックを足す。
                `build_panel`: long 形式 mart（iso3, year, unit, metric, value, source）のソート・キー重複検査
                `_fetch_ipu`（`links.next` で 3＋2 ページを辿る、非 JSON は raw に入れない）/ `_stage_ipu` / `_mart_ipu`
  wiring.py     PIPELINE（entry point）。stage 関数の登録のみ
  ipu.py        IPU Parline API（JSON:API、鍵不要）: `url(kind, page)`/`raw_name`、`CHAMBER_ATTRS`/`COUNTRY_ATTRS`（採用属性）、
                `parse(payload, kind, page)`（属性ごとの時間付きレコードを long に。`{"type": 通貨, "value": 額}` は value_num＋unit、
                `[{"term": …}]` は `;` 結合。data 無し・type 不一致・value 無しは ValueError）、`has_next`、
                `build_mart`（議院 1 行、各属性の最新レコード、国の人口・OECD 加盟を結合。国が無い議院は ValueError）
  <source>.py   （予定、採用順）soumu.py 総務省 結果調 PDF / apportion.py ドント・修正サンラグ・アダムズ・Gallagher の純粋関数 /
                mof.py 予算書 PDF / shugiin.py 議案審議経過
  analysis/     report 用スクリプト（決定的、1 report 1 ファイル）: a20261027_r1_ratio.py（H1・H1b・H1c、図 3 枚）
queries/        DuckDB 用 SQL（? バインド）
reports/        <yyyy-mm-dd>-<slug>.md ＋ figures/
tests/          conftest.py（実 API の形を写した合成ページ）＋ Fake による状態テスト
```

## テーブル
| name | 粒度 | 列 |
|---|---|---|
| `staged/ipu/chamber_attributes` | 議院×属性×レコード（long） | kind(chambers), entity_id（JP-LC01 など）, attribute（`ipu.CHAMBER_ATTRS`）, seq, value（文字列）, value_num, unit（通貨など）, date_from, date_to, source(`ipu_parline`)。281 議院（2026-10-27 取得） |
| `staged/ipu/country_attributes` | 国×属性×レコード（long） | 同列、kind(countries), entity_id（JP など）, attribute（`ipu.COUNTRY_ATTRS`。population_in_thousands は 1950– 年次） |
| `marts/ipu_parliaments` | 議院 | iso3, country, region, subregion, oecd_member, chamber_id, chamber_type(lower/upper), chamber_name, electoral_system, electoral_subsystem, designation_mode, statutory_seats, statutory_seats_since, current_members, directly_elected, majoritarian_tier_seats, proportional_tier_seats, permanent_staff, staff_year, staff_combined_parl, chamber_budget, budget_currency, chamber_budget_ppp, budget_year, budget_combined_parl, basic_salary_ppp, salary_year, plenary_days, plenary_year, committees, members_per_country, population_thousands, population_year, parliament_budget_pct_gov, source。281 行（OECD 38 か国 58 議院、2026-10-27 取得） |
| `marts/parliament_size_panel` | iso3×year×unit×metric×source（long） | **未作成**（行ができるまで書かない） |

## 状態
IPU Parline を採用し fetch/stage/mart 実装済み（**CC BY-NC-SA 4.0**、非商用）。
R1 report（H1 整合・H1b 整合・H1c 整合）: `reports/2026-10-27-r1-ratio.md`（`analysis/a20261027_r1_ratio.py`、図 `figures/r1_*.png` 3 枚）。
次: ② 総務省 結果調 PDF ＋ 公選法 別表（H3・H4）。

## テーマ固有の規約
- 「議員数」は定数（statutory）と現員（current）を列で分け、混ぜない。上院の選出方法（designation_mode）を注記できるよう議院単位で持つ。
- 配分方式（ドント・修正サンラグ・アダムズ）は純粋関数で実装し、現行の配分（衆院 比例 176・小選挙区 289）を再現できることをテストで固定してから試算に使う。
- 比例の機械的試算は「票が同じなら」の目安。report に必ず「行動の変化は織り込まない」と書く。
- 一票の格差は 有権者数（選挙時）と 国勢調査人口 の両方で出し、どちらかを明記する。
- 推進・反対のどちらにも都合の良い指標だけを選ばない。事前登録した H1〜H6 をすべて報告する。
- IPU Parline 由来のデータは非商用（CC BY-NC-SA 4.0）。
