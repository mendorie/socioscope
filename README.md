# socioscope

グローバル／日本国内の公開統計・公開情報を収集・構造化し、社会学的な分析と因果推論を行うモノレポ。

## テーマ
| slug | 問い | 状態 |
|---|---|---|
| `wealth-population-distribution` | 戦後、資本主義の進展とともに富の偏りは極端化しているのか（世界各国・日本） | 分析中（WID.world 取得〜mart 実装済み（46 か国）。H1 report: `themes/wealth-population-distribution/reports/2026-10-04-h1-ushape.md`。H2 用に OECD SDMX（最高税率・社会支出・税収）fetch〜mart 実装済み（OECD 38）。H2 report（限定・関連のみ）: `.../2026-10-04-h2-institutions.md`。**総括（一般向け・日本語）**: `.../2026-10-05-summary-wealth-population-distribution.md`） |
| `growth-fertility` | 経済成長と出生率の関係は国間・国内（所得階層）でフラクタルか | H1〜H3b report 済み（`themes/growth-fertility/reports/2026-10-04-h1-income-tfr.md`, `...-h2-growth-shocks.md`, `...-h3-jp-income-class.md`, `...-h3b-age-adjusted.md`）。**総括（一般読者向け・日本語・図 13 枚）**: `themes/growth-fertility/reports/2026-10-05-summary-growth-fertility.md`。データ: World Bank WDI、e-Stat 国民生活基礎調査・就業構造基本調査 fetch〜mart 実装済み |
| `bicycle-industry` | 日本および世界の自転車産業はどのような状況か（実用層と趣味層の分化、部品供給、小売構造。自動車・二輪との対比） | 設計済み（`design/themes/bicycle-industry.md`、H1〜H6 事前登録、2026-10-22）。データソース調査済み（`design/data-sources.md`）。①生産動態統計（自転車・自動車・二輪、2017–2025）、④UN Comtrade（9 か国 2010–2024）、⑤Eurostat HICP・BLS CPI、⑦シマノ 有報（FY2013–2025）、③総務省 CPI 品目別（自転車 A/B・乗用車）、⑧経済センサス 自転車小売業（1994–2021）fetch〜mart 実装済み（`marts/meti_production`, `bicycle_trade`, `price_indices`, `shimano_segments`, `jp_cpi_vehicles`, `jp_retail_census`）。R1 report（H1 不支持: 台数はコロナ前を割り込む）: `themes/bicycle-industry/reports/2026-10-22-r1-volume-price.md`。R2 report（H3 不支持: 部品の落ち幅 ÷ 完成車 1.15、H4 不支持: 高価格帯の方が上がった）: `.../2026-10-22-r2-bullwhip-price.md`。R3 report（H5 (a) 整合・定義差込み、(b) 整合。個人店の減少は小売業全体に共通）: `.../2026-10-22-r3-retail.md`。R4 report（H7 先食い: 6 か国合計は整合だが水準は 0.79 の新常態、H8 台湾産単価は上昇で不支持、中国部品シェア +4.99pt 中間）: `.../2026-10-22-r4-pullforward-origin.md`。R6 report（H11 高齢化・非補充は不支持: サイクリング行動者率は 20 代で上昇、60 代で低下）: `.../2026-10-22-r6-participation.md`。R5 report（H9 台湾輸出は不支持・代理として弱い、H10 部品 → 完成車 の位相は整合、完成車の売上は 2026 年も 2019 年末を下回る）: `.../2026-10-22-r5-world-cycle.md`。R7 report（H14 Specialized は整合: Merida の持分法損益は FY2023–24 損失、FY2025 は FY2022 の 15%。SBC 向け売上 −42% vs 全体 −28%。ADR 0006。補足: Halfords Cycling 売上は特需後にコロナ前の 0.94 倍、Accell 2010–2021）: `.../2026-10-22-r7-specialized.md` |

## セットアップ
```bash
make sync              # uv sync --all-packages（venv は `venv/`、`.venv` は symlink。ADR 0005）
cp .env.example .env   # ANTHROPIC_API_KEY（LLM 構造化を使う場合のみ）
make check             # lint / type / test
make doctor            # import できない時の診断
```

## 使い方
```bash
uv run socioscope themes                      # 登録テーマ一覧
uv run socioscope run growth-fertility fetch  # 取得（data/raw + manifest）
uv run socioscope run growth-fertility stage  # 正規化 → data/staged/*.parquet
uv run socioscope run growth-fertility mart   # 分析用テーブル → data/marts/*.parquet
uv run socioscope db build                    # Parquet から socioscope.duckdb を再生成
uv run socioscope db query "select * from marts.growth_fertility_panel limit 5"
```

## レイアウト
```
packages/core/      共有ライブラリ（取得・来歴・LLM 構造化・Parquet/DuckDB・CLI）
themes/<slug>/      テーマごとのパイプライン・SQL・ノートブック・レポート
data/               raw（gitignore）/ staged・marts（Parquet, git 管理）/ llm_cache
design/, docs/      設計・ADR・spec・方法論
.claude/            Claude Code ハーネス（agents / skills / rules / hooks）
```
設計の詳細は `CLAUDE.md` と `design/overview.md`、決定は `docs/adrs/` を参照。

## トラブルシュート
- `ModuleNotFoundError: socioscope_core`（`uv run python -v -c pass 2>&1 | grep pth` に `Skipping hidden .pth file`）: macOS で `~/Desktop`・`~/Documents` が iCloud Drive 同期の対象だと、ドット始まりの項目（`.venv` を含む）とその配下に `UF_HIDDEN` が付き、Python 3.13 は hidden な `.pth` を無視する。本リポジトリは venv を **`venv/`（ドット名でない）** に置くことで回避している（ADR 0005）。`make doctor` で診断、`make sync` で復旧。Claude Code 外の素の `uv run` も `.venv -> venv` symlink 経由で同じ環境を使う。実体の `.venv/` が残っている場合は `make sync` が symlink に置き換える。根本的には iCloud 同期外（例 `~/code`）にリポジトリを置くのが最善。

## ライセンス
- **コード・ドキュメント**: MIT（`LICENSE`）。
- **データ（`data/staged`, `data/marts`）**: 各出典のライセンスに従う派生物で、MIT の対象外。出典と条件は `design/data-sources.md` と `data/raw/manifest.jsonl` の `license` 列を正とする。
  - World Bank WDI 由来: CC BY 4.0（出典表記）。
  - e-Stat（国民生活基礎調査）由来: 政府標準利用規約（第2.0版）、CC BY 4.0 互換。出典表記必須（「出典：政府統計の総合窓口(e-Stat)」、加工した旨を記載）。
  - WID.world 由来: **CC BY-NC-SA 4.0**（出典表記・非商用・同一ライセンス継承）。本プロジェクトは非商用の研究目的に限る。
  - OECD（SDMX: Tax Database / SOCX / Revenue Statistics）由来: OECD Terms & Conditions（2024-07-01 改定、出典表示で自由利用。OECD 発行物は CC BY 4.0）。出典表記「OECD (2026), <dataset>, https://sdmx.oecd.org (accessed on 2026-10-04)」。`marts/wealth_institutions_panel` は WID と OECD の結合なので WID の NC 条件を継承する。
