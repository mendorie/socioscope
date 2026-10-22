# themes/bicycle-industry
設計（問い・事前登録仮説 H1〜H6・指標・採用順）: `design/themes/bicycle-industry.md`。規約: root `CLAUDE.md`、`.claude/rules/themes.md`。

## 構成
```
src/theme_bicycle_industry/
  pipeline.py   fetch / stage / mart（Port 経由。I/O はここだけ）。ソースごとに `# ---- <source>` ブロックを足す。
                `build_panel`: long 形式 mart（iso3, year, product, metric, value, source）のソート・キー重複検査
  wiring.py     PIPELINE（entry point）。stage 関数の登録のみ
  meti.py       経産省 生産動態統計 年報 xlsx（2021–2025）: `YEARS`/`annual_url`/`raw_name`、`parse(payload, report_year)`
                （「実数表」の時間軸コード→ Period、2430 自転車・2400 自動車の行を long に。品目は NFKC 正規化名で同定、
                必須品目欠落・ヘッダ不一致・非 xlsx は ValueError）、`build_mart`（mapped 系列のみ、最新 report_year 優先、
                月次 12 本そろう年は `cy_from_months` 年計を追加、キー重複は ValueError）
  comtrade.py   UN Comtrade preview API: `REPORTERS`（9 か国、TWN=490）/`COMMODITIES`（8712/871160/8714）/`YEARS` 2010–2024、
                `url(year)`、`parse(payload, year)`（期間・相手国不一致は ValueError、未知の報告国・品目は skipped）、`build_mart`
  prices.py     Eurostat HICP CP0711/0712/0713（JSON-stat、`hicp_url`/`parse_hicp`）と US BLS CPI（`BLS_SERIES`×`BLS_RANGES`、
                `bls_url`/`parse_bls`。"-" は skipped）、`build_mart`（2 ソースを 1 つの long 表に、キー重複は ValueError）
  shimano.py    シマノ 有報 PDF（EDINET、`DOCS` FY2014–2025 → docID）: `pdf_text`（pypdf）、`parse_pages`（当期・前期の
                セグメント売上・利益と地域別売上を正規表現で読む、fail-closed）、`build_mart`（その年の有報を優先、翌年と食い違えば `restated_next_year`）
  <source>.py   （予定）customs.py 貿易統計 CSV / cpi.py・kakei.py e-Stat Excel /
                jbpi.py JBPI PDF / shimano.py EDINET PDF / census_jp.py 経済センサス
  analysis/     report 用スクリプト（決定的、1 report 1 ファイル）: a20261022_r1_volume_price.py（H1 判定、H2/H3/H4/H6 の記述、図 5 枚）
queries/        DuckDB 用 SQL（? バインド）
reports/        <yyyy-mm-dd>-<slug>.md ＋ figures/
tests/          fixtures/（実レスポンスの縮約）＋ Fake による状態テスト
```

## テーブル
| name | 粒度 | 列 |
|---|---|---|
| `staged/meti/seidou_annual` | survey×item×measure×period×report_year（long） | survey_no, industry(bicycle/motor_vehicle), item_no, item_code, product_ja, product_en, product（`meti.PRODUCTS` のキー、未知は NULL）, measure_ja, measure（`meti.MEASURES`、未知は NULL）, unit, period_type(month/cy/fy/quarter), period, year, value, value_flag(""/X/***/missing), report_year, source(`meti_seidou`)。5 年報を結合（改定前の値も残る） |
| `marts/meti_production` | industry×product×measure×period_type×period | iso3(JPN), industry, product（bicycle_light / bicycle_e_assist / bicycle_other / wheelchair_manual / wheelchair_electric / car_kei / car_small / car_standard / moto_le50 / moto_51_125 / moto_126_250 / moto_gt250）, measure（production_qty / production_value / receipts_qty / sales_qty / sales_value / other_shipments_qty / inventory_qty）, unit, period_type（＋ `cy_from_months`）, period, year, value, value_flag, report_year, source。7,332 行（2026-10-22 取得: 月次 2021-01–2025-12、暦年 2017–2023、年計 2021–2025） |
| `staged/comtrade/bicycle_trade` | iso3×year×flow×hs | iso3, reporter_code, year, flow(import/export), hs(8712/871160/8714), product(bicycle_complete/ebike_motor_only/bicycle_parts), qty（台、無ければ NULL）, qty_unit_code, net_wgt_kg, value_usd, source(`un_comtrade`) |
| `marts/bicycle_trade` | 〃 | staged と同列。`iso3, year, flow, hs` でソート・一意（608 行、9 か国 × 2010–2024、2026-10-22 取得） |
| `staged/eurostat/hicp_cp071x` | geo×coicop×month | iso3（EU27/EA20 は疑似コード）, geo, series(cars/motorcycles/bicycles), series_id(CP0711/…), period(YYYY-MM), year, month, value, base("2015=100"), source(`eurostat_hicp`) |
| `staged/bls/cpi_vehicles` | series×month | 同列。iso3=USA, geo=US, series(sports_vehicles_incl_bicycles/new_vehicles), series_id(CUUR0000SERC01/SETA01), base("1982-84=100"), source(`bls_cpi`) |
| `marts/price_indices` | source×geo×series_id×period | 両 staged を結合。キー順ソート・一意（8,210 行: HICP 2005-01–2025-12 13 geo、BLS 2006-01–2026-09、2026-10-22 取得）。基準年が違うので比較は再基準化して行う |
| `staged/edinet/shimano_segments` | fy×table×key×metric×doc_fy（long） | fy, doc_fy, docid, table(segment/region), key（bicycle_components / fishing_tackle / other ／ japan / north_america / europe / asia / other_regions / total）, metric(sales/profit), value_mn_jpy, source(`edinet_shimano`)。12 有報 × 当期・前期 |
| `marts/shimano_segments` | fy×table×key×metric | iso3(JPN), company(Shimano), fy, table, key, metric, value_mn_jpy, restated_next_year, docid, source。156 行（FY2013–2025、2026-10-22 取得、食い違い 0） |
| `marts/bicycle_industry_panel` | iso3×year×product×metric×source（long） | iso3, year, product（bicycle_total / e_assist / sports / city / parts / car_kei / car_registered / moto_lt125 / moto_126_250 / moto_251p …）, metric（units / value_jpy / value_usd / price_index / avg_price_jpy …）, value, source。**未作成**（行が 0 の Parquet は列を持たず DuckDB が読めないため、行ができるまで書かない） |

## テーマ固有の規約
- 「スポーツ車」の定義はソースごとに違う（JBPI 車種分類・POS 小売分類）。`product` に出典別の値を使い、混ぜない。
- 電動アシスト車の輸入（HS 8711.60）は原付・電動バイクを含む。国内生産（生産動態統計）を主とする。
- 協会系ソース（JBPI・JAMA・自販連・全軽自協・JAIA）は利用規約がない。出典明記・raw 非コミット。
- ボット UA を拒否するサイト（METI・shimano.com・JBPI）は fetcher 側で UA を設定し、HTML が返ったら fail-closed。
