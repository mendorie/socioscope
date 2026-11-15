# テック成功事例（海外）: 巨大資本の参入・模倣・バンドルを受けて守り切った企業

- 調査日: 2026-11-15
- 枠組み: `design/themes/moat-cases.md`（問い Q1・事例選定基準・MOAT コード表・失敗原因コード表）に従う。
- 出典の質: 各社 S-1（SEC EDGAR 原本）・決算リリース・公式発表を優先し、WSJ/FT/Bloomberg/TechCrunch 等の報道を次に、Sacra・GetLatka 等の推計および Wikipedia は最後の手段として **[Wikipedia]** / **[推計]** と明記した。非上場企業（Canva・Notion・Stripe・Discord）の売上は会社発表値以外は推計である。
- 調査上の制約: 本セッションの Web 検索回数上限（200 回／ターン）に達したため、後半は一次資料の直接取得（WebFetch）のみで補った。取り切れなかった項目は各事例の `### Gaps` に残した。Cursor（進行中事例）は本ノートでは数値収集を行わず「落とした候補」に状態のみ記す。
- 表記: 「事実（Cited Findings）」と「解釈（Inferences）」を厳密に分ける。資本差は「巨大資本の年間売上 ÷ 新興企業の年間売上（または ARR）」で概算し、計算は分析者による。

---

## Figma（vs Adobe XD／Adobe による $20B 買収の破談）

### Takeaway
ブラウザ・マルチプレイヤー設計という製品形態の差で先行し、デザイナー以外（開発者・PM）を巻き込んだ **SC-WF（ワークフロー埋め込み）** と **ECO（コミュニティ・プラグイン）** を参入前に築いた。Adobe は 2016 年に XD で追随したが勝てず、2022 年に買収を試み、2023 年に規制当局の反対で断念、XD をメンテナンスモードにした。「巨大資本側の制約」が反トラスト審査として最も明確に観察できる事例。

