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
| Merida（9914.TW）連結財務報告 Q4（Specialized 持分法） | FY2023–2025 の Q4 報告 PDF（各報告に前期あり → FY2022–2025）。自社 IR ページは robots 許可、PDF 実体は `merida-cdn.m-c-g.net`（robots 全面 Disallow → **ADR 0006 の例外**）。FY2022 以前の報告は自社サイトに無い | `merida-cdn.m-c-g.net/merida-v2/media-raw/countries/zh-tw/financial-report/<file>.pdf` | 開示書類（出典表示） | **採用**（bicycle-industry H14、2026-10-22、ユーザー承認） |
| Halfords（HFD.L）通期決算発表 PDF | Retail 売上・Cycling 構成比（FY2015–24）・Cycling 売上 £m（FY2025–）。粗利率は年により様式が違い未採用 | `www.halfordscompany.com/media/<id>/<file>.pdf`（robots 許可、投資家ページに静的リンク） | 開示書類（出典表示） | **採用**（bicycle-industry R7 補足、2026-10-22） |
| Accell Group 年報（Wayback） | グループ売上 2010–2021（2017 年報の 8 年表＋2021 年報の 5 年表）。2015・16・19・20 の年報は Wayback で 1 MB 切れ | `web.archive.org/web/<ts>id_/<原 URL>` | 開示書類（出典表示） | **採用（限定）**（bicycle-industry R7 補足、2026-10-22） |
| Bike24（BIKE.DE）IR | EQS の SPA、API は JWT 認証 → 鍵なし取得不可 | — | — | **不可** |
| 台湾 MOPS 月次営業収入 JSON API | Giant・Merida・KMC・Ideal Bike の月次売上（NT$ 千）2014-01〜 | `POST mops.twse.com.tw/mops/api/t05st10_ifrs`（JSON、キー不要） | 公開開示（出典表示） | **採用**（bicycle-industry H10、2026-10-22） |
| SEC EDGAR（Fox Factory 10-K、Specialty Sports Group） | 自転車部品セグメント売上 FY2018– | FilingSummary.xml → R ページ（連絡先付き UA が必須: `SOCIOSCOPE_SEC_CONTACT`） | パブリックドメイン | 候補（未結線。連絡先未設定のためスキップ） |
| 総務省 社会生活基本調査 時系列統計表 | スポーツ種類別 行動者率（男女 × 年齢階級 × 1986–2021、サイクリング含む 23 種目） | e-Stat `statInfId=000032229293&fileKind=0`（xlsx、appId 不要） | 政府標準利用規約 2.0 | **採用**（bicycle-industry H11、2026-10-22） |
| 経産省 生産動態統計（機械統計）年報 | 自転車（軽快車／電動アシスト車／その他／車いす）と自動車（軽・小型・普通乗用車、排気量別二輪）の生産・受入・販売・出荷その他・月末在庫 数量・金額、月次（2021–2025 年報）＋暦年 2017–2023・年度・四半期（2021–2023 年報）。1 ファイル＝全品目 | METI 直置き xlsx（`…/08_seidou/nenpo/<YYYY>/h2daa<YYYY>k.xlsx`、appId 不要）。**非ブラウザ UA は 403** → `Settings.browser_ua_hosts` でこのホストだけブラウザ UA。2007–2020 は業種別 .xls（未対応） | 経産省 利用規約＝政府標準利用規約 2.0 準拠（出典表示、確認 2026-10-22） | **採用**（bicycle-industry ①、2026-10-22） |
| 財務省 貿易統計（e-Stat 配信 CSV、品別国別表） | HS 8712 完成自転車・8714 部品・8711.60 電動二輪・8703 乗用車・8711 二輪の輸出入 数量・金額、国別、月次 1988–・年次 | e-Stat `toukei=00350300`、`file-download?statInfId=…&fileKind=1`（appId 不要）。月次 statInfId は一覧ページから解決が必要。税関サイトの検索も CSV 可（≤3,000 行、Shift_JIS） | 政府標準利用規約 2.0（e-Stat）／税関サイトは公共データ利用規約 PDL1.0（確認 2026-10-22） | 候補（bicycle-industry ②） |
| 総務省 消費者物価指数 **2025 年基準** 品目別 長期時系列（全国） | 自転車（類 0115）、自転車Ａ 7201（1970–）、自転車Ｂ 7202（2015–）、軽乗用車 7105・小型乗用車 7106（1980–）、普通乗用車Ａ 7113・Ｂ 7115（1995–）、総合 0001。2025=100。年平均 1970–2025、月次 1970-01–2026-08。**自動二輪の品目はない** | e-Stat `file-download?statInfId=000040482831`（年）/ `000040482945`（月）`&fileKind=1`（CSV、CP932、appId 不要）。2020 年基準（000032103938 / 000032103844）は旧基準として更新停止見込み | 政府標準利用規約 2.0（CC BY 4.0 互換） | **採用**（bicycle-industry ③、2026-10-22） |
| 総務省 家計調査 品目分類 年次（二人以上の世帯） | 自転車購入（745）は**支出金額のみ**（購入数量・平均価格は収集されない）。自動車購入（740）は支出金額・購入数量・平均価格あり。**自動二輪車購入の品目はなく**「自動車以外の輸送機器購入（742）」に含まれる（支出金額のみ）。2000–2025 | e-Stat 長期時系列 CSV（`statInfId=000040270652` 1-2 小分類 2000–、全品目 2015/2020/2025 改定ごと 000040270655/656/000040409801、`fileKind=1`、CP932、行=品目・列=年）。年報 表 6-1 は `fileKind=4` の xlsx | 政府標準利用規約 2.0 | 候補（bicycle-industry。H4 の平均購入価格には使えない → ZIV・JBPI POS 単価で代替） |
| 自転車産業振興協会（JBPI）統計 PDF | 国内向自転車生産輸入統計 12 月分（車種別 台数・金額、各版 3 年、2021–2025）、POS 販売統計 年間総括（2024-07–、車種別 月次、11 社約 2,300 店、カバー率約 42%）。「スポーツ車」は 2025 年まで単独行なし（MTB・クロス／その他＝スポーツ車・外装変速機付軽快車） | `jbpi.or.jp/wp-content/uploads/<YYYY>/<MM>/<日本語ファイル名>.pdf`（要 percent-encode、robots: `/wp-admin/` のみ Disallow）。2026-10-22 に復旧確認 | 利用規約の記載なし → 出典「(一財)自転車産業振興協会」明記で引用、raw 非コミット | **採用**（bicycle-industry H2、R8、2026-10-22） |
| シマノ（7309、EDINET E02257）有価証券報告書 PDF | セグメント情報（自転車部品／釣具／その他 の外部顧客売上高・セグメント利益）と 地域ごとの情報（日本／北米／ヨーロッパ／アジア／その他 売上高、顧客所在地ベース）、百万円、FY2013–2025（12 本の有報。各有報は前期も載せる） | EDINET PDF 直リンク `disclosure2dl.edinet-fsa.go.jp/searchdocument/pdf/<docID>.pdf`（キー不要、docID は `shimano.DOCS` に固定）。**2026-10-24 のメンテで URL 形式変更の予告** → 取得済み raw を保持、再取得時は再調査。shimano.com は 403 | 開示書類（著作権は提出者、引用・研究目的で利用、raw 非コミット。確認 2026-10-22） | **採用**（bicycle-industry ⑦、2026-10-22） |
| あさひ（3333）月次営業速報 PDF | 全社・既存店 売上・客数・客単価、店舗数（月次） | TDnet PDF（`www2.jpx.co.jp/disc/33330/<id>.pdf`、URL は一覧 API 有料のため検索で解決） | 開示書類 | 候補（bicycle-industry、小売の補助） |
| 総務省・経産省 経済センサス-活動調査（令和 3 年）卸売業・小売業 産業編（総括表）第 1 表 | 産業分類細分類別・年次別（1994・97・99・2002・04・07・12・14・16・21）の事業所数（合計／法人／個人）・従業者数・年間商品販売額（百万円）・売場面積。自転車小売業 592 のほか 小売業計・自動車小売業 591・二輪自動車小売業 5914・機械器具小売業 593 を採る。2007 年以前と 2014 年は商業統計。2021 年の個人経営は販売額・売場面積を含まない | e-Stat `file-download?statInfId=000040032840&fileKind=0`（xlsx 1 シート、149 KB、appId 不要）。第 3 表（経営組織別、000040032842）・平成 28 年 産業編（000031676907、.xls 4 MB）は未採用 | 政府標準利用規約 2.0 | **採用**（bicycle-industry ⑧、2026-10-22） |
| UN Comtrade preview API | HS 8712 完成自転車・871160 電動二輪・8714 部品 の輸出入 数量（台。8714 と一部の報告国・年は数量なし）・純重量・金額 USD、報告国 9（JPN USA DEU NLD FRA GBR ITA CHN TWN=490）× 2010–2024、相手国 世界計 | `comtradeapi.un.org/public/v1/preview/C/A/HS?reporterCode=…&period=<年>&cmdCode=8712,871160,8714&flowCode=M,X&partnerCode=0`（キー不要、1 期間/呼び出し、≤500 行。逐次でも 429 が返るので `HttpxFetcher` が Retry-After で再試行） | UN Comtrade 利用条件: 非商用・出典表示で利用可、バルク再配布は制限 → raw 非コミット（確認 2026-10-22） | **採用**（bicycle-industry ④、2026-10-22） |
| Eurostat HICP `prc_hicp_midx` | COICOP CP0711 自動車・CP0712 二輪・CP0713 自転車 の価格指数（2015=100）、EU27・EA20・DE FR NL IT ES BE AT DK SE PL UK CH、月次 2005-01–2025-12 | dissemination API JSON-stat 1 リクエスト（キー不要）。「廃止・`prc_hicp_minr` に置換」表示だが配信中。`minr` は次元名が違う（COICOP 2018）ため未切替 | Eurostat copyright notice（出典表示で再利用可、確認 2026-10-22） | **採用**（bicycle-industry ⑤、2026-10-22） |
| US BLS CPI | `CUUR0000SERC01`（Sports vehicles including bicycles）、`CUUR0000SETA01`（New vehicles）、1982-84=100、月次 2006-01–。二輪は 2000 年で終了、自転車単独の品目はない | `api.bls.gov/publicAPI/v2/timeseries/data/<series>?startyear=&endyear=`（GET、キー無しで 10 年/リクエスト・25 リクエスト/日。6 リクエスト） | パブリックドメイン（確認 2026-10-22） | **採用**（bicycle-industry ⑤、2026-10-22） |
| ZIV（独 二輪産業協会）市場データ PDF | 独 販売台数（e-bike／従来車）、平均価格、売上、生産・輸出入、在庫、2015–2025 | `ziv-zweirad.de/marktdaten-archiv/`（46 PDF、英語版あり。例 `wp-content/uploads/2026/03/Market-Data-Bicycle-Industry-2025.pdf`） | 著作権 ZIV → 引用のみ、PDF 非再配布 | 候補（bicycle-industry ⑩） |
| TWSE OpenAPI 上場企業月次売上 | Giant（9921）・Merida（9914）の月次売上・前年比（当月分のみ → 毎月スナップショット、過去分は MOPS） | `openapi.twse.com.tw/v1/opendata/t187ap05_L`（JSON、キー不要。確認 2026-10-22） | 政府資料開放授權條款 v1（台湾、出典表示） | 候補（bicycle-industry ⑩） |
| Fox Factory（FOXF）10-K | 自転車（Specialty Sports Group）売上・比率 | SEC EDGAR XBRL / HTML（キー不要、UA 必須） | パブリックドメイン | 候補（bicycle-industry、補助） |
| 全国軽自動車協会連合会 | 軽四輪 新車販売 年別・車種別（1967–2025）、軽二輪（126–250cc）・小型二輪（251cc–）新車販売 年別（1967–2025） | `zenkeijikyo.or.jp/zenkei17/zen/wp-content/uploads/2026/01/hanbai4-2025kaku.xls`、`hanbai2-2025.xls`（年ごと別ファイル） | 利用規約なし → 「全国軽自動車協会連合会調べ」出典明記、raw 非コミット | **採用**（bicycle-industry H6、R9、2026-10-22） |
| 日本自動車販売協会連合会（自販連） | 登録車 車種別 新車登録台数 年計（2021–2025）、登録車＋軽 販売台数（2022–2025） | `jada.or.jp/files/libs/<id>/<id>.xls`（ページ 336・343 から取得した不透明 ID、manifest で固定） | 利用規約なし → 出典明記、raw 非コミット | **採用**（bicycle-industry H6、R9、2026-10-22） |
| 日本自動車輸入組合（JAIA） | 輸入乗用車 車両本体価格帯別 新規登録台数（年次 2003–2025、13 帯） | `jaia-jp.org/cms/wp-content/uploads/stats_ja/PriceRange_year.xls`（固定名、上書き更新 → manifest でスナップショット）。robots.txt `Crawl-delay: 10`、AI クローラーの UA は Disallow（本ツールの UA は socioscope、1 ファイルのみ・遅延遵守） | 利用規約なし → 出典明記、raw 非コミット | **採用**（bicycle-industry H6、R9、2026-10-22） |
| 日本自動車工業会（JAMA）Active Matrix DB | 四輪 生産・輸出・販売、二輪 生産・出荷・輸出（原付一種・二種・軽二輪・小型二輪、月次） | `jamaserv.jama.or.jp/newdb/`（Shift_JIS の HTML フォーム、CSV なし。adapter はブラウザで引数確認後に書く）。統計月報 PDF は 2020-09 で終了 | 利用規約なし → 出典明記、raw 非コミット | 候補（bicycle-industry ⑨ 対比、原付の唯一のソース） |
| ACEM / ACEA / OICA | EU 二輪・原付 登録台数（PDF、5〜6 か国）、EU 乗用車登録、世界生産・販売 | PDF 中心 | 各団体の著作権 | 候補（bicycle-industry、補助） |
| e-Stat（政府統計の総合窓口） | 国民生活基礎調査 所得票（所得階級×配偶者の有無・児童のいる世帯） | 統計表ファイル直接ダウンロード（`stat-search/file-download?statInfId=…&fileKind=1`、appId 不要） | **政府標準利用規約（第2.0版）＝CC BY 4.0 互換**（確認 2026-10-04） | **採用**（growth-fertility H3） |
| e-Stat — 就業構造基本調査（総務省） | 令和4年 全国編 第40表: 男女×配偶関係×年齢×所得（有業者） | 統計表ファイル直接ダウンロード（`…&fileKind=0`、**Excel のみ**、appId 不要。標準ライブラリで解析） | 同上（確認 2026-10-04） | **採用**（growth-fertility H3b 年齢調整） |
| e-Stat — 就業構造基本調査（総務省）4 波 | 有業者の 雇用形態 × 配偶関係（総数／うち未婚）× 年齢 × 性（2022 第16表・2017 第16表・2012 第16表・2007 第14表）と 無業者の 配偶関係 × 年齢 × 性（2022 第118表・2017 第99表・2012 第93表・2007 第86表） | 統計表ファイル直接ダウンロード（`…&fileKind=0`、2022/2017 は xlsx、2012/2007 は .xls、appId 不要。xls は xlrd） | 同上（確認 2026-10-18） | **採用**（growth-fertility H10 検定 B） |
| DHS Program Indicator Data API | 調査前 3 年の TFR（15–49 歳）× 富裕五分位（`FE_FRTR_W_TFR` × Wealth quintile）、約 90 か国 1990–2025 の DHS/MIS/AIS 調査；国コード表（ISO3） | REST JSON（`api.dhsprogram.com/rest/dhs/data`, `/countries`、API キー不要） | **引用義務**（Terms: 「The DHS Program Indicator Data API, The Demographic and Health Surveys (DHS) Program. ICF. Originally funded by USAID. Available from api.dhsprogram.com. [Accessed 10-05-2026]」。確認 2026-10-05） | **採用**（growth-fertility H4） |
| 国家データ処（韓国）新婚夫婦統計 報道資料 PDF | 初婚新婚夫婦（婚姻 5 年以内）の所得区間（6 区間＋全体）× 子ども有無・人数・平均子ども数、2015–2024 年基準 | 報道資料掲示板の静的 PDF（`mods.go.kr/boardDownload.es?bid=11815&list_no=…&seq=…`、キー不要。pypdf でテキスト抽出し表をパース） | **公共ヌリ（KOGL）第 1 類型＝出典表示のみ・商用・改変可**（確認 2026-10-06） | **採用**（growth-fertility H5） |
| 교육부（韓国教育部）初中高 사교육비조사 報道資料 PDF | 学校外教育費（私教育費）: 年次（2007–2025）の総額・参加率・週当たり参加時間・1 人当たり月平均（全学生／参加学生）、자녀수別（1/2/3+）と 학교급別（초/중/고）の 2024–2025 | 報道資料掲示板の静的 PDF（`moe.go.kr/boardCnts/fileDown.do?…&fileSeq=…`、キー不要。pypdf でテキスト抽出し 3 表をパース） | **公共ヌリ（KOGL）第 1 類型＝出典表示のみ**（確認 2026-10-17） | **採用**（growth-fertility H8d 仮説 K、記述のみ） |
| Testa (2012) *Family sizes in Europe* 付表（VID/ÖAW EDRP 2、データ＝Eurobarometer 75.4, 2011）＋ BiB (2025) *Intended, ideal and actual fertility in 11 European countries* Table 1（GGS-II 2020–23） | 理想・意図・実際の子ども数の国別平均と分布（EB: EU-27 × 性 × 年齢 15–24/25–39/40–54/55+/計、2011。GGS: 11 か国 × 女性 18–29/30–39/40–49/計、2020–23） | 静的 PDF（`oeaw.ac.at/.../edrp_2012_02.pdf`、`bib.bund.de/Publikation/2025/pdf/...`、キー不要。pypdf でテキスト抽出し付表をパース） | Testa 2012: **ライセンス未明示 → 出典明記で事実の転記のみ、PDF は再配布しない**（EB 75.4 自体は欧州委員会 CC BY 4.0）。BiB 2025: **CC BY-SA 4.0**（本文表記、確認 2026-10-06） | **採用**（growth-fertility H6） |
| Standard Eurobarometer（data.europa.eu）Volume A | 「今後 12 か月の期待（生活全般・家計・国の経済・国の雇用）」の国別 Better/Worse/Same/DK 割合、STD91（2019 春）〜STD105（2026 春）15 波 | hub API の JSON-LD（`data.europa.eu/api/hub/repo/datasets/<id>.jsonld`）から Volume A の静的 URL（`webgate.ec.europa.eu/ebsm/api/public/odp/download?key=…`、キー不要）を解決して xlsx/xls を取得 | **欧州委員会 再利用方針（Decision 2011/833/EU）＝CC BY 4.0 相当**（JSON-LD も `licence/CC_BY_4_0`。`commission.europa.eu/legal-notice_en`、確認 2026-10-06） | **採用**（growth-fertility H6） |
| 国立社会保障・人口問題研究所（IPSS） | 『人口統計資料集 2026』表 4-25 妻の年齢別 予定子ども数・4-24 平均出生児数（1977–2021）・4-23 妻の生まれ年別 完結出生児数（1890–1976 生まれ）・4-15 出生順位別出生数・4-16 出生順位別 TFR／平均出生年齢（1950–2024）・4-09 年齢各歳別出生率（1925–2024）・4-11 コーホート別累積出生率；『第 16 回出生動向基本調査 結果の概要』図表 7-1（夫婦の平均理想・予定子ども数 1977–2021）・図表 3-3（未婚者の平均希望子ども数 1982–2021） | 静的 xlsx（`ipss.go.jp/syoushika/tohkei/Data/Popular2026/T04-NN.xlsx`、標準ライブラリで解析）＋ 静的 PDF（AES 暗号化、pypdf ＋ `cryptography`）。キー不要 | **PDL1.0（公共データ利用規約 第 1.0 版）＝出典表示で商用含め利用可**（確認 2026-10-18） | **採用**（growth-fertility H9） |
| Special Eurobarometer 253（data.europa.eu、dataset `s406_65_1_ebs253`）EB65.1 Volume C ＋ EB65.3 Volume A | 2006 年の理想子ども数（一般理想・個人理想）の国別分布と平均、EU-25 × 性・年齢 ＋ 候補 4 か国 | hub の JSON-LD から 2 配布物（zip 内 xls）を解決して取得、xlrd で解析 | 欧州委員会 再利用方針（CC BY 4.0 相当、確認 2026-10-18） | **採用**（growth-fertility H9） |
| OECD Family Database SF2.5 Childlessness（xlsx） | 出生コーホート（1935–1975）別 定義的無子率 %、1975 コーホートの完結出生率 | 静的 xlsx（`webfs.oecd.org`、鍵不要）、openpyxl | OECD Terms（CC BY 4.0、確認 2026-10-18） | **採用**（growth-fertility H9） |
| OECD 住宅価格（`DF_HOUSE_PRICES`）・有期雇用（`DF_TEMP_I`）・LFS 指標（`DF_LFS_INDIC`）＋ Family Database SF3.1 婚姻（xlsx） | 住宅価格対所得比・対家賃比・実質指数（2015=100）、有期雇用比率（15–24 / 25–54 / 計 × 性）、若年失業率（15–24 / 25–34 × 性）、粗婚姻率 1960–・平均初婚年齢 1990– | SDMX REST CSV 3 本（鍵不要）＋静的 xlsx、openpyxl | OECD Terms（CC BY 4.0、確認 2026-10-18） | **採用**（growth-fertility H10） |
| Eurostat `demo_nind` / `lfsa_etpgan` / `une_rt_a` / `ilc_lvho07a` | 粗婚姻率・初婚平均年齢・初婚率（1960–）、有期雇用比率 15–24 / 25–34（1995–）、若年失業率 15–24（2003–）、若年層の住宅費過重負担率（2004–） | dissemination API JSON-stat（鍵不要、国別分割） | Eurostat copyright notice（出典明記で再利用可） | **採用**（growth-fertility H10） |
| 国税庁 統計年報 / 民間給与実態統計 | 所得分布 | Excel | 政府標準利用規約 | 候補（日本） |
| 野村総研 富裕層レポート等 | 資産階層別世帯数（推計） | PDF（公開レポート） | 引用のみ | 候補（LLM 構造化対象） |
| IPU Parline（data.ipu.org） | 272 議院の定数・現員・選挙制度・任期（parliament-size H1・H2） | JSON API（鍵の要否は確認要） | **CC BY-NC-SA 4.0**（API `meta.licence`、確認 2026-10-27）。非商用 | **採用**（parliament-size H1。`marts/ipu_parliaments`） |
| ParlGov | 欧州・OECD の選挙結果（政党別得票・議席）（parliament-size H3c 国際比較） | CSV | CC BY 4.0（確認要） | 候補（parliament-size） |
| V-Dem | 立法府の制約指数 `v2xlg_legcon` 等（parliament-size H2） | CSV（登録の要否 確認要） | CC BY-SA 4.0（確認要） | 候補（parliament-size） |
| Eurostat `gov_10a_exp` / OECD COFOG | 執行・立法機関 歳出（COFOG 01.1）（parliament-size H5b） | JSON-stat / SDMX、鍵不要 | Eurostat: CC BY 4.0 / OECD Terms & Conditions | 候補（parliament-size。01.1 は執行機関と合算、立法のみ分離できる国に限る） |
| 総務省 衆議院議員総選挙 結果調（第 49〜51 回） | 都道府県別・比例ブロック別 有権者数、政党別得票・議席（parliament-size H3・H4） | **Excel あり**（xls／xlsx、`main_content/<id>.xls(x)`、鍵不要）。PDF の結果調全体版もある | 政府標準利用規約（第 2.0 版） | **採用**（parliament-size H3・H4、2026-10-27。`marts/jp_hr_pr_results`, `jp_hr_seats_by_party`, `jp_hr_electorate`） |
| 衆議院 議案審議経過・国立国会図書館 日本法令索引 | 回次別の閣法・衆法・参法の提出数・成立数（parliament-size H2） | HTML（表） | 衆議院サイトの利用規約 確認要 | 候補（parliament-size） |
| 財務省 予算書・決算書（国会所管）、歳費法・立法事務費交付法 | 国会所管歳出、議員 1 人当たり法定経費（parliament-size H5） | PDF / e-Gov 法令 API | 政府標準利用規約（第 2.0 版） | 候補（parliament-size） |
| 衆議院・参議院 公式サイト 定数の変遷、総務省 人口推計、IPSS 将来推計 | 定数の時系列 1890–、人口（parliament-size H6・H4b） | HTML / xlsx | 確認要 / 政府標準利用規約 | 候補（parliament-size） |
| e-Stat 令和 2 年国勢調査 人口等基本集計 表 2-1 | 都道府県別 国籍総数・日本人 人口（parliament-size H4b: アダムズ方式の基礎人口） | `file-download?statInfId=000032142404&fileKind=0`（xlsx、appId 不要） | 政府標準利用規約 2.0 | **採用**（parliament-size、2026-10-27。`marts/jp_census2020_prefecture`） |

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

