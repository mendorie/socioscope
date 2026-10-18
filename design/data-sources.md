# データソース方針

## ルール
- **本プロジェクトは非商用の研究目的に限る。** コードは MIT だが、派生データは出典ライセンスを継承する（例: WID.world は CC BY-NC-SA 4.0）。商用利用を検討する場合は NC 条件のソースを除外するか権利者に確認する。
- **公式 API / オープンデータ優先**。スクレイピングは利用規約・robots.txt を確認し、許される場合のみ。
- 採用したソースは下表に **ライセンス・取得方法・更新頻度** を記録する（`source-scout` エージェント / `/new-source`）。
- 取得物は必ず manifest（`data/raw/manifest.jsonl`）に URL・sha256・取得日時・ライセンスを残す。
- LLM で構造化する対象は「公開レポート本文・表の文章化された数値」など構造化 API のないものに限る。数値の一次ソースは可能な限り構造化 API から取る。

## 候補ソース（採用時に状態を更新）
| ソース | 内容 | 取得 | ライセンス（確認要） | 状態 |
|---|---|---|---|---|
| World Bank WDI API | GDP 成長率、出生率、人口、Gini 等（国×年）。H8（2026-10-17 取得）で `SP.DYN.SMAM.FE`（女性初婚年齢）, `SP.DYN.WFRT`（wanted TFR）, `SP.M18.2024.FE.ZS`（18 歳未満婚 %）, `SP.DYN.CONU.ZS`（避妊実行率）を追加。H8c（2026-10-17 取得）で `SE.TER.ENRR`（高等教育総就学率）, `SE.SCH.LIFE`（期待就学年数。WDI には無く Education Statistics source 12 から返るため `date=1960:2025` を付けて取得）, `SE.XPD.TOTL.GD.ZS`（政府教育支出 % GDP）, `SE.XPD.SECO.PC.ZS` / `SE.XPD.TERT.PC.ZS`（中等・高等の生徒一人当たり政府支出 % of GDP pc）, `SE.SEC.PRIV.ZS`（中等教育の私立在籍割合）を追加 | REST JSON（`api.worldbank.org/v2`） | CC BY 4.0 | **採用**（growth-fertility） |
| World Inequality Database (WID.world) | 所得・資産の上位シェア、人口、長期系列 | 国別 zip（`bulk_download/WID_fulldataset_<ISO2>.zip`） | **CC BY-NC-SA 4.0**（サイト表記。CC BY 4.0 は未確認） | **採用**（wealth-population-distribution） |
| UN World Population Prospects | 人口・年齢構成・出生率 | CSV / API | CC BY 3.0 IGO | 候補 |
| OECD Data Explorer（SDMX REST） | 最高限界所得税率（Tax Database Table I.7）、公的社会支出 %GDP（SOCX）、税収 %GDP・相続税収 %GDP（Revenue Statistics）；家族支出 TP51（growth-fertility H5） | SDMX REST CSV（`sdmx.oecd.org/public/rest/data/...?format=csvfilewithlabels`、鍵不要） | **OECD Terms & Conditions（2024-07-01 改定）: 出典表示で商用含め自由利用。OECD 発行物は CC BY 4.0**（確認 2026-10-04） | **採用**（wealth-population-distribution H2 / growth-fertility H5） |
| Eurostat dissemination API（JSON-stat 2.0） | 2021 センサス 配偶関係×年齢×性×ISCED（`cens_21me_r2`）、母の年齢×出生順位の出生数（`demo_fordagec`）、女性人口（`demo_pjan`）、母の年齢×ISCED の出生数（`demo_faeduc`）、LFS 女性人口×ISCED（`lfsa_pgaed`） | REST JSON（`ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/<dataset>?format=JSON&lang=EN&<dim>=<code>`、キー不要、国別リクエスト） | **Eurostat copyright notice: 出典表示で商用含め再利用可**（第三国データは別条件、本件は EU/EFTA のみ。確認 2026-10-06） | **採用**（growth-fertility H5） |
| OECD Education at a Glance（SDMX REST、`OECD.EDU.IMEP`） | 財源別教育支出割合・%GDP（UOE finance）、学歴別相対賃金（LSO earnings）、学生 1 人当たり支出（USD PPP） | 同上（3 リクエスト、鍵不要） | 同上（OECD Terms & Conditions、出典表示） | **採用**（growth-fertility H8c） |
| UN SDG Global Database（UNSD SDG API） | 5.4.1 無償家事・ケア労働時間の 24 時間比 %（`SL_DOM_TSPD`、性 × 年齢 × 地域、98 か国・地域 2000–）、5.5.2 管理職に占める女性割合 %（`IC_GEN_MGTL`、ILO 由来、195 か国・地域 2000–） | REST JSON（`unstats.un.org/sdgapi/v1/sdg/Series/Data?seriesCode=…&pageSize=…`、鍵不要、series ごと 1 リクエスト） | **UN Terms of Use（`un.org/en/about-us/terms-of-use`）と UNdata Terms（`data.un.org/Host.aspx?Content=UNdataUse`、出典引用で複製・再配布可）が食い違う → raw 非コミット、staged/mart は出典明記で保持**（確認 2026-10-17） | **採用**（growth-fertility H8d） |
| UNDP Human Development Report 2025 複合指数 CSV | GII とその構成要素（`gii, mmr, abr, se_f, se_m, pr_f, pr_m, lfpr_f, lfpr_m`）の国 × 年 1990–2023 | 静的 CSV（`hdr.undp.org/sites/default/files/2025_HDR/HDR25_Composite_indices_complete_time_series.csv`、latin-1、2.0 MB、鍵不要） | **CC BY 3.0 IGO**（`hdr.undp.org/terms-use`、確認 2026-10-17） | **採用**（growth-fertility H8d） |
| OECD Data Explorer（IDD 等） | 所得分配（IDD）、出生率 | SDMX API | 同上 | 候補 |
| Maddison Project / Penn World Table | 長期 GDP 系列 | Excel/CSV | 要確認 | 候補（戦後長期） |
| Our World in Data | 整形済み系列（出典明記） | CSV / grapher API | CC BY | 候補（検証用） |
| e-Stat（政府統計の総合窓口） | 国民生活基礎調査 所得票（所得階級×配偶者の有無・児童のいる世帯） | 統計表ファイル直接ダウンロード（`stat-search/file-download?statInfId=…&fileKind=1`、appId 不要） | **政府標準利用規約（第2.0版）＝CC BY 4.0 互換**（確認 2026-10-04） | **採用**（growth-fertility H3） |
| e-Stat — 就業構造基本調査（総務省） | 令和4年 全国編 第40表: 男女×配偶関係×年齢×所得（有業者） | 統計表ファイル直接ダウンロード（`…&fileKind=0`、**Excel のみ**、appId 不要。標準ライブラリで解析） | 同上（確認 2026-10-04） | **採用**（growth-fertility H3b 年齢調整） |
| DHS Program Indicator Data API | 調査前 3 年の TFR（15–49 歳）× 富裕五分位（`FE_FRTR_W_TFR` × Wealth quintile）、約 90 か国 1990–2025 の DHS/MIS/AIS 調査；国コード表（ISO3） | REST JSON（`api.dhsprogram.com/rest/dhs/data`, `/countries`、API キー不要） | **引用義務**（Terms: 「The DHS Program Indicator Data API, The Demographic and Health Surveys (DHS) Program. ICF. Originally funded by USAID. Available from api.dhsprogram.com. [Accessed 10-05-2026]」。確認 2026-10-05） | **採用**（growth-fertility H4） |
| 国家データ処（韓国）新婚夫婦統計 報道資料 PDF | 初婚新婚夫婦（婚姻 5 年以内）の所得区間（6 区間＋全体）× 子ども有無・人数・平均子ども数、2015–2024 年基準 | 報道資料掲示板の静的 PDF（`mods.go.kr/boardDownload.es?bid=11815&list_no=…&seq=…`、キー不要。pypdf でテキスト抽出し表をパース） | **公共ヌリ（KOGL）第 1 類型＝出典表示のみ・商用・改変可**（確認 2026-10-06） | **採用**（growth-fertility H5） |
| 교육부（韓国教育部）初中高 사교육비조사 報道資料 PDF | 学校外教育費（私教育費）: 年次（2007–2025）の総額・参加率・週当たり参加時間・1 人当たり月平均（全学生／参加学生）、자녀수別（1/2/3+）と 학교급別（초/중/고）の 2024–2025 | 報道資料掲示板の静的 PDF（`moe.go.kr/boardCnts/fileDown.do?…&fileSeq=…`、キー不要。pypdf でテキスト抽出し 3 表をパース） | **公共ヌリ（KOGL）第 1 類型＝出典表示のみ**（確認 2026-10-17） | **採用**（growth-fertility H8d 仮説 K、記述のみ） |
| Testa (2012) *Family sizes in Europe* 付表（VID/ÖAW EDRP 2、データ＝Eurobarometer 75.4, 2011）＋ BiB (2025) *Intended, ideal and actual fertility in 11 European countries* Table 1（GGS-II 2020–23） | 理想・意図・実際の子ども数の国別平均と分布（EB: EU-27 × 性 × 年齢 15–24/25–39/40–54/55+/計、2011。GGS: 11 か国 × 女性 18–29/30–39/40–49/計、2020–23） | 静的 PDF（`oeaw.ac.at/.../edrp_2012_02.pdf`、`bib.bund.de/Publikation/2025/pdf/...`、キー不要。pypdf でテキスト抽出し付表をパース） | Testa 2012: **ライセンス未明示 → 出典明記で事実の転記のみ、PDF は再配布しない**（EB 75.4 自体は欧州委員会 CC BY 4.0）。BiB 2025: **CC BY-SA 4.0**（本文表記、確認 2026-10-06） | **採用**（growth-fertility H6） |
| Standard Eurobarometer（data.europa.eu）Volume A | 「今後 12 か月の期待（生活全般・家計・国の経済・国の雇用）」の国別 Better/Worse/Same/DK 割合、STD91（2019 春）〜STD105（2026 春）15 波 | hub API の JSON-LD（`data.europa.eu/api/hub/repo/datasets/<id>.jsonld`）から Volume A の静的 URL（`webgate.ec.europa.eu/ebsm/api/public/odp/download?key=…`、キー不要）を解決して xlsx/xls を取得 | **欧州委員会 再利用方針（Decision 2011/833/EU）＝CC BY 4.0 相当**（JSON-LD も `licence/CC_BY_4_0`。`commission.europa.eu/legal-notice_en`、確認 2026-10-06） | **採用**（growth-fertility H6） |
| Special Eurobarometer 253（data.europa.eu、dataset `s406_65_1_ebs253`）EB65.1 Volume C ＋ EB65.3 Volume A | 2006 年の理想子ども数（一般理想・個人理想）の国別分布と平均、EU-25 × 性・年齢 ＋ 候補 4 か国 | hub の JSON-LD から 2 配布物（zip 内 xls）を解決して取得、xlrd で解析 | 欧州委員会 再利用方針（CC BY 4.0 相当、確認 2026-10-18） | **採用**（growth-fertility H9） |
| OECD Family Database SF2.5 Childlessness（xlsx） | 出生コーホート（1935–1975）別 定義的無子率 %、1975 コーホートの完結出生率 | 静的 xlsx（`webfs.oecd.org`、鍵不要）、openpyxl | OECD Terms（CC BY 4.0、確認 2026-10-18） | **採用**（growth-fertility H9） |
| 国立社会保障・人口問題研究所 | 出生動向基本調査、将来推計人口 | CSV/Excel | 要確認 | 候補（日本） |
| 国税庁 統計年報 / 民間給与実態統計 | 所得分布 | Excel | 政府標準利用規約 | 候補（日本） |
| 野村総研 富裕層レポート等 | 資産階層別世帯数（推計） | PDF（公開レポート） | 引用のみ | 候補（LLM 構造化対象） |

## 採用ソースの記録

