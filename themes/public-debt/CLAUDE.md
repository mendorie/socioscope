# themes/public-debt
設計（動機の修正・問い・事前登録仮説 H1〜H6・指標・採用順）: `design/themes/public-debt.md`。規約: root `CLAUDE.md`、`.claude/rules/themes.md`。
データソースの調査記録: `design/data-sources.md`（候補表の public-debt 行。採用時に「採用ソースの記録」へ節を足す）。

## 構成
```
src/theme_public_debt/
  pipeline.py   fetch / stage / mart（Port 経由。I/O はここだけ）。ソースごとに `# ---- <source>` ブロックを足す。
                `build_panel`: long 形式 mart（iso3, year, unit, metric, value, source）のソート・キー重複検査
  wiring.py     PIPELINE（entry point）。stage 関数の登録のみ
  jst.py        Macrohistory Database R6 xlsx（採用済み）
  imf.py        IMF DataMapper API（WEO・FM・GDD、採用済み。見通し年は LAST_ACTUAL_YEAR で切る）
  <source>.py   （予定、採用順）boj.py 国債保有者別 / mof.py 長期国債統計 / bis.py 総信用
  debt_dynamics.py（予定）債務動態の恒等式 Δd = (r − g)/(1 + g)·d₋₁ − pb + sfa の純粋関数
  analysis/     report 用スクリプト（決定的、1 report 1 ファイル）
queries/        DuckDB 用 SQL（? バインド）
reports/        <yyyy-mm-dd>-<slug>.md ＋ figures/
tests/          fixtures/（実ファイルの縮約）＋ Fake による状態テスト
```

## テーブル
| name | 粒度 | 列 |
|---|---|---|
| `staged/jst/macrohistory` | iso3×year（18 か国 1870–2020） | iso3, year, country, pop, gdp, cpi, stir, ltrate, debtgdp（比率）, revenue, expenditure, tloans, thh, tbus, crisis_jst, source |
| `marts/jst_debt_panel` | iso3×year×unit×metric（long） | unit: general_gov_gross（debt_gdp %, fiscal_balance_gdp % ＝ 総合収支）/ households / nfc / private_nonfin / total_nonfin（debt_gdp %）/ macro（ltrate, stir, ngdp_growth, cpi_inflation, pop, crisis_jst） |
| `staged/imf/datamapper` | iso3×year×code | iso3, year, dataset（weo/fm/gdd）, code, value, source |
| `marts/imf_debt_panel` | iso3×year×unit×metric×source（long） | source imf_weo: general_gov_gross（debt_gdp, fiscal_balance_gdp）/ imf_fm: general_gov_net（debt_gdp）, general_gov_gross（primary_balance_gdp, interest_gdp ＝ 基礎的収支 − 総合収支）/ imf_gdd: general_gov_gross, central_gov_gross, households, nfc, private_nonfin（debt_gdp） |
| `marts/public_debt_panel` | iso3×year×unit×metric×source（long） | jst ＋ imf_* の結合。予定 unit: general_gov_market（中銀保有控除） |

## テーマ固有の規約
- 債務の定義（中央／一般政府、総／純、市中保有）は `unit` で分け、**同じ unit 同士でしか比べない**。ソース内で定義が切り替わる年は staged に `definition_break` 列を持たせ report に注記する。
- 債務動態の分解は純粋関数で実装し、既知の数値例（恒等式が閉じること、sfa = 0 の合成データで Δd を再現すること）をテストで固定してから実データに使う。
- 戦時（1914–1918、1939–1945）は区間として別扱いにする。比率のピークを「平時の最高」と呼ばない。
- JST は CC BY-NC-SA 4.0。派生 Parquet は非商用に限り、`data/README.md` に継承を書く。
- 「終焉が近い／遠い」のどちらにも都合の良い指標だけを選ばない。事前登録した H1〜H6 をすべて報告する。