### IPSS 国立社会保障・人口問題研究所 — 人口統計資料集 2026（xlsx）と 第 16 回出生動向基本調査 結果の概要（PDF）（growth-fertility H9: 規範の崩れ vs 実現の阻害、出生順位、コーホート）
- URL / API:
  - 人口統計資料集 2026 の表 xlsx（固定 URL 規則、`theme_growth_fertility.ipss.TABLES`）: `https://www.ipss.go.jp/syoushika/tohkei/Data/Popular2026/T04-NN.xlsx`（NN = 25, 24, 23, 15, 16, 09, 11。2026-10-18 確認: すべて 200、`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`、10–41 KB）。各 xlsx は 1 シートだが、★付き表（T04-09, T04-11, T04-16）は第 2 シート `T04-NN★` に各年版があり、adapter はそちらを読む（第 1 シートは 5 年刻み等の抜粋）。
  - 第 16 回出生動向基本調査 結果の概要: `https://www.ipss.go.jp/ps-doukou/j/doukou16/JNFS16gaiyo.pdf`（`ipss.PDF_URL`。2026-10-18 確認: 200、`application/pdf`、5.3 MB、95 ページ、**AES 暗号化**（空パスワード）→ pypdf の復号に `cryptography` が必要なので `themes/growth-fertility/pyproject.toml` に追加）。
- 表の列構成（実測、`estat.xlsx_rows(payload, sheet)` の 1 始まり列番号）:
  - T04-25 妻の年齢（5 歳階級）別予定子ども数 / T04-24 同 平均出生児数: A=年次, B=（第N回）, C=総数, D..I=20～24歳…45～49歳。1977/1982/1987/1992/1997/2002/2005/2010/2015/2021（第 7〜16 回）の 10 行。
  - T04-23 妻の生まれ年別出生児数割合および平均出生児数: A=妻の生まれ年（`1890～1895` … `1971～1976`、B に注記号）, C=調査年次（1950–2021）, D..H=無子/1人/2人/3人/4人以上（%）, I=平均出生児数。15 行。1970 年以前は国勢調査（既婚女性）、1977 年以降は出生動向基本調査（初婚どうし夫婦、妻 45–49 歳 = 結婚持続 15–19 年）。
  - T04-15 出生順位別出生数および割合: A=年次, C=総数, D..H=第1子…第5子～。C に「実数」「割合(％)」のブロック見出し。実数 1950–2015 は 5 年刻み、2016–2024 は各年（23 行）、割合は 1950–2020 の 10 年刻み＋2024（9 行）。総数は順位不詳を含む。
  - T04-16★ 出生順位別合計特殊出生率および平均出生年齢: A=年次（1950–2024 各年）, B..G=TFR 総数/第1子…第5子～, H..M=平均出生年齢 同。1951–1953 の順位別は '…'。
  - T04-09★ 女性の年齢（各歳）別出生率: A=年齢 15..49 ＋ 合計（= TFR）, 列 = 1925年, 1930年, 1940年, 1947年…2024年（81 列）。
  - T04-11★ 女性のコーホート別累積出生率: A=年齢 15..49, 列 = 1950年…2020年（71 列）。**列見出しはコーホートが 15 歳に達した年**（1950 列 = 1935 年生まれ。T04-09 の累積と一致することを確認）。未到達年齢は空白。
  - PDF 図表 7-1（p.54、pypdf index 53）: タイトル行の直後にデータラベル 20 個が 1 行（理想 10 ＋予定 10、`2.252.17` のように連結）。注に妻 35 歳未満の理想・予定（`第N回（YYYY）d.dd` × 10 × 2）。図表 3-3（p.34、index 33）: タイトル行〜「男性 女性」の間に 18 個（男 9 ＋女 9、1982–2021）。