### World Inequality Database (WID.world)
- URL / API:
  - 国別 zip: `https://wid.world/bulk_download/WID_fulldataset_<ISO2>.zip`（中身: `WID_data_<ISO2>.csv`, `WID_metadata_<ISO2>.csv`, `WID_countries.csv`, `README.md`）。日本 5.1MB、米国 7.2MB、フランス 9.0MB 程度。
  - 国別 CSV（非圧縮）: `https://wid.world/bulk_download/WID_data_<ISO2>.csv`（日本 35MB。圧縮 zip の方を使う）。
  - 全量 zip: `https://wid.world/bulk_download/wid_all_data.zip`（**882MB**、848 ファイル、展開 6.9GB。raw 予算 ~200MB を超えるため不採用）。
  - JSON API（`rfap9nitz6.execute-api.eu-west-1.amazonaws.com/prod/`）は R/Stata パッケージとサイト JS が使うが `x-api-key` 必須で公開ドキュメントなし。鍵をコードに埋めることになるため**使わない**。
  - robots.txt（2026-10-04）: `User-agent: * / Disallow:`（全許可）。
- 対象指標・粒度（国×年×百分位）:
  - `sptinc992j` 税引前国民所得シェア（成人・equal-split）: p0p50 / p50p90 / p90p100 / p99p100
  - `shweal992j` 個人純資産シェア（成人・equal-split）: 同上
  - `npopul999i` 総人口（全年齢・個人）: p0p100
  - 資本/所得比率 `wwealn999i` は bulk CSV に存在しなかった（日本で確認）ため今回は見送り。
  - **H4 用に追加（2026-10-05）**: 同じ `sptinc992j` / `shweal992j` の一般化百分位（g-percentile）ブラケット 127 個（`p0p1 … p98p99`, `p99p99.1 … p99.8p99.9`, `p99.9p99.91 … p99.98p99.99`, `p99.99p99.991 … p99.998p99.999`, `p99.999p100`。コード生成は `distribution.g_percentiles`）と上位テール `p99.9p100` / `p99.99p100` を `staged/wid/distribution` に、閾値変数 `tptinc992j` / `thweal992j`（bulk 表記 `tptincj992` / `thwealj992`）の `p10p11` / `p50p51` / `p90p91` / `p99p99.1`（WID はブラケット pXpY の閾値を X の値として持つ。単位は現地通貨・実質）を `staged/wid/thresholds` に起こす。平均 `aptinc992j` / `ahweal992j` は今回使わない。**実ファイルで照合済み（2026-10-06、wid.world 復旧後に 46 zip を再取得。sha256 は 2026-10-04 の記録と全件一致）**: `WID_data_JP.csv` の `sptincj992` / `shwealj992` は 1 年あたり 387 の percentile コードを持ち、そのうち 127 の g-percentile（小数は `p99.99p99.991` のように 3 桁まで）と `p99.9p100` / `p99.99p100` が存在。`tptincj992` / `thwealj992`（閾値、metadata の unit は `JPY` 等の現地通貨）と `aptincj992` / `ahwealj992`（平均）も存在し、閾値は g-percentile コード `p10p11` 等で与えられ、`p10p11` = `p10p100`、`p50p51` = `p50p100`、`p90p91` = `p90p100`、`p99p99.1` = `p99p100` が同値（ブラケットの下限値）。`staged/wid/distribution` は 807,413 行（国×年×変数 6,259 件が 129 行、GBR 資産 1907・1909 年の 2 件は `p99.9p100` のみ）、`staged/wid/thresholds` は 25,012 行（所得 3,538 国×年、資産 2,715 国×年、各 4 分位）。資産の P10 閾値は国×年の 57% が ≤ 0（純資産が負）、所得の P10 は ARG BRA CHL COL CRI MEX RUS の一部年で事実上 0（P50/P10 が発散）。
  - **2026-10-05 wid.world domain parked (GoDaddy lander); fetch now fails closed.** `HttpxFetcher` は HTTP 200 なら中身を問わず返すため、パーキングページの HTML（114 バイト、`/lander` へリダイレクト）が zip として保存・manifest 追記されうる。`pipeline.fetch` に `wid.is_zip_payload`（`PK\x03\x04` マジック）の検査を入れ、非 zip は raw・manifest に触れず `skipped` に「`<ISO2>: non-zip payload (site down?)`」を残す。取得できた全件が非 zip なら `RuntimeError` で終了コード非 0。同じ守りを OECD（`oecd.is_csv_payload`: `STRUCTURE,STRUCTURE_ID,` で始まるか）と growth-fertility の World Bank（`worldbank.is_json_list_payload`: JSON 配列か）にも入れた（Fetcher Port は Content-Type を公開しないため本文検査のみ）。
  - bulk CSV のフォーマット: `;` 区切り、列 `country;variable;percentile;year;value;age;pop;data_quality`。`variable` 列は `sptincj992`（型+概念+人口単位+年齢）の順で、サイト表記 `sptinc992j` とは並びが異なる。stage で `sptinc992j` に正規化する。`data_quality`（0〜5、空あり）は staged に残す。
  - metadata CSV のフォーマット（**2026-10-04 に 46 か国の zip すべてで確認**）: `WID_metadata_<ISO2>.csv` は `;` 区切り 18 列 `country;variable;age;pop;countryname;shortname;simpledes;technicaldes;shorttype;longtype;shortpop;longpop;shortage;longage;unit;source;method;avg_quality`（zip 内 README は「seventeen variables」と書くが実ファイルには `avg_quality` が追加されている）。1 行 = 国×変数×age×pop（日本 2,073 行）。**`data_points` / `extrapolation` / `data_quality` / `quality_notes` といった列は存在しない**。年別の補間・外挿の情報は `method` の自由記述のみ（欧州 DINA 所得系列 26 か国: 「Summary of data construction by year (see source for details): 1980: extrapolated distribution, 1981-2005: survey + concept correction + tax data, 2006-2014: survey + tax data, 2015-2020: extrapolated distribution using survey data, …」。資産系列・米日等の所得系列: 「Before 1980, series is constructed based on the trend observed in the fiscal income data available (see sources).」「Before 1913, pretax income shares estimated based on methodology in long-run paper (see sources).」のみ）。`source` 列は `[URL][URL_LINK]…[/URL_LINK][URL_TEXT]…[/URL_TEXT][/URL]` 形式の文献リンク。stage は `staged/wid/metadata`（`source` を `source_text` に改名、`source` 列は来歴 `wid_world`）と `staged/wid/data_points`（年別 observed/partial/imputed/不明）に起こす。
  - `data_quality` / `avg_quality` の定義（調査 2026-10-04）: `wid.world/methodology/`、`wid.world/codes-dictionary/`、`wid.world/data-quality-score-world-map/`、zip 内 README のいずれにも定義なし。見つかった公式記述は R パッケージ `wid` 0.0.3 manual（CRAN, 2026-07-28）のみ: `data_quality` = "Observation-level data quality score. Since 2026, this score varies by country, series, and year."、`avg_quality` = "Country-series data quality score. It is a weighted average of data_quality over years, with greater weight on more recent observations."、`quality_filter` = "A single number is interpreted as a minimum data_quality"（高いほど良い向きを示唆）。旧 wid-r-tool の doc には "quality: Data quality (when applicable). The quality field is a score from 0 to 5 indicating the quality of the data." と "imputation: Type of estimate (when applicable). The imputation field is a short qualitative description of the type of estimate provided, which is strongly related to data quality."（`imputation` 列は bulk には無い）。API には `no_extrapolation`（"should interpolated/extrapolated years be included or not?"）引数があるが bulk zip には相当する列が無い。各レベル 0–5 の意味は非公開。World Inequality Lab Technical Note 2020/12（Inequality Transparency Index）はソースの品質を 5 点満点で採点するが（"We evaluate the quality of each data source out of 5 points… When considering data for which only tabulations are available, we give a maximum grade of 2.5. When microdata is considered, the maximum grade is 5."）、それが `data_quality` と同一かは確認できない。
- ライセンス・利用規約（確認日 2026-10-04）:
  - サイト各ページの `rel="license"` リンクは **CC BY-NC-SA 4.0**（`creativecommons.org/licenses/by-nc-sa/4.0/`）。ツールチップ文「Creative Commons Attribution 4.0」は HTML コメントアウトされており無効。`wid.world/terms-of-use/` は 404。zip 内 README にライセンス記載なし。World Inequality Report も CC BY-NC-SA 4.0。
  - 判定: **CC BY-NC-SA 4.0 として扱う**（出典表示・非営利・継承）。本リポジトリは非営利の研究用途で問題なし。WID 由来の staged/marts Parquet を再配布するときは出典（World Inequality Database, wid.world）と同ライセンスを明記する。raw はコミットしない（既定どおり）。CC BY 4.0 の明示が必要なら WID へ問い合わせ（人間ゲート）。
- 取得方法（adapter 名、レート制限）: `theme_wealth_population_distribution.wid`（純粋変換）＋ `pipeline.fetch`（`HttpxFetcher`）。OECD 38 ＋ 非 OECD G20 8 の 46 か国を 1 回ずつ逐次取得（合計 ~196MB）。公開レート制限なし。再取得は年 1 回程度（WID の年次更新時）。
- 既知の欠損・断絶・定義変更: 戦前は少数国のみ（日本の所得シェアは 1820/1850 以降に飛び飛び、資産シェアは 1820 から 56 年分）。`data_quality` は本データとの照合では**高いほど一次データに近い**（USA DINA 1962 年以降 = 5、SAU・JPN 資産の全年 = 0、DEU 資産は調査年 4・その間の補間年 0。metadata で observed と明示された所得の年は q3–5 のみ。ただし q3 以上にも imputed 年が多い）。旧記述「4〜5 は推計・外挿を含む」は誤り（2026-10-04 訂正、H1b レポート参照）。資産統計の定義は国で異なる（`staged/wid/metadata` の `source_text`/`method` 参照）。資産系列には年別の観測／推計の記述が無い（1980 年以前の trend 構築のみ）。ISO2→ISO3 は `wid_iso2_to_iso3.csv`（pycountry 由来・旧国コードは ISO 3166-3、コソボ KS→XKX）で決定的に変換し、地域集計（WO, QE, XF…）・サブナショナル（US-CA, CN-RU…）・非 ISO コード（XI, ZZ…）は捨てる。

### e-Stat（政府統計の総合窓口）— 国民生活基礎調査（厚生労働省）
- URL / API:
  - 統計表ファイル: `https://www.e-stat.go.jp/stat-search/file-download?statInfId=<12桁>&fileKind=1`（CSV, **CP932**。`fileKind=0`(Excel) は対象表では 404）。**アプリケーション ID 不要**。`statInfId` は公開表ごとに固定。
  - e-Stat API 3.0（`api.e-stat.go.jp/rest/3.0/...`）は全エンドポイントで appId 必須のため**使わない**（本リポジトリはアカウント登録しない）。将来必要になれば `ESTAT_APP_ID` 環境変数経由で fail-closed に実装する。
  - 表の所在: 国民生活基礎調査 → 各年 → 「所得・貯蓄」巻（一覧は `stat-search/files?...&tclass1=<巻>&cycle=7&cycle_facet=tclass1`）。
  - robots.txt（2026-10-04）: Drupal 既定（`/admin/`, `/search/`, `/user/*` 等のみ Disallow）。`/stat-search/file-download` は許可。
- 対象表・粒度（`theme_growth_fertility.estat.TABLES`）:
  | key | statInfId | 表 | 単位 |
  |---|---|---|---|
  | `hh_income_dist_ts` | 000040473361 | 令和7年 第002表 世帯数の相対度数分布，年次・所得金額階級別（1985–2024 所得年） | % |
  | `children_hh_income_dist_ts` | 000040473376 | 令和7年 第017表 児童のいる世帯数の相対度数分布，年次・所得金額階級別 | % |
  | `workers_marital_income_<2013,2016,2019,2022,2025>` | 000026222087 / 000031734158 / 000031957928 / 000040076501 / 000040473461 | 第102表 有業人員（15歳以上），勤めか自営かの別・**配偶者の有無・性・所得金額階級別**（大規模調査年） | 人員10万対 |
  | `hh_type_income_<同5波>` | 000026222010 / 000031734081 / 000031957851 / 000040076424 / 000040473384 | 第025表 世帯数，世帯類型－**児童のいる世帯**・所得金額階級別 | 世帯数1万対 |
