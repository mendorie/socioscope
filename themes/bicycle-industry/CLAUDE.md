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
  <source>.py   （予定）customs.py 貿易統計 CSV / cpi.py・kakei.py e-Stat Excel /
                jbpi.py JBPI PDF / shimano.py EDINET PDF / comtrade.py / hicp.py / bls.py / census_jp.py 経済センサス
queries/        DuckDB 用 SQL（? バインド）
reports/        <yyyy-mm-dd>-<slug>.md ＋ figures/
tests/          fixtures/（実レスポンスの縮約）＋ Fake による状態テスト
```

## テーブル
| name | 粒度 | 列 |
|---|---|---|
| `staged/meti/seidou_annual` | survey×item×measure×period×report_year（long） | survey_no, industry(bicycle/motor_vehicle), item_no, item_code, product_ja, product_en, product（`meti.PRODUCTS` のキー、未知は NULL）, measure_ja, measure（`meti.MEASURES`、未知は NULL）, unit, period_type(month/cy/fy/quarter), period, year, value, value_flag(""/X/***/missing), report_year, source(`meti_seidou`)。5 年報を結合（改定前の値も残る） |
| `marts/meti_production` | industry×product×measure×period_type×period | iso3(JPN), industry, product（bicycle_light / bicycle_e_assist / bicycle_other / wheelchair_manual / wheelchair_electric / car_kei / car_small / car_standard / moto_le50 / moto_51_125 / moto_126_250 / moto_gt250）, measure（production_qty / production_value / receipts_qty / sales_qty / sales_value / other_shipments_qty / inventory_qty）, unit, period_type（＋ `cy_from_months`）, period, year, value, value_flag, report_year, source。7,332 行（2026-10-22 取得: 月次 2021-01–2025-12、暦年 2017–2023、年計 2021–2025） |
| `marts/bicycle_industry_panel` | iso3×year×product×metric×source（long） | iso3, year, product（bicycle_total / e_assist / sports / city / parts / car_kei / car_registered / moto_lt125 / moto_126_250 / moto_251p …）, metric（units / value_jpy / value_usd / price_index / avg_price_jpy …）, value, source。現在は空 |

## テーマ固有の規約
- 「スポーツ車」の定義はソースごとに違う（JBPI 車種分類・POS 小売分類）。`product` に出典別の値を使い、混ぜない。
- 電動アシスト車の輸入（HS 8711.60）は原付・電動バイクを含む。国内生産（生産動態統計）を主とする。
- 協会系ソース（JBPI・JAMA・自販連・全軽自協・JAIA）は利用規約がない。出典明記・raw 非コミット。
- ボット UA を拒否するサイト（METI・shimano.com・JBPI）は fetcher 側で UA を設定し、HTML が返ったら fail-closed。
