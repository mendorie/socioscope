# themes/parliament-size
設計（問い・事前登録仮説 H1〜H6・指標・採用順）: `design/themes/parliament-size.md`。規約: root `CLAUDE.md`、`.claude/rules/themes.md`。
データソースの調査記録: `design/data-sources.md`（候補表の parliament-size 行、採用記録「IPU Parline API」「総務省 衆議院議員総選挙 結果調 Excel」「e-Stat 令和 2 年国勢調査 表 2-1」）。

## 構成
```
src/theme_parliament_size/
  pipeline.py   fetch / stage / mart（Port 経由。I/O はここだけ）。ソースごとに `# ---- <source>` ブロックを足す。
                `build_panel`: long 形式 mart（iso3, year, unit, metric, value, source）のソート・キー重複検査
                `_fetch/_stage/_mart_ipu`（`links.next` で 3＋2 ページ）、`_fetch/_stage/_mart_soumu`（選挙 × 表 の Excel）、
                `_fetch/_stage/_mart_estat`（国勢調査 xlsx 1 枚）。非 JSON／非 Excel（magic 不一致）は raw に入れない
  wiring.py     PIPELINE（entry point）。stage 関数の登録のみ
  ipu.py        IPU Parline API（JSON:API、鍵不要）: `url(kind, page)`/`raw_name`、`CHAMBER_ATTRS`/`COUNTRY_ATTRS`（採用属性）、
                `parse(payload, kind, page)`（属性ごとの時間付きレコードを long に。`{"type": 通貨, "value": 額}` は value_num＋unit、
                `[{"term": …}]` は `;` 結合。data 無し・type 不一致・value 無しは ValueError）、`has_next`、
                `build_mart`（議院 1 行、各属性の最新レコード、国の人口・OECD 加盟を結合。国が無い議院は ValueError）
  soumu.py      総務省 結果調 Excel: `ELECTIONS`（45〜51 回。`seats` = 法定定数、`exts` = 表ごとの拡張子の例外）/`KEYS`/`url`/`raw_name`/`magic`/`ext_of`/`rows_of`、
                `parse_electorate_smd`（47 都道府県、計で検算）、`parse_electorate_pr`（ブロック付き、ブロック計で検算）、
                `parse_pr_votes`（＜ブロック選挙区＞ごとの党派別得票、得票総数で検算）、`parse_pr_seats`（議席配分表の
                順位セルを数える。順位の列は党名と同じ列（50・51）か 1 列左（45〜49）。順位 1..S が埋まることで検算）、
                `parse_winners`（党派別 小選挙区／比例 当選人数、選挙ごとの法定定数で検算。2 行党名の連結、本人届出の空白小見出しに対応）、
                `build_electorate_mart`/`build_pr_mart`/`build_winners_mart`。`BLOCKS`（11 ブロック、「東京都」→「東京」）
  estat.py      e-Stat 国勢調査 2020 表 2-1 xlsx: `URL`/`RAW_NAME`、`workbook_rows`、`parse`（国籍総数／うち日本人 × 総数 × 都道府県、
                全国行で検算）、`build_mart`。人口推計 長期時系列 表 1（`LONGPOP_URL`、1920–2000）: `parse_longpop`、`build_longpop_mart`
  mof.py        財務省 令和 7 年度 一般会計予算（衆参修正後）PDF: `pdf_pages`（pypdf、AES を空パスワードで復号）、`parse`（所管別内訳の
                数値行を `ORGANS` の順に割り当て、主要行の合計 = 合計行で検算）、`build_mart`
  worldbank.py  World Bank WDI `NY.GDP.MKTP.CN`（名目 GDP、現地通貨、2005–2025）と `SP.POP.TOTL`（人口、1980–2025）: `URL`/`POP_URL`、
                `parse`（[meta, data]、ページ分割は ValueError）/`parse_population`/`build_mart`/`build_population_mart`
  parlgov.py    ParlGov 2024（Harvard Dataverse `view_election.tab`、CC0）: `URL`/`RAW_NAME`/`parse`（parliament 選挙 × 国 で 1 行、seats_total）/`build_mart`
  ukbills.py    UK Parliament Bills API: `url(page)`/`raw_name`/`has_next`（totalResults）/`parse`（法案 1 行、isAct なら Royal Assent 日を必須）/
                `origin_of`（billTypeId → government/member/other）/`build_mart`（成立法案のみ）
  fran.py       仏 国民議会 Dossiers législatifs zip（第 16・17 期）: `url(leg)`/`raw_name`/`is_law`/`parse`（ドシエ 1 行: 手続・提出種別 PRJL/PION・公布日）/
                `build_mart`（公布済みのみ、立法期をまたぐ uid は新しい方）
  clb.py        内閣法制局「法律案の提出・成立件数一覧」HTML: `parse`（html.parser で表を走査、「第 N 回（種別）」と
                「（継続 n 件） m 件」を読み、計 = 閣法 ＋ 議員立法 で検算）、`build_mart`（議員立法の成立シェア付き）
  jp_member_costs.csv   議員 1 人当たりの法定経費（歳費・調査研究広報滞在費・立法事務費・秘書給与の別表）。出典列あり、手入力
  jp_seats_history.csv  衆院・参院の定数の変遷 1890–2022（法令・衆議院 HP）。出典列あり、手入力
  apportion.py  配分の純粋関数: `dhondt`、`sainte_lague`（first_divisor=1.4 で修正サンラグ）、`highest_averages`、
                `adams`（切り上げ、各単位 1 以上、除数は二分探索）、`gallagher`、`threshold_share`（1 議席の最小得票率）
  analysis/     report 用スクリプト（決定的、1 report 1 ファイル）: a20261027_r1_ratio.py（H1・H1b・H1c、図 3 枚）、
                a20261027_r2_pr_blocks.py（H3・H3b・H3c・H4・H4b、図 3 枚。アダムズ方式で現行 176・289 を再現してから試算）、
                a20261027_r3_cost.py（H5・H5b、図 2 枚）、a20261027_r4_history.py（H6、図 2 枚）、a20261027_r5_roles.py（H2、図 2 枚）、
                a20261028_r6_pr_history.py（事後追加 H3d・H3e・H4c・H4d、7 選挙の比例試算と小選挙区の格差の下限、図 3 枚）、
                a20261028_r7_roles_gdp.py（事後追加 H2c・H5c、質問主意書と議会費の対 GDP 比、図 2 枚）、
                a20261028_r8_member_bills.py（事後追加 H2d、日英仏の議員立法シェア、図 1 枚）、
                a20261028_r9_seats_history.py（事後追加 H6b、ParlGov 1990– の定数変更 × 人口変化、図 1 枚。R4 の各国判定を上書き）