- ライセンス・利用規約（確認日 2026-10-04, `https://www.e-stat.go.jp/terms-of-use`）: **政府標準利用規約（第2.0版）**。「クリエイティブ・コモンズ・ライセンスの表示 4.0 国際と互換性があり」と明記。出典表記必須（`出典：政府統計の総合窓口(e-Stat)`、加工した場合はその旨を記載）。商用利用可。API 利用には別規約があるが本実装は API を使わない。raw はコミットしない（既定どおり）。staged/marts を再配布するときは「出典：政府統計の総合窓口(e-Stat)、国民生活基礎調査（厚生労働省）を加工」を明記。
- 取得方法（adapter 名、レート制限）: `theme_growth_fertility.estat`（URL 組み立て・CSV→行の純粋変換）＋ `pipeline.fetch`（`HttpxFetcher`）。12 ファイル（計 ~80KB）を逐次取得。公開レート制限なし。再取得は年 1 回（7 月の公表後）。新しい大規模調査年（次は 2028）を足すときは `TABLES` に statInfId を追加する。
- 既知の欠損・断絶・定義変更:
  - **所得年と調査年**: 所得票は前年 1 年間の所得を聞く。年次推移表の列、および staged の `year` は**所得年**（`survey_year = year + 1`）。令和2年調査は中止（2019 所得が `…` → None）。平成6年は兵庫県、平成22年は岩手・宮城・福島、平成23年は福島、平成27年は熊本を除く。平成21年は定額給付金等の補完を含む。
  - **所得階級**: 世帯所得（万円）。年次推移表と第025表は 50 万円刻み（1000 万円以上は 100・300・500 万円刻み、2000 万円以上で打ち切り）。第102表は**有業者個人の所得**で 500 万円以上は 100 万円刻み、1000 万円以上で打ち切り、「所得なし」階級あり。`income_class_upper_yen` は上限なし階級で NULL。
  - **有配偶率の定義**: 第102表は「15 歳以上の有業人員」の配偶者の有無であり、無業者（専業主婦・学生・無職）を含まない。配偶者不詳は分母から外す（`denominator = 配偶者あり + 配偶者なし`）。年齢調整なし（所得は年齢と相関するため、年齢構成の差を含む粗い指標）。値は人員 10 万対の重みであり実数ではない。
  - **児童のいる世帯**: 18 歳未満の未婚の者がいる世帯。世帯所得階級別の「児童のいる世帯／全世帯」は子ども「数」ではなく有無の割合。母子世帯（2013 表では「母子世帯」列、他年は「高齢者世帯以外」の内訳）は別列で staged に保持。
  - 第025表のヘッダは年により複数行に分かれる（2013 年は「（再掲）児童のいる世帯」が 1 セル）。stage はヘッダ行を列ごとに連結して「児童のいる世帯」「母子世帯」「総数」を一意に特定し、見つからなければ fail-closed。

### e-Stat（政府統計の総合窓口）— 就業構造基本調査（総務省）令和4年 全国編 第40表（H3b 年齢調整用）
- URL / API:
  - 統計表ファイル: `https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040077301&fileKind=0`（**Excel .xlsx 2.2MB**、1 シート、tidy 形式: 階層レベル／地域区分／男女／配偶関係／年齢／従業上の地位・雇用形態・起業の有無／所得 の列＋教育別の値列）。`fileKind=1`（CSV）は **404**。**アプリケーション ID 不要**。xlsx は `zipfile` ＋ `xml.etree`（標準ライブラリ）で読み、依存は追加しない。
  - 表の所在: 就業構造基本調査 → 令和4年（tstat=000001163626）→ 全国編（tclass1=000001163627）→ 人口・就業に関する統計表（tclass2=000001163628、271 表）。調査年月 2022 年 10 月、公開 2023-07-21。
  - e-Stat API 3.0（appId 必須）は引き続き使わない。この表はファイルで取得できたため `ESTAT_APP_ID` 経路は未実装。
- 調査結果（2026-10-04）: 国民生活基礎調査 令和7年「所得・貯蓄」234 表に 年齢×配偶者の有無×所得 のクロスは無い（配偶者の有無を持つのは第102表・第215表のみ）。就業構造基本調査 2022 年 全国編では第40表のみが 配偶関係×年齢×所得（有業者）を持つ。**2017 年（平成29年）・2012 年（平成24年）全国編に同等表は無い**（2017 年は非正規職員のみの第67表）。したがって 1 波のみ。
- 対象表・粒度（`theme_growth_fertility.estat.TABLES`、`TableKind.SHUGYO_MARITAL_AGE_INCOME`）:
  | key | statInfId | 表 | 単位 |
  |---|---|---|---|
  | `shugyo_marital_age_income_2022` | 000040077301 | 令和4年 第40表 男女、配偶関係、年齢、従業上の地位・雇用形態・起業の有無、所得（主な仕事からの年間収入・収益）、教育別人口（有業者）－全国 | 人（推定人数） |
- ライセンス・利用規約: e-Stat と同じ **政府標準利用規約（第2.0版）**（確認 2026-10-04）。出典表記「出典：政府統計の総合窓口(e-Stat)、就業構造基本調査（総務省）を加工」。raw はコミットしない。
- 取得方法（adapter 名、レート制限）: `theme_growth_fertility.estat`（`xlsx_rows` → `parse_shugyo_marital_age_income`）＋ `pipeline.fetch`（`HttpxFetcher`）。1 ファイル。raw は `data/raw/growth-fertility/estat_shugyo/`、staged は `staged/estat/shugyo_marital_age_income`（従業上の地位＝総数、教育＝総数の列のみ: 3 性 × 2 配偶関係 × 16 年齢 × 17 所得 = 1,632 行）、mart は `marts/jp_income_age_marital`（816 行）。
- 既知の欠損・断絶・定義変更:
  - **配偶関係は「総数」「うち未婚」のみ**。有配偶／死別・離別は公表されないため、mart の metric は `ever_married_share` = (総数 − 未婚) ÷ 総数（既婚経験率）。国民生活基礎調査の「配偶者あり」率とは定義が異なる。
  - **所得**は主な仕事からの年間収入・収益（調査前 1 年＝2021 年 10 月〜2022 年 9 月、名目）。staged/mart の `year` は**調査年 2022**（国民生活基礎調査の「所得年＝調査年−1」とは規則が異なる）。階級ラベル「50〜99万円」は 50 以上 100 未満として `income_class_upper_yen` = 100 万円に正規化（`parse_income_class_shugyo`）。「所得なし」階級は無く、所得不詳は総数にのみ含まれる（男性 2.4%、女性 4.3%）。
  - 年齢は 5 歳階級 15–19 〜 85 歳以上（`age_upper` は排他的上限、85 歳以上は NULL）。有業者 0 のセルは `'-'` → 0 → 比率 NULL（補完しない）。
  - 値は標本から復元した推定人数で、標準誤差は非公表。

### OECD Data Explorer（SDMX REST API）— 税制・社会支出（wealth-population-distribution H2）
- URL / API:
  - データ: `https://sdmx.oecd.org/public/rest/data/<agency>,<dataflow>,<version>/<key>?format=csvfilewithlabels`。**API キー不要**。`<key>` は dataflow の次元順に `.` 区切り（REF_AREA は空＝全国）。構造: `.../dataflow/<agency>/<dataflow>/<version>?references=all`、期間: `.../availableconstraint/<agency>,<dataflow>,<version>/all`。
  - 採用 dataflow（2026-10-04 に構造とデータ断片を取得して確認。ID は dataflow 一覧 `rest/dataflow/all` 1,549 件から特定）:
    | staged 名 | dataflow | key（REF_AREA を除く） | 期間 | 内容 |
    |---|---|---|---|---|
    | `top_pit_rate` | `OECD.CTP.TPS,DSD_TAX_PIT@DF_PIT_TOP_EARN_THRESH,1.0` | `.A._Z.TS_PIT.PT_WG_EARN_G.S13._Z._Z._Z._Z._Z._Z` | **2000–2025** | 最高限界個人所得税率（中央＋地方の合算、Tax Database Table I.7 の `TS_PIT`）、% |
    | `social_expenditure_gdp` | `OECD.ELS.SPD,DSD_SOCX_AGG@DF_SOCX_AGG,1.0` | `.A.SOCX.PT_B1GQ.ES10._T._T._Z` | 1980–2024 | 公的社会支出（現金＋現物、全プログラム）、%GDP |
    | `tax_revenue_gdp` | `OECD.CTP.TPS,DSD_REV_COMP_OECD@DF_RSOECD,2.0` | `.TAX_REV.S13._T._T.PT_B1GQ.A` | 1965–2024 | 一般政府 総税収、%GDP |
    | `inheritance_tax_rev_gdp` | 同上 | `.TAX_REV.S13.T_4300._T.PT_B1GQ.A` | 1965–2024 | 相続・遺産・贈与税収（4300）、%GDP。相続税「有無」の dataflow は SDMX に無いため税収ベースの代理 |
  - 当初候補の `DSD_TAX_WAGES_PIT@DF_TAX_PIT` / `DSD_TABLE_I7` / `DSD_SOCX_AGG@DF_SOCX_AGG`（これのみ一致）/ `DSD_REV@DF_REVOECD` は、`DF_SOCX_AGG` を除き存在しなかった。Revenue Statistics の国別 dataflow（`DSD_REV_OECD@DF_REV<ISO3>`）ではなく比較表 `DF_RSOECD` を使う（1 リクエストで全国）。
  - Table I.7 の 1981–1999 の歴史系列は oecd.org 上の Excel（`/content/dam/oecd/...`）にあるが、**robots.txt で `/content/dam/oecd/` が Disallow** のため取得しない。最高税率は 2000 年以降のみ。
  - robots.txt（2026-10-04）: `www.oecd.org` は `/content/dam/oecd/` と `/adobe/dynamicmedia/deliver/` のみ Disallow。`sdmx.oecd.org/robots.txt` は 404（制限なし）。
- 対象指標・粒度: 国（OECD 加盟 38 か国の ISO3）× 年。dataflow には集計（`OECD`, `OECD_REP`, `FEDOECD`, `UNIOECD`）や非加盟国（`BGR`, `HRV`, `PER`, `ROU`）も含まれるが、stage で `oecd.OECD_MEMBERS` の 38 か国に限定する。
- ライセンス・利用規約（確認日 2026-10-04、`https://www.oecd.org/en/about/terms-conditions.html`、「Last updated on 1 July 2024」）: **Data 節**「you can extract from, download, copy, adapt, print, distribute, share and embed Data for any purpose, even for commercial use」。条件は出典表示（`OECD (year), (dataset name), (data source) DOI or URL (accessed on (date))` 形式）と、再配布時に同じ出典表示義務を継承させること。「CC BY 4.0」の明示は **2024-07-01 以降に公表された OECD 著作物（Written Content）**に対するもので、データ節自体は上記の独自条件（実質 CC BY 相当）。第三者所有データが含まれ得る旨の注意あり（採用 3 dataflow は OECD 自身の統計）。API 節: 「as-is」、レート・量の制限を OECD が任意に課せる、最新版 API を使うこと。raw はコミットしない（既定どおり）。staged/marts の再配布時の出典表記: 「OECD (2026), OECD Tax Database / Social Expenditure Database (SOCX) / Revenue Statistics, https://sdmx.oecd.org (accessed on 2026-10-04)」。
- 取得方法（adapter 名、レート制限）: `theme_wealth_population_distribution.oecd`（URL 組み立て・CSV→行の純粋変換、Pydantic で STRUCTURE_ID と全次元コードを照合し fail-closed）＋ `pipeline._fetch_oecd` / `_stage_oecd`（`HttpxFetcher`）。**4 リクエスト（計 ~2.3MB）**。`socioscope run wealth-population-distribution fetch --only oecd` で WID の再取得を避けられる。公開レート制限なし（規約上 OECD が任意に制限可）。再取得は年 1 回程度。
- 既知の欠損・断絶・定義変更:
  - `top_pit_rate` は 2000 年以降のみ（上記）。H2 の 1980 起点の長期差分には使えない。
  - `social_expenditure_gdp` は 1980 年時点で 23 か国。遅れて始まる国: MEX 1985, CHL 1986, CZE/ISL/KOR/POL 1990, LVA 1994, ISR/SVK/SVN 1995, LTU 1996, EST/HUN 1999, COL 2010, CRI 2011。2023 以降は暫定で欠損あり。
  - `tax_revenue_gdp` / `inheritance_tax_rev_gdp` は 1980 年時点で 26 か国。遅れて始まる国: CHL/COL/CRI 1990, HUN/POL 1991, CZE 1993, EST/ISR/LTU/LVA/SVK/SVN 1995。
  - `OBS_VALUE` 空（`OBS_STATUS` M/L 等）は行ごと落とす（補完しない）。staged に `obs_status` 列を残す。
  - 最高税率は賃金所得に対する法定税率で、資本所得・配当の税率ではない。社会支出・税収は GDP 比で、GDP 改定の影響を受ける。

