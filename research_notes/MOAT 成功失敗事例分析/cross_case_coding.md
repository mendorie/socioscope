# 横断コーディング表と事前登録仮説の集計

作成 2026-11-16。各事例ノート（`tech_success_global.md`・`tech_failure_global.md`・`hr_global.md`・`japan_cases.md`・`ai_era_2022_2026.md`）の一覧表を、`design/themes/moat-cases.md` の選定基準で母集団に入れる／入れないを判定し、仮説 H1〜H6 を事前登録の判定基準どおりに集計する。コードの根拠（出典）は各事例ノートにある。本ファイルは集計のみで、新しい事実は含まない。

## 1. 母集団の確定

### 1-1. 成功（確定）: 16 事例
条件: 巨大資本（売上または時価総額 10 倍以上）の参入・模倣・バンドル後 5 年以上、カテゴリ上位 2 位・拡大・独立存続（または首位のまま高倍率買収）。

| # | 事例 | 業界 | 巨大資本（参入年） | 資本差 | 主 MOAT | 副 MOAT | 主 MOAT の成立 | 巨大資本側の構造的制約（一次資料で確認できたもの） |
|---|---|---|---|---|---|---|---|---|
| 1 | Figma | テック | Adobe（XD 2016／買収提案 2022） | 44 倍 | SC-WF | ECO, NE-D | 参入前 | 反トラスト（EC・CMA が買収を阻止）、既存課金との共食い |
| 2 | Canva | テック | Adobe（Spark 2016／Express 2021） | 16 倍 | CP | ECO, BRAND | 参入前 | プロ向け高単価サブスクとの共食い |
| 3 | Zoom | テック | Microsoft（Teams 同梱 2017） | 590 倍 | BRAND | NE-D, SC-WF | **参入後**（2020 年） | 反トラスト（EU が Teams 分離を要求） |
| 4 | Shopify | テック | Amazon（Webstore 〜2015／Buy with Prime 2023） | 520 倍 | CP | ECO, SC-WF | 参入前 | マーケットプレイスとの共食い（Webstore 閉鎖） |
| 5 | Airbnb | テック | Google（旅行検索 2019） | 34 倍 | NE-X | BRAND, PP | 参入前 | 広告モデル上、供給側を自前で持たない |
| 6 | Datadog | テック | AWS（CloudWatch は創業前から） | 177 倍 | SC-WF | CP, SCALE | **先行者の市場に後から築いた** | 利益相反（他社クラウドを監視する動機なし） |
| 7 | Snowflake | テック | AWS（Redshift 2012、創業と同年） | 132 倍 | SC-DATA | CP, NE-X | **先行者の市場に後から築いた** | 利益相反（最大級の計算資源購入者） |
| 8 | Stripe | テック | PayPal／eBay（Braintree 買収 2013） | 10 倍超 | SC-WF | ECO, SCALE | 参入前（配布）／後（厚み） | 組織の優先度（消費者ウォレット中心） |
| 9 | Discord | テック | Microsoft（Skype 先行／買収提案 2021） | 700 倍超 | NE-D | SC-DATA, ECO | 参入前 | 組織の優先度（Teams 集中）、Skype 終了 2025 |
| 10 | Indeed | 人材 | Monster／CareerBuilder（既存大手）、Google for Jobs 2017 | 10 倍超 | NE-X | CP, NE-DATA, DIST | 参入前 | 掲載課金との共食い（Monster 10-K が参入障壁の低さを自認） |
| 11 | LinkedIn | 人材 | Monster（既存大手）、Google Hire 2017 | 17 倍 | NE-D | NE-DATA, NE-X, CP | 参入前 | 未確認 |
| 12 | Workday | 人材 | Oracle／SAP（Taleo・SuccessFactors 買収 2011–12） | 100 倍超 | SC-DATA | SC-WF, CP, PP | 参入前 | 保守収益との共食い（オンプレ） |
| 13 | ビズリーチ | 人材 | リクルート・パーソル・エン（ダイレクトスカウト、年未確認） | 30 倍 | NE-X | CP, BRAND | 参入前 | 弱い（リクルートは自社媒体の共食いを厭わない。§4 参照） |
| 14 | メルカリ | テック | ヤフー（ヤフオク!）、楽天（ラクマ 2016）、PayPay フリマ 2019 | 10 倍超（要確認） | NE-X | BRAND, SCALE | 参入前 | 未確認 |
| 15 | freee・マネーフォワード（法人） | テック | 弥生（オリックス 2014→KKR 2022）、OBIC、TKC | 10 倍超 | SC-DATA | SC-WF, ECO, CP | 参入前 | デスクトップ版ライセンスとの共食い |
| 16 | Pairs（エウレカ） | テック | Match Group／Tinder（2015 買収） | 10 倍超 | NE-X | BRAND | 参入前 | 該当なし（買収で解消） |

