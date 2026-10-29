# themes/essential-work-wages
設計（問い・事前登録仮説 H0〜H6・操作的定義 E/L/P/T/F/R・対照群・採用順）: `design/themes/essential-work-wages.md`。規約: root `CLAUDE.md`、`.claude/rules/themes.md`。
データソースの調査記録: `design/data-sources.md`（候補表の essential-work-wages 行）。

## 構成
```
src/theme_essential_work_wages/
  pipeline.py   fetch / stage / mart（Port 経由。I/O はここだけ）。ソースごとに `# ---- <source>` ブロックを足す。
                `build_panel`: long 形式 mart（iso3, year, occupation, classification, metric, value, source）のソート・キー重複検査
  wiring.py     PIPELINE（entry point）。stage 関数の登録のみ
  analysis/     report の数値を生成するスクリプト（a<YYYYMMDD>_r<N>_<slug>.py）。未作成
tests/          古典派 TDD。Fake（FakeFetcher / InMemoryRawStore / InMemoryTableStore）＋状態検証
queries/        DuckDB SQL（`?` バインド）。未作成
reports/        report-template.md 準拠。figures/ に図
```

## ソースモジュールの契約（並列実装のため pipeline.py は触らない）
ソース 1 つ = モジュール 1 つ（`src/theme_essential_work_wages/<source>.py`）。`pipeline.py` の `SOURCES` への登録は統合役が行う。モジュールは次を公開する。
- `SOURCE: str`（raw-store の source 名、`--only` で指定する名前）、`LICENSE: str`、URL 定数、`RAW_NAME`／`raw_name(...)`、`MAGIC`（payload 先頭の検査用）。
- `fetch(ctx, written, skipped) -> (written, skipped)`: `ctx.fetcher.fetch(url)` → `FetchError` は `skipped.append(f"{raw_name}: {e}")` で続行、payload が `MAGIC` で始まらなければ `skipped.append(f"{raw_name}: non-<kind> payload")` で raw に入れない。入れるときは `ctx.raw.put(theme=THEME, source=SOURCE, name=raw_name, url=url, license=LICENSE, payload=payload)` し `written.append(rec.relative_path)`。
- `stage(ctx, written, skipped)`: `ctx.raw.get(theme=THEME, source=SOURCE, name=raw_name)` が None なら `skipped.append(f"{raw_name}: no raw")`。純粋変換 `parse(payload, ...) -> list[dict]` を呼び `ctx.tables.write_table("staged/<source>/<name>", rows)`、`written.append(table)`。
- `mart(ctx, written, skipped)`: staged を `read_table` し（無ければ `FileNotFoundError` を捕まえて skipped）、純粋変換 `build_mart(rows) -> list[dict]` を呼んで `ctx.tables.write_table("marts/<source>_<内容>", rows)`。
- 純粋変換（`parse` / `build_mart`）は I/O を持たず、入力が想定と違えば `ValueError` を投げる（fail-closed）。決定的（ソート・乱数なし・現在時刻なし）。
- `THEME` は `theme_essential_work_wages.pipeline` から import する（`from theme_essential_work_wages.pipeline import THEME`）。
- テストは `tests/test_<source>.py`。`FakeFetcher`／`InMemoryRawStore`／`InMemoryTableStore` を `Context` に詰め、`mod.fetch(ctx, [], [])` → `mod.stage(...)` → `mod.mart(...)` の状態を検証する。fixture は実データの**先頭数行＋検算に要る行だけ**を切った小さなファイルを `tests/fixtures/` に置く（実データ全体はコミットしない）。
- 列名は snake_case、共通キーは `iso3`・`year`（int）・`source`。職業は `occupation`（ソースの名称）＋`classification`（分類の版）。

## テーマ固有の規約
- **定義表は先にコミットする**: 職業 × {E, L, P, T} の対応表（`*_occupation_flags.csv`、出典列・判断理由列・境界フラグ列あり）は賃金データを stage する前に確定し、以後は変更履歴を design doc の「事後追加」に残す。
- **職業分類の断絶を隠さない**: 賃金構造基本統計調査は 2020 年に職種分類を改定した。`classification` 列でどの分類かを常に持ち、接続は対応表（手入力）経由のみ。接続できない職種は落とし、落とした旨を report に書く。
- **H3b の対照職業は固定**: 販売店員・警備員・ビル清掃員・調理師。結果を見てから入れ替えない。
- **個人データは扱わない**: 職業レベルの集計統計のみ（`design/overview.md` 非スコープ）。
- mart のテーブル名は `marts/<source>_<内容>`、横断パネルは `marts/essential_work_wages_panel`。