- 対象指標・粒度: `marts/jp_fertility_survey`（long: survey_year × metric(planned_children / children_born / completed_fertility / completed_parity_share / ideal_children / planned_children_pdf / desired_children_single) × group × birth_cohort、288 行）と `marts/jp_births_order_cohort`（long: year × metric(births / births_share / tfr_order / mean_age_order / asfr / cohort_cum_fertility) × group(総数 / 第1子…第5子以上 / age 15..49) × cohort（生まれ年）、5,917 行）。列定義は `themes/growth-fertility/CLAUDE.md`。
- ライセンス・利用規約（確認日 2026-10-18）: IPSS サイトは **PDL1.0（公共データ利用規約（第 1.0 版））** = 出典表示で複製・改変・商用利用可。出典表記: 「国立社会保障・人口問題研究所『人口統計資料集 2026』『第 16 回出生動向基本調査 結果の概要』（PDL1.0）」。`ipss.LICENSE` に記載し manifest に残す。raw（xlsx・PDF）はコミット可だが既定どおりコミットしない。
- 取得方法（adapter 名、レート制限）: `theme_growth_fertility.ipss`（`parse_table` / 表ごとの `*_rows` / `survey_pdf_rows_from_pages` / `build_survey_mart` / `build_births_mart` の純粋変換。xlsx は `estat.xlsx_rows(payload, sheet)` のシート名指定、PDF は `kostat.pdf_text` を再利用）＋ `pipeline._fetch_h9_jp` / `_stage_h9_jp` / `_mart_h9_jp`（`HttpxFetcher`）。**8 リクエスト（合計 5.5 MB）**。raw は `data/raw/growth-fertility/ipss/{T04-NN.xlsx, JNFS16gaiyo.pdf}`、staged は `staged/ipss/{t04_25, t04_24, t04_23, t04_15, t04_16, t04_09, t04_11, jnfs16}`。公開レート制限なし。再取得は年 1 回（人口統計資料集の次年版は `ipss.BASE_URL` の `Popular2027`、出生動向基本調査は第 17 回公表時に `PDF_URL`・`_ANCHORS` を更新）。
- 既知の欠損・断絶・定義変更:
  - **予定子ども数の 2 系統**: xlsx T04-25 の 2021 年総数は 1.95、PDF 図表 7-1 のデータラベルは 2.01（2010 年も 2.08 vs 2.07）。同じ第 16 回でも集計・公表時点が違うため、mart では `planned_children`（xlsx）と `planned_children_pdf`（PDF）を別 metric で保持する。設計 H9 V1 の主判定にどちらを使うかは分析側で明記する。
  - T04-15/T04-16 は 1970（T04-16★ は 1972）年以前が沖縄県を含まない。T04-16 の 1950–64・1966–67 の順位別 TFR は 5 歳階級から算出で Σ順位 と総数の差が最大 0.03（adapter の許容 0.05）。1951–1953 の順位別は未公表（'…' → 行なし）。
  - T04-09 の分母は 1925–40 が総人口、1947 年以降が日本人人口。T04-11 の 1976 年生まれ以降（列 1991–）は 49 歳未到達で完結していない（空白 → 行なし）。1966 年生まれ（列 1981）の累積は丙午の影響で前後より低い（1.43）。
  - T04-23 は 1950 年調査に 3 コーホート（妻 55–59・50–54・45–49 歳）が並ぶ。1970 年以前（国勢調査の既婚女性）と 1977 年以降（初婚どうし夫婦）で母集団が違う。
  - PDF の図表 3-3 は「いずれ結婚するつもり」の 18–34 歳未婚者のみ（未婚者全体の値は注にあるが未取込）。希望子ども数は 5 人以上を 5 として平均。
  - 解析は fail-closed: 表題・ヘッダ・年／年齢／調査回の範囲・列数・合計の照合、PDF はラベル点数と第 7 回・第 16 回（図表 3-3 は第 8 回・第 16 回）の公表値による端点照合。違えば `ValueError` → stage の skipped に「`<raw>: layout not recognised (<reason>)`」として残し、その表だけ書かない。
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
### 国家データ処（韓国）— 2025년 출생 통계 報道資料 PDF（growth-fertility H9-KR: 出生順位別出生数・母の年齢別出生率）
- URL / API: 掲示板 `https://mods.go.kr/board.es?mid=a10301010000&bid=204`（보도자료）。PDF（固定 URL、`theme_growth_fertility.kostat.BIRTHS_URL`）: `https://mods.go.kr/boardDownload.es?bid=204&list_no=446625&seq=1`（2026-10-18 確認: 200、3.47 MB、`%PDF`、50 ページ）。KOSIS OpenAPI はキー必須のため使わない。robots.txt は 신혼부부통계 の節と同じ（`boardDownload.es` 許可）。
- 表の位置（pypdf の `extract_text`、0 始まりのページ index）: index 37（資料の p.33）統計表 2「모(母)의 연령별 출산율, 1981-2025」（列 = 연도 / 합계출산율 / 15-19세 / … / 45-49세。単位: 가임 여자 1명당 명、해당 연령 여자인구 1천 명당 명）、index 38（p.34）統計表 3「출산 순위별 출생아 수, 1981-2025」（列 = 연도 / 계* / 첫째아 / 둘째아 / 셋째아 / 넷째아 이상。単位 명、`* 출산 순위 미상 포함`）。index 34 の統計表目次は見出しが行末アンカーで一致しない。2022–2024 行は空白が不規則だが正規化で吸収。
- 対象指標・粒度: `marts/kr_births_order_asfr`（long）: year(1981–2025) × metric(births / births_share / asfr / tfr) × group(계 / 첫째아 / 둘째아 / 셋째아 / 넷째아 이상 / 15-19 … 45-49)。births_share = 順位別出生数 ÷ 계（계 は順位未詳を含むので 4 順位の和は 1 をわずかに下回る）。母集団: 가족관계등록법 により申告された全出生（인구동향조사、承認番号 101003）。
- ライセンス・利用規約（確認日 2026-10-18）: 국가데이터처 報道資料は **공공누리（KOGL）제1유형（출처표시）**。出典表記: 「국가데이터처, 2025년 출생 통계 보도자료, mods.go.kr（KOGL 제1유형）」。`kostat.BIRTHS_LICENSE` に記載し manifest に残す。raw（PDF）はコミットしない。
- 取得方法（adapter 名、レート制限）: `theme_growth_fertility.kostat`（`births_rows_from_pages` / `build_births_mart` の純粋変換、`pdf_text` 再利用）＋ `pipeline._fetch_h9_kr` / `_stage_h9_kr` / `_mart_h9_kr`（`HttpxFetcher`）。**1 リクエスト（3.5 MB）**。raw は `data/raw/growth-fertility/kostat_births/births_2025.pdf`、staged は `staged/kostat/births_order_asfr`、mart は `marts/kr_births_order_asfr`（765 行）。公開レート制限なし。再取得は年 1 回（翌年 8 月頃の確定公表後、`list_no`/`seq` を掲示板で確認）。
- 既知の欠損・断絶・定義変更:
  - **1997–2000 年**は旧資料と再集計差（出生申告の遅れ分の補正）があるため、全期間を再掲する**最新資料を正**とする。年ごとの資料を積まない。
  - 計 は 출산 순위 미상 を含む（2025 年: 254,341 − 4 順位の和 254,213 = 128）。順位別の比は 계 を分母にする。女性人口は未取込なので順位別 TFR ではなく出生数の比で近似する（設計 H9 V2 の韓国の扱い）。
  - 解析は fail-closed: 見出し不一致・年の連番外（1981 から）・列数不一致・順位合計が 계 の 99% 未満または超過・両表の年不一致は `ValueError` → stage の skipped に「`births_2025.pdf: layout not recognised (<reason>)`」。
  - 統計表 1（出生数・粗出生率・合計特殊出生率 1970–）、表 4（母の年齢別出生数）、시도별・結婚持続期間別などは資料にあるが未取込（任意項目）。

### Eurostat `demo_frate`（年齢各歳別出生率）— 欧州のコーホート累積・完結出生率（growth-fertility H9-EU）
- URL / API: 上の Eurostat 節と同じ dissemination API。`https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/demo_frate?format=JSON&lang=EN&geo=<GEO>&sinceTimePeriod=1960&agedef=COMPLET&age=Y15&…&age=Y49`（`theme_growth_fertility.eurostat.frate_requests`、ORDER_GEOS 13 か国 × 1 リクエスト、raw `eurostat_demo_frate_<geo>.json`、各 18–39 KB）。次元（`id` 順、2026-10-18 に実レスポンスで確認）: freq.unit.age.agedef.geo.time、unit=NR（女性 1 人当たり、例 0.00106）、agedef=COMPLET（満年齢。`REACH` = 到達年齢は使わない）。
- 対象指標・粒度: `staged/eurostat/asfr_single_age`（iso3 × year × age 15–49、rate）、`marts/eu_cohort_fertility`（long）: asfr（期間）、cohort_cum（cohort = year − age の 15 歳から age までの累積）、completed（45 歳時点。未到達は 40 歳以上の最終観測で打ち切り `censored_at`）。
- ライセンス・利用規約: 上の Eurostat 節と同じ（出典明記で再利用可、確認日 2026-10-06）。出典表記: 「Source: Eurostat, demo_frate（accessed 2026-10-18）」。raw はコミットしない。
- 取得方法（adapter 名、レート制限）: `theme_growth_fertility.eurostat`（`frate_requests` / `frate_rows` / `cohort_cumulative` / `build_cohort_mart` の純粋関数）＋ `pipeline._fetch_h9_eu` / `_stage_h9_eu` / `_mart_h9_eu`（`HttpxFetcher`、H5 の `_fetch_h5` とは別ブロック）。**13 リクエスト（計 ~430 KB）**。公開レート制限なし。再取得は年 1 回。
- 既知の欠損・断絶・定義変更:
  - 開始年が国で異なる: DE 2000（統一後の系列のみ、completed 行なし）、FR 1998（completed は 1983 コーホート 41 歳打ち切りのみ）、PL 1990、ES 1971、SE 1968、IS 1963、NO 1961、CZ/DK/FI/HU/IT/NL 1960。CZ は 1960–1986 に 45–49 歳が無い（1945 コーホート以降の累積には影響しない）。NO は 1971/1973/1978/1979/1987 に 47–49 歳の 1 セルが欠ける（同上）。`status` フラグ（b 断絶、p 暫定、e 推計）は保持しない。
  - 15 歳の観測が無いコーホート（1960 年開始の国では 1944 以前）は累積を出さない。途中で欠けた歳があるコーホートは落として mart の skipped に出す（2026-10-18 時点 0 件）。完結（45 歳）は 1979 コーホートまで、1980–1984 は 40–44 歳打ち切り。
  - cohort = year − age は満年齢ベースなので、誕生年は 2 暦年にまたがる（通常のコーホート出生率の近似）。

### e-Stat（政府統計の総合窓口）— 就業構造基本調査（総務省）雇用形態 × 配偶関係 × 年齢 × 性、4 波（growth-fertility H10 検定 B: 雇用形態別分解）
- URL / API: 統計表ファイル `https://www.e-stat.go.jp/stat-search/file-download?statInfId=<id>&fileKind=0`（**アプリケーション ID 不要**。2022/2017 は xlsx、2012/2007 は .xls（OLE2）で `xlrd>=2.0` で読む）。表の所在: 就業構造基本調査 → 各年 → 全国編 → 人口・就業に関する統計表（2022 tstat=000001163626 / 2017 tstat=000001107875 / 2012 tstat=000001058052 / 2007 tstat=000001017285）。
- 調査結果（2026-10-18）: 15 歳以上人口の **配偶関係 × 年齢 × 性** を直接持つ表は 4 波とも全国編に無い（第1-1表／第1表の「未婚／配偶者あり／死別・離別」列は **世帯主 → 単身者 の内訳**で、2012 年は 9,247,500 ＋ 1,743,400 ＋ 7,103,400 = 18,094,300 = 単身者数。配偶関係のある表は他に「平均年齢」表のみ）。そこで分母は **有業者表（配偶関係 総数／うち未婚）＋ 無業者表（同）** で作る: 2022 年 67,060,400 ＋ 43,134,800 = 110,195,200 は第1-1表の 15 歳以上人口総数と一致（2012: 64,420,700 ＋ 46,394,400 = 110,815,100、2007: 65,977,500 ＋ 44,324,000 = 110,301,500 も一致）。2002 年は年齢クロスが無く使わない。
- 対象表・粒度（`theme_growth_fertility.estat.MARITAL_EMPLOYMENT_TABLES`）:
  | key | statInfId | 表 | layout |
  |---|---|---|---|
  | `shugyo_employment_2022` | 000040077274 | 令和4年 第16表 男女、配偶関係、年齢、教育、従業者規模、従業上の地位・雇用形態・起業の有無別人口（有業者）－全国（xlsx 3.2 MB） | tidy |
  | `shugyo_not_employed_2022` | 000040077389 | 令和4年 第118表 男女、配偶関係、年齢、教育、就業希望の有無・求職活動の有無、前職の有無・離職期間、就業状態・仕事の主従別人口（無業者）－全国（xlsx 9.3 MB） | tidy |
  | `shugyo_employment_2017` | 000031738323 | 平成29年 第16表 男女，配偶関係，教育，年齢，従業者規模，従業上の地位・雇用形態・起業の有無別人口（有業者）（xlsx 2.9 MB、J/E 行・英語列あり） | tidy_je |
  | `shugyo_not_employed_2017` | 000031729447 | 平成29年 第99表 男女，配偶関係，教育，就業希望の有無・求職活動の有無，年齢，前職の有無・離職期間，就業状態・仕事の主従別人口（無業者）（xlsx 6.1 MB） | tidy_je |
  | `shugyo_employment_2012` | 000021291492 | 平成24年 第16表 男女，配偶関係，年齢，教育，従業上の地位・雇用形態，起業の有無，従業者規模別有業者数（.xls 2.4 MB、6 シート = 性 × 配偶関係） | wide_xls |
  | `shugyo_not_employed_2012` | 000021291719 | 平成24年 第93表 就業状態・仕事の主従，教育，就業希望の有無，求職活動の有無，年齢，男女，配偶関係，前職の有無，離職期間別無業者数（.xls 2.3 MB、4 シート = 就業状態、第 1 シートのみ） | wide_xls |
  | `shugyo_employment_2007` | 000001234529 | 平成19年 第14表 男女，配偶関係，年齢，教育，従業上の地位，雇用形態，起業の有無，従業者規模別有業者数（.xls 4.4 MB、6 シート） | wide_xls |
  | `shugyo_not_employed_2007` | 000001234601 | 平成19年 第86表 就業状態，教育，就業希望の有無，求職活動の有無，年齢，男女，配偶関係，前職の有無，離職期間別無業者数（.xls 4.6 MB、4 シート） | wide_xls |
  使うのは 従業者規模・教育・就業希望・前職 = 総数、配偶関係 = 総数／うち未婚、年齢 = 総数＋5 歳階級 15 区分、男女別。単位は人（標本から復元した推定人数、100 人単位、標準誤差非公表）。staged は `staged/estat/shugyo_marital_by_employment`（3,744 行）、mart は `marts/jp_marital_by_employment`（同数、キー一意）。
- ライセンス・利用規約: e-Stat と同じ **政府標準利用規約（第2.0版）**（確認 2026-10-18）。出典表記「出典：政府統計の総合窓口(e-Stat)、就業構造基本調査（総務省）を加工」。raw はコミットしない（manifest 8 行）。
- 取得方法（adapter 名、レート制限）: `theme_growth_fertility.estat`（`marital_wave_rows` → `_parse_tidy` / `_parse_wide_employment` / `_parse_wide_not_employed`、`xls_sheets` = xlrd）＋ `pipeline._fetch_h10_jp/_stage_h10_jp/_mart_h10_jp`（`HttpxFetcher`、8 ファイル、レート制限なし）。
- 既知の欠損・断絶・定義変更:
  - **2007 年の第14表には「非正規の職員・従業員」列が無い**（正規と パート／アルバイト／派遣／契約 の 4 内訳のみ。嘱託・その他は無く、雇用者 − 正規 は役員も含む）。mart の `nonregular` は 2012 年以降のみ。2007 → 2022 の分解で非正規を使うときは 2012 起点か 4 内訳の和（下限）を使い、定義差を report に書く。
  - 2012/2007 の無業者表に 男女総数 × うち未婚 のセルは無く、mart の値は 男＋女 の派生。
  - 雇用者には会社などの役員を含む（正規＋非正規 ≤ 雇用者 の検査はこの差を許す）。「起業者」列は雇用形態と直交するため落とす。
  - 2017 年の表は列順が 教育→年齢（2022 は 年齢→教育）、2007 年の派遣社員ラベルは「労働派遣事業所」（2012 年以降「労働者派遣事業所」）。
  - 調査時点は各年 10 月 1 日。配偶関係は「総数」「うち未婚」のみ（有配偶／死別・離別は非公表）なので未婚率 = うち未婚 ÷ 総数、既婚経験率はその補数。
