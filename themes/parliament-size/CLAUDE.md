# themes/parliament-size
設計（問い・事前登録仮説 H1〜H6・指標・採用順）: `design/themes/parliament-size.md`。規約: root `CLAUDE.md`、`.claude/rules/themes.md`。
データソースの調査記録: `design/data-sources.md`（候補表の parliament-size 行。採用時に「採用ソースの記録」へ節を足す）。

## 構成
```
src/theme_parliament_size/
  pipeline.py   fetch / stage / mart（Port 経由。I/O はここだけ）。ソースごとに `# ---- <source>` ブロックを足す。
                `build_panel`: long 形式 mart（iso3, year, unit, metric, value, source）のソート・キー重複検査
  wiring.py     PIPELINE（entry point）。stage 関数の登録のみ
  <source>.py   （予定、採用順）ipu.py Parline API / worldbank.py WDI 人口 / soumu.py 総務省 結果調 PDF /
                apportion.py ドント・修正サンラグ・アダムズ・Gallagher の純粋関数 / mof.py 予算書 PDF / shugiin.py 議案審議経過
  analysis/     report 用スクリプト（決定的、1 report 1 ファイル）
queries/        DuckDB 用 SQL（? バインド）
reports/        <yyyy-mm-dd>-<slug>.md ＋ figures/
tests/          fixtures/（実レスポンスの縮約）＋ Fake による状態テスト
```

## テーブル
| name | 粒度 | 列 |
|---|---|---|
| `marts/parliament_size_panel` | iso3×year×unit×metric×source（long） | iso3, year, unit（lower_house / upper_house / both / pr_block:<name> / pref:<code>）, metric（seats / population / seats_per_million / staff_per_member / …）, value, source。**未作成**（行が 0 の Parquet は列を持たず DuckDB が読めないため、行ができるまで書かない） |

## テーマ固有の規約
- 「議員数」は定数（statutory）と現員（current）を `metric` で分け、混ぜない。上院は非公選の国（英・加など）を注記できるよう `unit` を分ける。
- 配分方式（ドント・修正サンラグ・アダムズ）は純粋関数で実装し、現行の配分（衆院 比例 176・小選挙区 289）を再現できることをテストで固定してから試算に使う。
- 比例の機械的試算は「票が同じなら」の目安。report に必ず「行動の変化は織り込まない」と書く。
- 一票の格差は 有権者数（選挙時）と 国勢調査人口 の両方で出し、どちらかを明記する。
- 推進・反対のどちらにも都合の良い指標だけを選ばない。事前登録した H1〜H6 をすべて報告する。