#### H8c EAG: Education at a Glance（growth-fertility、`marts/oecd_education_finance`、取得日 2026-10-17）
- URL / API（同じ SDMX REST、`format=csvfilewithlabels`、鍵不要。source-scout が 2026-10-17 に httpx で成功を確認。URL は `theme_growth_fertility.oecd_eag.DATASETS` に固定し改変しない）:
  | raw（`data/raw/growth-fertility/oecd_eag/`） | dataflow（STRUCTURE_ID） | key（次元順） | 行（うち値あり） | 内容 |
  |---|---|---|---|---|
  | `eag_fin_source.csv`（18 MB） | `OECD.EDU.IMEP:DSD_EAG_UOE_FIN@DF_UOE_FIN_SOURCE_GV_PR_NDOM(3.2)` | `REF_AREA.MEASURE.EDUCATION_LEV.EXP_SOURCE.EXP_DESTINATION.EXPENDITURE_TYPE.PRICE_BASE.UNIT_MEASURE.Q_SHEET` = `.EXP.ISCED11_1T8+ISCED11_1T4+ISCED11_5T8+ISCED11_02.S13+S1D_NON_EDU+S2+_T.INST_EDU.DIR_EXP..PT_EXP+PT_B1GQ.SOURCE`、`startPeriod=1995` | 24,780（15,135） | 財源別（政府 S13 / 私的 S1D_NON_EDU / 国外 S2 / 合計）の教育機関支出。`PT_EXP` = 支出に占める割合（`S1D_NON_EDU` が私的負担割合）、`PT_B1GQ` = %GDP |
  | `eag_earn_rel.csv`（11.7 MB） | `OECD.EDU.IMEP:DSD_EAG_LSO_EA@DF_LSO_EARN_REL_UPPER(1.0)` | 17 次元 `REF_AREA.SEX.AGE.ATTAINMENT_LEV.EDUCATION_FIELD.MEASURE.INCOME.BIRTH_PLACE.MIGRATION_AGE.EDU_STATUS.LABOUR_FORCE_STATUS.DURATION_UNEMP.UNIT_MEASURE.STATISTICAL_OPERATION.WORK_TIME_ARNGMNT.QUESTIONNAIRE.FREQ` = `..Y25T64.ISCED11A_0T2+ISCED11A_5T8+ISCED11A_5+ISCED11A_6+ISCED11A_7_8._T.EARN_RELATIVE._Z._T._Z.ED_NED.EMP._Z.PT_EARN_WR_ISCED11A_3.OBS..EARNINGS.A`、`startPeriod=2000`（SEX と WORK_TIME_ARNGMNT が可変） | 16,545（12,796） | 25–64 歳就業者の学歴別相対賃金（後期中等 = 100）。性 `_T/F/M`、労働時間 `_T/FT`（`_O` も返るが全件空） |
  | `eag_fin_perstud.csv`（5.1 MB） | `OECD.EDU.IMEP:DSD_EAG_UOE_FIN@DF_UOE_INDIC_FIN_PERSTUD(3.2)` | 上と同じ 9 次元 = `.FIN_PERSTUD.ISCED11_1T8+ISCED11_1T4+ISCED11_5T8+ISCED11_02._T.INST_EDU.DIR_EXP.Q+V.USD_PPP_ST.SOURCE`、`startPeriod=1995` | 7,080（4,530） | フルタイム換算学生 1 人当たり教育機関支出（USD PPP）。`PRICE_BASE` Q = 2020 年不変価格（`BASE_PER=2020`）、V = 当年価格 |
- 対象指標・粒度: 国 × 年 × 次元（long）。dataflow には 53 REF_AREA（集計 OECD/EU25/G20、非加盟 ARG/BGR/BRA/CHN/HRV/IDN/IND/PER/ROU/SAU/THA/ZAF）が混ざるので、stage で `oecd.OECD_MEMBERS` の 38 か国に限定し、落とした REF_AREA を skipped に列挙する。空 `OBS_VALUE` は `OBS_STATUS` を問わず落とす（`O` 欠損のほか `A`/`B`/`K` にも空がある）。`OBS_STATUS`（A 通常 / W 他区分を含む / B 断絶 / R 改訂 / L・U）と `BASE_PER` は列として保持する。使わない次元は `_Z`（`base_per` は空文字）で埋め、mart のキー `(iso3, year, dataset, measure, education_level, exp_source, sex, work_time, price_base, unit)` は一意（重複は `ValueError`）。結果: 28,329 行、38 か国、1995–2025（fin_source 13,069 / earn_rel 11,272（37 か国、ISL なし）/ fin_perstud 3,988。2012 年以降が中心）。
- ライセンス・利用規約: 上の OECD 節と同じ（OECD Terms & Conditions 2024-07-01、出典表示で商用含め自由利用）。raw はコミットしない。staged/marts の出典表記: 「OECD (2026), Education at a Glance database (UOE finance / LSO earnings), https://sdmx.oecd.org (accessed on 2026-10-18)」。
- 取得方法（adapter 名、レート制限）: `theme_growth_fertility.oecd_eag`（`DATASETS`・`parse`・`build_mart` の純粋変換、Pydantic で STRUCTURE_ID・固定次元・閉じた可変次元を照合し fail-closed）＋ `pipeline._fetch_h8c / _stage_h8c / _mart_h8c`（`HttpxFetcher`）。**3 リクエスト（計 ~35 MB）**。staged は dataset ごと `staged/oecd_eag/{fin_source,earn_rel,fin_perstud}`、mart は `marts/oecd_education_finance`（ある staged だけを結合）。公開レート制限なし。再取得は年 1 回程度（EAG 刊行時）。
- 既知の欠損・断絶・定義変更:
  - KOR の私的負担割合（`S1D_NON_EDU`/`PT_EXP`/ISCED11_1T8）は 2015 30.3 → 2022 17.4 → 2023 20.5 と大きく下がり全年 `OBS_STATUS=W`（他区分を含む）。定義改訂の疑いがあり、H8c の頑健性で韓国除外を行う。
  - JPN の相対賃金は 2005・2012 の 2 年のみ（`_T`/`_T` で 148.3・151.7）。Y2 では相対賃金を外した版も報告する。ISL は相対賃金なし。
  - `fin_perstud` の Q（不変価格）は 2020 年基準で、V（当年価格）と混ぜない。分析では Q を使う。
  - 一人当たり支出は「子どもが少ないほど 1 人当たりが増える」機械的な逆因果を含むため判定には使わない（設計 H8c）。

### DHS Program Indicator Data API（growth-fertility H4: 国内の富裕五分位別 TFR）
- URL / API:
  - データ: `https://api.dhsprogram.com/rest/dhs/data?indicatorIds=FE_FRTR_W_TFR&breakdown=all&characteristicCategory=Wealth%20quintile&perpage=5000&f=json`（1 ページ、2026-10-05 時点 1,565 レコード = 313 調査 × 5 五分位）。レスポンスは JSON オブジェクト `{TotalPages, RecordCount, RecordsReturned, Page, Data[]}`。`Data` の主フィールド: `Value`(数値), `DHS_CountryCode`, `CountryName`, `SurveyYear`(int), `SurveyId`(例 `AF2015DHS`), `IndicatorId`, `CharacteristicCategory`, `CharacteristicLabel`(Lowest/Second/Middle/Fourth/Highest), `SurveyType`(DHS/MIS/AIS), `CILow`/`CIHigh`/`DenominatorWeighted`(**文字列**、この指標では空)。
  - 国コード: `https://api.dhsprogram.com/rest/dhs/countries?f=json&perpage=300`（92 件。`DHS_CountryCode` → `ISO3_CountryCode`。`OS`＝Nigeria (Ondo State) は ISO3 空）。
  - API キー不要。`TotalPages != 1` や `RecordCount != len(Data)` は `ValueError`（fail-closed）。
- 対象指標・粒度: 調査（国 × 調査年 × 調査種別）× 富裕五分位 1..5。富裕五分位は**資産指数による国内の相対順位**で所得額ではない。TFR は調査前 3 年の 15–49 歳女性ベース。
- ライセンス・利用規約（確認日 2026-10-05、`https://api.dhsprogram.com/#/terms.cfm`）: 利用は自由だが**引用必須**: 「The DHS Program Indicator Data API, The Demographic and Health Surveys (DHS) Program. ICF. Originally funded by the United States Agency for International Development (USAID). Available from api.dhsprogram.com. [Accessed 10-05-2026]」。`theme_growth_fertility.dhs.LICENSE` に記載し manifest に残す。raw はコミットしない。
- 取得方法（adapter 名、レート制限）: `theme_growth_fertility.dhs`（URL 組み立て・`iso3_map`・`rows_from_response`・`unmapped_codes` の純粋変換、Pydantic `extra="ignore"`）＋ `pipeline.fetch` / `pipeline._stage_dhs`（`HttpxFetcher`）。**2 リクエスト**。raw は `data/raw/growth-fertility/dhs_api/{dhs_tfr_wealth,dhs_countries}.json`、staged は `staged/dhs/tfr_by_wealth_quintile`（countries raw が無ければ fail-closed）、mart は `marts/dhs_tfr_by_wealth_quintile`（staged をそのまま `survey_year, iso3, quintile` でソート）。公開レート制限なし。
- 既知の欠損・断絶・定義変更:
  - ISO3 の付かない DHS 国コード（サブナショナル調査 `OS` 等）の行は落とし、stage の skipped に残す。
  - `CILow`/`CIHigh`/`DenominatorWeighted` はこの指標では全件空（None）。列は保持する。
  - 対象国は低・中所得国に偏る（高所得国の国内勾配は観測できない）。同一国の複数調査は調査種別（DHS/MIS/AIS）が混在する。