### OECD 住宅価格・有期雇用・若年失業（SDMX REST）＋ Family Database SF3.1 婚姻（xlsx）— 家族形成を阻む制約（growth-fertility H10-OECD）
- URL / API（source-scout が 2026-10-18 に httpx で 200 を確認。`theme_growth_fertility.oecd_labour.DATASETS` / `MARRIAGE_URL` に固定、改変しない）。REF_AREA は 19 か国 `JPN+KOR+ITA+ESP+PRT+GRC+SWE+DNK+FIN+NOR+FRA+DEU+NLD+GBR+USA+AUT+CZE+HUN+POL`（`H10_COUNTRIES`）:
  | raw | dataflow / key（次元順） | 取れた範囲 |
  |---|---|---|
  | `oecd_labour/house_prices.csv`（671 KB） | `OECD.ECO.MPD,DSD_AN_HOUSE_PRICES@DF_HOUSE_PRICES,1.0/<REF>.A.HPI_YDH+HPI_RPI+RHP.`（REF_AREA.FREQ.MEASURE.UNIT_MEASURE。UNIT は空 = 全部、返るのは `IX`（2015=100）のみ。`PT_AVG_L_TERM` は許容するが今回は無し） | 2,522 行。JPN 1960–2025、ITA/SWE/DEU/DNK/FIN/FRA/NLD/NOR/USA 1970–、GBR 1969–、KOR 1986–、PRT 1988–、GRC 1997–、AUT 2000–、POL 2005–、HUN 2007–、CZE 2008–。`HPI_YDH`（対所得比）は DEU/NLD 1980–、DNK 1981–、GBR 1987–、PRT 1995– と遅い。USA の `HPI_RPI` は 2024 まで |
  | `oecd_labour/temp_employment.csv`（1.7 MB） | `OECD.ELS.SAE,DSD_TEMP@DF_TEMP_I,1.0/<REF>.EMP_TEMP.PT_POP_SUB._T+M+F.Y15T24+Y25T54+_T.ICSE93_1.A`（REF_AREA.MEASURE.UNIT_MEASURE.SEX.AGE.WORKER_STATUS.FREQ） | 5,841 行。JPN 1980–、FRA/GBR/GRC/ITA/NLD 1983–、DEU/DNK 1984–、PRT 1986–、ESP 1987–、CZE 1993–、AUT/USA 1995–、FIN/HUN/SWE 1997–、NOR 1999–、POL 2001–、KOR 2004–。USA は 1995/1997/1999/2001/2005/2017/2023 の 7 時点のみ |
  | `oecd_labour/youth_unemployment.csv`（1.7 MB） | `OECD.ELS.SAE,DSD_LFS@DF_LFS_INDIC,1.1/<REF>.UNE_RATE.PT_LF_SUB._T+M+F.Y15T24+Y25T34.UNE`（REF_AREA.MEASURE.UNIT_MEASURE.SEX.AGE.LABOUR_FORCE_STATUS。FREQ 次元なし） | 5,489 行。USA 1960–、FIN/SWE 1963–、JPN 1968–、DEU/ITA 1970–、KOR 1980–、HUN/POL 1992–、CZE 1993–、AUT 1994–。`OBS_STATUS` は A（AUT 2023–2024 の 17 行は空） |
  | `oecd_labour/sf3_1_marriage_divorce_rates.xlsx`（970 KB） | `https://webfs.oecd.org/Els-com/Family_Database/SF_3_1_Marriage_divorce_rates.xlsx`。読むシートは `MarriageRates`（行 = ISO3・国名・Note、列 = 1960–2022、粗婚姻率 人口 1,000 人当たり）と `MeanAgeFirstMarriage`（行 = 国名 × Gender、列 = 1990–2021、平均初婚年齢）。他 7 シート（Chart SF3.1.A–D、同性婚、離婚率、前婚姻状態）は未取込 | 粗婚姻率 1,114 行（FRA 1994–、KOR/USA 1970–、GBR 2020 まで、他 1960–2022）、初婚年齢 1,096 行（FRA 1998–2018、POL 1993–、PRT 1991–、DEU –2017、AUT/FIN/GBR –2019、USA のみ 2021） |
- 対象指標・粒度: `staged/oecd_labour/{house_prices,temp_employment,youth_unemployment,marriage}` → `marts/oecd_family_formation`（long: iso3, year, dataset, measure, sex, age, unit, value, obs_status, source。16,062 行、19 か国、1960–2025。キー `(iso3, year, dataset, measure, sex, age, unit)` 一意）。測度コード `CMR`/`MAFM`、単位 `PER_1000_POP`/`YR` は本テーマの命名（xlsx にコードは無い）。
- ライセンス・利用規約（確認日 2026-10-18）: OECD Terms & Conditions（`oecd.LICENSE`、CC BY 4.0）。出典表記: 「OECD (2026), House prices / Temporary employment / LFS indicators (sdmx.oecd.org) and Family Database SF3.1 (accessed 2026-10-18)」。raw はコミットしない（manifest のみ）。
- 取得方法（adapter 名、レート制限）: `theme_growth_fertility.oecd_labour`（`parse` / `parse_marriage` / `build_mart`、openpyxl）＋ `pipeline._fetch_h10_oecd / _stage_h10_oecd / _mart_h10_oecd`（`HttpxFetcher`）。**4 リクエスト（計 ~5 MB）**。公開レート制限なし。再取得は年 1 回。
- 既知の欠損・断絶・定義変更:
  - 住宅価格は OECD Analytical house price indicators（季節調整済み年次平均、2015=100 の指数）。対所得比は「名目住宅価格 ÷ 1 人当たり名目可処分所得」の指数なので水準の国際比較はできない（同一国内の推移・差分で使う。設計 H10 A は 5 年差分）。
  - 有期雇用は ICSE-93 の被用者（`ICSE93_1`）に占める有期契約の割合（OECD 定義、各国 LFS）。日本の「非正規」（パート・アルバイト・派遣・契約・嘱託）とは定義が異なり、日本の値は契約期間が有期の者のみ（2020 年 15–24 歳 16.3%、ESP 66.4%、ITA 58.8%、SWE 53.8%）。設計 H10 の「南欧の有期雇用と日本の非正規は制度が違う」に対応。
  - 若年失業率は ILO 定義。AUT 2023–2024 は `OBS_STATUS` 空（上流の暫定値の可能性、値はそのまま）。
  - SF3.1 の注記: 初婚年齢は AUS/NZL/USA が中央値、MEX は全婚姻（非対象国なので落ちる）。GBR の婚姻は 2014 年以降同性婚を含み、2021–2022 が未公表。'..' と空セルは行なし（補完しない）。`MeanAgeFirstMarriage` に ISO3 列が無いので国名を `oecd_labour.NAME_TO_ISO3` で引き、`MarriageRates` のコードと国名の対応を照合する（不一致は `ValueError`）。
  - 解析は fail-closed: `STRUCTURE_ID`・固定次元・閉集合外の可変次元・見出し違い・年列が文字列・未知の国名・Gender ∉ {Male, Female}・数値でも '..' でもないセル・シート内キー重複は `ValueError` → stage の skipped（xlsx は「`layout not recognised`」）。

### Eurostat `demo_nind` / `lfsa_etpgan` / `une_rt_a` / `ilc_lvho07a` — 婚姻・有期雇用・若年失業・住宅費負担（growth-fertility H10-EU）
- URL / API: 上の Eurostat 節と同じ dissemination API。`theme_growth_fertility.eurostat.family_formation_requests`（`H10_GEOS` = ORDER_GEOS 13 ＋ PT/EL/AT = 16 か国 × 4 dataset = 64 リクエスト、raw `eurostat_<dataset>_<geo>.json`、各 4–9 KB）。source-scout が 2026-10-18 に httpx で 200 を確認。次元（`id` 順、実レスポンスで確認）:
  | dataset | 次元 | 絞り込み | 取れた範囲 |
  |---|---|---|---|
  | `demo_nind` | freq.indic_de.geo.time | `sinceTimePeriod=1960`（indic_de は全部: GNUPRT 粗婚姻率、MARRIAGE 婚姻数、FAGEMAR1/MAGEMAR1 初婚平均年齢、FMAR1CUM/MMAR1CUM 合計初婚率、FMAR1PC/MMAR1PC 初婚割合。unit 次元なし） | 5,668 行、1960–2024。初婚年齢・合計初婚率は 1990–。FRA 1994–2023、DNK –2021、IS/NO –2020 |
  | `lfsa_etpgan` | freq.unit.sex.age.citizen.geo.time | `sinceTimePeriod=1995&sex=T,M,F&age=Y15-24,Y25-34&citizen=TOTAL`（unit=PC、被用者に占める有期契約 %） | 2,918 行、1995–2025。CZ/HU/PL 1997–、IS は小セル欠損。`status: b`（断絶）は保持しない |
  | `une_rt_a` | freq.age.unit.sex.geo.time | `sinceTimePeriod=1990&sex=T,M,F&age=Y15-24,Y25-29&unit=PC_ACT` | 846 行。**返るのは Y15-24 のみ**（Y25-29 は dataset に無い）。FR 2003–、SE 2005–、他 2009– |
  | `ilc_lvho07a` | freq.unit.rskpovth.age.sex.geo.time | `sinceTimePeriod=2003&age=Y20-29,Y25-29,Y16-29&sex=T&rskpovth=TOTAL`（unit=PC、住宅費が可処分所得の 40% 超の人の割合） | 1,002 行、2004–2025。DE 2010–、IS –2020、3 age とも返る |
- 対象指標・粒度: `staged/eurostat/{demo_nind,lfsa_etpgan,une_rt_a,ilc_lvho07a}` → `marts/eu_family_formation`（long: iso3, year, dataset, indicator, sex, age, unit, value, source。10,434 行、16 か国、1960–2025。キー `(iso3, year, dataset, indicator, sex, age, unit)` 一意）。`indicator` は demo_nind が `indic_de` そのまま、他は `temp_share` / `unemployment_rate` / `housing_cost_overburden`。
- ライセンス・利用規約: 上の Eurostat 節と同じ（出典明記で再利用可、確認日 2026-10-06）。出典表記: 「Source: Eurostat, demo_nind / lfsa_etpgan / une_rt_a / ilc_lvho07a（accessed 2026-10-18）」。raw はコミットしない。
- 取得方法（adapter 名、レート制限）: `theme_growth_fertility.eurostat`（`family_formation_requests` / `family_formation_rows` / `build_family_formation_mart` の純粋関数）＋ `pipeline._fetch_h10_eu` / `_stage_h10_eu` / `_mart_h10_eu`（`HttpxFetcher`、H5・H9-EU とは別ブロック）。**64 リクエスト（計 ~400 KB）**。公開レート制限なし。再取得は年 1 回。
- 既知の欠損・断絶・定義変更:
  - 次元コードが dataset ごとの閉集合の外なら `ValueError`（fail-closed）。要求したが返らない組み合わせ（`une_rt_a` Y25-29）は行なし。
  - OECD SF3.1 の粗婚姻率は欧州諸国については Eurostat Demographic Statistics が出典なので、同じ国・年では `demo_nind` GNUPRT と一致する（2020 年 ITA 1.6、ESP 1.9、SWE 3.6）。重複して保持するのは日本・韓国・米国と欧州を同じ mart で比べるため。
  - `lfsa_etpgan` は LFS 標本で、小セル（IS）は非公表 → 行なし。2021 年に LFS の調査設計が変わり `status: b`。

### 経済産業省 生産動態統計（機械統計）年報 xlsx（bicycle-industry ①: 自転車 2430・自動車 2400）
- URL / API: `https://www.meti.go.jp/statistics/tyo/seidou/result/ichiran/resourceData/08_seidou/nenpo/<YYYY>/h2daa<YYYY>k.xlsx`（2021–2025、各 2.3–3.2 MB、全品目 1 ファイル）。一覧 `…/ichiran/08_seidou.html`。2007–2020 は `…/ichiran/nenpo_2007-2020.html` に業種別 .xls（機械は `03_kikai/nenpo/h2dcd<YYYY>k{mc,hc1,hc2,ml}.xls`）で別形式 → 未対応（必要なら xlrd で追加）。
- 対象・粒度: シート「実数表」。調査票 2430「自転車及び車いす」= 軽快車／電動アシスト車／その他（スポーツ車等を含む完成車）／手動式・電動式車いす、2400「自動車」= 軽・小型・普通乗用車、バス・トラック、二輪（≤50 / 51–125 / 126–250 / >250 ml）。アイテム = 生産数量・生産金額（千円）・受入数量・販売数量・販売金額・出荷その他数量・月末在庫数量。時間軸コード 1 行目（YYYY000000 暦年 / YYYY100000 年度 / YYYY00ssee 四半期 / YYYY00MMMM 月）。2021–2023 年報は暦年 5 年分（→ 2017 年まで遡れる）・年度 2・四半期 4・月次 12、2024 年報から月次 12 のみ。秘匿 "X"、不詳 "***"。**販売数量は受入（他社・輸入品の仕入）を含むため生産数量より大きい**。
- ライセンス・利用規約（確認 2026-10-22）: `meti.go.jp/main/rules.html` 経済産業省ウェブサイト利用規約 = 政府標準利用規約（第 2.0 版）準拠、出典表示で商用含め利用可。raw は非コミット（既定）。出典: 経済産業省「経済産業省生産動態統計年報 機械統計編」。
- 取得方法: `theme_bicycle_industry.meti`（URL 組み立て・xlsx → long 行 `parse`・`build_mart`）＋ `pipeline._fetch_meti/_stage_meti/_mart_meti`。**www.meti.go.jp は非ブラウザ UA に 403**（robots.txt も 403。一覧 HTML は 202 でボット判定）→ `socioscope_core.config.Settings.browser_ua_hosts`（既定 `["www.meti.go.jp"]`）に載せたホストだけ `HttpxFetcher` が汎用ブラウザ UA を送る。5 ファイル逐次、年 1 回（年報は翌年 4 月頃）。
- 既知の欠損・断絶・定義変更: 品目番号は年で振り直される（2024 年にトラック細分が変更）ため、品目は NFKC 正規化した品目名で同定（`meti.PRODUCTS`、必須 5 品目が欠けると fail-closed）。同じ系列×期間が複数年報にあるときは最新の年報を採る（改定反映）。「その他」自転車にスポーツ車・ミニサイクル・子供車が混在し分離不可。原付一種は 2400 の「二輪自動車 ≤50 ml」。

### UN Comtrade preview API（bicycle-industry ④: 自転車関連 HS の輸出入）
- URL / API: `https://comtradeapi.un.org/public/v1/preview/C/A/HS?reporterCode=392,842,276,528,250,826,380,156,490&period=<年>&cmdCode=8712,871160,8714&flowCode=M,X&partnerCode=0`（年ごと 1 JSON、2010–2024 の 15 リクエスト、各 ~48 行）。preview は 1 期間/呼び出し・≤500 行。逐次呼び出しでも 429（Retry-After 2 s 前後）→ `HttpxFetcher` が Retry-After を守って最大 5 回再試行する。登録キー（無料）の tier は使わない。
- 対象・粒度: 報告国 × 年 × HS（8712 完成自転車、871160 電動機のみの二輪＝ e-bike と原付・電動バイクが混在、8714 部品）× フロー（M 輸入 / X 輸出）、相手国 世界計。列: `qty`（台。`qtyUnitCode` −1 の行は None。8714 は数量なし、DEU 2010・2012–2014、USA 2014、CHN 2015–2017、TWN 2012 の 8712 も数量なし）、`net_wgt_kg`、`value_usd`（primaryValue = 輸入 CIF / 輸出 FOB）。台湾は reporterCode 490（Other Asia, nes）。
- ライセンス・利用規約（確認 2026-10-22）: UN Comtrade Terms of Use — 非商用・出典表示で利用可、バルク再配布は制限。raw は非コミット、staged/marts は出典「UN Comtrade Database」を明記。
- 取得方法: `theme_bicycle_industry.comtrade`（`url(year)`・`parse(payload, year)`（期間・相手国不一致は ValueError、知らない報告国・品目は skipped）・`build_mart`）＋ `pipeline._fetch_comtrade/_stage_comtrade/_mart_comtrade`。年 1 回。
- 既知の欠損・断絶・定義変更: 871160 は HS2017 から（2016 以前は 871190 に含まれ系列が切れる）。数量欠損は上記。`isReported=false, isAggregate=true` の行（UN 推計を含む）をそのまま使う。