### 1-2. 成功（暫定）: 参入後 5 年未満または資本差 10 倍未満
Notion、Duolingo、Rippling、Gusto、Deel、Greenhouse、タイミー（資本差 6〜8 倍）、Cursor、Lovable、Replit、Midjourney、ElevenLabs、Runway、Harvey、Glean、Granola、Otter.ai、Calendly、Notion AI。頑健性チェックでのみ使う。

### 1-3. 失敗（確定）: 13 事例
条件: 一時カテゴリ首位または最速成長 → 巨大資本の参入後 5 年以内にシェア喪失・縮小・撤退・ピークを大幅に下回る売却。

| # | 事例 | 業界 | 巨大資本（参入年） | 資本差 | 主張していた堀 | 主 F | 副 F | 結末 |
|---|---|---|---|---|---|---|---|---|
| 1 | Evernote | テック | Apple・Microsoft（Notes 強化・OneNote 無料化 2014–15） | 1,000 倍超 | BRAND, SC-DATA | F-BUNDLE | F-SINGLE | 2023 年 約 2 億ドルで売却（ピーク 1/5〜1/10） |
| 2 | Meerkat | テック | Twitter（グラフ遮断・Periscope 2015-03） | 売上ゼロ | なし（SPEED） | F-PLATFORM | F-COPY | 2016 年終了 |
| 3 | Clubhouse | テック | Twitter Spaces 2020-12、Meta ほか 2021 | 売上ゼロ | NE-D, BRAND | F-COPY | F-SINGLE | 2023 年 人員半減 |
| 4 | Zynga | テック | Facebook（バイラル制限 2010・特別契約終了 2012） | 時価総額 10 倍超 | NE-D, NE-DATA, SCALE | F-PLATFORM | F-TECH | 株価 1 年で −80%、再建後 2022 年売却 |
| 5 | Vine | テック | Instagram 動画 2013-06 | 12 倍 | 独自フォーマット・クリエイター | F-COPY | F-ECON | 2017 年閉鎖 |
| 6 | Pebble | テック | Apple Watch 2015-04 | 1,000 倍超 | BRAND, ECO | F-COPY | F-ECON | 2016 年破産、2,300 万ドル |
| 7 | Houseparty | テック | Messenger Rooms 2020-04 | ほぼゼロ | NE-D, UX | F-COPY | F-SINGLE | 2021 年閉鎖 |
| 8 | Fitbit | テック | Apple Watch 2015-04 | 100 倍超 | BRAND, NE-D, DIST（小売） | F-COPY | F-ECON | 2019 年 Google へ 21 億ドル（ピーク 1/5） |
| 9 | Hired | 人材 | LinkedIn／Microsoft 2016〜 | 10 倍超 | キュレーション・両面市場 | F-ECON | F-SUPPLY | 2020 年清算協議→買収→2024 年吸収 |
| 10 | Triplebyte | 人材 | LinkedIn ほか | 10 倍超 | 技術評価 | F-SINGLE | F-ECON | 2023 年終了 |
| 11 | Origami Pay | テック | PayPay（ソフトバンク・ヤフー）2018-10、100 億円還元 | 100 倍超 | 先行・加盟店網 | F-ECON | F-COPY, F-SUPPLY | 2020 年 報道 259 万円で売却 |
| 12 | mixi（SNS） | テック | Facebook・Twitter 2010–12、LINE 2011 | 時価総額 10 倍超 | NE-D（国内グラフ） | F-TECH | F-COPY | SNS 縮小、ゲームで業態転換 |
| 13 | GREE・DeNA（Mobage） | テック | Apple・Google ストア 2010–13 | 10 倍超 | NE-D, DIST（自社プラットフォーム） | F-PLATFORM | F-TECH | GREE 売上ピーク比 −50% 超 |