#### H8: 複数指標 × 内訳（`marts/dhs_mechanisms`、取得日 2026-10-17）
- 同じ API を**30 リクエスト**（1 リクエスト = 1 指標群 × 1 内訳。H8b の 8 本を含む）で呼ぶ。`theme_growth_fertility.dhs.H8_REQUESTS`（raw 名 → URL、決定的順序）。内訳なし（Total のみ）は `breakdown` を付けず `…/data?indicatorIds=<ID[,ID…]>&perpage=5000&f=json`、内訳ありは `&breakdown=all&characteristicCategory=<Category>`（空白は `%20`）。`perpage` の上限は 5,000 で、超えると `TotalPages > 1` になり fail-closed（下表はすべて 1 ページで確認済み）。国コード → ISO3 は H4 の `dhs_countries.json` を再利用（countries raw が無ければ H8 全体を stage しない）。
  | raw（`data/raw/growth-fertility/dhs_api/`） | indicatorIds | characteristicCategory | 行 / 調査（2026-10-17） |
  |---|---|---|---|
  | `dhs_h8_FE_FRTR_W_TFR_total.json` | `FE_FRTR_W_TFR` | （Total） | 368 / 368 |
  | `dhs_h8_FE_FRTR_W_TFR_education.json` | 〃 | `Education` | 1,407 / 365 |
  | `dhs_h8_FE_FRTR_W_TFR_wealth_quintile.json` | 〃 | `Wealth quintile`（H4 と同じ URL。raw は別名で再保存） | 1,565 / 313 |
  | `dhs_h8_FE_FRTR_W_A15_ASFR_total.json` | `FE_FRTR_W_A15,…,FE_FRTR_W_A45`（7 本を 1 リクエスト） | （Total） | 2,567 / 368（A45 は 359 調査） |
  | `dhs_h8_PR_WTFR_W_WFR_{total,education,wealth_quintile}.json` | `PR_WTFR_W_WFR` | Total / Education / Wealth quintile | 320 / 320、1,260 / 317、1,325 / 265 |
  | `dhs_h8_PR_IDLC_W_MNA_total.json` | `PR_IDLC_W_MNA` | （Total） | 320 / 320 |
  | `dhs_h8_PR_DESC_W_WNM_total.json` | `PR_DESC_W_WNM` | （Total 15-49） | 322 / 322 |
  | `dhs_h8_CM_ECMR_C_U5M_{total,education,wealth_quintile}.json` | `CM_ECMR_C_U5M` | Total / Education / Wealth quintile | 658 / 329（Total は 5 年版＋10 年版の 2 行/調査）、1,096 / 329、1,456 / 292（内訳は 10 年版のみ） |
  | `dhs_h8_MA_AAFM_W_M2B_{total,education,wealth_quintile}.json` | `MA_AAFM_W_M2B` | Total / Education / Wealth quintile | 326 / 326、1,111 / 329、1,348 / 275 |
  | `dhs_h8_MA_MBAG_W_NMA_{total,age_5_year_groups}.json` | `MA_MBAG_W_NMA` | Total 25-49 / `Age (5-year groups)` | 330 / 330、2,308 / 330 |
  | `dhs_h8_MA_MSTA_W_UNI_{total,age_5_year_groups}.json` | `MA_MSTA_W_UNI` | Total 15-49 / `Age (5-year groups)` | 332 / 332、2,322 / 332 |
  | `dhs_h8_ED_EDUC_W_SEH_total.json` | `ED_EDUC_W_SEH` | （Total 15-49） | 345 / 345 |
  | `dhs_h8_FP_CUSM_W_MOD_{total,education}.json` | `FP_CUSM_W_MOD` | Total / Education | 324 / 324、1,242 / 324 |
  | `dhs_h8_EM_EMPL_W_EMC_{total,education,wealth_quintile}.json`（H8b、2026-10-17 取得） | `EM_EMPL_W_EMC`（過去 12 か月に働き現在も働いている女性 % → `women_employed`） | Total 15-49 / Education / Wealth quintile | 262 / 262、1,022 / 262、1,310 / 262（76 か国、1994–2024）。**内訳指定なし（`breakdown=all` のみ）は 12,906 行で 2 ページ以上になるため呼ばない** |
  | `dhs_h8_EM_EMPM_W_EMP_total.json`（H8b） | `EM_EMPM_W_EMP`（既婚女性の過去 12 か月就業率 → `married_employed`） | （Total 15-49） | 254 / 254（77 か国） |
  | `dhs_h8_EM_ERNM_W_CSH_total.json` / `dhs_h8_EM_ERNM_W_CAK_total.json`（H8b） | `EM_ERNM_W_CSH` / `EM_ERNM_W_CAK`（就業した既婚女性のうち現金のみ／現金＋現物の報酬 → `married_cash_only` / `married_cash_inkind`） | （Total 15-49） | 204 / 204（71 か国）、202 / 202（70 か国）、1999– |
  | `dhs_h8_ED_NARP_B_BTH_total.json` / `dhs_h8_ED_NARS_B_BTH_total.json`（H8b） | `ED_NARP_B_BTH` / `ED_NARS_B_BTH`（世帯の子どもの初等／中等純就学率 → `child_primary_attendance` / `child_secondary_attendance`） | （Total） | 182 / 182（68 か国、1999–2025）ずつ |
- レコード構造（H4 の主フィールドに加えて使うもの）: `ByVariableLabel`（文字列。U5MR の Total は "Five years preceding the survey" と "Ten years preceding the survey" の 2 行/調査、他は空）、`IsPreferred`（int。U5MR では 5 年版が 1、10 年版が 0）、`IsTotal`。Total 行の `CharacteristicCategory`/`CharacteristicLabel` は指標により "Total" / "Total 15-49" / "Total 25-49" と異なり、mart の `characteristic_category` にそのまま入れる。`CILow`/`CIHigh`/`DenominatorWeighted` は指標により数値文字列が入る（U5MR の CI、婚姻指標の分母など）。
- 変換: `dhs.mechanism_rows`（`METRICS` にある IndicatorId の行だけ、内訳はリクエストしたカテゴリ＋Total 系のみ通す。ISO3 の無い国コードの行は落とし skipped に残す）→ `staged/dhs/mechanisms`（全 raw を 1 表に結合。raw が欠けた分は skipped）→ `marts/dhs_mechanisms`（`survey_year, iso3, survey_id, metric, characteristic_category, characteristic_label, by_variable` でソート。キー重複は `ValueError`）。列は `iso3, country, dhs_country_code, survey_id, survey_year, survey_type, indicator_id, metric, characteristic_category, characteristic_label, by_variable, is_preferred, value, ci_low, ci_high, denominator_weighted, source`。
- 引用義務は H4 と同じ（`dhs.LICENSE`、[Accessed 10-17-2026] 相当。manifest に残す）。raw はコミットしない。2026-10-17 時点で ISO3 の付かない国コードは H8 の 30 レスポンス中に無い（87 国コードすべてに ISO3 あり）。H8b 追加後の `marts/dhs_mechanisms` は 26,270 行・374 調査・87 か国（調査数は増えない。H8b の指標は 1994 年以降の調査のみ）。
- 既知の注意: `FE_FRTR_W_TFR × Wealth quintile` は H4 と同一リクエストで、raw を 2 つの名前で保存する（H4 側の raw・staged・mart は無変更）。学歴ラベルは `No education / Primary / Secondary / Higher` の 4 群（`Higher` が無い調査あり）。U5MR の Education / Wealth 内訳は 10 年版しか返らないため、Total と内訳を比べるときは `by_variable` をそろえる。

### Eurostat dissemination API（JSON-stat 2.0）— 欧州の学歴別 有配偶率・出生順位別／学歴別 TFR（growth-fertility H5）
- URL / API: `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/<dataset>?format=JSON&lang=EN&geo=<geo>&<dim>=<code>…`（同一次元の複数値は引数を繰り返す。`sinceTimePeriod=<year>` で開始年）。**API キー不要**。レスポンスは JSON-stat 2.0（`class: "dataset"`, `id`（次元順）, `size`, `dimension.<d>.category.index`（code→位置）, `value` は**疎な dict（文字列セル番号→値）**、`status` に欠損フラグ）。エラーは `{"error": …}` の JSON。`theme_growth_fertility.eurostat.jsonstat_rows` が各セルを次元コード dict に展開し、`value` に無いセルは出さない（補完しない）。`error` / `class != dataset` / `id`・`size`・`value` 欠落 / 次元サイズ不一致は `ValueError`（fail-closed）。
- 採用 dataset（2026-10-06 に実レスポンスで次元コードを確認）。すべて国別に 1 リクエスト（raw `eurostat_<dataset>_<geo>.json`）:
  | dataset | 次元（`id` 順） | 絞り込み | 対象国 | 年 |
  |---|---|---|---|---|
  | `cens_21me_r2` | freq.isced11.marsta.age.sex.unit.geo.time | sex=M,F; age=Y25-29…Y55-59（7 階級）; marsta=TOTAL,MAR_REP,UNK; isced11 全部（TOTAL, ED0…ED8, NAP, UNK） | EU27＋EFTA（IS NO CH LI）の 31 か国。geo は 2 文字の国コードのみ採用（NUTS 行は落とす） | 2021 |
  | `demo_fordagec` | freq.unit.age.ord_brth.geo.time | age=Y15…Y49（1 歳刻み 35 本）＋UNK; ord_brth 全部（TOTAL,1,2,3,GE4,UNK） | FI SE NO DK IS DE FR IT ES NL HU CZ PL | 2005– |
  | `demo_pjan` | freq.unit.age.sex.geo.time | sex=F; age=Y15…Y49 | 同上 | 2005– |
  | `demo_faeduc` | freq.unit.age.isced11.geo.time | age=1 歳刻み Y15…Y49 ＋ 5 歳階級 Y15-19…Y45-49 ＋ UNK（国により片方しか無い。FI は 1 歳刻みのみ）; isced11 全部（TOTAL, ED0-2, ED3_4, ED5-8, NAP, UNK） | FI SE NO DK IS NL BE AT | 2007– |
  | `lfsa_pgaed` | freq.unit.sex.age.isced11.geo.time | sex=F; age=Y15-19…Y45-49; isced11=ED0-2,ED3_4,ED5-8,TOTAL（単位 THS_PER＝千人） | 同上 | 2007– |
- geo → ISO3 は固定辞書 `eurostat.GEO_TO_ISO3`（EU27＋EFTA＋UK。`EL`→GRC、`UK`→GBR）。pycountry は使わない。
- ライセンス・利用規約（確認日 2026-10-06、`https://ec.europa.eu/eurostat/web/main/help/copyright-notice`）: Eurostat のデータは出典を明記すれば商用を含め自由に再利用・改変・配布できる（Commission Decision 2011/833/EU）。第三国（非 EU/EFTA）データは権利者の条件が別だが、本件は EU/EFTA のみ。出典表記: 「Source: Eurostat, <dataset>（accessed 2026-10-06）」。raw はコミットしない。
- 取得方法: `theme_growth_fertility.eurostat`（`Request` の URL 組み立て、`jsonstat_rows`、`census_rows` 等の純粋変換、`build_census_mart` / `build_tfr_by_order` / `build_tfr_by_education` の純粋集計）＋ `pipeline._fetch_h5` / `_stage_h5` / `_mart_h5`（`HttpxFetcher`）。**73 リクエスト**（31 ＋ 13×2 ＋ 8×2、各 10KB〜数百 KB）。公開レート制限なし（Eurostat は 1 リクエストあたりセル数上限あり → 国別分割）。再取得は年 1 回程度。
- 既知の欠損・断絶・定義変更:
  - センサスの配偶関係は法律婚＋登録パートナー（`MAR_REP`）のみで同棲を含まない（北欧の有配偶率を過小評価）。学歴 UNK/NAP は群に入れない。`total` は TOTAL − 配偶関係 UNK。
  - `demo_fordagec` の出生順位 UNK は TFR の順位別分解に含めず別行（`order="UNK"`）で保持。母の年齢 UNK の出生は TFR から落とし `births_age_unknown` に件数を残す。
  - `demo_faeduc` は国により 1 歳刻みと 5 歳階級の公開が異なる。mart では 5 歳階級セルが無ければ 1 歳刻み 5 本の合計を使う（5 本そろわなければ落とす）。
  - `lfsa_pgaed` は標本（LFS）由来で小さいセルは非公表（`value` 欠落、`status: u/b`）。分母が無く出生 > 0 の階級がある年・学歴群は落とす（補完しない）。出生 0 の階級は分母が無くても寄与 0。
  - 出生の 2024 年値は国により未公表。学歴別出生（`demo_faeduc`）は提供国が限られる（北欧以外は試行取得し、データがあれば残す）。
### 国家データ処（韓国）— 신혼부부통계（新婚夫婦統計）報道資料 PDF（growth-fertility H5: 韓国の所得区間別 有子率）
- URL / API:
  - 掲示板: `https://mods.go.kr/board.es?mid=a10301010000&bid=11815`（報道資料。検索語「신혼부부」で各年の「<year>년 (기준) 신혼부부통계 결과」投稿を特定。2026-10-06 時点の `list_no`/`seq`（pdf 添付）は `theme_growth_fertility.kostat.RELEASES` に固定）:
    | 基準年 | URL |
    |---|---|
    | 2015 | `https://mods.go.kr/boardDownload.es?bid=11815&list_no=358364&seq=5` |
    | 2016 | `…list_no=365445&seq=15` |
    | 2017 | `…list_no=371980&seq=2` |
    | 2018 | `…list_no=379256&seq=10` |
    | 2019 | `…list_no=386554&seq=2` |
    | 2020 | `…list_no=415466&seq=2` |
    | 2021 | `…list_no=422173&seq=1` |
    | 2022 | `…list_no=428407&seq=3` |
    | 2023 | `…list_no=434122&seq=3` |
    | 2024 | `…list_no=442387&seq=3` |
  - KOSIS OpenAPI はキー必須のため使わない。PDF は静的 URL、キー不要、各 1.5–3.7 MB。robots.txt（`https://mods.go.kr/robots.txt`、2026-10-06）: `User-agent: *` は `/ksows/wisenut/` のみ Disallow、Googlebot 向けに `/board.es?mid=b20306000000&bid=601` を Disallow。`boardDownload.es` と当該掲示板は許可。