### Eurostat HICP `prc_hicp_midx` と US BLS CPI（bicycle-industry ⑤: 自転車・自動車・二輪の価格指数）
- URL / API: HICP `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_midx?format=JSON&lang=EN&unit=I15&coicop=CP0711&coicop=CP0712&coicop=CP0713&geo=…&sinceTimePeriod=2005-01`（JSON-stat 2.0、1 リクエスト ~8 千値、キー不要）。BLS `https://api.bls.gov/publicAPI/v2/timeseries/data/<series>?startyear=<y1>&endyear=<y2>`（GET、キー無し 10 年/リクエスト、2 系列 × 3 区間 = 6 リクエスト）。
- 対象・粒度: HICP = CP0711 自動車 / CP0712 二輪 / CP0713 自転車、2015=100、EU27_2020・EA20・DE FR NL IT ES BE AT DK SE PL UK CH（US は geo にあるが CP071x の値なし）、月次 2005-01–2025-12。BLS = `CUUR0000SERC01`（Sports vehicles including bicycles、自転車単独の品目はない）と `CUUR0000SETA01`（New vehicles）、1982-84=100、月次 2006-01–2026-09（2025-10 は未公表 "-" → 落とす）。米国の二輪 CPI は 2000 年で終了。
- ライセンス・利用規約（確認 2026-10-22）: Eurostat copyright notice（出典表示で商用含め再利用可）、BLS はパブリックドメイン。raw 非コミット（既定）。
- 取得方法: `theme_bicycle_industry.prices`（`hicp_url`/`parse_hicp`（次元順 freq/unit/coicop/geo/time と unit=I15 を検査、疎な値は欠損）、`bls_url`/`parse_bls`（REQUEST_SUCCEEDED 以外は ValueError）、`build_mart`）＋ `pipeline._fetch_prices/_stage_prices/_mart_prices`。mart `marts/price_indices` は両ソースを 1 つの long 表に（基準年が違うので `base` 列で区別、比較は再基準化して行う）。
- 既知の欠損・断絶・定義変更: `prc_hicp_midx` は「廃止・`prc_hicp_minr` に置換」と表示（2026-02 更新で 2025-12 まで配信）。`minr` は COICOP 2018 で次元名が違うため、構造を確認して切り替える（追跡項目）。HICP はヘドニック調整済みでセールの深さは直接は捉えない。

### シマノ 有価証券報告書 PDF（EDINET、bicycle-industry ⑦: 自転車部品セグメント・地域別売上）
- URL / API: `https://disclosure2dl.edinet-fsa.go.jp/searchdocument/pdf/<docID>.pdf`（キー不要、各 0.5–0.7 MB）。docID（事業年度 → docID）: 2025 S100XQSE、2024 S100VGFP、2023 S100T5J9、2022 S100QH4Z、2021 S100NQC5、2020 S100L203、2019 S100IA93、2018 S100FGAL、2017 S100CMXI、2016 S1009Z4C、2015 S10078MN、2014 S1004EF8（`theme_bicycle_industry.shimano.DOCS`、2026-10-22 に全部取得・manifest 記録）。FY2013 以前の有報は EDINET に無い（FY2013 は FY2014 有報の前期比較で得る）。**EDINET は 2026-10-24 のメンテナンス後に PDF 表示用 URL の形式を変える**（予告）。EDINET API v2 はキー登録要のため使わない。shimano.com / corporate.shimano.com は非ブラウザ・ブラウザ UA とも 403。決算短信補足資料は xj-storage.jp に置かれ取れるが URL にランダム hex を含み一覧は取れない（直近分のみ手で控える）。
- 対象・粒度: 「セグメント情報」の 外部顧客に対する売上高・セグメント利益（自転車部品／釣具／その他）、「地域ごとの情報 (1) 売上高」（日本／北米／ヨーロッパ／アジア／その他の地域／合計）。百万円。当期と前期の両方を取り、mart はその年の有報を採って翌年の有報と食い違えば `restated_next_year` に残す（2026-10-22 時点で食い違い 0）。
- ライセンス・利用規約（確認 2026-10-22）: EDINET 開示書類（著作権は提出者）。引用・非商用の研究目的で利用。raw PDF は非コミット（既定）。出典「株式会社シマノ 有価証券報告書（EDINET）」。
- 取得方法: `theme_bicycle_industry.shimano`（`url`/`raw_name`、`pdf_text`（pypdf）、`parse_pages`（「前／当連結会計年度（自 …」でブロックに割り、`外部顧客に対する売上高` 行・`セグメント利益` 行・`地域ごとの情報 (1) 売上高` 直後の 6 数値行を正規表現で読む。「△ 1」は負、「－」は None、和暦は西暦に変換。表が無ければ ValueError）、`build_mart`）＋ `pipeline._fetch_shimano/_stage_shimano/_mart_shimano`。年 1 回（3 月末の有報提出後。URL 形式の再確認が要る）。
- 既知の欠損・断絶・定義変更: FY2018 有報から和暦→西暦。FY2023 有報から収益認識の内訳行（一時点で移転される財）が加わるが「外部顧客に対する売上高」行は共通。FY2010–2012 は取れない（gap）。地域別は「顧客の所在地」ベースで自転車部品だけの地域別ではない（補足説明資料には自転車部品の仕向地別があるが未採用）。

### 総務省 消費者物価指数 2025 年基準 品目別 長期時系列 CSV（bicycle-industry ③: 自転車 A/B・乗用車の価格指数）
- URL / API: `https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482831&fileKind=1`（年平均 `zni2025a.csv`、214 KB）、`…statInfId=000040482945&fileKind=1`（月次 `zmi2025a.csv`、2.2 MB）。appId 不要。一覧: 政府統計コード 00200573、2025 年基準 `tstat=000001243876`。stat.go.jp 直置き `data/cpi/2025/csv/zmi2025aa.csv`（2025-01– のみ、3 桁）もある。2026-08 分（2026-10-02 公表）から 2025 年基準に切り替わり、2020 年基準（000032103938 / 000032103844）は旧基準。
- 対象・粒度: 全国、品目 752 列のうち符号で選ぶ 8 品目（`cpi.ITEMS`）。行 0 品目名・1 英語名・2 符号・3 含類総連番・4 ウエイト・5 ウエイト 1 万分比、6 行目以降が期間（`YYYYMM` または `YYYY  `）。CP932（e-Stat の Content-Type は UTF-8 と誤表記）。空セルは未収集（自転車Ｂは 2015-01 から、普通乗用車 A/B は 1995 から）。2025 年平均 = 100。
- ライセンス・利用規約（確認 2026-10-22）: 政府標準利用規約（第 2.0 版）。出典「政府統計の総合窓口(e-Stat)、消費者物価指数（総務省）2025 年基準 を加工」。raw 非コミット。
- 取得方法: `theme_bicycle_industry.cpi`（`FILES`/`url`/`raw_name`、`parse`（ヘッダ検査・符号で列選択・対象符号欠落は ValueError）、`build_mart`）＋ `pipeline._fetch_cpi/_stage_cpi/_mart_cpi`。月 1 回（毎月第 3 金曜の公表後）。
- 既知の欠損・断絶・定義変更: 基準改定で列位置が動く（2020 基準 745 列 → 2025 基準 752 列）ため符号で選ぶ。自転車Ａ／Ｂ、普通乗用車Ａ／Ｂ の銘柄規格は基準ごとに見直されるので長期系列は接続指数（総務省が遡及）に依存。品目「自転車」は A・B の加重。自動二輪の品目はない（米 BLS も 2000 年で終了）→ 二輪の価格は Eurostat HICP CP0712 のみ。

### 経済センサス-活動調査（令和 3 年）卸売業・小売業 産業編（総括表）第 1 表 xlsx（bicycle-industry ⑧: 自転車小売業の長期時系列）
- URL / API: `https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040032840&fileKind=0`（`f1_001.xlsx`、149 KB、appId 不要）。政府統計コード 00200553。`fileKind=1/4` は 404。
- 対象・粒度: シート `f1_001`。列: 地域（`00_全国` ＋ 都道府県）、階層、産業ラベル（`592_自転車小売業` 等）、年次ラベル（`9_2021年`）、事業所数・事業所数（法人）・事業所数（個人）・従業者数_合計・年間商品販売額（百万円）・売場面積（㎡）。年次 1994・1997・1999・2002・2004・2007・2012・2014・2016・2021。全国行だけを `census.INDUSTRIES` の 5 業種で採る。`-` は該当なし、`x` は秘匿（None）。
- ライセンス・利用規約（確認 2026-10-22）: 政府標準利用規約（第 2.0 版）。出典「政府統計の総合窓口(e-Stat)、令和3年経済センサス‐活動調査（総務省・経済産業省）卸売業，小売業 産業編（総括表）第1表 を加工」。raw 非コミット。
- 取得方法: `theme_bicycle_industry.census`（`URL`/`RAW_NAME`、`parse`（指標ヘッダ行を探し、5 業種の全国行を long に。業種欠落・シート欠落・非 xlsx は ValueError）、`build_mart`）＋ `pipeline._fetch_census/_stage_census/_mart_census`。5 年に 1 回（次は 2026 年調査の 2028 年公表）。
- 既知の欠損・断絶・定義変更（表の注記）: 2007 年以前と 2014 年は商業統計調査、2012・2016・2021 年は経済センサス（注 5）。1999・2004 年は簡易調査（注 6）。2016 年の個人経営は売場面積を含まず、**2021 年の個人経営は年間商品販売額・売場面積を含まない**（注 7）→ 2016→2021 の販売額の比較は法人中心。2012 年以降は格付不能の事業所を含むため合計と内訳が一致しないことがある（注 8）。二輪自動車小売業 5914 は一部の年で値なし。

### UN Comtrade preview API — 原産国別（bicycle-industry H8: 中国・台湾からの輸入）
- URL / API: `https://comtradeapi.un.org/public/v1/preview/C/A/HS?reporterCode=392,842,276,528,826&period=<年>&cmdCode=8712,871160,8714&flowCode=M&partnerCode=156,490`（年ごと 1 JSON、2015–2024 の 10 リクエスト、各 30 行）。世界計の行は既存の `comtrade_<年>.json` から取り、mart で `WLD` と `OTH`（= 世界 − 中国 − 台湾）を足す。
- 対象・粒度: 輸入国 5（日・米・独・蘭・英）× 相手国（中国 156・台湾 490）× HS 3 × 2015–2024。列は世界計と同じ ＋ `partner`。
- ライセンス: 世界計と同じ（UN Comtrade Terms of Use、raw 非コミット）。
- 取得方法: `comtrade.origin_url/origin_raw_name`、`parse(payload, year, partners=True)`、`build_origin_mart`（staged/comtrade/bicycle_trade と結合）＋ `pipeline._fetch_comtrade_origin/_stage_comtrade_origin/_mart_comtrade_origin`（source 名 `un_comtrade_origin`）。
- 既知の欠損: 一方の相手国しか無い年は OTH が None。台数欠損は世界計と同じ扱い。

### 総務省 社会生活基本調査 時系列統計表（bicycle-industry H11: スポーツ種類別 行動者率 1986–2021）
- URL / API: `https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032229293&fileKind=0`（令和 3 年調査の時系列統計表「男女、年齢、スポーツの種類別行動者率の推移（10 歳以上）昭和 61 年〜令和 3 年」、xlsx 62 KB、シート `jikei2`、appId 不要）。政府統計コード 00200533。`fileKind=1/4` は 404（Excel のみ）。各年の詳細表（行動者数・頻度別・平均行動日数、2021: 000032222867〜869、2016: 000031592990〜、2011: 000013345604〜（.xls）、2006: 000001091702〜（.xls））は未採用。
- 対象・粒度: スポーツ 23 種目（2021 年区分）× 男女（総数／男／女）× 年齢階級（総数、10–14、15–19、20–24、25–29、30–39、40–49、50–59、60–64、65–69、70 歳以上、再掲 15 歳以上・65 歳以上）× 調査年（1986・1991・1996・2001・2006・2011・2016・2021）。値は過去 1 年の行動者率（%）。`...` は集計なし。
- ライセンス・利用規約（確認 2026-10-22）: 政府標準利用規約（第 2.0 版）。出典「政府統計の総合窓口(e-Stat)、社会生活基本調査（総務省）令和3年 時系列統計表 を加工」。raw 非コミット。
- 取得方法: `theme_bicycle_industry.shakai`（`URL`/`RAW_NAME`、`parse`（スポーツ名行と西暦行から列を組み立て、総数／男／女 × 年齢階級の行を long に。必須種目・シート・男女×年齢の欠落は ValueError）、`build_mart`）＋ `pipeline._fetch_shakai/_stage_shakai/_mart_shakai`。5 年に 1 回（次は 2026 年調査、2027 年公表）。
- 既知の欠損・断絶・定義変更: サイクリングは 2001 年に集計なし、1986・1991 は総数と 10–14 歳なし。2021 年に種目区分が変更（ゲートボール削除、グラウンドゴルフ・ヨガ追加。サイクリングの定義は不変）。2011 年は東日本大震災で一部地域を除く。年齢の上限は 70 歳以上（詳細表は 75／85 歳以上）。行動者数（千人）は別表。
- 補助候補（未採用）: 笹川スポーツ財団 スポーツライフ・データ（サイクリング 年 1 回以上の実施率は版ページの HTML 文中のみ、週 1 回以上・年代別は有料）。日本雑誌協会 印刷証明付部数は『サイクルスポーツ』『BiCYCLE CLUB』を収録していない（H12 取り下げ）。

### 台湾 MOPS 月次営業収入 JSON API（bicycle-industry H10: Giant・Merida・KMC・Ideal Bike）
- URL / API: `POST https://mops.twse.com.tw/mops/api/t05st10_ifrs`、本文 `{"companyId": "<4 桁>", "dataType": "2", "subsidiaryCompanyId": "", "year": "<民國年>", "month": "<1–12>"}`（JSON、キー不要）。`dataType` が "2" 以外だと最新月だけ返る。収録は民國 103 年（2014 年）1 月から。1 社 1 月 1 リクエスト（4 社 × 2014–2026 = 624 件、2026-10-22 取得。429 なし）。`mops.twse.com.tw/robots.txt` は 404（方針なし）。**旧 `mopsov.twse.com.tw`（全社月次 HTML）と `doc.twse.com.tw`（年報 PDF）は robots.txt が全面 Disallow のため使わない。**
- 対象・粒度: 巨大 9921（Giant）、美利達 9914（Merida）、桂盟 5306（KMC、チェーン）、愛地雅 8933（Ideal Bike、OEM）。`本月`（当月営業収入、NT$ 千）、`去年同期`、`本年累計`。応答の `result.data` は `[ラベル, 値]` の配列。
- ライセンス・利用規約（確認 2026-10-22）: 臺灣證券交易所の公開開示（上場企業の月次営業収入）。政府資料開放授權條款 v1 の公開情報として出典表示で利用。raw 非コミット。
- 取得方法: `theme_bicycle_industry.tw_mops`（`body`/`raw_name`/`requests`、`parse`（未収録月は行なし、`yymm` 不一致は ValueError）、`build_mart`）＋ `pipeline._fetch_mops/_stage_mops/_mart_mops`（`SourceFetcher.post_json` を使う）。月 1 回（各月 10 日の公表後）。
- 既知の欠損・断絶: 2013 年以前は JSON API に無い。連結ベース（海外工場を含む）で、台湾からの輸出とは一致しない。