### 1-4. 混合（存続したがシェア喪失）: 集計から除外、頑健性で使用
Slack（F-BUNDLE/F-SINGLE）、Dropbox（F-BUNDLE/F-SINGLE）、Foursquare（F-COPY/F-SINGLE）、ZipRecruiter（F-SUPPLY）、Glassdoor（F-SINGLE）、Lever、Handshake、リブセンス（F-COPY/F-SUPPLY）、ニコニコ動画（F-SUPPLY/F-ECON）、SmartNews（F-PLATFORM/F-COPY）、Gunosy（F-PLATFORM/F-COPY）、Retty（F-SUPPLY/F-ECON）。AI 期（暫定）: Perplexity（F-BUNDLE＋F-PLATFORM 圧力）、Grammarly（F-BUNDLE/F-SINGLE）、Loom（F-SINGLE/F-ECON）、Windsurf（F-PLATFORM）。

### 1-5. 失敗（暫定、AI 期）
Jasper（F-PLATFORM＋F-COPY）、Chegg（F-PLATFORM＋F-COPY）、Stack Overflow（F-TECH＋F-SUPPLY）、Stability AI（F-ECON＋F-COPY）、Character.ai（F-ECON）、Inflection（F-ECON＋F-COPY）。

### 1-6. 除外台帳（落とした候補と理由の分布）
各ノートの「落とした候補」を理由別に数える（重複を除く概数）。
| 除外理由 | 件数 | 例 |
|---|---|---|
| 自滅（F-SELF）で巨大資本の参入が主因でない | 7 | WeWork、Quibi、Theranos、Yik Yak、Humane／Rabbit、Tome、Zenly（親会社都合） |
| 資本差の向きが逆・10 倍未満 | 6 | Myspace（News Corp 傘下）、Wimdu、Sketch、SmartHR、カオナビ、タイミー（暫定へ） |
| 巨大資本側の失敗（本テーマの対象は資本で劣る側） | 3 | Google+、Google Hire／for Jobs、Indeed Japan（リクルートの判断） |
| 母集団期間外（2005 年以前創業） | 5 | Monster、CareerBuilder、Dice、Netscape、Lotus／WordPerfect |
| 初期首位の条件を満たさない | 2 | Rdio、Bolt.new（不明） |
| 買収後に買収側の判断で終了（参入による喪失でない） | 3 | Mailbox、Sunrise、Wunderlist |
| 業種外（ソフトウェアでない） | 2 | Blue Apron、WeWork（重複） |
| 明確な巨大資本参入なし（参照のみ） | 3 | Adyen、Sansan、LINE Pay |

除外の最多理由は「自滅」と「資本差条件」であり、「失敗したが都合が悪いので落とした」型の除外はない。ただし母集団に入れた事例は「巨大資本が参入した事例」に限られるため、Zhu & Liu（2018）が示すとおり**参入自体が成功している補完者に選択的に起きる**。本母集団は「すでに成功していた企業」に偏る（`theory_and_evidence.md` §2）。

## 2. 事前登録仮説の集計（確定事例のみ。判定基準は `design/themes/moat-cases.md` のまま）

### H1 機能は堀にならない
成功 16 の主 MOAT: NE-X 5（Airbnb・Indeed・ビズリーチ・メルカリ・Pairs）、SC-WF 3（Figma・Datadog・Stripe）、SC-DATA 3（Snowflake・Workday・freee/MF）、CP 2（Canva・Shopify）、NE-D 2（Discord・LinkedIn）、BRAND 1（Zoom）。
- SPEED 単独・機能優位を主 MOAT とする事例: **0 / 16（0%）** ＜ 20% → 整合。
- NE-*・SC-*・CP・DIST・ECO のいずれかが主: **15 / 16（94%）** ≥ 80% → 整合。例外は Zoom（BRAND）。
- 暫定を含めても SPEED を主とする成功は Cursor（SPEED＋SC-WF の併記）のみで、SPEED 単独は 0。
**判定: H1 整合。**