- 対象指標・粒度: 基準年 × 所得区間（전체 / 1천만원 미만 / 1천만~3천만 / 3천만~5천만 / 5천만~7천만 / 7천만~1억 / 1억원 이상。万ウォン単位の下限・上限に変換、上限なしは NULL）。値: 부부 수（쌍）, 자녀있음 %, 1명 %, 2명 %, 3명 이상 %, 평균 자녀 수。**母集団**: 基準年 11 月 1 日時点で婚姻 5 年以内・婚姻継続中・両者国内居住の**初婚**夫婦（`population = first_marriage_within_5y`）。**所得概念**: 夫婦合算の年間 근로＋사업소득（`income_concept = earned_business`）。**2015 年基準の断絶**: 2015 年基準報道資料は健康保険職場加入者の**賃金勤労者**夫婦（852,618 쌍）のみを所得区間別に集計 → `income_concept = wage_only`。2016 年基準資料が 2015 年を 근로＋사업소득 ベース（1,179,000 쌍）で再掲しているため、2015 年は両概念の行が存在する。各資料は前年も再掲するので、mart では (ref_year, income_concept) ごとに**最新の資料**を採用する。
- ライセンス・利用規約（確認日 2026-10-06、`https://mods.go.kr/menu.es?mid=a10706000000` 저작권정책）: 報道資料は **공공누리（KOGL）제1유형（출처표시）**（`https://www.kogl.or.kr/info/license.do`）。出典表示のみで商用・改変可。出典表記: 「국가데이터처, 신혼부부통계（<year>년 기준）, 보도자료, mods.go.kr」。`kostat.LICENSE` に記載し manifest に残す。raw（PDF）はコミットしない。
- 取得方法（adapter 名、レート制限）: `theme_growth_fertility.kostat`（`RELEASES`、`pdf_text`（pypdf）、`find_income_children_table`、`income_children_rows` の純粋変換）＋ `pipeline._fetch_kostat` / `_stage_kostat` / `_mart_kostat`（`HttpxFetcher`）。**10 リクエスト（計 ~22 MB）**。raw は `data/raw/growth-fertility/kostat_newlywed/newlywed_<ref_year>.pdf`、staged は `staged/kostat/newlywed_income_children`、mart は `marts/kr_newlywed_income_children`。公開レート制限なし。再取得は年 1 回（12 月の公表後）。
- 既知の欠損・断絶・定義変更:
  - 表のレイアウトは 3 系統（2015: 行＝所得区間・実数＋構成比、2016–2019: 行＝所得区間・構成比＋千쌍、2020–2024: 列＝所得区間・年ブロック）。`kostat.py` はこの 3 系統のみ解析し、見出し・行数・合計（区間の合計＝全体、자녀없음＋자녀있음＝100、1명＋2명＋3명 이상＝자녀있음）が合わないときは `ValueError` → stage の skipped に「`newlywed_<year>.pdf: layout not recognised (<reason>)`」として残す（補完しない）。
  - 2016–2020 年基準資料の 부부 수 は**千쌍単位**（2016–2018 は小数 1 桁、2019–2020 は整数）→ ×1000 で쌍に換算。2021 年以降と 2015 年は実数。最新資料優先のため、mart で千쌍由来なのは 2015（earned_business）・2016・2017・2018 年の行のみ。
  - 共稼ぎ（맞벌이）別・婚姻年次別の平均子ども数は資料にあるが未取込（任意項目）。所得は夫婦合算で、共稼ぎと所得が同時決定（`design/themes/growth-fertility.md` H5 の限界）。
  - 2018 年基準 PDF は本文フォントが抽出で文字化けするが、表部分は正常に抽出される。

### 教育部（韓国）— 초중고 사교육비조사（初中高 私教育費調査）報道資料 PDF（growth-fertility H8d-K: 学校外教育費）
- URL / API:
  - 掲示板（보도자료、検索語「사교육비」）: `https://www.moe.go.kr/boardCnts/listRenew.do?boardID=294&m=020402&s=moe&searchType=S&searchStr=%EC%82%AC%EA%B5%90%EC%9C%A1%EB%B9%84`。掲示 boardSeq=105597「2025년 초중고 사교육비 조사 결과」（2026-03-12 公表、교육부・국가데이터처 共同）。
  - PDF（固定 URL、`theme_growth_fertility.moekr.URL`）: `https://www.moe.go.kr/boardCnts/fileDown.do?m=020402&s=moe&fileSeq=7562a697bdba006065fa92054b1d634e`（2026-10-17 確認: 200、`application/octet-stream`、2.77 MB、`%PDF-1.6`、51 ページ、sha256 `0beaa654…`）。KOSIS OpenAPI はキー必須のため使わない。
- 表の位置（pypdf 6 の `extract_text`、0 始まりのページ index）:
  - 年次表: index 48（資料の p.44）「21. 연도별 초중고사교육비조사 주요 결과 및 증감률」。列 = 연도 / 총액(억원) / 참여율(%) / 참여시간(시간/주) / 학생 1인당 월평균 사교육비(만원) 전체학생 / 참여학생。2007–2025。下段の「< 증감(률) >」ブロックは取り込まない。
  - 자녀수별: index 39–40（統計表 10「자녀수별 전체학생 1인당 월평균 사교육비」、11「자녀수별 사교육 참여율」）。列 = 전체 / 1명 / 2명 / 3명 이상、行 `< 2024 >`・`< 2025 >`（科目・参加類型別の内訳行は取り込まない）。本文 <표13>（index 16）と同じ値。
  - 학교급별: index 7–9 の本文 <표1>（총액）、<표2>（참여율・주당 참여시간）、<표4>（1인당 월평균、전체학생・참여학생）、2024・2025 年のみ。학교급別の年次系列は資料に無い。
- 対象指標・粒度: `marts/kr_private_tutoring`（long）: year × table(annual / by_children / by_level) × group(총계 / 자녀 1명 / 자녀 2명 / 자녀 3명 이상 / 초등학교 / 중학교 / 고등학교) × metric(total_100m_krw / participation_rate_pct / hours_per_week / spend_per_student_10k_krw / spend_per_participant_10k_krw)。値は**名目**（CPI 未取込。所得比は WDI 一人当たり GDP で代替、H8d Z5）。母集団: 全国初中高の在学生（表本 約 3,000 校・74,000 人、保護者回答）。사교육비 = 正規課程外に学校外で個人が支出する補習教育費（늘봄·방과후학교、EBS 教材、語学研修は別項目で含まない）。
- ライセンス・利用規約（確認日 2026-10-17）: 교육부 報道資料は **공공누리（KOGL）제1유형（출처표시）**（`https://www.kogl.or.kr/info/license.do`）。出典表記: 「교육부, 2025년 초중고 사교육비 조사 결과 보도자료（2026-03-12）, moe.go.kr（KOGL 제1유형）」。`moekr.LICENSE` に記載し manifest に残す。raw（PDF）はコミットしない。
- 取得方法（adapter 名、レート制限）: `theme_growth_fertility.moekr`（`annual_rows` / `by_children_rows` / `by_level_rows` / `private_tutoring_rows_from_pages` / `build_mart` の純粋変換、`kostat.pdf_text` を再利用）＋ `pipeline._fetch_h8d_k` / `_stage_h8d_k` / `_mart_h8d_k`（`HttpxFetcher`）。**1 リクエスト（2.8 MB）**。raw は `data/raw/growth-fertility/moe_kr/private_tutoring_2025.pdf`、staged は `staged/moe_kr/private_tutoring`、mart は `marts/kr_private_tutoring`。公開レート制限なし。再取得は年 1 回（3 月の公表後、`fileSeq` を掲示板で確認して `moekr.URL` を更新）。
- 既知の欠損・断絶・定義変更:
  - **2020 年**: COVID-19 で総額 −7.8%・参加率 −7.7%p と落ち込み、2021 年に反発（+21.0%）。時系列の図では明示する。
  - **2017 年**から「참여학생 1인당 월평균 사교육비」を追加（2007–2016 は `-` → 行なし。補完しない）。
  - **영유아**（就学前）と **재수생**（高卒後の受験生）は調査対象外。2018 年から成績区間は高校生のみ調査（本 mart では未取込）。
  - 解析は fail-closed: 見出し不一致・年の連番外・列数不一致・数値変換不可・各表の 전체 列が年次表と不一致のときは `ValueError` → stage の skipped に「`private_tutoring_2025.pdf: layout not recognised (<reason>)`」として残す。
  - 家計所得区間別（統計表 6–7）・親の就業状態別（8–9）は資料にあるが未取込（任意項目）。

### Testa (2012) / Eurobarometer 75.4 と BiB (2025) / GGS-II — 理想・意図・実際の子ども数（growth-fertility H6）
- URL / API:
  - Testa, M.R. (2012) *Family sizes in Europe: evidence from the 2011 Eurobarometer survey*. VID European Demographic Research Paper 2: `https://www.oeaw.ac.at/fileadmin/subsites/Institute/VID/PDF/Publications/EDRP/edrp_2012_02.pdf`（100 ページ、~1 MB）。付表 A.1.1（低/高の個人理想、両性、15–39 歳・55 歳以上）、A.2.1–A.2.4（一般理想・個人理想・実際・追加意図の平均、国 × 性 × 年齢 15–24/25–39/40–54/55+/Total）、A.2.5–A.2.8（同じ 4 指標の分布 0/1/2/3+/[理想なし]/DK と N）。
  - Bundesinstitut für Bevölkerungsforschung (2025) *Intended, ideal and actual fertility in 11 European countries: Evidence on fertility gaps in different age groups from the Generations and Gender Survey*, BiB Working Paper: `https://www.bib.bund.de/Publikation/2025/pdf/Intended-ideal-and-actual-fertility-in-11-European-countries-Evidence-on-fertility-gaps-in-different-age-groups-from-the-Generations-and-Gender-Survey.pdf?__blob=publicationFile&v=2`（31 ページ、~1.8 MB）。Table 1（p. 14）: DE AT NL CZ HR EE NO DK FI MD UK × 年齢（18–29/30–39/40–49/Total）× {意図−実際, 理想−実際, 理想−意図 のギャップ, 実際, 意図（合計）, 個人理想 の平均} ＋ Observations、注記に国別の調査年（GGS-II DE 2021–22, AT 2022–23, NL 2022–23, CZ 2020–22, HR 2023, EE 2021–22, NO 2020, DK 2021, FI 2021–22, MD 2020, UK 2022–23）。
  - マイクロデータ（GESIS EB、GGP、ESS、EVS）は登録制のため使わない。