### UN Comtrade 台湾輸出（bicycle-industry H9: reporter 490 × 仕向地）
- URL / API: `…/preview/C/A/HS?reporterCode=490&period=<年>&cmdCode=8712,871160&flowCode=X&partnerCode=392,842,276,528,826,0`（年ごと 1 JSON、2015–2024）。mart で OTH（= 世界 − 5 か国）を足す。
- 既知の欠損: 871160 は 2017 年から。台湾の完成車輸出は 2015 → 2019 に半減しており（生産の海外移転）、世界需要の代理としては弱い（R5 で明記）。

### Merida 連結財務報告 PDF（bicycle-industry H14: Specialized 持分法・関連当事者売上）— ADR 0006 の例外
- URL / API: 投資家向けページ `https://www.merida-bikes.com/zh-tw/p/tou-zi-ren-zi-xuninvestors/cai-wu-zi-xun`（`www.merida-bikes.com/robots.txt` は空＝許可）からリンクされた PDF 3 本: FY2023 Q4 `…/financial-report/112q4.pdf`、FY2024 Q4 `…/2024he-bing-cai-bao.pdf`、FY2025 Q4 `…/merida114q4-fsc.pdf`（ベース `https://merida-cdn.m-c-g.net/merida-v2/media-raw/countries/zh-tw/financial-report/`、クエリ `?p1`）。
- ADR 0006 の例外（満たした条件）: (1) 取引所規則に基づく公開開示（連結財務報告、会計師核閲済み）。(2) 開示主体 Merida 自身の、robots 許可ページから直接リンク（上記 URL）。(3) Disallow を置いているのは制作会社の資産 CDN `merida-cdn.m-c-g.net`（`User-agent: * / Disallow: /`、LinkChecker のみ許可）で、Merida のサイトではない。(4) 文書単位 3 本、年 1 回、クロールなし。ユーザー承認 2026-10-22。
- 対象・粒度: NT$ 千。損益表 4000 營業收入淨額、7370/7770 採用權益法認列之關聯企業損益之份額（SBC を含む関連企業全体。SBC 単独の損益は開示されない）、注記「採用權益法之投資」の SBC 帳簿価額と関連企業合計、注記「關係人交易」の SBC 集團向け銷貨。各報告の当期・前期。
- ライセンス・利用規約（確認 2026-10-22）: 会社の公開開示文書（著作権は会社）。引用・研究目的で出典表示。raw 非コミット（manifest のみ）、再配布しない。
- 取得方法: `theme_bicycle_industry.merida`（`DOCS`/`url`/`raw_name`、`parse_pages`（正規表現、5 指標のどれかが無ければ ValueError）、`build_mart`（当年の報告を優先、翌年と食い違えば `restated_next_year`））＋ `pipeline._fetch_merida/_stage_merida/_mart_merida`。年 1 回（Q4 報告の公表後、3 月末）。
- 既知の欠損・断絶: FY2022 以前の報告は自社サイトに無い（doc.twse は robots 全面 Disallow で使わない）。持分法損益は関連企業全体の行。NT$ 建て（為替換算差額を含む）。CDN が 403 を返すようになれば従う（ADR 0006）。

### Halfords 通期決算発表 PDF（bicycle-industry R7 補足: 英国小売の Cycling 売上）
- URL / API: `https://www.halfordscompany.com/investor-hub/results-reports-and-presentations/`（robots.txt: `Allow: /`、`/*?*` のみ Disallow）に静的リンクされた Preliminary Results PDF。`theme_bicycle_industry.halfords.DOCS` に FY2015–FY2026 の 12 本のパス（`/media/<id>/<file>.pdf`）。UA は既定で 200。
- 対象・粒度: £m。Retail 売上（53 週決算の FY2015・2020・2026 は 52 週列）、Cycling 構成比（% of Retail revenue、小数 1 桁、FY2015–2024）、Cycling 売上（FY2025 以降 £m 開示）。FY2015–2024 の Cycling £m は Retail × 構成比で導出（`derived`）。
- ライセンス・利用規約（確認 2026-10-22）: RNS 公開開示（著作権は会社）。引用・研究目的で出典表示。raw 非コミット。
- 取得方法: `theme_bicycle_industry.halfords`（`url`/`raw_name`、`parse_pages`（年により表の様式が違うため正規表現 3 種、fail-closed）、`build_mart`）＋ `pipeline._fetch/_stage/_mart_pdf_source(HALFORDS)`。年 1 回（6 月の通期発表後）。
- 既知の欠損・断絶: 粗利率は Retail／Group、%／£m が年で混在するため未採用。FY2024 の本文「Cycling 38% of Retail」と表 35.4% の不一致（表を採用）。Cycling は自転車以外（用品・整備）を含む。

### Accell Group 年報 PDF（bicycle-industry R7 補足: 欧州 e-bike メーカーのコロナ前基準線）— Wayback Machine
- URL / API: 本体サイトに年報は無く、年次マイクロサイト `annualreport20YY.accell-group.com` は消滅。Wayback の `https://web.archive.org/web/<ts>id_/<原 URL>`（`id_` = 原本をそのまま返す）。2017 年報 EN 全文（ts 20181112021717、17.5 MB）と 2021 年報 EN（ts 20240104114552、29.3 MB。20220817 のキャプチャは切れている）。Wayback の 1 MB 切れは Content-Length では分からず、`%%EOF` と pypdf で確認した。
- 対象・粒度: グループ売上 €m。2017 年報の 8 年表（2010–2017、小数 1 桁）と 2021 年報の 5 年表（2017–2021、整数）。2017 年は 2017 年報を優先し、2021 年報の値を `restated_later` に残す。
- ライセンス・利用規約（確認 2026-10-22）: 公開開示（著作権は会社）。Internet Archive 経由の取得は研究目的の引用。raw 非コミット。
- 取得方法: `theme_bicycle_industry.accell`（`DOCS`（ts, 原 URL）、`url`/`raw_name`、`parse_pages`、`build_mart`）＋ `pipeline._fetch/_stage/_mart_pdf_source(ACCELL)`。更新なし（2022 年に非上場化）。
- 既知の欠損・断絶: 2015・2016・2019・2020 の年報は Wayback で 1 MB 切れ。セグメント（自転車／部品）や e-bike 比率は年報本文にあるが未採用。2022 年以降の開示なし。

### JBPI 国内向自転車生産輸入統計・POS 販売統計 PDF（bicycle-industry H2: 車種別の台数・単価）
- URL / API: 一覧ページ `https://jbpi.or.jp/business/statistics/production_dynamics/data/`（robots.txt は `/wp-admin/` のみ Disallow）。国内向統計 12 月分: `…/uploads/2024/02/2021-2023国内向自転車生産輸入統計12月分.pdf`、`…/2025/02/2022-2024…`、`…/2026/02/2023-2025…`（`jbpi.DOMESTIC_DOCS`、版の最終年がキー）。POS 年間総括: `…/uploads/2026/04/POS販売統計2025年年間総括.pdf`（`jbpi.POS_DOCS`）。日本語ファイル名は percent-encode。
- 対象・粒度: 国内向統計 = 経産省 生産動態統計（国内生産、工場出荷）＋ 財務省 貿易統計（輸入、CIF）の合算、各版 3 年 × 品目（軽快車 生産／輸入、マウンテンバイク＝MTB・クロスバイク 輸入、ミニサイクル、幼児車、子供車、その他＝スポーツ車・外装変速機付軽快車 輸入、電動アシスト車 生産、その他 生産）、台・千円。2026 年から貿易統計の分類が変わり「スポーツ車」が単独行になる（7 月分 PDF、未採用）。POS = 月次 × 6 分類（軽快車／スポーツ車／幼児車／子ども車／電動アシスト自転車／その他）、台・税込円、2024-07 開始。
- ライセンス・利用規約（確認 2026-10-22）: 利用規約の記載なし。出典「（一財）自転車産業振興協会」を明記して引用。raw・staged は非コミット（manifest のみ）。
- 取得方法: `theme_bicycle_industry.jbpi`（`parse_domestic_pages`: 行ラベルの出現順で品目を割り当て、年見出しと生産合計で検算。`parse_pos_pages`: 時系列表の 14 数値＋月の行、分類合計で検算（金額は端数 10 円まで許容）。`build_domestic_mart`: 新しい版を優先し食い違いは `restated_from`、単価 = 金額 ÷ 台数。`build_pos_mart`: 平均単価）＋ `pipeline._fetch/_stage/_mart_pdf_source(JBPI_DOMESTIC / JBPI_POS)`。年 1 回（2 月の 12 月分、4 月の年間総括）。
- 既知の欠損・断絶: 2020 年以前は同じ表組みの PDF が無い（「2017-2023 自転車生産動態輸出入統計」は合計のみ）。電動アシスト車の輸入は原付・キックボード等を含む参考値で除外。2026 年の分類変更で 2025 年以前と接続しない。POS はカバー率 42%、家電量販を含まない。サイトは 2026-10-22 午前に 503（メンテ）だった。

### 自動車・二輪の協会統計 xls（bicycle-industry H6: 全軽自協・自販連・JAIA）
- URL / API: 全軽自協 `https://www.zenkeijikyo.or.jp/statistics/4new-yearsui`・`/2new-year` にリンクされた `hanbai4-2025kaku.xls`・`hanbai2-2025.xls`（robots: `/wp-admin/` のみ Disallow）。自販連 `https://www.jada.or.jp/pages/336/`（車種別）・`/343/`（登録車＋軽）にリンクされた `/files/libs/<id>/<id>.xls`（robots: `/files` Allow。ID は更新で変わるので manifest で固定）。JAIA `https://www.jaia-jp.org/stats/` の `PriceRange_year.xls`（robots: `Crawl-delay: 10`、GPTBot・ClaudeBot 等の AI クローラー UA は Disallow。本ツールは UA `socioscope/0.1` で 1 ファイルを年 1 回取得し遅延を守る）。
- 対象・粒度: 全軽自協 = 軽四輪 総台数・乗用車群計、軽二輪・小型二輪（台、暦年、1967–）。自販連 = 普通／小型乗用車・貨物・バス・合計（台、暦年、2021–2025）、登録車＋軽（2022–2025）。JAIA = 車両本体価格帯 13 帯（2,000 万円以上〜199 万円以下・不明・計、台、暦年、2003–2025）。
- ライセンス・利用規約（確認 2026-10-22）: いずれも利用規約の記載なし。出典（「全国軽自動車協会連合会調べ」「日本自動車販売協会連合会調べ」「日本自動車輸入組合調べ」）を明記して引用。raw 非コミット。
- 取得方法: `theme_bicycle_industry.auto_moto`（`xls_rows` → `parse_zenkei_rows`（和暦ラベルの `(yy)` から西暦）、`parse_jada_rows`（「1～12月」列の年計／年計シートの車種行）、`parse_jaia_rows`（帯の見出し順を検査、合計を検算）、`build_*_mart`）＋ `pipeline._fetch/_stage/_mart_pdf_source(ZENKEI / JADA / JAIA)`（`magic` を xls に）。年 1 回。
- 既知の欠損・断絶: 原付一種・二種の販売統計は協会に公開系列が無い（JAMA DB はフォーム専用）→ 生産動態統計で代理。自販連の年計は 2021 年から。JAIA の「不明」帯は 2021 年以前に数%。2025 年の新基準原付移行で原付一種は断絶しうる。

### IPU Parline API（Inter-Parliamentary Union、parliament-size H1・H2・H5b: 議院の定数・現員・職員数・予算、国の人口）
- URL / API: `https://api.data.ipu.org/v1/chambers` と `/v1/countries`（JSON:API、`page[size]=100&page[number]=N`、`links.next` で辿る。鍵不要）。chambers 281 件 = 3 ページ（各 7〜10 MB）、countries 193 件 = 2 ページ。`fields[...]` の sparse fieldset は効かない（全属性が返る）。
- 対象指標・粒度: 議院 × 属性 × 期間（long）。採用した属性は `ipu.CHAMBER_ATTRS`（statutory_members_number / current_members_number / directly_elected_number / designation_mode / electoral_system / electoral_subsystem / major_sys_elect_mems / mixed_sys_elect_mems / permanent_staff_number / is_staff_combined_parl / chamber_budget（`{"type": 通貨, "value": 額}`）/ chamber_budget_ppp / is_budget_combined_parl / basic_salary / basic_salary_ppp / num_days_parl_plen / num_cham_perm_committees）と `ipu.COUNTRY_ATTRS`（country_name / iso_alpha3 / region / subregion / political_system / local_currency / members_per_country / population_in_thousands（1950– 年次）/ inhabitants_per_parliament / parliament_devoted_budget_perc / ppp_conversion_factor / other_groupings（`[{"term": "oecd_members"}]`）。
- ライセンス・利用規約（確認日）: API レスポンスの `meta.licence` に「Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International」、`meta.terms_of_use` に ipu.org/terms-use（2026-10-27 確認）。**非商用・出典表示・継承**。`data/README.md` に記載。出典表記: 「Inter-Parliamentary Union, Parline: global data on national parliaments, https://data.ipu.org (accessed 2026-10-27)」。
- 取得方法（adapter 名、レート制限）: `theme_parliament_size.ipu`（`url`/`raw_name`/`parse`/`has_next`/`build_mart`）、`pipeline._fetch_ipu`。レート制限の記載なし。5 リクエストで完了。`data.ipu.org` の HTML ページ（about、terms）はボット UA に 403 を返すが API は返す。
- 既知の欠損・断絶・定義変更: `statutory_members_number` は OECD 38 か国で欠損なし。`permanent_staff_number` は AUT・CHE・CHL（上院）・IRL が欠損、`chamber_budget_ppp` は OECD 24 議院が欠損（H2・H5b では国数が減る）。人口は 2023 年が 276 議院、2024–25 年が 5 議院。`parliament_structure` は常に null（一院制・二院制は chamber_id の LC/UC 接尾辞で判定）。`country_name` は `{"en", "fr"}` の辞書。

