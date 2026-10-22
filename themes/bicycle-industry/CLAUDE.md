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
                `url(year)`、`parse(payload, year)`（期間・相手国不一致は ValueError、未知の報告国・品目は skipped）、`build_mart`。
                H8: `ORIGIN_REPORTERS`/`PARTNERS`（中国 156・台湾 490）/`ORIGIN_YEARS` 2015–2024、`origin_url`、`parse(..., partners=True)`、
                `build_origin_mart`（WLD と OTH = 世界 − 中国 − 台湾 を追加、キー重複は ValueError）
  prices.py     Eurostat HICP CP0711/0712/0713（JSON-stat、`hicp_url`/`parse_hicp`）と US BLS CPI（`BLS_SERIES`×`BLS_RANGES`、
                `bls_url`/`parse_bls`。"-" は skipped）、`build_mart`（2 ソースを 1 つの long 表に、キー重複は ValueError）
  shimano.py    シマノ 有報 PDF（EDINET、`DOCS` FY2014–2025 → docID）: `pdf_text`（pypdf）、`parse_pages`（当期・前期の
                セグメント売上・利益と地域別売上を正規表現で読む、fail-closed）、`build_mart`（その年の有報を優先、翌年と食い違えば `restated_next_year`）
  cpi.py        総務省 CPI 2025 年基準 品目別 長期時系列 CSV（年・月、CP932）: `FILES`（statInfId）、`ITEMS`（符号 → キー 8 品目）、
                `parse`（符号で列選択、ヘッダ・符号欠落・非数値は ValueError）、`build_mart`
  census.py     経済センサス（R3）小売業 産業編 第 1 表 xlsx: `URL`/`RAW_NAME`、`INDUSTRIES`（5 業種）、`METRICS`（6 指標）、
                `SURVEY_OF_YEAR`（商業統計／経済センサス）、`parse`（全国行を long に、業種欠落は ValueError）、`build_mart`
  shakai.py     総務省 社会生活基本調査 時系列統計表 xlsx: `URL`/`RAW_NAME`、`SEXES`/`AGES`、`parse`（スポーツ名行 × 西暦行で列を組み、
                総数／男／女 × 年齢階級を long に。必須種目・シート・行欠落は ValueError）、`build_mart`
  tw_mops.py    台湾 MOPS 月次営業収入 JSON API（POST）: `COMPANIES`（9921/9914/5306/8933）、`body`/`raw_name`/`requests`、
                `parse`（`[ラベル, 値]` 配列を辞書に、未収録月は行なし、yymm 不一致は ValueError）、`build_mart`
  merida.py     Merida 連結財務報告 PDF（Q4、ADR 0006 の例外で `merida-cdn.m-c-g.net` から）: `DOCS` FY2023–2025 → ファイル名、`url`/`raw_name`、
                `pdf_text`、`parse_pages`（売上・持分法損益・SBC 帳簿価額・関連企業合計・SBC 集団向け売上を当期・前期で読む、fail-closed）、
                `build_mart`（当年の報告を優先、翌年と食い違えば `restated_next_year`）
  halfords.py   Halfords 通期決算発表 PDF（FY2015–2026）: `DOCS`/`url`/`raw_name`、`parse_pages`（Retail 売上・Cycling 構成比・Cycling £m を
                年ごとの様式（3 種の正規表現）で読む、53 週は 52 週列、fail-closed）、`build_mart`
  accell.py     Accell 年報 PDF（Wayback `id_`、2017・2021）: `DOCS`（ts, 原 URL）、`parse_pages`（8 年表・5 年表）、`build_mart`（`restated_later`）
  jbpi.py       JBPI 国内向自転車生産輸入統計 12 月分（`DOMESTIC_DOCS` 版の最終年 → URL、3 版で 2021–2025）と POS 年間総括
                （`POS_DOCS`）: `parse_domestic_pages`（行ラベルの出現順で品目、年見出し・生産合計で検算）、`build_domestic_mart`
                （新しい版を優先、`restated_from`、単価）、`parse_pos_pages`（14 数値＋月の行、分類合計で検算）、`build_pos_mart`
  pipeline.py   （追加）`PdfSource` ＋ `_fetch/_stage/_mart_pdf_source`: PDF 1 文書 1 キーのソースの共通結線（HALFORDS / ACCELL / JBPI_DOMESTIC / JBPI_POS）
  comtrade.py   （追加）H9: `taiwan_url`/`parse_taiwan`/`build_taiwan_mart`（reporter 490 の輸出、仕向地別 ＋ OTH）
  <source>.py   （予定）edgar.py Fox Factory（要 SOCIOSCOPE_SEC_CONTACT）/ customs.py 貿易統計 CSV / kakei.py 家計調査（支出金額のみ）/
                shimano.py EDINET PDF / census_jp.py 経済センサス
  analysis/     report 用スクリプト（決定的、1 report 1 ファイル）: a20261022_r1_volume_price.py（H1 判定、H2/H3/H4/H6 の記述、図 5 枚）、a20261022_r2_bullwhip_price.py（H3・H4 判定、図 2 枚）、a20261022_r3_retail.py（H5 判定、図 2 枚）、a20261022_r4_pullforward_origin.py（H7 先食い・H8 原産国別、図 5 枚）、a20261022_r6_participation.py（H11 高齢化・非補充、図 2 枚）、a20261022_r5_world_cycle.py（H9 台湾輸出・H10 在庫サイクルの位相、図 3 枚）、a20261022_r7_specialized.py（H14 Specialized 持分法 ＋ 補足 Halfords・Accell、図 3 枚）、a20261022_r8_segments.py（H2 車種別 台数・単価 ＋ POS、図 2 枚）
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
| `staged/comtrade/bicycle_trade_origin` | iso3×year×hs×partner | 世界計と同列 ＋ partner(CHN/TWN)。輸入のみ、5 か国 × 2015–2024 |
| `marts/bicycle_trade_by_origin` | 〃 ＋ WLD/OTH | partner ∈ {CHN, TWN, WLD, OTH}。OTH の qty/value は両相手国がそろう年のみ。560 行（2026-10-22 取得） |
| `staged/eurostat/hicp_cp071x` | geo×coicop×month | iso3（EU27/EA20 は疑似コード）, geo, series(cars/motorcycles/bicycles), series_id(CP0711/…), period(YYYY-MM), year, month, value, base("2015=100"), source(`eurostat_hicp`) |
| `staged/bls/cpi_vehicles` | series×month | 同列。iso3=USA, geo=US, series(sports_vehicles_incl_bicycles/new_vehicles), series_id(CUUR0000SERC01/SETA01), base("1982-84=100"), source(`bls_cpi`) |
| `marts/price_indices` | source×geo×series_id×period | 両 staged を結合。キー順ソート・一意（8,210 行: HICP 2005-01–2025-12 13 geo、BLS 2006-01–2026-09、2026-10-22 取得）。基準年が違うので比較は再基準化して行う |
| `staged/edinet/shimano_segments` | fy×table×key×metric×doc_fy（long） | fy, doc_fy, docid, table(segment/region), key（bicycle_components / fishing_tackle / other ／ japan / north_america / europe / asia / other_regions / total）, metric(sales/profit), value_mn_jpy, source(`edinet_shimano`)。12 有報 × 当期・前期 |
| `marts/shimano_segments` | fy×table×key×metric | iso3(JPN), company(Shimano), fy, table, key, metric, value_mn_jpy, restated_next_year, docid, source。156 行（FY2013–2025、2026-10-22 取得、食い違い 0） |
| `staged/estat/cpi_items` | item_code×freq×period | item_code, item（all_items / bicycles / bicycle_a / bicycle_b / car_kei / car_small / car_standard_a / car_standard_b）, period(YYYY or YYYY-MM), freq(annual/monthly), year, month, value, base("2025=100"), source(`estat_cpi`) |
| `marts/jp_cpi_vehicles` | 〃 | iso3(JPN) ＋ staged と同列。4,393 行（年 1970–2025、月 1970-01–2026-08、2026-10-22 取得） |
| `staged/estat/census_retail` | industry×year×metric | industry_label, industry（retail_total / auto_retail / motorcycle_retail / bicycle_retail / machinery_retail_other）, year（1994–2021 の 10 時点）, survey, metric（establishments / establishments_corporate / establishments_individual / persons_engaged / annual_sales_mn_jpy / sales_floor_m2）, value（`-`/`x` は NULL）, source(`estat_census`) |
| `marts/jp_retail_census` | 〃 | iso3(JPN) ＋ staged と同列。300 行（2026-10-22 取得） |
| `staged/estat/shakai_sports_rates` | sport×sex×age×year | sport（23 種目、日本語名）, sex(total/male/female), age（total / 10_14 / … / 70_plus / r_15_plus / r_65_plus）, year（1986–2021 の 8 時点）, rate_pct（過去 1 年の行動者率 %）, source(`estat_shakai`)。`...` は行なし |
| `marts/jp_sports_participation` | 〃 | iso3(JPN) ＋ staged と同列。5,890 行（2026-10-22 取得） |
| `staged/comtrade/taiwan_exports` | year×hs×partner | iso3(TWN), year, flow(export), hs(8712/871160), product, partner(JPN/USA/DEU/NLD/GBR/WLD), qty, net_wgt_kg, value_usd, source |
| `marts/taiwan_bicycle_exports` | 〃 ＋ OTH | 126 行（2015–2024、2026-10-22 取得） |
| `staged/tw_mops/monthly_revenue` | company_id×period | company_id, company(giant/merida/kmc/ideal_bike), year, month, period(YYYY-MM), revenue_ntd_k, revenue_prev_year_ntd_k, ytd_ntd_k, source(`tw_mops`) |
| `marts/tw_bicycle_monthly_revenue` | 〃 | iso3(TWN) ＋ staged と同列。612 行（2014-01–2026-09、2026-10-22 取得） |
| `staged/merida/specialized_equity` | fy×metric×doc_fy（long） | fy, doc_fy, metric（revenue / equity_method_share / sbc_carrying_amount / associates_carrying_total / sbc_group_sales）, value_ntd_k, source(`merida_ir`)。3 報告 × 当期・前期 |
| `marts/merida_specialized` | fy×metric | iso3(TWN), company(Merida), fy, metric, value_ntd_k, restated_next_year, doc_fy, source。20 行（FY2022–2025、2026-10-22 取得、食い違い 0） |
| `staged/halfords/cycling_revenue` | fy×metric | fy, doc_fy, metric（retail_revenue / cycling_mix / cycling_revenue）, value, unit（GBP_m / pct_of_retail）, derived（bool）, source(`halfords_ir`) |
| `marts/halfords_cycling` | 〃 | iso3(GBR), company(Halfords) ＋ staged と同列。34 行（FY2015–2026、2026-10-22 取得） |
| `staged/accell/net_turnover` | year×report_year | year, report_year(2017/2021), metric(net_turnover), value_eur_m, source(`accell_ar`) |
| `marts/accell_turnover` | year | iso3(NLD), company(Accell) ＋ staged と同列 ＋ restated_later。12 行（2010–2021、2026-10-22 取得） |
| `staged/jbpi/domestic_by_type` | year×category×flow×edition | year, edition, category（total / light / mtb_cross / mini / infant / kids / other_sports_geared / eassist / other）, flow(production/import), qty, value_k_jpy, source(`jbpi_domestic`) |
| `marts/jp_bicycle_by_type` | year×category×flow | iso3(JPN) ＋ staged と同列 ＋ restated_from, unit_price_jpy。50 行（2021–2025、2026-10-22 取得、食い違い 0） |
| `staged/jbpi/pos_monthly` | period×category | period(YYYY-MM), year, month, category（total / other / eassist / kids / infant / sports / light）, qty, value_jpy（税込）, source(`jbpi_pos`) |
| `marts/jp_pos_sales` | 〃 | iso3(JPN) ＋ staged と同列 ＋ avg_price_jpy。126 行（2024-07–2025-12、2026-10-22 取得） |
| `marts/bicycle_industry_panel` | iso3×year×product×metric×source（long） | iso3, year, product（bicycle_total / e_assist / sports / city / parts / car_kei / car_registered / moto_lt125 / moto_126_250 / moto_251p …）, metric（units / value_jpy / value_usd / price_index / avg_price_jpy …）, value, source。**未作成**（行が 0 の Parquet は列を持たず DuckDB が読めないため、行ができるまで書かない） |

## テーマ固有の規約
- 「スポーツ車」の定義はソースごとに違う（JBPI 車種分類・POS 小売分類）。`product` に出典別の値を使い、混ぜない。
- 電動アシスト車の輸入（HS 8711.60）は原付・電動バイクを含む。国内生産（生産動態統計）を主とする。
- 協会系ソース（JBPI・JAMA・自販連・全軽自協・JAIA）は利用規約がない。出典明記・raw 非コミット。
- ボット UA を拒否するサイト（METI・shimano.com・JBPI）は fetcher 側で UA を設定し、HTML が返ったら fail-closed。