### Cited Findings
- 創業 2012 年（Dylan Field・Evan Wallace）[Adobe 発表 2022-09-15](https://news.adobe.com/news/news-details/2022/adobe-to-acquire-figma)。
- Adobe XD は 2016-03-14 に macOS 向け公開ベータ（当初名 Adobe Experience Design CC）**[Wikipedia]** [Adobe XD](https://en.wikipedia.org/wiki/Adobe_XD)。
- 2022-09-15、Adobe は Figma を約 $20B（現金・株式半々）で買収すると発表。Figma の ARR は「2022 年に約 $200M 純増し、年末に $400M 超」、粗利率約 90%、営業 CF 黒字 [Adobe 発表](https://news.adobe.com/news/news-details/2022/adobe-to-acquire-figma)。Adobe 株は当日約 17% 下落 [CNBC 2022-09-15](https://www.cnbc.com/2022/09/15/adobe-to-acquire-design-platform-figma-for-20-billion.html)。
- 資本差（2022）: Adobe FY2022 売上 $17.61B [Adobe 8-K](https://www.sec.gov/Archives/edgar/data/796343/000079634322000225/adbeex991q422.htm) ÷ Figma ARR ~$0.4B ≒ **約 44 倍**（分析者計算）。
- 2023-12-18、両社は「EC と英 CMA から必要な規制承認を得る明確な道筋がない」として合意解消 [Adobe 発表](https://news.adobe.com/news/news-details/2023/adobe-and-figma-mutually-agree-to-terminate-merger-agreement)。解約金は $1B [TechCrunch 2023-12-18](https://techcrunch.com/2023/12/18/adobe-has-a-big-hole-to-fill-after-the-20b-figma-deal-falls-through)。EC は本件を、Adobe XD の開発停止につながる「reverse killer acquisition」と位置づけていた [Engadget](https://www.engadget.com/adobe-walks-away-from-its-20-billion-figma-acquisition-amid-regulatory-scrutiny-132203336.html)。
- Adobe XD は 2023-06 に単体販売を終了し、Adobe は「継続的な開発や新機能提供に投資しない（メンテナンスモード）」と公式に表明 [Adobe コミュニティ（Adobe サポート文言の引用）](https://community.adobe.com/questions-525/xd-is-in-maintenance-mode-does-that-mean-adobe-is-discontinuing-the-app-1545659)、[Creative Bloq](https://www.creativebloq.com/news/future-of-adobe-xd)。
- 参入後の推移: 2024 年売上 $749M（前年比 +48%）、2025Q1 売上 $228.2M（+46%）、粗利率 91%、$100K 超顧客 1,031 社、NDR 132%（2025-03-31）、MAU 約 1,300 万、Fortune 500 の 95% が利用（2025-03）[Fortune 2025-07-02](https://fortune.com/2025/07/02/figma-ipo-s-1-filing-growth-profitability-dual-class-share-structure-dylan-field-nyse-fig/)、[S-1 分析（Tunguz）](https://tomtunguz.com/figma-s1-analysis/)、[S-1 分析（alexandre）](https://alexandre.substack.com/p/figmas-ipo-s-1-breakdown)。原本: [S-1 2025-07-01](https://www.sec.gov/Archives/edgar/data/1579878/000162828025033742/figma-sx1.htm)、[424B4 2025-07-31](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001579878&type=424B4)。
- 自社が主張する強み（S-1 の二次整理）: web-first・マルチプレイヤー・フリーミアムによる「製品デザインの民主化」、ユーザーの約 1/3 がデザイナー・約 1/3 が開発者、NDR 主導の成長、プロダクトレッドグロース [alexandre](https://alexandre.substack.com/p/figmas-ipo-s-1-breakdown)。S-1 は競合として Adobe・Canva・Miro・Sketch・InVision・Microsoft・Webflow・Lovable（AI prompt-to-app）を挙げる（同上）。
- シェア: UX Tools 調査（n=2,220、2024-11〜2025-01）で UI デザインツールの 82.3% が Figma、Sketch に対し 46:1 [UX Tools](https://www.uxtools.co/survey/interface-design/trends)。
- 結末（2026-11 時点）: 2025-07-31 に NYSE 上場（FIG）、独立存続。

### Inferences
- 主 MOAT: **SC-WF**（デザイン→開発ハンドオフ・デザインシステムが組織横断で埋め込まれ、非デザイナーが MAU の 2/3 を占める）。副: **ECO**（コミュニティ・プラグイン）、**NE-D**（同一ファイルの同時編集は同僚が同じツールにいることで価値が増す）。いずれも Adobe の 2016 年参入「以前〜同時期」に製品構造として組み込まれており、2022 年の買収提案時点で完成していた。
- 巨大資本側の制約: (1) **反トラスト**（EC・CMA）。(2) **共食い**: Adobe の既存製品は買い切り由来のデスクトップ中心で、ブラウザ・フリーミアム・マルチプレイヤーに全面移行すると Creative Cloud の課金構造と衝突する（CP 的側面）。XD が無料枠を持ちながら勝てなかった事実は「機能模倣だけでは差分が消えない」を支持する。
- 「買収で解決しようとした」こと自体が、Adobe が内製では追いつけないと判断した証拠と読める（ただし公式にはそう述べていない）。

### Gaps
- Figma S-1 原本の「Competitive Strengths」節は、ファイルサイズ超過で直接取得できず二次整理に依拠。
- Adobe XD の ARR・利用者数（Adobe は非開示）。Figma の 2016〜2021 年の売上推移（非上場期）。
- Figma 2025Q3 以降の決算（investors.figma.com が取得不可）。

---

## Canva（vs Adobe Spark／Adobe Express）

### Takeaway
非デザイナー向けテンプレート型デザインという **CP（Adobe のプロ向け課金と衝突する無料・簡易モデル）** を 2013 年に確立し、Adobe が 2016 年（Spark）・2021 年（Express 再出発）と二度追随しても、Canva は ARR $4B・MAU 2.65 億（2025 年末）まで拡大した。ECO（テンプレート・教育）と BRAND が CP を補強する。

### Cited Findings
- 創業 2013 年（Melanie Perkins）[GetLatka](https://getlatka.com/companies/canva)。
- Adobe 側: 2015 年 Adobe Post（iOS）→ 2016 年 Adobe Spark → 2021 年 Creative Cloud Express として再出発、後に Adobe Express に改称 **[Wikipedia]** [Adobe Express](https://en.wikipedia.com/wiki/Adobe_Spark)、[TechCrunch 2022-10-17](https://techcrunch.com/2022/10/17/with-over-43m-k-12-users-adobe-express-for-education-gets-new-ai-and-safe-search-tools)。TechCrunch は Express を「Adobe の Canva 対抗」と記す（同上）。
- 資本差: Adobe FY2021 売上 $15.78B [Futurum（Adobe 開示の再掲）](https://futurumgroup.com/insights/adobe-q4-revenue-hits-record-4-53b-for-fy2022-up-10-yoy)。Canva の 2021 年 ARR は $1B（2021-09）**[推計: GetLatka]** [GetLatka](https://getlatka.com/companies/canva) → **約 16 倍**（分析者計算、Canva 側は推計値）。
- Canva の推移: ARR $1.7B（2023 末）→ $2.3B（2024-05）→ $2.55B（2024-09）**[推計: Sacra]** [Sacra](https://sacra.com/research/canva-at-2-55b-arr/)。2025 年末: ARR $4B（COO Cliff Obrecht）、2025 年認識売上 $3.5B、MAU 2.65 億（+20%）、有料 3,100 万、B2B（25 席以上）ARR $500M（+100%）、LLM 経由流入が「二桁%」[TechCrunch 2026-02-18](https://techcrunch.com/2026/02/18/canva-gets-to-4b-in-revenue-as-llm-referral-traffic-rises/)。
- 評価額 $42B（2025-08 従業員株売却）[Sacra](https://sacra.com/research/canva-at-4b-arr-growing-43-yoy/)。2024 年に Affinity（Adobe 的なプロ向けツール）を買収 [Motley Fool 2024-03-31](https://www.fool.com/investing/2024/03/31/this-26-billion-unicorn-is-gunning-for-adobe)。
- Adobe Express の規模: Adobe は MAU の絶対値を開示せず、「モバイル MAU 前四半期比 +96%」等の成長率のみ [Adobe 2024-06-11](https://news.adobe.com/news/news-details/2024/adobes-design-made-easy-event-showcases-how-leading-companies-are-supercharging-design-across-teams)。
- 結末（2026-11 時点）: 非上場・独立存続、IPO は「数年内」[TechCrunch 2026-02-18](https://techcrunch.com/2026/02/18/canva-gets-to-4b-in-revenue-as-llm-referral-traffic-rises/)。

### Inferences
- 主 MOAT: **CP**。Adobe が Express を本気で無料・簡易化すると Creative Cloud（FY2022 で $10.46B [PetaPixel](https://petapixel.com/2022/12/16/adobe-made-17-61-billion-in-2022-10-46-billion-on-creative-cloud-alone)）の単価を下げる圧力になる。Adobe が Express Premium を CC プランに「同梱」する形（DIST）で対抗したのは、単体で値下げ競争をしない選択と読める。
- 副 MOAT: **ECO**（テンプレート・教育機関・クリエイター）、**BRAND**（「Canva する」層での第一想起）。NE-D は弱い（共同編集はあるが単独利用が主）。
- 参入前/後: CP は 2013 年の創業時点のモデル → 2016 年 Spark 参入**前**に確立（H3 整合）。
- 巨大資本側の制約: **共食い**（プロ向け高単価サブスク）と **組織の優先度**（Adobe の成長の柱は Firefly・Acrobat・Experience Cloud で、Express は従属的）。

### Gaps
- Canva の 2016〜2022 年の売上はすべて推計（会社開示なし）。Adobe Express の MAU・売上は非開示。
- Canva が自社の堀を公式にどう表現しているか（S-1 がない）。

---

## Notion（vs Evernote／Microsoft Loop）

### Takeaway
「ブロック」を組み合わせて各自がツールを自作する汎用性で、個人・小チームのボトムアップ採用を取り、**SC-DATA（チームの wiki・DB が蓄積）** と **ECO（テンプレート市場）** を築いた。Microsoft は 2021 年に Loop を発表し M365 に同梱したが、Notion は 2025 年に ARR $500〜600M へ拡大。ただし Loop 参入から 5 年未満で、「成功」判定は**暫定**。

### Cited Findings
- 創業 2013 年（Ivan Zhao ら）**[Wikipedia]** [Notion](https://en.wikipedia.org/wiki/Notion_(productivity_software))。利用者 100 万（2019-09）、2,000 万（2021-10）。評価額 $2B（2020-01）→ $10B（2021-10、$275M 調達）（同上、[Axios 2020-04-02](https://www.axios.com/2020/04/02/notes-app-notion-raises-money-at-2-billion-valuation)）。
- Microsoft Loop: 2021-11-02 に M365 の一部として発表 **[Wikipedia]** [Microsoft Loop](https://en.wikipedia.org/wiki/Microsoft_Loop)、2023-03 公開プレビュー [Product Hunt](https://www.producthunt.com/products/microsoft-loop/launches)、報道は「Notion への回答」と位置づけ [ITPro](https://www.itpro.com/business-strategy/collaboration/370318/microsoft-launches-collaboration-platform-loop-its-answer-to)。
- 資本差: Microsoft FY2017 売上 $89.95B [Microsoft IR](https://www.microsoft.com/en-us/investor/earnings/fy-2017-q4/press-release-webcast)（2021 年はこれより大きい）。Notion の 2021 年売上は非開示 → 評価額ベースでも **100 倍超**は確実（分析者判断）。
- 参入後の推移: ARR $500M（2025-09、CNBC 報道）[newsio 要約](https://newsio.com/2025/09/18/notion-rides-ai-boom-to-500-million-in-annual-revenue-but-microsoft-competition-looms/?amp=1)、$600M 超（2025-12、Forbes）・評価額 $11B（2025-12）[iTiger 要約](https://www.itiger.com/news/1136424118)、利用者 1 億超・有料 400 万超 [AI Magazine](https://aimagazine.com/news/notion-ai-agents-for-a-workspace-used-by-100-million-people)。Sacra 推計 ARR $610M（2025 末）**[推計]** [Sacra](https://sacra.com/c/notion/)。
- テンプレート市場: 公式ギャラリーが「Marketplace」化し、クリエイターが販売（手数料 10%、Stripe 払い）[Notion ヘルプ](https://www.notion.com/en-gb/help/guides/getting-started-as-a-template-creator-on-marketplace)、[nocodefounders](https://www.nocodefounders.com/guides/6-best-places-to-sell-your-notion-templates)。
- 創業者の主張: Zhao は Notion を「ソフトウェアの LEGO」と説明（ページ・DB・リスト等のブロック）[Ness Labs](https://nesslabs.com/notion-featured-tool)、[Lenny's Podcast 2025-08](https://www.lennysnewsletter.com/p/inside-notion-ivan-zhao)。
- 対照（Evernote）: 登録 2.25 億（2018 年）を主張したが、2022-11 に Bending Spoons へ売却 [The Register](https://www.theregister.com/2022/11/17/evernotes_fall_from_grace_ends/)。年間 DL は 960 万（2017）→170 万（2023）**[推計: Appfigures]** [Appfigures](https://appfigures.com/resources/insights/20240126/3-is-evernote-past-its-prime)。
- 結末（2026-11 時点）: 非上場・独立存続。

### Inferences
- 主 MOAT: **SC-DATA**（組織の wiki・プロジェクト DB が system of record 化）。副: **ECO**（テンプレート・クリエイター）、**NE-D**（チーム内）。
- 参入前/後: ボトムアップ採用と SC-DATA は 2021 年 Loop 発表**前**に 2,000 万ユーザー規模で成立。
- 巨大資本側の制約: **組織の優先度**（M365 の中核は Teams・Copilot。Loop は OneNote・SharePoint・Teams と機能が重なり、社内競合を抱える）。DIST（M365 同梱）は Slack に対しては効いたが、Notion に対して効いた証拠はまだない。
- Evernote は同じ SC-DATA を持ちながら衰退した対照例で、SC-DATA 単独では「製品の陳腐化（F-TECH/F-SELF）」を防げないことを示す。

### Gaps
- Notion の売上はすべて報道・推計。Loop の利用者数は Microsoft 非開示。
- Loop 参入から 5 年未満（2021-11 発表 →2026-11 でちょうど 5 年、GA ベースでは 3 年）。成功判定は暫定。

---

## Zoom（vs Skype for Business／Microsoft Teams／Google Meet）

### Takeaway
2017 年に Microsoft が Teams を Office 365 に自動プロビジョニングし、Google も G Suite に Meet を同梱したにもかかわらず、Zoom は「動く・簡単」という体験差とボトムアップの口コミで FY2019 $330M→FY2022 $4.1B に拡大し、2026 年時点でも $4.87B を維持する。ただし成長は 4% に減速しており、**DIST（バンドル）に対して BRAND＋NE-D＋SPEED で守った**事例として、堀の持続性に注意が要る。

### Cited Findings
- 創業 2011-04（Delaware、当初名 Saasbee）[Zoom S-1 2019-03-22](https://www.sec.gov/Archives/edgar/data/1585521/000119312519083351/d642624ds1.htm)。
- Teams は 2017-03-14 に Office 365 顧客へ「自動プロビジョニング」で展開、Office 365 の MAU は 8,500 万超 [Microsoft 2017-03-14](https://www.microsoft.com/en-us/microsoft-365/blog/2017/03/14/microsoft-teams-rolls-out-to-office-365-customers-worldwide/)。Teams は Office 365 顧客に追加費用なし [SiliconANGLE 2019-07-11](https://siliconangle.com/2019/07/11/microsoft-teams-surges-ahead-13m-users-likely-surpassing-slack/)。
- 資本差（2017）: Microsoft FY2017 売上 $89.95B [Microsoft IR](https://www.microsoft.com/en-us/investor/earnings/fy-2017-q4/press-release-webcast) ÷ Zoom FY2018 売上 $151.5M [S-1] ≒ **約 590 倍**（分析者計算）。
- S-1 の強み（原文の節名 "Competitive Strengths"）: ビデオファーストのクラウドネイティブ設計／市場リーダー認知／個人ユーザー起点のバイラル需要／NPS 70 超／多層 GTM／24 時間サポート。競合として Webex・Skype for Business・Google（バンドル型）・LogMeIn、Amazon・Facebook を名指しし、「競合は広範な製品群をバンドルし得る」と記載 [S-1](https://www.sec.gov/Archives/edgar/data/1585521/000119312519083351/d642624ds1.htm)。$100K 超顧客 344 社のうち 55% が無料ホストから開始（同上）。
- 売上推移: FY2019 $330.5M → FY2020 $622.7M → FY2021 $2,651.4M → FY2022 $4,099.9M（10-K）[MarketScreener（10-K 再掲）](https://uk.marketscreener.com/quote/stock/ZOOM-VIDEO-COMMUNICATIONS-57086220/news/ZOOM-VIDEO-COMMUNICATIONS-INC-MANAGEMENT-S-DISCUSSION-AND-ANALYSIS-OF-FINANCIAL-CONDITION-AND-RES-39689491/)。従業員 10 名超の顧客 46.7 万（FY2021 末、+470%）[Skift 2021-03-02](https://meetings.skift.com/2021/03/02/2020-year-end-zoom-earnings/)。
- FY2026（2026-01 期）: 売上 $4,868.8M（+4.4%）、Enterprise $2,934.1M（+6.5%）、Online $1,934.7M（+1.2%）[Zoom 決算](https://investors.zoom.us/node/14156/html)。FY2027 ガイダンス $5.065〜5.075B（同上）。
- Microsoft 側の制約: Slack が 2020-07 に EU へ Teams バンドルを申し立て、EC が調査。Microsoft は 2023 年に欧州で、後に全世界で Teams を Office から分離、2025-09 に EC が 7 年間の約束を受け入れて制裁金を回避 [The Register 2025-09-12](https://www.theregister.com/2025/09/12/eu_regulators_let_microsoft_off/)、[Engadget](https://www.engadget.com/apps/microsoft-escapes-eu-antitrust-fine-after-unbundling-teams-123052522.html)。Teams の MAU は約 3.2 億（2025）（同上）。
- 対照（Skype）: Microsoft は 2025-05-05 に Skype を終了し Teams へ移行。MAU は 2011 年の約 1.5 億から 2023 年には 3,600 万へ [UC Today](https://www.uctoday.com/unified-communications/microsoft-kills-skype-urges-a-move-to-teams/)、[Fox Business](https://www.foxbusiness.com/technology/microsoft-shuts-down-skype-after-22-years-shifting-users-teams)。
- 結末（2026-11 時点）: 上場・独立存続、売上成長は一桁。

### Inferences
- 主 MOAT: **BRAND**（「Zoom する」が動詞化し、会議の相手が Zoom を期待する）。副: **NE-D**（外部参加者がアカウントを持つほど摩擦が減る、S-1 の "viral demand"）、**SC-WF**（Zoom Rooms・Phone・Contact Center への拡張で埋め込み）。**SPEED**（品質・使いやすさの先行）は参入直後の主因だが、7 Powers 上は堀ではない。
- 参入前/後: Teams 参入（2017）時点で Zoom は FY2018 $151M で、BRAND は 2020 年のパンデミック期に**参入後**に完成した。「参入後に堀を築いた」稀な例で、H3（CP は参入前）には抵触しない（CP ではない）が、「堀は参入前に要る」という一般化には反例となる。
- 巨大資本側の制約: **反トラスト**（EU による Teams 分離）。ただし Teams は Slack のシェアは奪っており、同じ DIST が Zoom には決定的に効かなかった理由は、ビデオ会議は「社外の相手」を含む用途で、社内同梱だけでは置き換わらない点にあると解釈する。
- Skype は NE-D を持ちながら衰退した対照例: ネットワーク効果は製品品質の劣化（F-SELF/F-TECH）を補わない。

### Gaps
- Zoom のビデオ会議シェア（2023〜2025）の第三者調査。Google Meet の G Suite 同梱時期と利用者数。
- Zoom S-1 の net dollar expansion rate（本文後半、未取得）。

---

## Shopify（vs Amazon Webstore 閉鎖 2015／Amazon "Buy with Prime" 2023）

### Takeaway
Amazon は自社出店基盤 Webstore を 2015 年に閉鎖し、移行先として Shopify を推奨した。これは「巨大資本が追随できない構造的理由（**共食い**: 出店者に独自ブランドを持たせることは Amazon マーケットプレイスと矛盾）」の最も明確な例。Shopify は **ECO（アプリ・テーマ・パートナー）** と **SC-WF（決済・在庫・チャネル統合）** で 2015 年 GMV $7.7B → 2025 年 $378.4B へ拡大し、2023 年に Amazon が Buy with Prime で再接近した際も Shopify Checkout を通す形で統合した。

### Cited Findings
- 2015-09、Amazon は Webstore 閉鎖（2016 年）にあたり Shopify を優先移行先に指定。Shopify は Login and Pay with Amazon・FBA・Amazon 販売チャネルを統合、株価は当日約 24% 上昇 [CBC 2015-09-17](https://amp.cbc.ca/news/business/shopify-has-deal-to-take-on-amazon-s-webstore-merchants-1.3232345)、[MarTech](https://martech.org/amazon-points-retailers-to-shopify-as-it-nears-the-end-of-its-e-commerce-platform)、[Fortune 2015-09-17](https://fortune.com/2015/09/17/shopify-amazon)。
- 資本差（2015）: Amazon 2015 売上 $107.0B [Amazon 8-K 2016-01-28](https://www.sec.gov/Archives/edgar/data/1018724/000101872416000170/amzn-20151231xex991.htm) ÷ Shopify 2015 売上 $205.2M [Shopify 2016-02-17](https://www.shopify.com/news/shopify-announces-fourth-quarter-and-full-year-2015-financial-results) ≒ **約 520 倍**（分析者計算）。Shopify の 2015 年 GMV $7.7B（+105%）、加盟店 24.3 万（同上）。
- 2023-08-30、Amazon は Shopify 向け Buy with Prime アプリを発表。Prime 会員は Amazon ウォレットの支払手段を使うが、決済は **Shopify Payments が Shopify Checkout 経由で処理**し、注文・税は Shopify 管理画面に同期 [Amazon 発表](https://press.aboutamazon.com/2023/8/amazon-announces-app-integration-for-merchants-to-enable-buy-with-prime-on-shopify-stores)。
- 2025 年通年: 売上 $11.6B（+30%）、GMV $378.4B（+29%）、Shopify Payments 浸透率 65.6%、FCF $2B [Shopify 2026-02-11](https://www.newsfilecorp.com/release/283507/Shopifys-Standout-2025-The-Launchpad-for-a-New-Era-of-Commerce-in-2026)、[Retail Insight](https://www.retail-insight-network.com/newsletters/shopify-posts-30-revenue-growth)。
- 創業者の主張: Lütke は「Amazon は帝国を築き、Shopify は反乱軍を武装させる」と繰り返し述べ（2018 年株主書簡・2019 年 Q&A）[Quartz 2021](https://qz.com/1954108/shopify-is-arming-the-rebels-against-amazon)、[Globe and Mail](https://arc-dev.theglobeandmail.com/business/article-tobi-vs-goliath-how-shopify-is-bracing-for-a-looming-battle-with)。
- 結末（2026-11 時点）: 上場・独立存続、米 EC で Amazon に次ぐ規模（2021 年時点の推計）[Quartz](https://qz.com/1954108/shopify-is-arming-the-rebels-against-amazon)。

### Inferences
- 主 MOAT: **CP**（出店者に自前ブランド・顧客データを持たせるモデルは、Amazon の「顧客は Amazon のもの」というマーケットプレイス経済と両立しない。Webstore 閉鎖はその帰結）。副: **ECO**（アプリストア・テーマ・代理店）、**SC-WF**（Payments 浸透率 65.6%、POS・Capital・配送の統合で移行コストが上がる）。
- 参入前/後: Amazon Webstore は 2006 年開設で Shopify（2006 年創業）より先行〜同時期。CP は創業時点のモデルで、巨大資本の「参入前」。Buy with Prime（2023）に対しては、すでに SC-WF/ECO が完成していたため、Amazon 側が Shopify Checkout に従う形で統合された（分析者の読み）。
- 巨大資本側の制約: **共食い**が決定的。加えて Shopify は Amazon を「流通網（FBA・Amazon Pay）」として取り込み、競合を補完財に転じた。

### Gaps
- Amazon Webstore の売上・出店者数（Amazon 非開示）。Shopify F-1（2015）の強み節原文。
- 2022 年に Shopify が Buy with Prime を一時制限したという報道の一次確認（未取得）。

---

## Airbnb（vs Rocket Internet の Wimdu／Google 旅行検索）

### Takeaway
2011 年に Samwer 兄弟の Wimdu が $90M を調達し 100 日で 1 万件を掲載したが、Airbnb は **NE-X（ホスト×ゲストの両面ネットワーク）** と **BRAND** で勝ち、Wimdu は 2018 年に閉鎖。2019 年に Google がホテル検索へバケーションレンタルを追加した後も、Airbnb は流入の約 9 割を直接・無料チャネルで得ており、Google への依存を回避している。ただし Wimdu は「10 倍の資本差」の条件を満たさない（Google が該当）。

### Cited Findings
- 創業 2007 年（AirBedandBreakfast.com）、法人化 2008-06 [Airbnb S-1 2020-11](https://www.sec.gov/Archives/edgar/data/1559720/000119312520294801/d81668ds1.htm)。
- Wimdu: 2011-03 設立、2011-06 に Kinnevik・Rocket Internet から $90M（当時欧州最大）、100 日未満で 150 都市 1 万件・従業員約 400 名。同時期の Airbnb は評価額 $1B で $100M 調達交渉中 [TechCrunch 2011-06-14](https://techcrunch.com/2011/06/14/investors-pump-90-million-into-airbnb-clone-wimdu)。Airbnb はホストに「偽サイト（9flats・Wimdu・Airizu）」を警告し、買収も検討したが文化の違いで見送り [TechCrunch 2011-06-09](https://techcrunch.com/2011/06/09/Airbnb)。2017-08 時点のドイツ掲載は Wimdu 約 1.2 万件 vs Airbnb 16 万件、2018-09 に年内閉鎖を発表 **[Wikipedia]** [Wimdu](https://en.wikipedia.org/wiki/Wimdu)、[TechCrunch 2018](https://techcrunch.com/?p=1721570)。
- Google: 2019-03 にホテル検索へバケーションレンタルを追加（Expedia・HomeAway・VRBO 等が供給、Airbnb は不参加）[Skift 2019-03-26](https://skift.com/2019/03/26/google-adds-vacation-rentals-feature-to-evolving-hotel-site)、[The Points Guy](https://thepointsguy.com/news/you-can-now-search-for-vacation-rentals-through-googles-hotel-search/)。
- S-1 の強み（"Our Strengths"）: 独自のホストコミュニティ（400 万ホスト超、560 万掲載の大半は Airbnb 限定）／関与の高いゲスト（2019 年売上の 69% がリピート）／世界的ブランド（動詞化）／グローバルネットワーク／自社構築プラットフォーム／デザイン主導 [S-1](https://www.sec.gov/Archives/edgar/data/1559720/000119312520294801/d81668ds1.htm)。有料パフォーマンス広告由来の流入は 2019 年 23%、2020 年 1〜9 月 9%（残りが直接・無料）、「Google Travel の投入で SEO が悪影響を受けたと考える」と明記（同上、Risk Factors）。2019 年売上 $4,805.2M、宿泊・体験予約 3.269 億件（同上）。
- 資本差（2019）: Alphabet 2019 売上は約 $162B（Alphabet 10-K。本調査では原本を直接取得できず**未検証**）÷ Airbnb $4.8B ≒ **約 34 倍**。
- 2025 年通年: 売上 $12.2B（+10%）、宿泊・座席予約 5.33 億件（+8%）、GBV $91.3B（+12%）、純利益 $2.5B [PhocusWire](https://www.phocuswire.com/airbnb-q4-full-year-2025-earnings)、[Airbnb 2026-02-12](https://news.airbnb.com/airbnb-q4-2025-financial-results/)。ホテルは夜数の一桁%（同上）。
- 結末（2026-11 時点）: 上場（2020-12）・独立存続。

### Inferences
- 主 MOAT: **NE-X**（ホスト供給の大半が Airbnb 限定であることが S-1 で強調される＝供給側の独占性）。副: **BRAND**（直接流入 9 割）、**PP**（信頼・保険・レビューの運用）。
- 参入前/後: Wimdu（2011）参入時点で NE-X は萌芽期。Airbnb が勝った要因は、Wimdu が需要側の広告投下で供給側（ホストの信頼・レビュー履歴）を複製できなかった点にあると読む（Wimdu は NE-X を「主張」しながら F-SUPPLY で失敗した対照例）。Google（2019）参入時点では BRAND・NE-X ともに完成していた。
- 巨大資本側の制約: Google は **仲介者の立場**（OTA からの広告収入）を守るため、自前で供給（ホスト）を獲得しない。供給側 NE-X は検索の DIST では代替できない。

### Gaps
- Alphabet 2019 売上の一次確認。Airbnb 2011〜2012 年の予約数・売上。
- Google 旅行検索による Airbnb の流入変化の定量。

---

## Datadog（vs AWS CloudWatch・Azure Monitor・Google Cloud 監視）

### Takeaway
クラウド事業者は自社監視ツールを「同梱」できる立場にあり、Datadog はそれより後発（2010 年創業）だが、**マルチクラウド横断（CP: AWS は Azure を監視する動機がない）** と **SC-WF（350→数百の統合・ダッシュボード・アラートの埋め込み）** で 2018 年 $198M → 2025 年 $3.43B に拡大した。AWS は 2025 年に Datadog と戦略提携を結び、競合を補完財として扱っている。

### Cited Findings
- 創業 2010-06 [Datadog S-1 2019-08-23](https://www.sec.gov/Archives/edgar/data/1561550/000119312519227783/d745413ds1.htm)。CloudWatch は Datadog 創業以前から存在（AWS の先行）。
- S-1 の強み（"Our Solution and Key Strengths"）: 動的クラウド向け設計（1 日 10 兆イベント）／簡潔／統合データプラットフォーム／協働向け／**クラウド非依存**／ユビキタス／350 超の統合／ML／スケーラブル。競合に IBM・Microsoft・Cisco・New Relic・Dynatrace・Splunk・Elastic、および「ネイティブ監視を提供する AWS・GCP・Azure」を名指し。インフラの実質すべてを第三者クラウドに委託し、クラウド事業者のマーケットプレイス経由販売が利益率を下げ得ると記載（同上）。2018 年売上 $198.1M、2019 上半期 $153.3M、顧客約 8,800、$100K 超 590 社、NRR 146%（2019-06）（同上）。
- 資本差（2019）: AWS 2019 売上 $35.0B [Amazon 8-K 2020-01-30](https://ir.aboutamazon.com/news-release/news-release-details/2020/Amazoncom-Announces-Fourth-Quarter-Sales-up-21-to-874-Billion/default.aspx) ÷ Datadog 2018 売上 $198.1M ≒ **約 177 倍**（分析者計算。Amazon 全体では $280.5B）。
- 2025 年通年: 売上 $3.427B（+28%）、顧客約 32,700、$100K 超 4,310 社（ARR の 90%）、$1M 超 603 社、NRR 約 120%、84% が 2 製品以上利用 [Panto（決算の再掲）](https://www.getpanto.ai/blog/datadog-statistics)、[iTiger](https://www.itiger.com/news/1148796144)。
- 2025-12-03、AWS と新たな戦略協業契約（SCA）。共同ソリューション開発・AWS Marketplace・GTM、「10 年超の共同イノベーション」[Datadog 発表](https://www.datadoghq.com/about/latest-news/press-releases/datadog-announces-expanded-collaboration-agreement-highlights-new-capabilities-with-aws-across-ai-observability-and-security-at-aws-reinvent/)。
- 結末（2026-11 時点）: 上場（2019-09）・独立存続。

### Inferences
- 主 MOAT: **SC-WF**（アラート・ダッシュボード・オンコール運用に埋め込まれ、84% が複数製品利用）。副: **CP**（マルチクラウド中立性は AWS が構造的に取れない立場）、**SCALE**（1 日 10 兆イベントの処理基盤）。
- 参入前/後: 巨大資本（CloudWatch）が先行していた市場に後から入り、堀を**参入後**に築いた型。「同梱された無料ツールがあるのに有料で勝つ」は、同梱品が最低限で深い運用には足りないケースで起こる。
- 巨大資本側の制約: **組織の優先度・利益相反**（AWS の収益は計算資源の消費であり、監視ツールで他社クラウドを支援する動機がない）。Datadog がクラウド消費を増やす補完財であることが提携の背景と読む。

### Gaps
- Datadog FY2025 決算リリース原本（投資家サイトが 403）。CloudWatch の売上・利用規模（AWS 非開示）。Gartner MQ の位置。

---

## Snowflake（vs AWS Redshift／Google BigQuery／Azure）

### Takeaway
Redshift（2012）・BigQuery（2010〜11）に対し、Snowflake（製品 2015 年）は「ストレージ・計算分離」「マルチクラウド」「データ共有」で後発参入し、FY2020 $264.7M → FY2026 製品売上 $4.47B に拡大。S-1 自身が「AWS・Azure・GCP は主要競合であり同時に唯一の稼働基盤」と記す、巨大資本の土地の上に堀を築いた事例。NRR 169%（FY2020）→125%（FY2026）と、堀の「使えば使うほど離れにくい」性質が数値に出る。

### Cited Findings
- 2012-07 法人化 [Snowflake S-1 2020-08](https://www.sec.gov/Archives/edgar/data/1640147/000162828020013010/snowflakes-1.htm)、製品一般提供は 2015 年 [Scalero](https://scalero.io/company/blog/snowflake-rise-data-cloud)。Redshift は 2012 年に AWS 初の DWH として登場 [Hidekazu Konishi](https://hidekazu-konishi.com/entry/cloud_data_warehouse_history_and_timeline.html)。
- S-1 の記述: 「我々は AWS・Azure・GCP のパブリッククラウド上でのみ提供しており、これらは主要競合でもある」、クラウド事業者が「特権的機能の埋め込み・バンドル・不利な価格設定」を行い得る（Risk Factors）。ソリューションの特徴として多様なデータ型・大規模スケール・同時多用途・価格性能・使いやすさ・サービス提供・**マルチクラウド**・**安全なデータ共有**。FY2020 売上 $264.7M（+174%）、顧客 2,392、NRR 169%。2020-07-31 時点: 顧客 3,117、NRR 158%、$1M 超 56 社 [S-1](https://www.sec.gov/Archives/edgar/data/1640147/000162828020013010/snowflakes-1.htm)。
- 資本差（FY2020）: AWS 2019 売上 $35.0B [Amazon 8-K](https://ir.aboutamazon.com/news-release/news-release-details/2020/Amazoncom-Announces-Fourth-Quarter-Sales-up-21-to-874-Billion/default.aspx) ÷ $264.7M ≒ **約 132 倍**（分析者計算）。
- FY2026（2026-01 期）: 製品売上 $4,472.3M（+29%）、Q4 製品売上 $1,226.6M（+30%）、NRR 125%、$1M 超顧客 733 社（+27%）、FY2027 ガイダンス $5.66B [Snowflake 2026-02-25](https://investors.snowflake.com/news/news-details/2026/Snowflake-Reports-Financial-Results-for-the-Fourth-Quarter-and-Full-Year-of-Fiscal-2026/)。
- 結末（2026-11 時点）: 上場（2020-09）・独立存続。

### Inferences
- 主 MOAT: **SC-DATA**（企業データが Snowflake 内に蓄積し、消費課金で使用量が増える＝NRR の高さ）。副: **CP**（マルチクラウド中立性。AWS が Redshift を Azure 上で動かすことはない）、**NE-X**（Data Marketplace／データ共有：共有相手が Snowflake にいることで価値が増す。S-1 本文で "network effects" を確認できず、分析者の付与）。
- 参入前/後: 巨大資本が先行していた市場への後発参入で、堀は**参入後**（Datadog と同型）。
- 巨大資本側の制約: **利益相反**（Snowflake は AWS 最大級の計算資源購入者であり、潰すより乗せた方が AWS の売上になる）。Redshift の価格・機能追随は続いているが、Snowflake の NRR 低下（169→125%）は Databricks を含む競争圧力の表れとも読める。

### Gaps
- S-1 の Business 節（AWS への $1.2B 購入コミットメント・Data Marketplace 記述）は本文後半で未取得。
- クラウド DWH の市場シェア（Redshift／BigQuery／Snowflake／Databricks）の第三者推計。

---

## Stripe（vs PayPal／Braintree／Adyen）

### Takeaway
PayPal（eBay 傘下）は 2013 年に Stripe の直接競合 Braintree を $800M で買収したが、Stripe は「開発者向け API」という流通経路を押さえ、2025 年の決済額 $1.9T・評価額 $159B（2026-02）に至った。**SC-WF（決済・サブスク・不正検知・Connect が事業の基盤コードに埋め込まれる）** が主で、開発者コミュニティ（ECO）が配布を担う。非上場で売上は非開示。

### Cited Findings
- 創業 2010 年 [Sacra](https://www.sacra.com/c/stripe)。創業の動機は「PayPal はエンドユーザー、エンタープライズ基盤は大企業向けで、開発者に誰も向いていなかった」[Social Radars（Collison 兄弟インタビュー）](https://rosetta.to/u/thesocialradars/patrick-and-john-collison-explain-why-stripe-was-built-for-developers-first)。
- 2013-09-26、eBay/PayPal が Braintree を $800M で買収すると発表（Braintree は $70M 超調達、30 か国）[FinTech Futures](https://www.fintechfutures.com/paytech/paypal-braintree-reach-800-million-purchase-agreement-sept-26-2013-)、[eBay 発表](https://www.ebayinc.com/stories/news/paypal-acquires-global-payments-innovator-braintree/)。2013-12-19 完了、対価約 $713M、目的は「モバイル決済の成長加速」[eBay 10-K FY2013](https://www.sec.gov/Archives/edgar/data/0001065088/000106508814000010/ebay201310-k.htm)。
- 資本差（2013）: eBay 2013 売上 $16.0B、PayPal アクティブ口座 1.43 億 [eBay 10-K](https://www.sec.gov/Archives/edgar/data/0001065088/000106508814000010/ebay201310-k.htm)。Stripe の 2013 年売上は非開示（評価額ベースで 10 倍超は確実、分析者判断）。
- 推移: 決済額 2024 年 $1.4T（+38%）、2024 年に通年黒字化 [Finextra](https://www.finextra.com/blogposting/28310/deep-dive-stripe-vs-adyen-comparing-2024-performance)。2025 年 $1.9T（+34%、世界 GDP の約 1.6%）、利用企業 500 万社超、ダウ構成銘柄の約 90%・ナスダック 100 の約 80% が利用、評価額 $159B（2026-02-24 従業員向け公開買付）[Stripe 2025 年次レター](https://stripe.com/newsroom/news/stripe-2025-update)。
- 対照: Adyen は 2024 年に €1.29T（+33%）を処理し、EBITDA 率約 50% で上場済 [Finextra](https://www.finextra.com/blogposting/28310/deep-dive-stripe-vs-adyen-comparing-2024-performance)。
- 結末（2026-11 時点）: 非上場・独立存続。

### Inferences
- 主 MOAT: **SC-WF**（決済は返金・税・サブスク・不正検知・プラットフォーム分配（Connect）と結合し、置換は事業ロジックの書き換えになる）。副: **ECO**（開発者コミュニティ・ドキュメントが配布網）、**SCALE**（不正検知のデータ規模、コンプライアンス固定費）。
- 参入前/後: Braintree 買収（2013）時点で Stripe は創業 3 年。開発者向け API という配布モデルは**参入前**から、SC-WF は参入後に厚くなった。
- 巨大資本側の制約: **組織の優先度**（PayPal の中核は消費者ウォレットと eBay 決済で、開発者向け API は Braintree 買収で「外付け」した）。Adyen は同じ SC-WF 型で成功しており、「開発者向け」単独が堀ではなく、エンタープライズ直販（Adyen）でも成立することを示す。

### Gaps
- Stripe の売上（非開示。Sacra 推計 take rate 0.36% 等は未採用）。Stripe 2014 年評価額 $3.5B の一次確認。
- 決済プロセッサ別シェア（BuiltWith 等）。

---

## Discord（vs Skype／Teams／Slack）

### Takeaway
Skype（Microsoft 傘下）が先行する音声チャットに 2015 年に参入し、ゲームコミュニティの **NE-D（サーバー＝コミュニティの同時在席）** で MAU 2 億超に達した。Microsoft は模倣ではなく 2021 年に $10B 超での買収を試み、Discord は拒否して独立を保った。Skype は 2025 年に終了。収益は Nitro 課金中心で、2026-01 に IPO を非公開申請。

### Cited Findings
- 公開 2015-05-13 **[Wikipedia]** [Discord](https://en.wikipedia.org/wiki/Discord)。登録 2,500 万（2016-12）→約 9,000 万（2017 末）→1.3 億（2018）、MAU 1 億（2020-06）→約 1.4 億（2020 末）、2024 年 MAU 2.27 億超（同上）。Nitro は 2017-01 開始 [Latka](https://blog.getlatka.com/discord-revenue/)。
- 2021-03-23、Bloomberg が Microsoft による $10B 超での買収交渉を報道 [Bloomberg](https://www.bloomberg.com/news/articles/2021-03-23/microsoft-said-to-be-in-talks-to-buy-discord-for-more-than-10b)、WSJ は交渉が「進んだ段階」と報道。2021-04-20、WSJ が Discord が交渉を打ち切ったと報道 [PCWorld（WSJ 引用）](https://www.pcworld.com/article/394288/report-microsoft-is-in-talks-to-buy-discord-for-over-10-billion.html)。2020 年売上 $130M（2019 年の 3 倍）**[Wikipedia（FT 引用）]**、[bit-tech](https://bit-tech.net/news/microsoft-in-talks-with-discord-over-potential-10-billion-deal/1/)。
- 資本差（2021）: Microsoft 売上は FY2017 で $89.95B [Microsoft IR](https://www.microsoft.com/en-us/investor/earnings/fy-2017-q4/press-release-webcast)（2021 年はこれ以上）÷ Discord 2020 年 $130M ≒ **700 倍超**（分析者計算、下限）。
- 2022 年売上 $445M **[推計: Business of Apps／Sacra]** [Business of Apps](https://businessofapps.com/data/discord-statistics)、[Sacra](https://www.sacra.com/research/discord-wechat-for-the-metaverse)。2025-12 時点で MAU 2 億超（会社声明）[Bloomberg Law 2026-01-07](https://news.bloomberglaw.com/securities-law/chat-platform-discord-is-said-to-file-confidentially-for-ipo)。
- 2026-01-07、Bloomberg が IPO の非公開申請を報道（Goldman・JPMorgan）（同上）。評価額はピーク $15B から二次市場で約 $8.5B に低下したとの報道 [Seeking Alpha](https://seekingalpha.com/news/4538199-discord-dilemma-will-an-ipo-change-one-of-the-most-beloved-chat-platforms)。
- 対照（Skype）: 2025-05-05 終了 [UC Today](https://www.uctoday.com/unified-communications/microsoft-kills-skype-urges-a-move-to-teams/)。対照（Houseparty）: 2020-03 に 1,700 万 DL、Epic 傘下で 2021-10 終了 **[Wikipedia]** [Houseparty](https://en.wikipedia.org/wiki/Houseparty_(app))。対照（Clubhouse）: 2021 年初に週間 1,000 万人超・評価額 $4B（2021-04）、Twitter Spaces 等の模倣後に減少し 2023-04 に半数解雇 **[Wikipedia]** [Clubhouse](https://en.wikipedia.org/wiki/Clubhouse_(app))。
- 結末（2026-11 時点）: 非上場・独立存続（IPO 準備中）。

### Inferences
- 主 MOAT: **NE-D**（サーバー単位のコミュニティ。友人・ギルドが居る場所に価値がある）。副: **SC-DATA**（サーバーの履歴・ロール・ボット設定）、**ECO**（ボット開発者）。
- 参入前/後: Skype・Teams は先行（Microsoft が「参入前から存在」）。Discord の NE-D は 2017〜2020 年に、Microsoft の買収提案**前**に完成した。
- 巨大資本側の制約: **組織の優先度**（Microsoft のコミュニケーション製品は企業向け Teams に集中し、Skype は消費者向けで放置された）。Discord を内製で複製せず買収を試みたのは、NE-D は資本で複製できないことの傍証と読む。
- Houseparty・Clubhouse は同じ NE-D を主張しながら失敗した対照例: 一時的な流行による NE-D は、巨大資本の模倣（Twitter Spaces・Facebook・Spotify）や親会社の優先度変更に耐えない。Discord との差は「継続的な用途（ゲーム・コミュニティ運営）」と「サーバーに蓄積する SC-DATA」にあると解釈する。

### Gaps
- Discord の売上・利益（S-1 公開前）。Microsoft 2021 年売上の一次確認。Teams Communities（消費者向け、2022）の利用規模。

---

## Duolingo（vs Google Translate／Apple Translate／Babbel・Rosetta Stone）

### Takeaway
無料・ゲーミフィケーション・口コミ主導で言語学習の最大ブランドとなり、2025 年に売上 $1.04B・DAU 5,270 万。**BRAND** と **NE-DATA（1 日 5 億問の学習データで A/B テスト・個別化）** を主張する。Google は 2025-08 に Translate へ Gemini 搭載の「練習」機能を無料で追加し、株価は下落した。巨大資本の本格参入からまだ 1 年強で、**成功判定は暫定**。

### Cited Findings
- 創業 2011-08（Delaware）[Duolingo S-1 2021-06-28](https://www.sec.gov/Archives/edgar/data/1562088/000162828021013065/duolingos-1.htm)。
- S-1 の強み（"Our Strengths"）: 製品至上の文化（ゲーミフィケーション）／主要消費者ブランド（無料で楽しい体験が有機的流入を生み有料マーケ依存を下げる）／**深いデータ分析（1 日 23 億イベント、四半期数百の A/B テスト）**／学習成果（大規模データで AI が個別化）／フライホイール（「競争上の堀を広げる」と自己記述）／スケーラブルな基盤／収益性／創業者経営。2020 年売上 $161.7M（2019 年 $70.8M）、MAU 約 3,700 万、DAU 820 万、有料 160 万、累計 DL 5 億超、1 日 5 億問。競合として Apple（Translate アプリ 2020 年）・Google を名指し、大手が「より多くの資源を投じ、より速く展開し得る」と記載（Risk Factors）（同上）。
- 創業者の主張: 「free が我々のマーケティングエンジンだった」[Courier](https://couriermedia-ecomm.netlify.app/content/article/achieving-growth-without-advertising)、2021 年成長の 90% が口コミ由来（年次報告の二次引用）[How They Grow](https://howtheygrow.beehiiv.com/p/how-duolingo-grows)、Babbel・Rosetta Stone は「広告中心」と評価 [Monocle](https://monocle.com/business/duolingo-language-learning-app/)。
- Google 参入: 2025-08-26、Translate に Gemini 搭載の言語練習（ベータ、英→西・仏など）と 70 言語超のライブ翻訳を追加 [Google 2025-08-26](https://blog.google/products/translate/language-learning-live-translate/)。Duolingo 株は当日最大 3% 下落、数日後に 7.3% 下落、2025-05 高値 $540.68 から 44.7% 下 [Investing.com](https://ng.investing.com/news/stock-market-news/duolingo-stock-falls-after-google-unveils-new-ai-translation-tools-2080269)、[StockStory 2025-08-29](https://finviz.com/news/153769/why-duolingo-duol-shares-are-falling-today)。Fortune は「存続の危機」と報道、Duolingo は「13 年かけて動機付けを作ってきた」と反論 [Fortune 2025-08-27](https://fortune.com/2025/08/27/duolingo-existential-crisis-ai-google-translate-language-learning-live-translation/)。
- 資本差（2025）: Alphabet 2025 売上は本調査で未取得（$350B 超は確実）÷ Duolingo 2025 年 $1.04B → **300 倍超**（分析者判断）。
- 2025 年通年: 売上 $1,037.6M（+39%）、DAU 5,270 万（Q4、前年 4,050 万）、有料 1,220 万（+28%）、2026 年ガイダンス +10〜12%（ユーザー成長を優先し収益化を抑える方針）[Duolingo 2026-02-26](https://investors.duolingo.com/news-releases/news-release-details/duolingo-reports-fourth-quarter-and-full-year-2025-results)、[Motley Fool](https://www.fool.com/investing/2026/02/16/3-key-takeaways-from-duolingos-2025)。
- 結末（2026-11 時点）: 上場（2021-07）・独立存続。巨大資本の本格参入（2025-08）から 1 年強。

### Inferences
- 主 MOAT: **BRAND**（第一想起と口コミ流入＝CAC 優位）。副: **NE-DATA**（S-1 が最も強調する点。ただし生成 AI 期にはモデル自体の優位は縮む可能性があり、H5 の検証対象）、**SC-DATA**（連続記録・ストリーク＝個人の switching cost）。
- 参入前/後: Apple Translate（2020）・Google 練習機能（2025）より前に BRAND・NE-DATA は完成。
- 巨大資本側の制約: **組織の優先度**（Translate は実用ツールで、Google が学習の継続率を KPI にして運営する組織的理由が弱い）。ただし Google が無料で提供できる点は Duolingo の無料モデル（CP）を無効化し得る。2026 年ガイダンスの減速が参入の影響か、収益化方針の転換かは現時点で分離できない。

### Gaps
- Alphabet 2025 売上の一次確認。Google Translate 練習機能の利用者数。Babbel・Rosetta Stone の売上。
- 「参入後 5 年」の観察ができていない（2030 年まで暫定）。

---

## 落とした候補

| 候補 | 判定 | 理由 |
|---|---|---|
| Cursor（Anysphere） | **進行中・暫定（本ノートでは数値収集せず）** | 2022 年創業、ARR $100M（2025-01）→$1B 超（2025-11）、評価額 $29.3B（2025-11-13）**[Wikipedia]** [Cursor](https://en.wikipedia.org/wiki/Cursor_(code_editor))。GitHub Copilot（Microsoft）が先行し参入条件は満たすが、「参入後 5 年」を満たさず、かつ本セッションの検索上限により一次資料を集められなかった。別ノートで扱う。 |
| Slack | 混合 | Teams（2017）のバンドル後、DAU で 2019 年に逆転され [SiliconANGLE](https://siliconangle.com/2019/07/11/microsoft-teams-surges-ahead-13m-users-likely-surpassing-slack/)、2021 年に Salesforce へ売却。設計上「混合」カテゴリへ。 |
| Dropbox | 混合 | 存続するが Google Drive・OneDrive の同梱でシェアを失った（設計で混合と事前指定）。本ノートでは未調査。 |
| Wimdu（Airbnb の競合として） | 資本差条件不適合 | Rocket Internet は Airbnb の 10 倍規模ではない（$90M 調達 vs Airbnb 評価額 $1B）。Airbnb 事例の「巨大資本」は Google（2019）とし、Wimdu は供給側 NE-X 失敗（F-SUPPLY）の対照例として記録。 |
| Adyen | 成功だが本ノートの対象外 | Stripe と同型（SC-WF）で成功。巨大資本の明確な参入イベントが特定できず、Stripe の節で「同じ堀の別成功例」として参照。 |
| Sketch | 失敗だが資本差条件不適合 | Figma に敗れたが Figma は巨大資本ではない。Figma 事例の「機能優位（SPEED）のみでは守れない」対照として言及。 |
| Evernote・Skype・Houseparty・Clubhouse | 失敗側ノートへ | 本ノートでは Notion・Zoom・Discord の対照例（同じ MOAT 類型を主張して失敗）として引用。詳細は失敗側ノートで扱う。 |

---

## 事例×MOAT コード一覧表

資本差は「巨大資本の年間売上 ÷ 新興企業の年間売上または ARR（参入年近傍）」の概算で、分析者計算。「参入前/後」は主 MOAT が巨大資本の参入・模倣・バンドル時点で既に成立していたか。

| 事例 | 巨大資本の参入年 | 資本差 | 主 MOAT | 副 MOAT | 参入前/後 | 結末（2026-11） | 巨大資本側の制約 |
|---|---|---|---|---|---|---|---|
| Figma | 2016（Adobe XD）／2022（買収提案） | 約 44 倍（2022） | SC-WF | ECO, NE-D | 前（2016 と同時期に製品構造として） | 上場・独立（2025-07）。Adobe XD はメンテナンスモード | 反トラスト（EC・CMA）、既存課金との共食い |
| Canva | 2016（Spark）／2021（Express） | 約 16 倍（2021、Canva 側は推計） | CP | ECO, BRAND | 前 | 非上場・独立。ARR $4B（2025 末） | プロ向け高単価サブスクとの共食い、組織の優先度 |
| Notion | 2021（Loop 発表）／2023（GA） | 100 倍超 | SC-DATA | ECO, NE-D | 前 | 非上場・独立。ARR $500〜600M（2025）。**暫定**（参入後 5 年未満） | 社内製品重複（OneNote・SharePoint・Teams）、組織の優先度 |
| Zoom | 2017（Teams 同梱） | 約 590 倍 | BRAND | NE-D, SC-WF（SPEED は非 MOAT） | **後**（2020 年に完成） | 上場・独立。FY2026 $4.87B（+4%） | 反トラスト（EU による Teams 分離） |
| Shopify | 2006〜2015（Webstore）／2023（Buy with Prime） | 約 520 倍（2015） | CP | ECO, SC-WF | 前 | 上場・独立。GMV $378B（2025） | マーケットプレイスとの共食い（Webstore 閉鎖） |
| Airbnb | 2019（Google 旅行検索）※Wimdu 2011 は資本差不適合 | 約 34 倍（2019、Alphabet 側未検証） | NE-X | BRAND, PP | 前 | 上場・独立。売上 $12.2B（2025） | 仲介者（広告）モデル上、供給側を自前で持たない |
| Datadog | 先行（CloudWatch は創業前から） | 約 177 倍（AWS 2019） | SC-WF | CP（マルチクラウド）, SCALE | **後** | 上場・独立。$3.43B（2025）。AWS と SCA（2025-12） | 利益相反（他社クラウド監視の動機なし）、補完財化 |
| Snowflake | 先行（Redshift 2012） | 約 132 倍（AWS 2019） | SC-DATA | CP, NE-X（データ共有） | **後** | 上場・独立。製品売上 $4.47B（FY2026） | 利益相反（最大級の計算資源購入者） |
| Stripe | 2013（PayPal の Braintree 買収） | eBay $16.0B vs 非開示（10 倍超） | SC-WF | ECO, SCALE | 前（配布モデル）／後（SC-WF 厚み） | 非上場・独立。決済額 $1.9T、評価額 $159B（2026-02） | 組織の優先度（消費者ウォレット中心） |
| Discord | 先行（Skype）／2021（買収提案） | 700 倍超 | NE-D | SC-DATA, ECO | 前 | 非上場・独立。IPO 非公開申請（2026-01）。Skype は 2025 年終了 | 組織の優先度（企業向け Teams 集中）、NE-D は買収でしか得られない |
| Duolingo | 2020（Apple Translate）／2025（Google Translate 練習） | 300 倍超 | BRAND | NE-DATA, SC-DATA | 前 | 上場・独立。$1.04B（2025）。**暫定**（参入後 1 年強） | 組織の優先度（Translate は実用ツール） |

### 集計上の所見（事実の整理。解釈は report 側で行う）
- 11 事例のうち主 MOAT に SPEED や機能優位を置けるものは 0。主 MOAT の内訳: SC-WF 3、CP 2、SC-DATA 2、BRAND 2、NE-X 1、NE-D 1。
- 主 MOAT が巨大資本の参入**後**に成立した事例は 3（Zoom・Datadog・Snowflake）。うち Datadog・Snowflake は「巨大資本が先行する市場への後発参入」で、CP（中立性）が参入後の堀形成を可能にした。CP を主または副に持つ 5 事例（Canva・Shopify・Datadog・Snowflake・Figma の共食い要素）で、CP が参入後に新たに作られた例はない（H3 と整合）。
- 巨大資本側の構造的制約が確認できた事例: 11 中 11（反トラスト 2、共食い 3、利益相反 2、組織の優先度 5、重複あり）。H6（半数以上）と整合するが、「制約が確認できた」の判定は分析者による。
- 同じ MOAT 類型で失敗した対照例: SC-DATA（Evernote）、NE-D（Skype・Houseparty・Clubhouse）、NE-X（Wimdu）、DIST（Adobe XD・Amazon Webstore・Microsoft Loop は巨大資本側の DIST が効かなかった例）。