### 総務省 衆議院議員総選挙 結果調 Excel（parliament-size H3・H4: 比例ブロック別 党派別得票・議席配分表・当選人数・都道府県別有権者数）
- URL / API: `https://www.soumu.go.jp/main_content/<id>.<xls|xlsx>`。第 50 回（2024-10-27、.xls）: 2(1) 000979118、2(2) 000979120、3(1) 000979122、3(10) 000979131、3(12) 000979133。第 51 回（2026-02-08、.xlsx）: 001061471、001061473、001061475、001061484、001061486。資料集ページ `senkyo/senkyo_s/data/shugiin<N>/index.html`（Shift_JIS、ボット UA でも 200）。robots.txt は `ia_archiver` のみ拒否。
- 対象指標・粒度: 2(1)/2(2) 都道府県 × 選挙当日の有権者数・投票者数（小選挙区／比例代表、比例はブロック付き）。3(10) ブロック × 党派 × 得票数（按分票は小数）・得票率。3(12) ブロック × 党派 × 当選順位（ドント商の表）。3(1) 党派 × 小選挙区／比例代表 当選人数（無所属・本人届出を含む）。
- ライセンス・利用規約（確認日）: 総務省ホームページは政府標準利用規約（第 2.0 版、CC BY 4.0 互換。2026-10-27 確認）。出典表記「総務省『衆議院議員総選挙 結果調』」。
- 取得方法（adapter 名、レート制限）: `theme_parliament_size.soumu`（`ELECTIONS`/`url`/`raw_name`/`rows_of`、`parse_electorate_smd`/`parse_electorate_pr`/`parse_pr_votes`/`parse_pr_seats`/`parse_winners`、`build_*_mart`）、`pipeline._fetch_soumu`。xls は xlrd、xlsx は openpyxl。レート制限の記載なし。
- 既知の欠損・断絶・定義変更: 第 50 回は得票数が「694,578.943」のような文字列、第 51 回は数値。3(12) の議席配分表は党が多いと同じブロックが複数チャンクに分かれる。公式議席は名簿登載者不足による他党への移転を含む（2024 国民民主党 3 議席、2026 自民党 14 議席）ので、純ドントとの差を `jp_hr_pr_results.seats` と比べて確認する。3(1) の「本人届出（政党等所属）」は党名ではないが 1 議席を持つ。ブロック名「東京都」は「東京」に正規化。

### e-Stat 令和 2 年国勢調査 人口等基本集計 表 2-1（parliament-size H4b: 都道府県別 日本人人口）
- URL / API: `https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032142404&fileKind=0`（xlsx 478 KB、appId 不要）。一覧 `stat-search/files?tclass=000001125102&cycle=0`。
- 対象指標・粒度: 国籍区分（国籍総数／うち日本人）× 男女 × 地域（全国・都道府県・21 大都市・特別区・人口 50 万以上の市）× 年齢各歳。採るのは 国籍総数・うち日本人 × 総数 × 都道府県（地域識別コード `a`）の総数列。
- ライセンス・利用規約（確認日）: 政府標準利用規約（第 2.0 版、CC BY 4.0 互換。2026-10-27 確認）。出典表記「政府統計の総合窓口(e-Stat)、令和 2 年国勢調査 人口等基本集計（総務省統計局）を加工」。
- 取得方法（adapter 名）: `theme_parliament_size.estat`（`URL`/`RAW_NAME`/`workbook_rows`/`parse`/`build_mart`）、`pipeline._fetch_estat`。
- 既知の欠損・断絶・定義変更: 「国籍総数」は国籍不詳を含む（全国 126,146,099）。「うち日本人」の全国計は 121,541,155 で、結果概要の「日本人人口 1 億 2,339 万人」（不詳補完値）とは異なる。画定審の配分はどちらを使ったか本書では未確認だが、アダムズ方式でこの値から現行の 289・176 の配分が完全に再現できる。

## 記録テンプレート（ソース採用時）
```
### <ソース名>
- URL / API:
- 対象指標・粒度（国×年 など）:
- ライセンス・利用規約（確認日）:
- 取得方法（adapter 名、レート制限）:
- 既知の欠損・断絶・定義変更:
```

### H10 日本の婚姻時系列・都道府県パネル（growth-fertility H10 検定 C。IPSS 人口統計資料集 2026 の追加 9 表、e-Stat 時系列 2 表、内閣府 県民経済計算。2026-10-18 追記）
- 概要表への追記（共有ファイルのため末尾に記す）:
  | ソース | 内容 | 形式 | ライセンス | 状態 |
  |---|---|---|---|---|
  | IPSS 人口統計資料集 2026（追加） | 表 6-24 性・年齢別 未婚割合（1920–2020）・6-12 平均婚姻年齢（1899–2024）・6-23 50 歳時未婚割合；都道府県別 12-33★ TFR（1925–2024）・12-35 平均初婚年齢・12-36 男 30–34／女 25–29 未婚割合・12-37 50 歳時未婚割合・12-52 労働力率・12-53 完全失業率 | 静的 xlsx（`Popular2026/T06-NN.xlsx`, `T12-NN.xlsx`） | PDL1.0 | **採用**（H10） |
  | e-Stat 就業構造基本調査 時系列統計表 第 18 表 | 都道府県・性・従業上の地位・雇用形態別 有業者数（1977–2022、10 時点） | `file-download?statInfId=000031732282&fileKind=4`（xlsx 110 KB） | 政府標準利用規約（第2.0版） | **採用**（H10） |
  | e-Stat 住宅・土地統計調査 時系列 第 34-2 表 | 都道府県別 借家の 1 か月当たり家賃（総数・民営借家、1993–2023、7 時点） | `file-download?statInfId=000040354073&fileKind=4`（xlsx 130 KB） | 同上 | **採用**（H10） |
  | 内閣府 県民経済計算 総括表 7 | 1 人当たり県民所得（千円、2011–2022 年度） | 静的 xlsx `https://www.esri.cao.go.jp/jp/sna/data/data_list/kenmin/files/contents/tables/2022/soukatu7.xlsx`（32 KB） | 政府標準利用規約（第2.0版）（内閣府サイト利用規約） | **採用**（H10） |
- URL / API（2026-10-18 確認、すべて 200・xlsx、キー不要）:
  - IPSS: `https://www.ipss.go.jp/syoushika/tohkei/Data/Popular2026/{T06-24,T06-12,T06-23,T12-33,T12-35,T12-36,T12-37,T12-52,T12-53}.xlsx`（12–39 KB）。`theme_growth_fertility.ipss.TABLES` の末尾 9 件。
  - e-Stat 第 18 表（`prefecture.SHUGYO_TS18_URL`）と 第 34-2 表（`prefecture.JUTAKU_URL`）: `fileKind=4` がこの 2 表の xlsx。
  - 内閣府（`cao.URL`）。年度版が変わるとパスの `2022` が変わる。
- 表の構成（実測、`estat.xlsx_rows(payload, sheet)` の 1 始まり列番号）:
  - T06-24: 4 シート `(1) 未婚` `(2) 有配偶` `(3) 死別` `(4) 離別`（未婚のみ取込）。A=年齢（総数, 15～19 … 80～84, 85歳以上）、B..L=1920年, 1930年, 1950年1), 1960年1), 1970年 … 2015年*, 2020年*。B 列に「男」「女」のマーカー行。
  - T06-12: 2 段組。A=年次 1899–1989（1899, 1900, 1905–1940 の 5 年刻み, 1947, 1950–1970 の 5 年刻み, 1971–1989 各年）, B–D=全婚姻 夫/妻/年齢差, E–G=初婚 同; H=年次 1990–2024, I–K / L–N 同。初婚 1899–1905、全婚姻 1947・1950 は '…'。
  - T06-23: A=年次（1920 … 2010, 2015*, 2020*）, B–E=男 未婚/有配偶/死別/離別, F–I=女 同（未婚のみ取込）。1940 年の離別は空欄。
  - T12-33★（第 2 シート。第 1 シートは 5 年刻みの抜粋）: A=都道府県, B..=1925年, 1930年, 1950年, 1951 … 2024（77 列）。全国の直下に A 列が空の行 = 全国を都道府県と同じ 5 歳階級で算出した（）内の値（落とす）。沖縄は 1950–1972 が '…'、都道府県は 1951–1969 の非国勢調査年が '…'。
  - T12-35: 2 シート `T12-35(1)` 男 / `(2)` 女。B..J=1950年, 1960年, …, 2020年, 2024年。沖縄 1950–1970 は '　　...'。
  - T12-36: 1 シート。B 列ヘッダ「男　性　　30～34歳」、G 列「女　性　　25～29歳」、次行に 1970年, 1990年, 2010年, 2015年*, 2020年* × 2。
  - T12-37: 2 シート (1) 男 / (2) 女。B..L=1920年, 1930年, 1940年, 1950年, 1970年, 1990年, 2000年, 2005年, 2010年, 2015年*, 2020年*。
  - T12-52: 4 シート `(1) 1980年` `(2) 2000年` `(3) 2010年` `(4) 2020年*`。D=男, I=女（ヘッダ行）、次行 B..F=総数1), 15～29歳, 30～44歳, 45～59歳, 60歳以上, G..K=女 同。
  - T12-53: 1 シート。B=男, H=女、次行 1980年 … 2020年（6 列）× 2。
  - 就業構造 第 18 表 `Z018`: 行 11（0 始まり）= 調査年 1977…2022 が 18 ブロック × 10 列（L..GI、L=12）。ブロック = 総数／自営業主／家族従業者／雇用者／正規／非正規 × 男女計／男／女。非正規 1992 列は `19921)`（パート・アルバイトの合計の注）。都道府県名は I 列（`北 海 道` のように空白入り）、全国は H 列。1977 年の正規・非正規は '...'。政令市（札幌市 … 熊本市、東京特別区部）は行 61 以降（落とす）。sharedStrings の `<rPh>` ルビは `estat.xlsx_rows` が落とす（確認済み）。
  - 住宅 第 34-2 表: 7 シート（平成5年 … 令和５年）。1993–2013 は B 列が「01　北　海　道」のようにコードと名前の結合、D=総数; 1993/1998 は民営借家が木造（設備専用）/木造（設備共用）/非木造（H/I/J）に分かれ総数なし、2003–2013 は木造/非木造（H/I）; 2018/2023 は B=コード（00/01…/01100 市）、C=名前、E=総数、I=民営借家 総数、J=木造、K=非木造。大都市（札幌市 … 熊本市、特別区部）は都道府県の後（落とす）。1 畳当たり家賃（右半分）は未取込。
  - 県民経済計算 総括表 7（シート『実数』）: A=コード 01–47, B=都道府県名（北海道 … 沖縄県）, D..O=2011…2022（行 4 に西暦、行 3 に和暦）。47 行の後に 全県計（→ `00`）、地域ブロック、政令市（落とす）。シート『増加率』は未取込。
- 対象指標・粒度: `marts/jp_marriage_series`（646 行）と `marts/jp_prefecture_panel`（14,884 行、16 metric）。列定義は `themes/growth-fertility/CLAUDE.md` の H10 追記。
- ライセンス・利用規約（確認日 2026-10-18）: IPSS = PDL1.0（既出）。e-Stat = 政府標準利用規約（第2.0版）（既出、出典表記「出典：政府統計の総合窓口(e-Stat)、就業構造基本調査／住宅・土地統計調査（総務省）を加工」）。内閣府 = 内閣府ウェブサイトの利用規約（`https://www.cao.go.jp/notice/notice.html`）が **政府標準利用規約（第2.0版）** に準拠（CC BY 4.0 互換、出典表示）。出典表記「出典：内閣府『県民経済計算（2022 年度）』総括表 7 を加工」（`cao.LICENSE`）。raw は 3 ソースともコミットしない（manifest のみ）。
- 取得方法（adapter 名、レート制限）: `theme_growth_fertility.ipss`（H10 部: `never_married_share_rows` / `mean_marriage_age_rows` / `never_married_at_50_rows` / `pref_tfr_rows` / `pref_first_marriage_age_rows` / `pref_never_married_young_rows` / `pref_never_married_at_50_rows` / `pref_lfp_rows` / `pref_unemployment_rows` / `build_marriage_mart`）、`theme_growth_fertility.prefecture`（`employment_rows` / `rent_rows` / `build_prefecture_mart`）、`theme_growth_fertility.cao`（`income_rows`）＋ `pipeline._fetch_h9_jp/_stage_h9_jp`（IPSS 9 表）と `_fetch_h10_pref/_stage_h10_pref/_mart_h10_pref`。**12 リクエスト（合計 約 0.5 MB）**。raw は `data/raw/growth-fertility/{ipss/T06-NN.xlsx, ipss/T12-NN.xlsx, estat_shugyo/shugyo_ts18_employment.xlsx, estat_jutaku/jutaku_34_2_rent.xlsx, cao_kenmin/kenmin_soukatu7.xlsx}`。再取得は年 1 回（IPSS は `Popular2027`、県民経済計算は年度版のパス、e-Stat は statInfId が年次更新で変わる可能性）。
- 既知の欠損・断絶・定義変更:
  - 都道府県 TFR の全国値は日本人人口・年齢各歳、都道府県は 5 歳階級による算出（全国の（）内行は落としている）。1950–1972 年は全国に沖縄県を含まない。
  - 2015・2020 年の列見出しに `*`、1950・1960 年に `1)`（沖縄県を含まない）、T12-52 の総数に `1)` の注記号が付く（adapter は記号を落として年を照合。意味は各表の注を参照）。T06-23 の 1940 年は離別列が空欄（行なし）。
  - T06-12 と T12-35 の平均初婚年齢は人口動態統計に基づく（表の出典行）。T12-53 は国勢調査報告の完全失業率（労働力調査とは別系列）。
  - 就業構造基本調査 第 18 表: 1977 年は正規／非正規が '...'（行なし）。非正規の 1992 列に注 1)「パート」及び「アルバイト」の合計。推定人数は標本から復元した値で標準誤差は非公表。
  - 住宅・土地統計調査 第 34-2 表: 家賃は名目円。`rent` は総数列（専用住宅＋併用住宅）。1993・1998 年の民営借家は木造の内訳が設備専用／共用で総数が無いため `rent_private` は 2018・2023 のみ、`rent_private_nonwood` は全期間（設計 H10 の頑健性「民営借家のみ」はこれで行う）。公的借家の列名は 公団・公社（1993–2003）→ 都市再生機構・公社（2008–）と変わるが未取込。
  - 県民経済計算 総括表 7: 2022 年度版の 2011–2022 年度系列（名目、千円）。全県計は 47 都道府県の合計ベース。
  - 解析は fail-closed: 表題・ヘッダ・年列・全国＋47 都道府県の JIS 順（`prefecture.regions`）・第 18 表の 雇用者 ≥ 正規＋非正規 と 有業者 ≥ 雇用者 を照合。違えば `ValueError` → stage の skipped に「`<raw>: layout not recognised (<reason>)`」として残し、その表だけ書かない。

### H11 結婚の減少が出生率低下の何割か（growth-fertility H11。IPSS T06-24 の残り 3 シート、OECD Family Database SF2.4。2026-10-18 追記）
- 概要表への追記（共有ファイルのため末尾に記す）:
  | ソース | 内容 | 形式 | ライセンス | 状態 |
  |---|---|---|---|---|
  | IPSS 人口統計資料集 2026 表 6-24（追加シート） | 性・5 歳階級別の 有配偶・死別・離別 割合（1920–2020 の国勢調査 11 回。未婚は H10 で取込済み） | 既存 raw `ipss/T06-24.xlsx` のシート `T06-24(2)`〜`(4)`（再取得なし、manifest 追加なし） | PDL1.0 | **採用**（H11） |
  | OECD Family Database SF2.4 Share of births outside of marriage（xlsx） | 国 × 年（1960–2024）の婚外出生割合 %（OECD 加盟 38 か国） | 静的 xlsx `https://webfs.oecd.org/Els-com/Family_Database/SF_2_4_Share_births_outside_marriage.xlsx`（94 KB、鍵不要）、openpyxl | OECD Terms（CC BY 4.0、確認 2026-10-18） | **採用**（H11） |