### H2 失敗の最多原因はバンドルと単機能
失敗 13 の主 F: F-COPY 5、F-PLATFORM 3、F-ECON 2、F-BUNDLE 1、F-SINGLE 1、F-TECH 1。
- 主 F が F-BUNDLE または F-SINGLE: **2 / 13（15%）** ＜ 30% → **不支持**。
- 頑健性（事前登録外の数え方、開示のみ）: 主または副に F-BUNDLE／F-SINGLE を含む 4 / 13（31%）。混合 12 を加えて主 F で数えると 5 / 25（20%）。AI 期暫定失敗 6 を加えても F-BUNDLE 主は増えない。
- 事後的に見出した再分類: F-COPY 5 件のうち 5 件すべてで、模倣者は機能そのものではなく**既存の配布網・グラフに機能を載せた**ことで勝っている（Instagram→Vine、Spaces→Clubhouse、Messenger Rooms→Houseparty、Apple Watch→Pebble・Fitbit）。F-BUNDLE・F-COPY・F-PLATFORM を「巨大資本が既存の配布に機能を載せた」とまとめると **9 / 13（69%）**。残り 4 件は資本戦（Hired・Origami）、単機能（Triplebyte）、技術シフト（mixi）。
**判定: H2 不支持。失敗の最多原因は「バンドル」ではなく、より広い「配布網に載せた模倣」であり、バンドルはその一形態にすぎない。**

### H3 カウンターポジショニングは参入前に築かれる
CP を主または副に持つ成功: Canva、Shopify、Datadog、Snowflake、Stripe（配布）、Indeed、LinkedIn、Workday、ビズリーチ、freee/MF の 10 件。
- 攻撃を受けた**後に反応として** CP を築いた例: 0 件。
- ただし Datadog・Snowflake は巨大資本の製品（CloudWatch・Redshift）が**すでに存在する市場に**、創業時から CP を持って参入した。「参入前」を「巨大資本の製品が存在する前」と読むと 2 件が反例になり、「攻撃への反応として後から作った」と読むと反例はない。
**判定: 字義どおり（参入前に確立）なら不支持（反例 2）。「攻撃への反応として築いた例はない」の読みなら整合。後者の読みは 2026-11-16 に事例を見た後で採用した読み替えであり、両方を report に記す。**

### H4 人材業界は供給側ネットワーク効果が決定的
人材の成功（確定 4）: Indeed NE-X、LinkedIn NE-D、Workday SC-DATA、ビズリーチ NE-X。
- 主 MOAT が NE-X または CR: **2 / 4（50%）** ＜ 70% → 不支持。暫定 5（Rippling・Gusto・Deel・Greenhouse・タイミー）を加えると 4 / 9（44%）。
- 人材の失敗（確定 3: Hired・Triplebyte・（人材扱いなら）リブセンスは混合）: 主 F が F-SUPPLY は **0 / 2**（副では Hired の 1 件）→ 不支持。
- 事後追加の分割（閾値は不変、注記つき）: 求人メディア・スキマバイト（Indeed・LinkedIn・ビズリーチ・タイミー）は 4 / 4 がネットワーク効果（NE-X または NE-D）を主 MOAT とし、HR SaaS・採用管理（Workday・Rippling・Gusto・Deel・Greenhouse）は 0 / 5 で、全件が SC-DATA・SC-WF・CR。
- タイミー vs メルカリ ハロは「供給側」の読みを反転させる: メルカリは供給側（登録者 1,200 万）を無料で取ったが需要側密度（事業所 15 万 vs 39 万、実シフト 19 倍差）を取れず 2025-12 に撤退。決定的なのは「供給側」ではなく**希少な側**。
**判定: H4 不支持（事前登録の形では）。人材業界は一枚岩ではなく、両面市場（メディア）ではネットワーク効果、記録系（SaaS）ではスイッチングコストが堀になる。**

### H5 生成 AI 期はモデル優位が堀にならない
AI 期暫定: モデル・アルゴリズム自体を主な堀とした企業（Jasper・Inflection・Character.ai・Stability）は 1〜3 年でシェアまたは独立性を失った。残っている企業の主 MOAT は SC-WF（Cursor・Harvey・Glean・Calendly・Lovable・Replit）、CP（Otter・Granola）、CR＋SC-WF（ElevenLabs・Runway）、BRAND＋コミュニティ（Midjourney）。
- モデル優位**のみ**を堀として 3 年持った成功例: 0。
**判定: H5 整合（暫定、観察期間 4 年未満）。**