queries/        DuckDB 用 SQL（? バインド）
reports/        <yyyy-mm-dd>-<slug>.md ＋ figures/
tests/          conftest.py（実 API の形を写した合成ページ）＋ Fake による状態テスト。結果調・国勢調査は実ファイルの様式を縮約した合成行
```

## テーブル
| name | 粒度 | 列 |
|---|---|---|
| `staged/ipu/chamber_attributes` | 議院×属性×レコード（long） | kind(chambers), entity_id（JP-LC01 など）, attribute（`ipu.CHAMBER_ATTRS`）, seq, value（文字列）, value_num, unit（通貨など）, date_from, date_to, source(`ipu_parline`)。281 議院（2026-10-27 取得） |
| `staged/ipu/country_attributes` | 国×属性×レコード（long） | 同列、kind(countries), entity_id（JP など）, attribute（`ipu.COUNTRY_ATTRS`。population_in_thousands は 1950– 年次） |
| `marts/ipu_parliaments` | 議院 | iso3, country, region, subregion, oecd_member, chamber_id, chamber_type(lower/upper), chamber_name, electoral_system, electoral_subsystem, designation_mode, statutory_seats, statutory_seats_since, current_members, directly_elected, majoritarian_tier_seats, proportional_tier_seats, permanent_staff, staff_year, staff_combined_parl, chamber_budget, budget_currency, chamber_budget_ppp, budget_year, budget_combined_parl, basic_salary_ppp, salary_year, plenary_days, plenary_year, committees, written_questions, written_questions_year, members_in_government, members_in_government_pct, carries_out_inquiries, government_appointments, members_per_country, population_thousands, population_year, parliament_budget_pct_gov, source。281 行（OECD 38 か国 58 議院、2026-10-28 取得。既存列は 2026-10-27 取得分と同値） |
| `staged/soumu/electorate` | 選挙×層×都道府県 | election, election_date, tier(smd/pr), block（pr のみ）, pref, electorate, voters, source(`soumu_senkyo`) |
| `staged/soumu/pr_votes` | 選挙×ブロック×党派 | election, election_date, block, rank, party, votes, share_pct |
| `staged/soumu/pr_seats` | 選挙×ブロック×党派（議席 > 0） | election, election_date, block, party, seats |
| `staged/soumu/winners_by_party` | 選挙×党派 | election, election_date, party, smd_seats, pr_seats |
| `marts/jp_hr_electorate` | 選挙×都道府県 | iso3(JPN), election, election_date, pref, block, electorate_smd, voters_smd, electorate_pr, voters_pr, source。329 行（第 45〜51 回） |
| `marts/jp_hr_pr_results` | 選挙×ブロック×党派 | iso3, election, election_date, block, party, rank, votes, share_pct, seats（公式、名簿不足の移転込み、0 を含む）, block_seats, block_votes, source。710 行（第 45〜51 回） |
| `marts/jp_hr_seats_by_party` | 選挙×党派 | iso3, election, election_date, party（無所属・本人届出（政党等所属）を含む）, smd_seats, pr_seats, total_seats, source。77 行（第 45〜51 回） |
| `staged/estat/census2020_prefecture` | 都道府県 | pref_code, pref, population_total, population_japanese, source(`estat_census`) |
| `marts/jp_census2020_prefecture` | 都道府県 | iso3, year(2020), pref_code, pref, population_total, population_japanese, source。47 行 |
| `staged/estat/population_longterm` → `marts/jp_population_longterm` | 年 | iso3, year(1920–2000), population_total_thousands, population_japanese_thousands（1950–）, source。81 行 |
| `staged/mof/budget_by_organ` → `marts/jp_budget_by_organ` | 年度×段階×所管 | iso3, fy(2024/2025), stage(initial/revised), organ（皇室費・国会・…・予備費・合計。内閣府の内訳 2 行は in_total=false）, in_total, amount_100m_jpy, source。46 行 |
| `staged/clb/bill_counts` → `marts/jp_bill_counts` | 国会回次 | iso3, session(183–221), kind（常会／臨時会／特別会）, start_date, year, cabinet_submitted, cabinet_enacted, member_submitted, member_enacted, member_share_of_enacted, source。39 行 |
| `staged/worldbank/gdp_lcu` → `marts/wdi_gdp_lcu` | 経済体×年 | iso3, year(2005–2025), country, gdp_lcu（名目、現地通貨）, source(`worldbank_wdi`)。4,396 行 |
| `staged/worldbank/population` → `marts/wdi_population` | 経済体×年 | iso3, year(1980–2025), country, population, source。11,996 行 |
| `staged/parlgov/elections` → `marts/parlgov_elections` | 国×議会選挙 | iso3, year, election_date, election_id, seats_total（選挙時の実議席）, source(`parlgov`)。845 行・37 か国 |
| `staged/ukbills/bills` → `marts/uk_acts` | 法案 | staged: bill_id, title, bill_type_id, bill_type, origin, is_act, royal_assent_date, introduced_session_id（4,065 行）。mart は成立法案のみ: iso3(GBR), year, royal_assent_date, bill_id, title, bill_type_id, bill_type, origin, source。695 行 |
| `staged/fran/dossiers` → `marts/fr_laws` | 法律ドシエ | staged: uid, legislature, procedure, origin, promulgated, promulgation_date。mart は公布済みのみ: iso3(FRA), year, promulgation_date, uid, legislature, procedure, origin, source。297 行 |
| `marts/parliament_size_panel` | iso3×year×unit×metric×source（long） | **未作成**（行ができるまで書かない） |

## 状態
- ① IPU Parline（**CC BY-NC-SA 4.0**、非商用）fetch/stage/mart 実装済み。R1 report（H1 整合・H1b 整合・H1c 整合）: `reports/2026-10-27-r1-ratio.md`。
- ② 総務省 結果調 Excel（第 50・51 回。2026-10-28 に第 45〜49 回を追加）＋ ③ e-Stat 国勢調査 2020 実装済み。R2 report（H3・H3b・H3c 整合、H4・H4b 不支持）: `reports/2026-10-27-r2-pr-blocks.md`。
- ④ 財務省 予算書 PDF ＋ 法定額 CSV 実装済み。R3 report（H5 整合、H5b 整合）: `reports/2026-10-27-r3-cost.md`。
- ⑤ 定数の変遷 CSV ＋ e-Stat 長期人口 実装済み。R4 report（H6 日本は僅差で不支持、各国は整合）: `reports/2026-10-27-r4-history.md`。
- ⑥ 内閣法制局 法律案件数 実装済み。R5 report（H2 (a) 整合 ρ = −0.42、(b) 判定不能）: `reports/2026-10-27-r5-roles.md`。
- **総括（H1〜H6 を「支える／支えない／規範の選択」に整理）**: `reports/2026-10-27-summary-parliament-size.md`（R6・R7 の結果を 2026-10-28 に追記）。
- ⑦ 追加分析（2026-10-28、事後追加の仮説。`docs/specs/parliament-size-followup.md`）: 結果調を第 45〜49 回に拡張、IPU に役割の 5 属性を追加、WDI 名目 GDP を結線。R6（H3d 頑健・H3e 記述・H4c 整合・H4d 記述）: `reports/2026-10-28-r6-pr-history.md`。R7（H2c 不支持・H5c 整合）: `reports/2026-10-28-r7-roles-gdp.md`。
- ⑧ 追加分析 2 回目（2026-10-28 夕）: ParlGov（Dataverse）・WDI 人口・英 Bills API・仏 AN ドシエを結線。R8（H2d 不支持: 議員立法シェアは英 21.5% ≈ 日 21.8% < 仏 50.9%）: `reports/2026-10-28-r8-member-bills.md`。R9（H6b 不支持: 1990 年以降の定数変更率 × 人口変化率 r = 0.51。**R4 の「人口減少国で減らしたのは日本のみ」を撤回**）: `reports/2026-10-28-r9-seats-history.md`。
- 未着手: 独・米・韓の法案 API（鍵が要る）、第 42〜44 回の結果調（PDF のみ）、選挙区単位の有権者数（H4c の係数の検証）、仏 第 15 立法期以前（zip 無し）。

## テーマ固有の規約
- 「議員数」は定数（statutory）と現員（current）を列で分け、混ぜない。上院の選出方法（designation_mode）を注記できるよう議院単位で持つ。
- 配分方式（ドント・修正サンラグ・アダムズ）は `apportion.py` の純粋関数。試算の前に現行の配分（比例 176・小選挙区 289）を再現できることを検算する（R2 で実施、一致）。
- 比例の機械的試算は「票が同じなら」の目安。report に必ず「行動の変化は織り込まない」と書く。公式議席は名簿不足の移転を含むため、基準線は純ドントとし公式値を併記する。
- 一票の格差は 有権者数（選挙時）と 国勢調査人口 の両方で出し、どちらかを明記する。
- 推進・反対のどちらにも都合の良い指標だけを選ばない。事前登録した H1〜H6 をすべて報告する。
- IPU Parline 由来のデータは非商用（CC BY-NC-SA 4.0）。総務省・e-Stat 由来は政府標準利用規約 2.0（出典表記）。
