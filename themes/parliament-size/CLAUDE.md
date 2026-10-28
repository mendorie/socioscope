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
  worldbank.py  World Bank WDI `NY.GDP.MKTP.CN`（名目 GDP、現地通貨、2005–2025）、`SP.POP.TOTL`（人口、1980–2025）、`NY.GDP.PCAP.CN`（1 人当たり GDP）: `URL`/`POP_URL`/`GDP_PCAP_URL`、
                `parse`（[meta, data]、ページ分割は ValueError）/`parse_population`/`build_mart`/`build_population_mart`
  parlgov.py    ParlGov 2024（Harvard Dataverse `view_election.tab`、CC0）: `URL`/`RAW_NAME`/`parse`（parliament 選挙 × 国 で 1 行、seats_total）/`build_mart`
  ukbills.py    UK Parliament Bills API: `url(page)`/`raw_name`/`has_next`（totalResults）/`parse`（法案 1 行、isAct なら Royal Assent 日を必須）/
                `origin_of`（billTypeId → government/member/other）/`build_mart`（成立法案のみ）
  fran.py       仏 国民議会 Dossiers législatifs zip（第 16・17 期）: `url(leg)`/`raw_name`/`is_law`/`parse`（ドシエ 1 行: 手続・提出種別 PRJL/PION・公布日）/
                `build_mart`（公布済みのみ、立法期をまたぐ uid は新しい方）
  ilostat.py    ILOSTAT（鍵不要）: `ECO_URL`（ISIC O ＋ 総数）/`INS_URL`（公的部門）/`EAR_URL`（平均月収 CUR_TYPE_LCU）/`parse`（JSON 配列 → 国×年×指標 long、
                採用 classif1 のみ）/`parse_earnings`/`build_mart`（重複キーは ValueError）
  ipss.py       IPSS 地域別将来推計人口（令和 5 年推計）結果表 1 xlsx: `URL`/`RAW_NAME`/`workbook_rows`/`parse`（都道府県 47 × 2020–2050、2020 年合計を国勢調査で検算）/`build_mart`
  camera.py     イタリア下院 dati.camera.it SPARQL: `LAWS_URL`/`SITTINGS_URL`（集計クエリ）/`parse_laws`/`parse_sittings`/`build_mart`（年×指標 long）
  jp_committee_seats.csv  衆院 常任委員会 17 の委員定数（衆議院規則 第 92 条）。出典列あり、手入力
  intl_thresholds.csv     OECD 比例・混合制 29 か国の法定阻止条項（各国選挙法・ACE）。出典列あり、手入力
  federal_states.csv      OECD の連邦制 8 か国のフラグ（Forum of Federations）。出典列あり、手入力
  seat_reduction_proposals.csv  OECD 15 か国の 2000 年以降の下院定数削減の提案・実現（年、状態、定数、提案主体、formal、理由）。出典列あり、手入力
  oecd.py       OECD Data Explorer SDMX-JSON（Government at a Glance 2025）: `Spec`（MEASURE → (metric, 単位)、次元フィルタ、指標別の上書き）、
                `URL`/`PF_SPEC`（公的財政: GE・GR の % GDP、GE_POP の USD PPP/人、S13）、`TRUST_URL`/`TRUST_SPEC`（信頼調査: TRUST_LE・TRUST_NG は
                尺度 HMH、TRUST_PVGA は LIK）、`parse`（観測キーを次元の値に戻し ISO3 の国のみ long に）/`parse_trust`/`build_mart`（重複キーは ValueError）
  eurobarometer.py  Standard Eurobarometer Volume A（data.europa.eu、13 波）: `WAVES`（波・調査時期・URL・raw 名）/`is_magic`（xlsx/zip か xls）/
                `parse_table`（「Tend to trust」の行を % に揃える）/`parse(payload, wave)`（国の議会への信頼の表を long に）/`build_mart`
  kokkai.py     国会会議録検索システム API: `url(year, page)`/`raw_name`/`has_next`（nextRecordPosition）/`parse`（会議 1 行、衆議院のみ）/
                `build_mart`（年 × plenary_days／committee_meetings／committee_days／sitting_days）
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
                a20261028_r9_seats_history.py（事後追加 H6b、ParlGov 1990– の定数変更 × 人口変化、図 1 枚。R4 の各国判定を上書き）、
                a20261028_r10_bureaucracy.py（事後追加 H2e、公務就業者 × 議員数、図 1 枚）、
                a20261029_r11_alternatives.py（事後追加 H8・H9・H10、修正サンラグ単独・職員増員の費用・委員会兼任率）、
                a20261029_r12_future_disparity.py（事後追加 H11、IPSS 推計での格差、図 1 枚）、
                a20261029_r13_after_cuts.py（事後追加 H7、イタリア・ハンガリーの削減前後）、
                a20261029_r14_pay_and_workload.py（事後追加 H12・H13、基本給の相対水準と稼働日数、図 2 枚）、
                a20261029_r15_small_parties.py（事後追加 H14a〜c、小政党の入口機能・阻止条項・泡沫政党の票）、
                a20261029_r16_government_size.py（番外編 H15a〜d、議会の大きさ × 一般政府支出比、図 2 枚）、
                a20261030_r17_system_oversight_trust.py（番外編 H16a〜c、選挙制度の層別・議員 1 人当たり政府支出・立法府への信頼、図 3 枚）、
                a20261030_r18_distrust_and_cuts.py（番外編 H17a〜c、削減提案の手入力表 × 信頼、Eurobarometer でイタリアの前後、図 2 枚）
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
| `staged/ilostat/emp_eco` → `marts/ilo_emp_public_admin` | 国×年×指標（long） | iso3, year(2015–2025), metric（emp_public_admin = ISIC O／emp_total）, value_thousands, source_note, source(`ilostat`) |
| `staged/ilostat/emp_ins` → `marts/ilo_emp_public_sector` | 国×年×指標（long） | 同列、metric = emp_public_sector |
| `staged/ipss/prefecture_projection` → `marts/jp_prefecture_projection` | 都道府県×年 | iso3, year(2020–2050、5 年刻み), pref_code, pref, population（総人口）, source(`ipss_regional`)。329 行 |
| `staged/camera/laws_by_year`・`sittings_by_year` → `marts/it_laws_by_year`・`it_sittings_by_year` | 年×指標 | iso3(ITA), year(2007–2026), metric（laws_promulgated／plenary_sittings）, value, source(`camera_it`)。各 20 行 |
| `staged/worldbank/gdp_pcap_lcu` → `marts/wdi_gdp_pcap_lcu` | 経済体×年 | iso3, year(2005–2025), country, gdp_pcap_lcu, source |
| `staged/ilostat/earnings` → `marts/ilo_earnings_monthly` | 国×年 | iso3, year(2015–2025), metric(earnings_monthly_lcu), value_thousands（月収、現地通貨。千人ではない）, source_note, source |
| `staged/kokkai/meetings` → `marts/jp_hr_sitting_days` | 会議 → 年×指標 | staged: issue_id, date, name_of_meeting, session, is_plenary（約 6,900 行）。mart: iso3(JPN), year(2013–2025), metric（plenary_days／committee_meetings／committee_days／sitting_days）, value, source(`kokkai_ndl`)。52 行 |
| `staged/oecd/gov_finance` → `marts/oecd_gov_finance` | 国×年×指標（long） | iso3, year(2007–2024), metric（gov_expenditure_pct_gdp／gov_revenue_pct_gdp／gov_expenditure_pcap_usd_ppp）, value（% of GDP または USD PPP/人、一般政府）, source(`oecd_gov_glance`)。2,250 行・43 か国 |
| `staged/oecd/gov_trust` → `marts/oecd_gov_trust` | 国×年×指標（long） | iso3, year(2021・2023), metric（trust_legislature_pct／trust_national_government_pct／parliament_holds_gov_accountable_pct）, value（回答者 %。accountable は 0〜1 の割合）, source。131 行・33 か国 |
| `staged/eurobarometer/trust_parliament` → `marts/eb_trust_parliament` | 国×波 | iso3（EU27・EU28 の集計を含む）, wave(91–103), year, season, fieldwork(yyyy-mm), metric(trust_national_parliament_pct), value（tend to trust %）, source(`eurobarometer`)。379 行・30 か国 |
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
- ⑨ R10（2026-10-28 夜、ユーザー提起 H2e「官僚が多い国ほど議員は少ないか」）: ILOSTAT を結線。ρ = +0.33 で向きは逆（議員が少ない国は公務就業者も少ない）、判定は事前基準で「中間」: `reports/2026-10-28-r10-bureaucracy.md`。
- ⑩ R11〜R13（2026-10-29、「削減の是非」の立場を支える根拠）: R11（H8 整合: 定数維持＋修正サンラグで Gallagher −2.33 pt、H9: 職員を上位 3 分の 1 に上げる費用 16〜25 億円 ≈ 45 減の節約額、H10: 兼任率 1.24 → 1.37）、R12（H11 整合: 289 でも 2040 年に係数込み 2.24 倍）、R13（H7: イタリア不支持、ハンガリー判定不能）。立場の文書: `reports/2026-10-29-position-parliament-size.md`。H3f（2000 年の前後）は第 42・43 回の資料が無く対象外。
- ⑪ R14（2026-10-29 夕、世論「議員 1 人の収入は多く働きは少ない」の検証）: H12 整合（歳費 ÷ 1 人当たり GDP 2.9 倍で 38 か国中 7 位、÷ 平均年収 4.2 倍で 31 か国中 7 位）、H13 整合（稼働日数 124 日 = 本会議 51 日の 2.43 倍）: `reports/2026-10-29-r14-pay-and-workload.md`。
- ⑫ R15（2026-10-29 夜、ユーザー提起「少数政党保護は守るべき原則か」）: H14a 整合（1〜3 議席で入った 3 政党中 2 が次回 5 議席以上）、H14b 整合（29 か国中 22 か国が法定閾値 3% 以上、日本の実効閾値は 6.6〜12.3%）: `reports/2026-10-29-r15-small-parties.md`。立場文書のキーメッセージを「人数ではなく報酬・手当の水準と透明性」に書き換え。
- ⑬ R16（2026-10-29 深夜、番外編。ユーザー提起「議会の大きさは小さな政府／大きな政府と関係するか」）: OECD Government at a Glance 2025 を結線。H15a 不支持（素の比率 ρ = +0.16）、H15b 不支持（立方根補正比で ρ = +0.34、相関はむしろ現れる）、H15c 正、H15d 整合: `reports/2026-10-29-r16-government-size.md`。本編の記事には含めない。
- ⑭ R17（2026-10-30、番外編の深掘り）: OECD Trust Survey を結線。H16a 選挙制度（Persson–Tabellini 再現せず、比例代表制内 ρ = +0.21 中間）、H16b 議員 1 人当たり政府支出（日本 51.7 億 USD で 2 位、整合）、H16c 議会の大きさ × 信頼（+0.23 中間、「小さい議会ほど信頼」は不支持）: `reports/2026-10-30-r17-system-oversight-trust.md`。
- ⑮ R18（2026-10-30 夜、番外編。ユーザー提起「議員への不信は海外でも削減の推進力か」）: 手入力表 `seat_reduction_proposals.csv` × OECD 信頼。H17a 整合（提案あり 31.1% vs なし 41.5%）だが法案・国民投票に限ると不支持、H17b 不信・費用理由の施行率 23%、H17c は OECD では判定不能、Eurobarometer（13 波、2026-10-31 結線）で補完すると イタリア +5.9 pt vs EU27 +0.4 pt で整合（境界。政権交代と同時）: `reports/2026-10-30-r18-distrust-and-cuts.md`。
- 未着手: 独・米・韓の法案 API（鍵が要る）、選挙区単位の有権者数（H4c の係数の検証）、仏 第 15 立法期以前（zip 無し）、規模を補正した官僚数 × 議員数、削減後の審査の質（修正率・審議時間）、手当込みの総報酬の国際比較（IPU に項目なし）。

## テーマ固有の規約
- 「議員数」は定数（statutory）と現員（current）を列で分け、混ぜない。上院の選出方法（designation_mode）を注記できるよう議院単位で持つ。
- 配分方式（ドント・修正サンラグ・アダムズ）は `apportion.py` の純粋関数。試算の前に現行の配分（比例 176・小選挙区 289）を再現できることを検算する（R2 で実施、一致）。
- 比例の機械的試算は「票が同じなら」の目安。report に必ず「行動の変化は織り込まない」と書く。公式議席は名簿不足の移転を含むため、基準線は純ドントとし公式値を併記する。
- 一票の格差は 有権者数（選挙時）と 国勢調査人口 の両方で出し、どちらかを明記する。
- 推進・反対のどちらにも都合の良い指標だけを選ばない。事前登録した H1〜H6 をすべて報告する。
- IPU Parline 由来のデータは非商用（CC BY-NC-SA 4.0）。総務省・e-Stat 由来は政府標準利用規約 2.0（出典表記）。