### H6 巨大資本側の制約が堀を生む
成功 16 のうち、巨大資本側の構造的制約を一次資料または規制文書で確認できたもの: 12 / 16（75%）（Figma・Canva・Zoom・Shopify・Airbnb・Datadog・Snowflake・Stripe・Discord・Indeed・Workday・freee/MF）。未確認: LinkedIn・メルカリ・ビズリーチ・Pairs。
- 反例（日本）: リクルートは Indeed 買収（2012）→ Indeed PLUS（2024）で自社媒体（リクナビ NEXT・タウンワーク）を配信先に格下げし、**共食いを自ら選んだ**。この結果、同じ CP（無料掲載＋成功報酬）を持つリブセンスの堀は消えた。「制約」は巨大資本の意思決定に依存し、構造的に保証されない。
**判定: H6 整合（75% ≥ 50%）。ただし後知恵バイアスを受けやすく、巨大資本が制約を自ら外した日本の例がある。**

## 3. 事後的に見出したパターン（事前登録外。仮説として次の検証に回す）
1. **組織の境界を越える製品はバンドルに耐える**。F-BUNDLE が主または副の事例（Slack・Dropbox・Evernote、AI 期 Grammarly・Loom）はすべて 1 人または 1 社の内側で完結する製品。バンドルを受けて守った事例（Zoom・Figma・Canva・Notion、暫定 Calendly・Otter・Granola）はすべて社外の相手（会議ゲスト・開発者・顧客・取引先）を巻き込むか、複数プラットフォームを横断する。Slack の Shared Channels GA は 2019 年で、Teams が DAU で Slack を上回ったと発表された 2019 年 7 月と同時期（GA の月は未確認）。
2. **「主張した堀」と「結果」の乖離**。失敗・混合のうち NE-D を堀と主張した事例は 9 件（Slack・Dropbox・Clubhouse・Zynga・Houseparty・Foursquare・Fitbit・mixi・GREE/DeNA。Clubhouse は推定）。失敗側だけを数えているので「守れなかった」は定義上の帰結で、予測力の証拠ではない。成功で NE-D が主なのは Discord・LinkedIn の 2 件のみ。ネットワーク効果は「自前のグラフが巨大資本のグラフより大きい」ときだけ堀になる。
3. **資本差の効果は評価できない**。成功側 16〜700 倍超、失敗側 10 倍超（売上比 4.5 倍）〜1,000 倍超で範囲は重なるが、全事例が 10 倍以上で選ばれている。
4. **知っていても守れない**。Slack S-1・Zynga S-1・Fitbit 10-K は致命的リスク（ゼロマージンのバンドル、Facebook 依存 91〜94%、Apple Watch）を事前に明記していた。同時代に提案された対策（Slack Connect 型・Pebble のフィットネス転換・Vine のクリエイター還元）は 2〜3 年遅れて実行された。
5. **反トラストは勝っても遅い**。Slack の EU 申立て（2020-07）は 2025-09 の確約で決着し、Netscape（1998 提訴）と同じ形で製品はすでに負けていた。
6. **公開データは堀ではなく訓練データ**。Chegg（1.35 億件 Q&A）・Stack Overflow は CR と信じたデータが競合の学習源に転じた。CR はアクセスを制御できるときだけ機能する（ElevenLabs・Harvey）。
7. **供給者＝競合の新型 F-PLATFORM**。Jasper（OpenAI）、Windsurf（Anthropic の遮断）、Chegg（Google）。回避策は自社モデル・マルチモデル・計算資源の自前化（Cursor→SpaceX）。
8. **売却額はピークの 1/5〜1/50**。失敗側で売却に至った事例（Evernote・Fitbit・Pebble・Houseparty・Origami）の売却額はピーク評価額の 1/5〜1/50。ピークを上回ったのは Slack（買収側の戦略）と Zynga（10 年の再建）のみ。
9. **日本固有**: 巨大資本が自ら共食いする（リクルート）、PE 資本が既存企業につく（弥生）、現金で両面を買う（PayPay）、企業は存続するがカテゴリで負ける（mixi・DeNA・ドワンゴ）。