- 対象指標・粒度: `marts/eu_fertility_ideals`（long）。EB2011: iso3（EU-27、ドイツは全体行。東西別・EU-27 行は落とす）× sex（F/M、A.1.1 のみ T）× age_class × metric[`ideal_general_mean` / `ideal_personal_mean` / `actual_mean` / `intended_additional_mean` / `ideal_zero_share`（個人理想 0 の %）/ `ideal_low_share`（0＋1 の %）/ `ideal_high_share`（3+ の %）/ `ideal_general_zero_share` / `childless_share` / `intended_additional_zero_share`]、分布由来の行には N。GGS2020: iso3 × F × age_class × metric[`actual_mean` / `intended_total_mean` / `ideal_personal_mean` / `gap_intended_actual` / `gap_ideal_actual` / `gap_ideal_intended`]、Total 行に N、`survey_year` は調査開始年。割合は**%**（出典のまま）。
- ライセンス・利用規約（確認日 2026-10-06）: Testa 2012 は VID/ÖAW のワーキングペーパーでライセンス未明示 → 事実（数値）を出典明記で転記するに留め、PDF は再配布しない（raw は gitignore）。基データの Eurobarometer 75.4 は欧州委員会（CC BY 4.0）。BiB 2025 は本文に CC BY-SA 4.0 の表記あり（p. 2）。両者の文言は `surveys.TESTA_LICENSE` / `surveys.BIB_LICENSE` に記載し manifest に残す。出典表記: 「Testa, M.R. (2012) Family sizes in Europe: evidence from the 2011 Eurobarometer survey. VID EDRP 2（data: Eurobarometer 75.4, European Commission）」「BiB (2025) Intended, ideal and actual fertility in 11 European countries, BiB Working Paper（data: GGS-II, CC BY-SA 4.0）」。
- 取得方法（adapter 名、レート制限）: `theme_growth_fertility.surveys`（`eb2011_rows` / `ggs_rows` / `build_ideals_mart` の純粋変換、pypdf）＋ `pipeline._fetch_h6` / `_stage_h6` / `_mart_h6`。2 リクエスト。raw は `data/raw/growth-fertility/testa2012_eb75_4/testa2012_edrp_2012_02.pdf`、`.../bib2025_ggs2/bib2025_ggs2_fertility_gaps.pdf`。staged は `staged/surveys/eb2011_ideals`、`staged/surveys/ggs2020_ideals`。再取得不要（固定文書）。
- 既知の欠損・断絶・定義変更:
  - pypdf の抽出で数値内に空白が入る（「2. 07」）→ 正規化。「United Kingdom」が「United」に、「Czech Rep.」が「Czech」に切れることがある → 別名で補う。分布表の 4 行（A.2.6 イタリア男性 15–24、A.2.8 マルタ 3 ブロック）は数字が混線して読めないため**行を落とし** stage の skipped に「garbled row」として残す（推定しない）。平均表は 27 か国 × 10 列がそろわなければ `ValueError`（fail-closed）。
  - EB の「追加意図」（additionally intended）と GGS の「意図（合計）」（intended total）は定義が異なる。EB の理想は 15 歳以上全体、GGS は女性 18–49。質問文・母集団が異なるため**水準の比較はできない**（H6 の仮定を参照）。
  - A.1.1 は両性合計で年齢 15–39/55+ のみ、N なし。GGS の N は国合計のみ（年齢別 N は非掲載）。

### Standard Eurobarometer（data.europa.eu）— 今後 12 か月の期待（growth-fertility H6）
- URL / API:
  - データセット記録（JSON-LD）: `https://data.europa.eu/api/hub/repo/datasets/<dataset_id>.jsonld`。配布物 `dcat:Distribution` の `dct:title`（"Link to <file>"）で Volume A（`vol(ume)?_A`、AA/AP/AAP/B/C は除外）を選び `dcat:accessURL`（`https://webgate.ec.europa.eu/{ebsm,eurobarometer}/api/public/odp/download?key=<32 hex>`）を取得する。dataset_id は hub 検索 API（`https://data.europa.eu/api/hub/search/search?q=Standard%20Eurobarometer&limit=100`、2026-10-06）で特定し `theme_growth_fertility.eurobarometer.WAVES` に固定（取得時に検索はしない）:
    | 波 | dataset_id | 調査時期（season / fieldwork 開始月） | Volume A の形式 |
    |---|---|---|---|
    | STD91 | `s2253_91_5_std91_eng` | 2019 H1 / 2019-06 | zip（.xls） |
    | STD92 | `s2255_92_3_std92_eng` | 2019 H2 / 2019-11 | zip（.xls、EU27＋UK のみ。候補国は別ファイル、未取込） |
    | STD93 | `s2262_93_1_93_1_eng` | 2020 H1 / 2020-07 | zip（.xlsx） |
    | STD94 | `s2355_94_1_std94_eng` | 2020 H2 / 2021-02（Winter 2020–21） | .xlsx |
    | STD95 | `s2532_95_3_95_eng` | 2021 H1 / 2021-06 | .xlsx |
    | STD96 | `s2553_96_3_std96_eng` | 2021 H2 / 2022-01（Winter 2021–22） | .xlsx |
    | STD97 | `s2693_97_5_std97_eng` | 2022 H1 / 2022-06 | .xlsx |
    | STD98 | `s2872_98_2_std98_eng` | 2022 H2 / 2023-01（Winter 2022–23） | .xlsx |
    | STD99 | `s3052_99_4_std99_eng` | 2023 H1 / 2023-05 | .xlsx |
    | STD100 | `s3053_100_2_std100_eng` | 2023 H2 / 2023-10 | .xlsx |
    | STD101 | `s3216_101_3_std101_eng` | 2024 H1 / 2024-04 | .xlsx |
    | STD102 | `s3215_102_2_std102_eng` | 2024 H2 / 2024-10 | .xlsx |
    | STD103 | `s3372_103_3_std103_eng` | 2025 H1 / 2025-03 | .xlsx |
    | STD104 | `s3378_104_1_std104_eng` | 2025 H2 / 2025-10 | .xlsx |
    | STD105 | `s3613_105_2_std105_eng` | 2026 H1 / 2026-03 | .xlsx（**上流から撤回**: 2026-10-13 時点で JSON-LD 404・download key 500、hub 検索にも無く、`europa.eu/eurobarometer/surveys/detail/3613` の openDataPublicationUrl は null。2026-10-06 取得分の raw 2 ファイルを `committed: true` でコミットし `Wave.withdrawn` で fetch をスキップ） |
  - 2019 春以降で欠けている波はない（2026-10-06）。STD90 以前（2018 年秋まで）は data.europa.eu にあるが未取込（H6 の窓は 2019–）。
- 対象指標・粒度: `marts/eu_expectations`: iso3 × wave × item[`life_general`（Your life in general）/ `household_finance`（The financial situation of your household）/ `national_economy`（The economic situation in (OUR COUNTRY)、STD100 は "The state of (OUR COUNTRY)'s economy"）/ `employment_situation`（The employment situation in (OUR COUNTRY)）] の `better_share` / `worse_share` / `same_share` / `dk_share`（**%**、加重）と `net_optimism = better − worse`。`fieldwork_year`/`fieldwork_half` は波の season（春・夏＝1、秋・冬＝2、冬の波は前年に帰属）で波ごとに一意、`fieldwork_start` は実際のフィールドワーク開始月（YYYY-MM）。国は EU27 ＋ UK・候補国・EFTA 等（波により 28–37 か国）。EU27 集計、D-W/D-E（DE を使う）、XK、CY(tcc) は落とす。
- ライセンス・利用規約（確認日 2026-10-06）: 欧州委員会の再利用方針（Commission Decision 2011/833/EU、`https://commission.europa.eu/legal-notice_en`）＝CC BY 4.0 相当。JSON-LD の `dct:license` も `licence/CC_BY_4_0`。出典表記: 「European Commission, Standard Eurobarometer <wave>, Volume A（data.europa.eu）」。
- 取得方法（adapter 名、レート制限）: `theme_growth_fertility.eurobarometer`（`WAVES`、`vol_a`（JSON-LD → 配布物）、`workbook_sheets`（zip / xlsx=openpyxl read-only / xls=xlrd）、`expectation_rows`、`build_expectations_mart`）＋ `pipeline._fetch_h6` / `_stage_h6` / `_mart_h6`。**28 リクエスト**（JSON-LD 14 ＋ Volume A 14、各 0.4–1 MB、計 ~13 MB。撤回された STD105 は要求しない）。raw は `data/raw/growth-fertility/eurobarometer_std/eb_<code>_meta.json` と `eb_<code>_vol_a.<zip|xlsx>`。staged は `staged/eurobarometer/expectations`。新しい波は hub 検索で dataset_id を確認して `WAVES` に追加する。
- 既知の欠損・断絶・定義変更:
  - シートは質問文（"expectations for the next twelve/12 months"）で探し、英語の項目名で 4 項目に限定する（「国の状況全般」「個人の仕事」「EU の経済」は未取込）。見つからない波は skipped。レイアウト差: STD91–92 は .xls（見出しに "<<Back to content" なし、ラベル TOTAL/DK）、STD93 は仏英ラベルが 1 セル（"Meilleurs\nBetter"）で割合が次行、STD93/STD91 は CY(tcc) 専用シートを別に持つ（国列なしとして無視）。想定外の構造（国見出しなし、回答行欠落、割合が 0–1 でない）は `ValueError` → skipped。
  - STD92 の Volume A 本体は EU27＋UK のみ（候補国は "with CC" ファイル、未取込）。STD100 は 35 か国（CH/NO/IS なし等、波により調査対象国が変わる）。
  - 「−」は回答者 0 を意味し 0 として扱う。割合は Volume A の四捨五入済み整数 %（ごく一部は小数）。
  - 質問は「今後 12 か月の期待」であり不確実性の分散ではない（H6 の限界）。

### UN SDG Global Database（UNSD SDG API）— 無償労働時間の性差・女性管理職割合（growth-fertility H8d: 男女分業の深さ仮説 G）
- URL / API（REST JSON、鍵不要。source-scout が 2026-10-17 に httpx で成功を確認。URL は `theme_growth_fertility.unsdg.SERIES` に固定し改変しない。`pageSize` は全件が 1 ページに収まる値）:
  | raw（`data/raw/growth-fertility/unsdg/`） | URL | 行（うち国・地域） | 内容 |
  |---|---|---|---|
  | `sl_dom_tspd.json`（2.8 MB） | `https://unstats.un.org/sdgapi/v1/sdg/Series/Data?seriesCode=SL_DOM_TSPD&pageSize=5000` | 3,960（3,946、98 か国・地域） | 5.4.1 無償家事・ケア労働時間の 24 時間比 %。`dimensions`: Location(ALLAREA/RURAL/URBAN)、Sex(FEMALE/MALE)、Age（"15+" 628 行が最多。10+/12+/14+/16+/20-74 や 5 歳階級など国で異なる）。`attributes.Nature`: C 国データ 3,544 / CA 国データ調整済み 402 / N 非該当 14（集計地域） |
  | `ic_gen_mgtl.json`（2.2 MB） | `https://unstats.un.org/sdgapi/v1/sdg/Series/Data?seriesCode=IC_GEN_MGTL&pageSize=10000` | 3,472（2,458、195 か国・地域） | 5.5.2 管理職に占める女性割合 %（13th ICLS、ILO 由来）。Sex=FEMALE、Age=15+ のみ、Location 次元なし。Nature N 1,014 行はすべて集計地域 |
  - メタデータ: 応答の `attributes`/`dimensions` にコード表が同梱。シリーズ一覧は `https://unstats.un.org/sdgs/dataportal`。
- 対象指標・粒度: 国 × 年 × 性 × 年齢層 × 地域（long）。`geoAreaCode` は UN M49 数値コードで、`unsdg.M49_TO_ISO3`（本データに出る国・地域 195 件の固定辞書）で ISO3 を付け、辞書に無い集計地域（World、大陸・小地域、LDCs/LLDCs/SIDS、Developed/Developing regions、SDG 地域区分）は落として stage の skipped に列挙する（SL_DOM_TSPD 7 件、IC_GEN_MGTL 39 件）。`value` は文字列で返るので float に変換し、変換できない行は落として skipped に出す（2026-10-17 の実データでは 0 行）。`totalPages != 1`／`totalElements != len(data)`（ページ分割）、他 series の行、`Units != PERCENT`、Sex/Location の閉集合外、非整数年は `ValueError`。年齢層の選択（15+ → 10+ → 20+ → 16+ → ALLAGE、設計 H8d）と `female_share = F/(F+M)` は分析側。結果: `marts/gender_equity` 6,404 行、195 か国・地域、2000–2026（SL_DOM_TSPD 3,946 / IC_GEN_MGTL 2,458）。SL_DOM_TSPD の ALLAREA で F・M がそろう国 × 年は 228（93 か国）、設計の優先年齢層でそろうのは 178 国・年（83 か国、うち 2 時点が 5 年以上離れる国 38）。
- ライセンス・利用規約（確認 2026-10-17）: UN Terms of Use（`https://www.un.org/en/about-us/terms-of-use`、UN サイト全体の一般規約）と UNdata Terms of Use（`https://data.un.org/Host.aspx?Content=UNdataUse`、出典引用で複製・再配布可）が食い違う。**raw はコミットしない**（manifest のみ、`unsdg.LICENSE` に両 URL を記録）、staged/marts は集計統計の派生物として出典明記で保持する。出典表記: 「United Nations Statistics Division, SDG Global Database (Series SL_DOM_TSPD, IC_GEN_MGTL), https://unstats.un.org/sdgs/dataportal (accessed 2026-10-18)」。
- 取得方法（adapter 名、レート制限）: `theme_growth_fertility.unsdg`（`SERIES`・`M49_TO_ISO3`・`parse`・`build_mart` の純粋変換、Pydantic で検証し fail-closed）＋ `pipeline._fetch_h8d / _stage_h8d / _mart_h8d`（`HttpxFetcher`）。**2 リクエスト（計 ~5 MB）**。staged は series ごと `staged/unsdg/{sl_dom_tspd,ic_gen_mgtl}`、mart は `marts/gender_equity`（ある staged だけを結合、キー `(iso3, year, series, sex, age, location)` 一意）。公開レート制限なし。再取得は年 1 回程度（SDG 報告の更新時）。
- 既知の欠損・断絶・定義変更:
  - 無償労働の測り方は国で異なる（調査設計・年齢下限・ICATUS 調整の有無）。年齢層は ESP 20-74 のみ、KOR 2004・2009 と DEU 2002 は 10+ のみ、SWE 2001 は 20+ のみ、NOR 2001 は 16+ のみ、JPN は 10+ と 15+ の両方（2001/2006/2011/2016/2021、総務省 社会生活基本調査）。
  - 日本の男性値は `Nature=C` のまま極端に低い（例 2021 年 15+ 男性 3.75 % vs 女性 14.71 %、USA 男性 10.1 %）。定義差とみて主指標は差ではなく比 `F/(F+M)`、日本除外を頑健性に（設計 H8d）。
  - GBR に year 2026 の行がある（上流の時点表記、そのまま保持。分析で 2000 年以降の最新年を取るときに注意）。
  - IC_GEN_MGTL は ILO モデル推計ではなく国データ（Nature C）のみが国・地域行に残る。