- URL / API: SF2.4 のファイル名は `https://webfs.oecd.org/Els-com/Family_Database/` のディレクトリ一覧（HTML、2026-10-18 に httpx で取得）から特定した（同名の `.pdf` が説明文書。`SF_2_4_Share_births_outside_marriage.xlsx`、Last-Modified 2025-10-16）。`oecd_family.BOM_URL` に固定。
- 表の構成（実測）:
  - T06-24 シート (2) 有配偶 / (3) 死別 / (4) 離別: シート (1) と同じ配置（A=年齢、B..L=1920年 … 2020年*、B 列に「男」「女」のマーカー行、表題末尾に「（つづき）」）。**1950 年の 85 歳以上は (2)–(4) が `#DIV/0!`**（(1) は 0）。4 シートの同じセルの和は 99.9–100.1。
  - SF2.4 シート `Births_outside_marriage`: 行 4 = `Country | Note | 1960 … 2024`（Note 列は全行空）、行 5–42 = 加盟 38 か国、空行の後に Bulgaria / Croatia / Cyprus / Malta / Romania（非加盟、落とす）、`.. Not available` の凡例、Notes、Sources。シート `Chart SF2.4.A`（2023 または最新年、列 L–N と Q–S に同じ表が 2 回）・`Chart SF2.4.B`（1970 / 1995 / 2020 / 2023、参照年の注記列つき）は年次表の抜粋なので未取込。
- 対象指標・粒度: `marts/jp_marriage_series` に metric `married_share` / `widowed_share` / `divorced_share`（各 350 行）を追加して 1,696 行。`marts/oecd_births_outside_marriage`（long: iso3, year, metric, value, chart, source。1,998 行、38 か国、1960–2024）。列定義は `themes/growth-fertility/CLAUDE.md` の H11 追記。
- ライセンス・利用規約（確認日 2026-10-18）: IPSS は PDL1.0（H9/H10 と同じ）。SF2.4 は OECD Terms & Conditions（`oecd.LICENSE`、CC BY 4.0）。出典表記: 「OECD Family Database, SF2.4 Share of births outside of marriage (accessed 2026-10-18)」。raw はコミットしない（manifest のみ）。
- 取得方法: T06-24 は H9-JP の枠（`_fetch_h9_jp/_stage_h9_jp`）で既に取得・stage され、`ipss.marital_status_share_rows` が 4 シートを読む。SF2.4 は `pipeline._fetch_h11_oecd / _stage_h11_oecd / _mart_h11_oecd`（**1 リクエスト**）。
- 既知の欠損・断絶・定義変更:
  - T06-24: 1950 年 85 歳以上の有配偶・死別・離別は行なし。1950・1960 年は沖縄県を含まない。2015・2020 年は不詳補完値に基づく（H10 と同じ）。
  - SF2.4: 定義が 2 系統。AUS・CAN（1960–1973）・JPN・KOR・NZL は「親が互いに婚姻登録していない出生」（ex-nuptial / out-of-wedlock）、他国は「出生時の母の配偶関係が有配偶以外の出生」。CAN（1991 年以降）と MEX は配偶関係が記録された出生を分母にする（2018 年の未記録は CAN 8.3 %、MEX 7 %）。ISR は 2016 年までユダヤ人女性のみ。USA の 1980 年以前は推計。欧州各国は Eurostat Demographic Statistics が出典。
  - SF2.4 の被覆: 開始年は多くが 1960、AUS 1975、KOR 1981、CRI 1983、MEX 1985、EST 1989、FRA/COL 1998、CHL/ISR 2002、TUR 2010。最新年は 2023 が多く、CAN/GBR/KOR/MEX/NZL 2024、BEL 2018、IRL/ISL 2019、CHE 2020、DNK 2021、CHL 2022。JPN は 1960–1995 が 5 年刻み（2000 年以降各年）、POL も 1970–1995 が 5 年刻み、CAN は 1974–1990 が '..'。'..' は行なし（補完しない）。
  - 最新年の値（2026-10-18 取得）: JPN 2023 2.4、KOR 2024 4.7、ITA 2023 40.5、ESP 2023 50.0、SWE 2023 57.4、DNK 2021 54.7、FRA 2023 58.5、USA 2023 40.0。
### H12 結婚が外れた背景（growth-fertility H12。IPSS 第 16 回出生動向基本調査 報告書グラフデータ CSV 12 件、人口統計資料集 2026 T06-01★、NHK「日本人の意識」Q49。2026-10-18 追記）
- 概要表への追記（共有ファイルのため末尾に記す）:
  | ソース | 内容 | 形式 | ライセンス | 状態 |
  |---|---|---|---|---|
  | IPSS 第 16 回出生動向基本調査 報告書グラフデータ | 未婚者の結婚意思・結婚／独身の利点・独身の理由・交際状況・交際相手と知り合ったきっかけ・結婚相手の条件・結婚観（第 8〜16 回 = 1982〜2021、男女・年齢別、一部 95% CI 付き）、結婚年次別 恋愛／見合い／ネット（1930 年代〜2019–21 年）、夫婦の知り合ったきっかけ（第 8〜16 回、第 16 回は 2 期間） | 静的 CSV `https://www.ipss.go.jp/ps-doukou/j/db_16/16HoukokuBaseData/houkokuFigure<章>_<節>_<番号>.csv`（12 件、各 4–36 KB、`application/octet-stream`、CP932、tidy） | PDL1.0 | **採用**（H12） |
  | IPSS 人口統計資料集 2026 表 6-1★ | 初婚・再婚別婚姻数・初婚の割合・婚姻率（1884–2024 各年） | `https://www.ipss.go.jp/syoushika/tohkei/Data/Popular2026/T06-01.xlsx`（24.9 KB、シート `T06-01★`） | PDL1.0 | **採用**（H12） |
  | NHK 放送文化研究所「日本人の意識」調査 Q49 結婚観 | 「人は結婚するのが当たり前だ」／「必ずしも結婚する必要はない」の割合、全体・男女・年齢 7 階級（1993–2018 の 6 回） | `https://www.nhk.or.jp/bunken/yoron-isiki/nihonzin/data/q49.json`（7.3 KB、`application/json`、鍵不要） | サイト利用ルール（出典記載・加工明記・**営利利用不可**） | **採用**（H12。raw 非コミット） |
- URL / API（2026-10-18 に httpx で実 GET 確認、すべて 200）: CSV の URL 規則と 12 ファイル（`1_1_1`, `1_1_2`, `1_2_1`, `1_2_2`, `1_3_2`, `2_1_1`, `2_1_2`, `2_3_1`, `3_2_1`, `5_2_1`, `5_2_2`, `12_1_2`）は `ipss.GRAPH_BASE_URL` / `ipss.GRAPH_FILES` に固定。T06-01 は `ipss.TABLES` に追加（既存 URL 規則）。NHK は `nhk.URL` に固定。
- 表の構成（実測）:
  - CSV: 1 行目 = 図表タイトル（`報告書図表1-1-1 調査別にみた、未婚者の生涯の結婚意思` 等）、2 行目 = ヘッダ、以降 tidy（全セル二重引用符、CRLF、`割合` は幅合わせの先頭空白 `" 2.3"`）。ヘッダはファイルで異なり `ipss.GRAPH_HEADERS` に固定: 1_1_1 `調査回,性別,生涯の結婚意思,度数,割合,標準誤差,95%信頼区間上限,95%信頼区間下限`、1_1_2 は `年齢` を追加、1_2_1 / 1_2_2 `調査回,性別,結婚の利点|独身生活の利点,度数,割合,総数`、1_3_2 / 2_1_1 / 2_1_2 `調査回,性別,年齢,独身の理由|異性との交際状況|交際希望,度数,割合,総数`、2_3_1 `調査回,性別,知り合ったきっかけ,度数,割合`、3_2_1 `調査回,性別,重視する項目,重視する程度,度数,割合,総数`（性別は「男性が相手の女性に求める条件」「女性が相手の男性に求める条件」）、5_2_1 `結婚年,知り合ったきっかけ,度数,割合,標準誤差,95%信頼区間上限,95%信頼区間下限`、5_2_2 `調査回,知り合ったきっかけ,度数,割合`（調査回に `第16回(2021)a` = 2015/7–2018/6 結婚、`第16回(2021)b` = 2018/7–2021/6 結婚）、12_1_2 `調査回,性別,結婚・家族に関する考え方,旧来的な考え方への支持／不支持,割合,度数`（割合が度数の前）。調査回は `第N回(YYYY)`（第 8 回 = 1982, 9 = 1987, 10 = 1992, 11 = 1997, 12 = 2002, 13 = 2005, 14 = 2010, 15 = 2015, 16 = 2021）。
  - T06-01★: A=年次（1884–2024。**1941–1946 は行なし**）, B=総数, C/D=夫 初婚/再婚, E/F=妻 初婚/再婚, G/H=初婚の割合(%) 夫/妻, I=婚姻率(‰)。初婚・再婚・割合は 1884–1898 と 1947–1951 が '…'。注: 1884–1898 は『国勢調査以前日本人口統計集成』、1899 年以降は人口動態統計、1947–72 年は沖縄県を含まない、1940 年以前の総数は初婚・再婚の別不詳を含む、婚姻率は 1940 年以前が総人口・1947 年以降が日本人人口 1,000 対。
  - NHK JSON: `q49[0].q[0]`（`num` 第４９問、`text` 設問文、`type` S）→ `a[]` 3 回答（`id`/`num` 01–03、`text` 甲に近い／乙に近い／どちらともいえない、わからない、無回答、`short` するのが当然／しなくてよい／""）→ `year["1993"…"2018"].{ratio, number}.{all, male, female, age[7], cross[14], city[5], acad[7]}`。`ratio` は整数 %、`number` はその回答を選んだ人数。50 人未満の層は `"*25"` のように `*` を前置（`main.js` の注記）。年齢階級のラベルは JSON に無く、サイトの表示（16-19歳 / 20-29歳 / 30-39歳 / 40-49歳 / 50-59歳 / 60-69歳 / 70歳以上）を `nhk.AGE_LABELS` に固定。
- 対象指標・粒度: `marts/jp_marriage_attitudes`（long、2,365 行、キー `(figure, survey_round, period, marriage_year, sex, age, category, item, sub)`）、`marts/jp_marriage_series` に T06-01 の 8 metric 954 行を追加（2,650 行）、`marts/jp_norms_nhk`（long、180 行）。列定義は `themes/growth-fertility/CLAUDE.md` の H12 追記。
- ライセンス・利用規約（確認日 2026-10-18）:
  - IPSS（CSV・xlsx）: PDL1.0（H9 と同じ）。raw はコミット可だが既定どおりコミットしない。出典表記: 「国立社会保障・人口問題研究所『第 16 回出生動向基本調査 報告書』グラフデータ、『人口統計資料集 2026』（PDL1.0）」。
  - NHK（`https://www.nhk.or.jp/bunken/yoron-isiki/nihonzin/usage.html`、2024-01-24 制定）: 権利は NHK に帰属。出典を記載すれば利用可、編集・加工して利用する場合はその旨を記載（NHK が作成したかのような態様は不可）、**営利目的の利用は不可**（要問い合わせ）。→ raw はコミットしない（manifest のみ）、staged/mart は出典明記で保持。report・note 記事は非営利媒体に限り、出典表記「NHK放送文化研究所「日本人の意識」調査（https://www.nhk.or.jp/bunken/yoron-isiki/nihonzin/）を加工して作成」を必ず付ける。`nhk.LICENSE` に記載し manifest に残す。
- 取得方法（adapter 名、レート制限）: `theme_growth_fertility.ipss`（`graph_rows` / `build_attitudes_mart` / `first_marriage_rows`）＋ `pipeline._fetch_h12_jp / _stage_h12_jp / _mart_h12_jp`（**12 リクエスト、合計 174 KB**。raw `data/raw/growth-fertility/ipss/houkokuFigure<figure>.csv`、staged `staged/ipss/graph_<figure>`）。T06-01 は H9-JP の枠（**1 リクエスト**、raw `ipss/T06-01.xlsx`、staged `staged/ipss/t06_01`）。`theme_growth_fertility.nhk`（`parse` / `build_mart`）＋ `pipeline._fetch_h12_nhk / _stage_h12_nhk / _mart_h12_nhk`（**1 リクエスト**、raw `nhk_nihonjin_ishiki/q49.json`、staged `staged/nhk/q49`）。公開レート制限なし。再取得は IPSS が第 17 回公表時（URL の `db_16` と `GRAPH_ROUND_YEARS` を更新）、NHK は更新なし（調査終了）。
- 既知の欠損・断絶・定義変更:
  - CSV（IPSS 第 16 回の注記）: 第 16 回は「見合い結婚」に結婚相談所（オンラインを含む）を含める。「ネットで」は第 16 回で新設（第 11〜15 回の「メディアを通じて」は自由記述の事後分類、第 8〜10 回は該当なし）。「アルバイトで」は第 10 回から。5_2_2 の 2021b（2018/7–2021/6 結婚）はコロナ下の婚姻減期間で、構成比の上昇は件数の増加と等しくない。3_2_1 は第 13 回（2005）に設問なし。2_1_2 の交際希望は第 14 回以降（第 8〜13 回は「交際相手なし－交際希望の設問なし」の 1 行で、第 14 回以降は 望む／望まない／不詳 の 3 行の合計が「交際相手なし」）。1_3_2 は第 10・11 回の各 性 × 年齢 で 1 選択肢の総数が `NA`（割合は印字どおり、denominator は NULL）。5_2_1 の「2019～21年 その他・不詳」は割合 0.3 % で CI 下限 −0.3（印字どおり保持）。
  - T06-01★: 1941–1946 の行なし。**1918 年の夫（初婚 442,504 ＋ 再婚 75,724 = 518,228 > 総数 500,580）と 1926 年の妻（495,111 ＋ 43,277 = 538,388 > 502,847）は上流の数値が内部で矛盾し、印字の初婚の割合（88.4 / 98.5）も再計算値（85.4 / 92.0）と合わない**ため、その性・年の初婚・再婚・割合は行なし（`ipss._T0601_KNOWN_INCONSISTENT` に閉じて記録。他の年で起きれば ValueError）。
  - NHK: 設問は 1993 年開始（1973–1988 の調査には無い）、2018 年で終了。2022・2024 の後続調査は 4 件法（「そう思う／どちらかといえば…」）で非連続のため取り込まない。`cross`（性 × 年齢）・`city`（都市規模）・`acad`（学歴）は未取込。`ratio` は整数 % で小数なし。
  - 主要値（2026-10-18 取得）: 「いずれ結婚するつもり」男 95.9 → 81.4、女 94.2 → 84.3（1982 → 2021）。交際相手なし（18–34 歳）男 36.8 → 72.1、女 30.1 → 64.2。夫婦の出会い 第 8 回 → 第 16 回 b: 見合い 29.4 → 9.0、職場 25.3 → 21.4、ネット（なし）→ 13.6。妻初婚 1982 704,840、2019 497,598、2020 437,169、2021 417,783。NHK「するのが当然」1993 45 → 2018 27（男 51 → 35、女 39 → 20）。