### UNDP Human Development Report 2025 — 複合指数の時系列 CSV（growth-fertility H8d: GII と構成要素）
- URL / API: 静的 CSV `https://hdr.undp.org/sites/default/files/2025_HDR/HDR25_Composite_indices_complete_time_series.csv`（2.0 MB、**latin-1**。`hdr.URL` に固定、鍵不要。source-scout が 2026-10-17 に httpx で成功を確認）。列定義は `https://hdr.undp.org/sites/default/files/2025_HDR/HDR25_Composite_indices_metadata.xlsx`（取得しない、リンクのみ `hdr.METADATA_URL`）。
- 対象指標・粒度: wide（206 行 × 1,112 列: `iso3, country, hdicode, region, hdi_rank_2023, hdi_1990…, gii_1990…gii_2023, gii_rank_2023, mmr_YYYY, abr_YYYY, se_f_YYYY, se_m_YYYY, pr_f_YYYY, pr_m_YYYY, lfpr_f_YYYY, lfpr_m_YYYY, …`）→ long（国 × 年 × metric）。取り込む metric は `gii`（ジェンダー不平等指数）, `mmr`（妊産婦死亡率）, `abr`（15–19 歳出生率）, `se_f`/`se_m`（中等教育以上の割合 25 歳以上、%）, `pr_f`/`pr_m`（議席割合 %）, `lfpr_f`/`lfpr_m`（労働力率 %）の 9 本。`<metric>_<YYYY>` の列だけを正規表現で拾い、`gii_rank_2023`・`hdi_*`・`hdicode`・`region` などは無視。`iso3` が 3 大文字でない集計行（`ZZA.VHHD` 〜 `ZZK.WORLD` の 11 行: 人間開発 4 区分・地域 6・World）は落として skipped に列挙。空セルは行を作らない。非数値セル・ヘッダ欠落・metric 列ゼロは `ValueError`。結果: `marts/hdr_gender` 51,522 行、195 か国、1990–2023（gii 4,600 行・172 か国 / mmr 6,256 / abr 6,630 / se_f・se_m 5,623 / pr_f・pr_m 6,135 / lfpr_f・lfpr_m 5,260）。
- ライセンス・利用規約（確認 2026-10-17）: **CC BY 3.0 IGO**（`https://hdr.undp.org/terms-use`）。raw はコミットしない（manifest のみ）。出典表記: 「UNDP (2025), Human Development Report 2025, composite indices time series, https://hdr.undp.org (accessed 2026-10-18), CC BY 3.0 IGO」。
- 取得方法（adapter 名、レート制限）: `theme_growth_fertility.hdr`（`URL`・`METRICS`・`parse`・`build_mart` の純粋変換）＋ `pipeline._fetch_h8d / _stage_h8d / _mart_h8d`。**1 リクエスト**。staged `staged/hdr/composite`、mart `marts/hdr_gender`（キー `(iso3, year, metric)` 一意）。再取得は年 1 回（HDR 刊行時。ファイル名に年が入るので新版は `hdr.URL` の更新が必要）。
- 既知の欠損・断絶・定義変更:
  - GII は 172 か国のみ（構成要素が欠ける国は空）。`mmr`・`abr` は TFR と機械的に関係するので判定には使わない（設計 H8d Z4）。GII 総合も Z4 では使わない。
  - 国名は UNDP 表記（例 "Korea (Republic of)", "Türkiye", "Côte d'Ivoire"）。latin-1 で復号するので UTF-8 として読むと壊れる。
  - 値は HDR 2025 時点の改訂済み系列で、過去版 HDR の数値とは一致しない。

### Special Eurobarometer 253（data.europa.eu）— 2006 年の理想子ども数（growth-fertility H9）
- URL / API: データセット記録（JSON-LD）`https://data.europa.eu/api/hub/repo/datasets/s406_65_1_ebs253.jsonld`（dataset_id は `theme_growth_fertility.eurobarometer.SPECIAL_WAVES` に固定、2026-10-18 確認）。配布物 5 件のうち使うのは 2 件（`special_volumes` が英語タイトルの正規表現で各 1 件に解決、`dcat:accessURL` = `https://webgate.ec.europa.eu/eurobarometer/api/public/odp/download?key=<32 hex>`）:
  | raw（`data/raw/growth-fertility/eurobarometer_special/`） | 配布物 | 内容 |
  |---|---|---|
  | `eb_EBS253_meta.json`（128 KB） | JSON-LD | 記録そのもの |
  | `eb_EBS253_vol_c.zip`（3.1 MB、key `1DDE…2467`） | `OP_VolumesCEB651EMPLageingandfertilityxls_v1.zip` = **EB65.1 Volume C**、国別 29 xls（EU-25 ＋ D-E/D-W、GB/NI） | QC2 一般理想・QC3 個人理想 × 国計／性／年齢 4 階級ほか（フィールドワーク 2006-02〜03） |
  | `eb_EBS253_vol_a.zip`（98 KB、key `2ED5…B58E`） | `OP_VolumeAEB653EMPLfertility20060627.zip` = **EB65.3 Volume A**（xls 1 件） | QE2/QE3 × 候補国 BG/RO/HR/TR（2006-05〜06） |
  - 使わない配布物: EB65.1 **Volume A'**（`OP_VolumeAPEB651…`、QC4〜QC9a のトレンド表のみで理想数は無い。記録に EU-25 の Volume A 本体は存在しない）、EB65.3 Volume AA（キプロス北部）、Volume B（社会人口属性別、国別なし）。
- 対象指標・粒度: `staged/surveys/eb2006_ideals` → `marts/eu_fertility_ideals` の `source=eb2006`（2,864 行、29 か国 × (T/total, M/total, F/total, T/15-24, T/25-39, T/40-54, T/55+) × 16 metric。候補 4 か国は T/total のみ）。metric は `ideal_personal_mean` / `ideal_general_mean`（「理想なし」「DK」を除いた加重平均。回答は 0〜6 と「6 より多い」で、5・6 は額面、「6 より多い」= 7。設計 H9 の「4+ を 4」は表が 4+ で打ち切られている前提だったが実表は 6 まで分かれている）と分布 `ideal_{zero,one,two,three,four_plus,no_ideal,dk}_share`（全回答者比 %、計数から再計算）、一般理想は `ideal_general_` 接頭。`n` は加重 TOTAL。**性 × 年齢の交差（女性 25–39）は Volume C に無い**（H9 V1 は T/25-39 と F/total で代替し限界に書く）。
- ライセンス・利用規約（確認日 2026-10-18）: 欧州委員会 再利用方針（Decision 2011/833/EU、CC BY 4.0 相当）。出典表記: 「European Commission, Special Eurobarometer 253 (EB65.1/65.3, 2006), Volume A/C (data.europa.eu)」。raw はコミットしない（manifest のみ）。
- 取得方法（adapter 名、レート制限）: `theme_growth_fertility.eurobarometer`（`SPECIAL_WAVES`、`special_volumes`、`zip_workbooks`）＋ `eb_ideals.ideal_rows` ＋ `pipeline._fetch_h9_eb / _stage_h9_eb`（mart は `_mart_h6` が第 3 のソースとして結合）。**3 リクエスト（計 ~3.3 MB）**。
- 既知の欠損・断絶・定義変更:
  - 準国家ファイル D-E / D-W（ドイツ東西）、GB / NI（英国）は落として skipped に出し、DE / UK の国別ファイルを使う。
  - 回答行は仏語（加重計数）→英語（割合）の順序対で読む。「Six」は両言語同形なので順序で対応付ける。計数は四捨五入済みで Σ ≠ TOTAL（差 ±2 % ＋ 2 まで許容、それ以上は ValueError）。
  - 2006（EB253、15 歳以上）・2011（EB75.4、Testa 2012 転記）・2020–23（GGS-II、女性 18–49）は質問文・母集団・集計者が異なる（H9 の限界）。

### OECD Family Database SF2.5 — コーホート別 定義的無子率（growth-fertility H9）
- URL / API: 静的 xlsx `https://webfs.oecd.org/Els-com/Family_Database/SF_2-5-Childlessness.xlsx`（66 KB、`oecd_family.URL` に固定。source-scout が 2026-10-18 に httpx で 200 を確認）。
- 対象指標・粒度: `marts/oecd_childlessness`（long: iso3, cohort, metric, value, chart, source。199 行、25 か国）。Chart SF2.5.A = 国 × 出生コーホート（1935/1940/1945/1950/1955/1960/1963/1964/1965/1970/1975）の定義的無子率 %（159 行）。Chart SF2.5.B = 1975 年生まれコーホートの無子率と完結出生率（20 か国 × 2）。
- ライセンス・利用規約（確認日 2026-10-18）: OECD Terms & Conditions（`oecd.LICENSE`、CC BY 4.0）。出典表記: 「OECD Family Database, SF2.5 Childlessness (accessed 2026-10-18)」。raw はコミットしない。
- 取得方法（adapter 名、レート制限）: `theme_growth_fertility.oecd_family`（`parse`・`build_mart`、openpyxl）＋ `pipeline._fetch_h9_oecd / _stage_h9_oecd / _mart_h9_oecd`。**1 リクエスト**。
- 既知の欠損・断絶・定義変更:
  - 非加盟国 China・Bulgaria と "England and Wales"（国ではない）は落として skipped に出す。Chart B の Poland 重複行（同値）は 1 回だけ保持。
  - 表の注記どおり一部セルは隣接コーホートの値: 1975 列は KOR・SVK = 1970 コーホート、DEU = 1975–77 年生まれ、ITA = 1978、FRA = 推計; 1955 列は ITA = 1950、FRA = 1951–55、DEU = 1954–56、POL = 1956、ESP = 1960、FIN = 1967、SVN = 1968、AUT = 1969; 1935 列は FRA = 1931–35、HUN = 1937、EST = 1944、NOR = 1952、DNK = 1953、JPN = 1953。KOR はセンサスが既婚・離別・死別女性にしか子ども数を尋ねていない。MEX は 45 歳時点。値はそのまま保持し、分析側で注記する。
  - ITA は Chart A に 1950 と 1975 しか無い（設計 V2 補助の 1955→1975 幅は 1950 起点で代替）。

## 記録テンプレート（ソース採用時）
```
### <ソース名>
- URL / API:
- 対象指標・粒度（国×年 など）:
- ライセンス・利用規約（確認日）:
- 取得方法（adapter 名、レート制限）:
- 既知の欠損・断絶・定義変更:
```
