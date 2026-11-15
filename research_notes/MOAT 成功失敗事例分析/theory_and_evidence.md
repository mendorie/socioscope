# MOAT 理論と体系的エビデンス（事例ノートの解釈枠組み）

- 調査日: 2026-11-15
- 対象テーマ: `design/themes/moat-cases.md`（事前登録 2026-11-15）
- 出典の性質: 学術論文（NBER・CEPR・SMJ・ISR・JPE・QJE・Political Analysis）、規制当局の決定（欧州委員会）、企業の開示（10-Q）、研究機関のブログ（METR）、ベンチマーク調査（High Alpha・SaaS Capital）、実務家のエッセイ（a16z・Stratechery・Spolsky、**コメンタリーとして扱う**）。
- 事実と解釈の区別: 各節の `Cited Findings` は出典に書かれた内容のみ。`Inferences` は本ノート執筆者の推論で、事例ノートの判定根拠には使わない。
- 本ノートで確認できなかった項目は `Gaps` に残す。出典 URL を確認できなかった記述には「（要確認）」を付ける。本ノートは Web 検索の回数制限により途中で検索を打ち切っており、「（要確認）」の項目は次回の調査で埋める。

---

## 1. MOAT の枠組みと定義

### Takeaway
枠組みは「堀＝模倣を妨げる構造」という点で一致するが、(a) 速度・実行力を堀と認めるか、(b) 流通（distribution）を独立の堀と見るか、(c) 破壊（disruption）が需要側か供給側かで割れる。本テーマのコード表（Helmer 骨格＋ DIST・ECO・SPEED）はこの不一致を**別コードとして保持**しており、妥当。

### Cited Findings
- **Helmer『7 Powers』（2016）**: Power ＝ Benefit × Barrier。Benefit は価格上昇・コスト低下・投資減のいずれか、Barrier は競合の裁定を防ぐ構造。どちらかが 0 なら Power ではない。7 類型は Scale Economies・Network Economies・Counter-Positioning・Switching Costs・Branding・Cornered Resource・Process Power。Counter-Positioning は「新規参入者が優れたビジネスモデルを採り、既存企業は追随すると自社の経済性を損なうためためらう」と定義される（[Sachin Rekhi の要約](https://sachinrekhi.com/7-powers-hamilton-helmer)、[Rework 解説](https://resources.rework.com/libraries/strategic-management/7-powers-framework)、[Marginal Futility](https://marginalfutility.substack.com/p/13-counter-positioning-as-a-business)）。Helmer は「優れた実行」「機能の優位」を Power から外す（出典は上記要約。原著の該当章は要確認）。
- **Greenwald & Kahn『Competition Demystified』（2005）**: 「戦略上重要なのは参入障壁のみ。障壁は customer captivity（習慣・スイッチングコスト・探索コスト）、規模の経済、政府保護の 3 種に収斂する」と主張する（**要確認**: 本調査では一次出典・公刊要約を取得できなかった。背景知識に基づく記述）。
- **Porter（1979/1980）**: 5 forces の一つとして「新規参入の脅威」を置き、参入障壁（規模・製品差別化・資本・スイッチングコスト・流通チャネルへのアクセス・政府政策）を列挙する（**要確認**: 原典未取得）。Porter は**流通チャネルへのアクセス**を独立の障壁として扱う点で Helmer と異なる。
- **Buffett（Berkshire 株主への手紙、1990 年代〜）**: 「economic moat」は投資家の比喩で、操作的定義は与えられていない（**要確認**: 本調査で出典を取得していない）。
- **NFX「Network Effects Bible」**: ネットワーク効果を 10 数種（物理・プロトコル・個人ユーティリティ・個人・マーケットプレイス（両面）・プラットフォーム（両面）・漸近的マーケットプレイス・データ・テックパフォーマンス・言語・信念・部族・バンドワゴン等）に分類し、両面市場型を強い部類に置く（**要確認**: 本調査で原典 URL を取得できていない。背景知識）。
- **a16z Rampell「Distribution vs. Innovation」（2015-11-05）**: 「あらゆるスタートアップと既存企業の戦いは、スタートアップが流通を得るのが先か、既存企業がイノベーションを得るのが先か、に帰着する」（[a16z](https://a16z.com/distribution-vs-innovation/)）。
- **Stratechery「Aggregation Theory」（Thompson 2015）**: インターネットがデジタル財の流通コストをゼロにし、「希少資源の流通を握る企業から、豊富な資源への**需要**を握る企業へ」価値が移る。Aggregator はユーザーとの直接関係を持ち、供給側を標準化・商品化する（[Stratechery 2015](https://stratechery.com/2015/aggregation-theory/)、[Defining Aggregators 2017](https://stratechery.com/2017/defining-aggregators/)）。
- **Christensen の破壊的イノベーション vs Gans『The Disruption Dilemma』（MIT Press 2016）**: Gans は破壊を**需要側**（Christensen 型。既存企業が主要顧客に集中し、ニッチから来る参入者を過小評価する）と**供給側**（Henderson 型。アーキテクチャ変化で既存能力が通用しなくなる）に分け、後者が「より危険」と主張する。需要側の処方（自律的部門・買収）と供給側の処方（統合開発）は両立できない、というのが「ジレンマ」（[Gans の論文](https://management-aims.com/index.php/mgmt/article/download/3770/9451)、[書評](https://spe.org.uk/reading-room/book-reviews/the-disruption-dilemma/)）。Christensen 側は 2015 年の HBR「What Is Disruptive Innovation?」で定義を再確認し、Uber は破壊的でないと論じた（**要確認**: 本調査で HBR 原典を取得していない）。

### Inferences
- 枠組み間の不一致は 3 点に整理できる。(i) **SPEED**: Helmer・Greenwald は堀と認めない。実務家（a16z・Stratechery）は「流通を得るまでの時間稼ぎ」として速度を重視する。本テーマの H1 はこの対立を直接検証する設計になっている。(ii) **DIST**: Porter・Rampell・Thompson は流通を独立の障壁とみる。Helmer は Scale や Network に吸収する。本テーマのコード表が DIST を独立コードにしたのは Porter/Rampell 側の立場であり、集計時に「DIST は巨大資本側の武器であって、新興側の堀にはなりにくい」という非対称を意識する必要がある。(iii) **破壊の方向**: Gans の供給側破壊は、生成 AI 期に「既存企業の能力が陳腐化する」局面を説明する候補。H5（モデル優位は堀にならない）は需要側の話で、供給側破壊が起きていれば巨大資本も追随できない可能性がある。
- Helmer の Benefit × Barrier は事例判定に使える操作的テスト。「成功企業が主張した堀」が Barrier を欠く（例: ブランドと言いつつ価格プレミアムがない）場合、堀として採用しない、という基準を事例ノートに適用できる。

### Gaps
- Greenwald・Porter・Buffett・NFX・Christensen 2015 の一次出典 URL を取得できていない（検索回数の制限）。事例ノート作成前に補う。
- Helmer が「速度」を Power から外す根拠の原文（『7 Powers』第 1 章の "operational excellence" の扱い）を確認する。

---

## 2. 既存企業 vs 参入者の体系的エビデンス（ソフトウェア・プラットフォーム）

### Takeaway
体系的エビデンスは「巨大資本の参入は補完者に**不利**」で概ね一致するが、効果の方向・大きさは文脈依存で、注目のスピルオーバーで**有利**になる研究もある。買収による「kill zone」は小標本の示唆にとどまり、2026 年の大標本研究は否定的。バンドルは理論上の強い参入障壁で、Teams/Slack の EU 事件は規制が 5 年かけてようやく部分的に是正した事例。プラットフォーム依存（Zynga・Twitter API）は一次資料で確認できる失敗類型。

### Cited Findings
**買収と参入抑止**
- [Kamepalli, Rajan & Zingales「Kill Zone」(NBER w27146, 2020)](https://www.nber.org/papers/w27146): Google・Facebook による 9 件のアプリ買収後、同分野への VC 投資は 3 年間で平均 40% 超減少。他社による買収では同分野投資が 40% 超増加。理論モデルは「早期買収の期待が、ユーザーの新プラットフォームへの適応意欲を下げ、優れた参入者でも顧客獲得が難しくなる」とする（[Chicago Booth Review](https://www.chicagobooth.edu/review/how-tech-giants-create-kill-zones-competitive-landscape)）。標本が 9 件と小さい点は著者も認める。
- [Cunningham, Ederer & Ma「Killer Acquisitions」(JPE 129(3), 2021)](https://papers.ssrn.com/abstract=3241707): 製薬で、買収者の既存製品と重複する開発中の薬は開発が中止されやすく、買収の 5.3〜7.4% が「killer acquisition」と推定。反トラスト審査の閾値直下に集中する。**製薬のデータ**であり、ソフトウェアへの外挿は著者の主張外。
- [Ederer, Seibel & Simcoe「Digital (Killer?) Acquisitions」(NBER w35762, 2026)](https://www.nber.org/papers/w35762): 1995〜2020 年の 8 大テック企業による約 1,200 件の買収で、特許データと LinkedIn 履歴を分析。平均的には買収技術に**投資**しており、被買収発明の被引用・後続イノベーションへの埋め込みは増える。「デジタル killer acquisition の存在を否定しないが、より一般的なのは買収して投資するパターン」（[VoxEU](https://cepr.org/voxeu/columns/what-happens-innovation-after-big-tech-buys-startup)）。
- Song & Pan「Tech Giants and New Entry Threats」（ICIS 2021）: テック大手の参入を受けたスタートアップは、近年、追加資金調達と長期存続の確率が有意に低い。効果は一時的で、**特許を持たず・ネットワーク効果の強いセグメント**に集中する。M&A による参入抑止の証拠は見つからなかった（[AIS eLibrary](https://aisel.aisnet.org/icis2021/dig_innov/dig_innov/11)、[LSU repository](https://repository.lsu.edu/finance_pubs/145)）。本調査では要旨レベルの確認。

**プラットフォーム所有者の参入（複製・コピー）**
- [Zhu & Liu「Competing with Complementors: An Empirical Look at Amazon.com」(SMJ 39(10), 2018)](https://dash.harvard.edu/bitstream/handle/1/37377131/zhu,liu_competing-with-complementors.pdf?sequence=1): 2013 年 6 月時点の第三者出品 163,853 商品のうち、Amazon は 10 ヶ月で 3% の商品空間に参入。参入確率は商品の人気・評価と正の相関。参入後、影響を受けた出品者はその後の成長を控える一方、商品需要自体は増える。
- [Wen & Zhu「Threat of Platform-Owner Entry and Complementor Responses」(SMJ 40(9), 2019)](https://econpapers.repec.org/RePEc:bla:stratm:v:40:y:2019:i:9:p:1336-1367): Google の Android アプリ参入の脅威が高まると、影響を受ける開発者は当該アプリのイノベーションを減らし（約 5.1% 減）価格を上げ（約 1.8%）、努力を他のアプリに移す。プラットフォームから撤退はしない。
- [Foerderer, Kude, Mithas & Heinzl「Does Platform Owner's Entry Crowd Out Innovation? Evidence from Google Photos」(ISR 29(2), 2018)](https://pubsonline.informs.org/doi/fpi/10.1287/isre.2018.0787): 2015 年の Google Photos 参入を自然実験とし、6,620 アプリの DID で、参入後に補完アプリの**イノベーションが増加**（大型アップデート確率 +9.6%）。消費者の注目のスピルオーバーで説明。Jamison の別研究は Android で Google アプリ導入が開発者アプリのユーザー数を減らすと報告し、結果は分野間で割れる（[Jamison, PURC](https://bear.warrington.ufl.edu/centers/purc/docs/papers/2302_Jamison_Effects_of_platforms_entry.pdf)）。

**バンドル**
- [Nalebuff「Bundling as an Entry Barrier」(QJE 119(1), 2004)](https://ideas.repec.org/a/oup/qjecon/v119y2004i1p159-187..html): 2 財に市場支配力を持つ企業がバンドルすると、1 財しか持たない参入者の参入が困難になる。価格差別による利得は小さく、参入抑止の利得が大きい。
- **Microsoft Teams / Slack（EU、2020〜2025）**: Slack が 2020 年に欧州委員会へ申し立て。正式調査は 2023 年 7 月開始、2024 年に alfaview も申し立て。欧州委員会は 2025 年 9 月に Microsoft のコミットメント（Teams なしの Office スイートを提供、2025 年 11 月 1 日から全世界で選択可、相互運用性改善、Teams からのデータ持ち出し、期間 7〜10 年）を**法的拘束力ある**ものとして受け入れ、違反認定はしなかった。市場テスト後に Slack・alfaview は申し立てを撤回（[欧州委員会プレス](https://app.1848.nl/document/item/579717)、[Computerworld](https://www.computerworld.com/article/4056473/microsoft-ec-reach-deal-on-teams-app-bundling.html)、[Verdict](https://www.verdict.co.uk/eu-approves-microsoft-teams-commitments/)）。Slack は 2020 年 12 月に Salesforce に買収された（**金額・DAU 推移は要確認**）。

**プラットフォーム依存**
- **Zynga / Facebook**: Zynga の 10-Q は「Facebook とそのプラットフォームに収益の大部分を依存」と開示（[SEC 10-Q 2013Q1](https://sec.gov/Archives/edgar/data/1439404/000119312513192799/d531456d10q.htm)、[10-Q 2012Q3](https://capedge.com/filing/1439404/0001193125-12-437790/10Q-2012Q3)）。報道では 2011 年の収益の 94% が Facebook ユーザー由来、Facebook に 30% を支払う（[IBTimes](https://www.ibtimes.co.uk/zynga-in-2012-where-did-it-all-go-wrong-1921)）。2012 年に DAU が 2 ヶ月連続で約 8% 減（Cowen）、Facebook のフィード変更が既存ゲームの表示を減らしたとの開発者の証言がある（[AOL/DailyFinance](https://www.aol.com/2012/05/27/heres-why-zyngas-game-plan-went-haywire/)）。**学術研究は見つかっていない**。
- **Twitter API v1.1（2012-08）**: 「Twitter のコア体験を複製する」クライアントに 100,000 ユーザートークンの上限（既存超過クライアントは現状の 200% まで）。Tweetro などが上限に達し開発停止（[Engadget](https://www.engadget.com/2012-08-16-twitter-api-1-1-third-party-client.html)、[TechRadar](https://techradar.com/news/software/applications/more-third-party-twitter-apps-fall-to-100-000-user-ceiling-1113370)、[TNW](https://thenextweb.com/news/twitter-releases-next-version-api-clarifies-user-token-limits-following-complaints)）。
- Startups が大型プラットフォームに統合すると cold start は解けるがプラットフォームの戦略行動に脆弱になる、という 29 件の founder post-mortem の質的研究がある（[Turku 大学リポジトリ](https://www.utupub.fi/server/api/core/bitstreams/ce50a387-4acc-4d8b-83f6-28e44d8ebedf/content)、要旨確認のみ）。

**コピーキャット（Samwer 兄弟／Rocket Internet）**
- Alando（eBay クローン、1999）は 100 日以内に eBay へ売却。CityDeal（Groupon クローン）は 2010 年に Groupon が買収（約 1.7 億ドルとの報道）。Zalando は独立し、Rocket は残余株（約 50 億ドル相当）を Kinnevik に売却。Jumia は 2019 年 4 月上場。Rocket Internet は 2014 年上場、2020 年に上場廃止（[TechCrunch 2020](https://techcrunch.com/2020/09/01/as-it-delists-rocket-internets-ill-fated-experiment-with-public-markets-is-over/amp)、[Fortune 2020](https://fortune.com/2020/09/01/rocket-internet-startup-incubator-germany-europe-tech-industry/)、[Knowledge at Wharton](https://knowledge.wharton.upenn.edu/article/can-cloning-businesses-work-ask-rocket-internet/)）。Lazada の Alibaba 売却（2016）・個別の減損額は**要確認**。

**SaaS スイッチングコスト・継続率**
- 公開 SaaS 企業の net dollar retention は 2024 年に 3 四半期連続で 110%（2022 年の高値から低下）（[High Alpha 2024](https://highalpha.com/saas-benchmarks/2024)）。
- 非公開 SaaS の 2025 年中央値は net retention 101%・gross retention 91%。複数年契約では 103%／94%（[SaaS Capital 2025](https://www.saas-capital.com/wp-content/uploads/2025/09/RB32WS1-2025-B2B-SaaS-Retention-Benchmarks.pdf)）。Aleph × Benchmarkit（230 社、CY2025）では NRR 中央値 102%、上位四分位 108%、GRR 中央値 88%→84%（[Growth Unhinged](https://www.growthunhinged.com/p/2025-saas-benchmarks-report)）。
- HR system of record: TD Cowen 2023 調査で HRMS のリテンションは Workday 99%・Oracle HCM 97%（[Pulse](https://www.pulse.bot/enterprise/news/workdays-moat-is-realbut-ai-is-testing-its-limits-f8f71229-3bbd-4f91-96fd-015d6dab1669/) 経由、**一次資料は要確認**）。Workday 98% 顧客継続率はベンダー系ブログの数字（[Biz Model Mastery](https://bizmodelmastery.substack.com/p/inside-workdays-98-retention-engine)、販促性あり）。

### Inferences
- 「巨大資本の参入」は 3 類型に分けて集計するべき。(i) **買収**（kill zone）、(ii) **プラットフォーム所有者による複製**（Amazon・Google）、(iii) **バンドル**（Teams）。エビデンスの強さは (iii) ＞ (ii) ＞ (i) の順で、(i) は大標本で否定的。事前登録の F-BUNDLE・F-COPY・F-PLATFORM はこの 3 類型と対応する。
- Zhu & Liu の「人気・高評価ほど参入される」は、**成功事例が参入を呼ぶ**という選択効果を示す。つまり「巨大資本の参入を受けた」という条件自体が、一定の初期成功を前提にしており、本テーマの母集団はすでに「成功したあと」の企業に偏る。
- Song & Pan の「特許なし・ネットワーク効果の強いセグメントで被害が集中」は、NE-* が**巨大資本側にも効く**ことを示す。「ネットワーク効果があれば堀」ではなく、「誰がネットワークを持っているか」が問題。H4（人材業界は NE-X が決定的）を解釈するとき、NE-X が新興側の堀にもなり、巨大資本側（リクルート・Indeed）の武器にもなる点を分けて記録する。
- SaaS の NRR 中央値が 101〜102% に下がっているのは、「SC-WF／SC-DATA が平均的な SaaS には備わっていない」ことの間接証拠。HR system of record の 97〜99% リテンションは例外的に高く、SC-DATA の存在を支持する（ただし出典は二次）。

### Gaps
- 「巨大資本の参入を受けたスタートアップの生存率」を定量的に出した研究は Song & Pan 以外に見つからず、同論文も要旨レベル。本文の標本・効果量を確認する。
- Teams vs Slack の DAU 推移・Salesforce 買収額、Hired/Vettery 統合（2020、Adecco）、Lazada 売却は検索回数制限のため未確認。事例ノート側で一次資料を取る。
- Zynga の Facebook 依存を扱う学術研究は見つかっていない。

---

## 3. ソフトウェアを作るコストは下がったか、下がると何が起きるか

### Takeaway
「作るコスト」低下の証拠は、統制実験で+26〜56%（単純課題）、現場の大規模観察で正味 +15〜20%、経験者の成熟リポジトリで −19% と、**課題の複雑さと文脈で符号まで変わる**。理論（Shapiro & Varian、Spolsky）は、生産コストがゼロに近づくと価値が流通・データ・信頼・希少な補完財に移ると予測し、本テーマの H5 の根拠になる。クラウド・OSS・ノーコードの費用曲線は本調査で一次資料を取れていない。

### Cited Findings
- [Peng, Kalliamvakou, Cihon & Demirer (2023)](https://arxiv.org/abs/2302.06590v1): GitHub Copilot のランダム化実験（JavaScript で HTTP サーバーを実装、2022 年 5〜6 月）。処置群は 55.8% 速く完了（95% CI 21〜89%）。
- Cui, Demirer ほか (2024)「The Effects of Generative AI on High Skilled Work」: Microsoft・Accenture 等での現場実験で完了タスク数 +26.08% と**二次引用**されている（[arXiv 2411.01067 内の引用](https://arxiv.org/pdf/2411.01067v2)）。**原論文は本調査で未確認**。
- [METR (2025-07-10)](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/): 大規模 OSS リポジトリ（平均 100 万行超）の経験豊富な開発者 16 名、246 課題の RCT。AI 利用可の条件で完了に **19% 長く**かかった。開発者は事前に 24% の高速化を期待し、事後も 20% 速くなったと信じていた。主要ツールは Cursor Pro ＋ Claude 3.5/3.7 Sonnet。著者は「この環境に固有の可能性」「Cursor の学習効果は数百時間後に現れうる」と注記。
- Stanford（Denisov-Blanch ほか、約 10 万人の開発者のコミット分析、2025 講演）: 見かけの出力増 30〜40% は、3 週間以内の再修正（rework）を差し引くと正味 15〜20%。単純な greenfield で 30〜35%、複雑な brownfield で 5〜10%（場合により低下）（[AI Engineer 講演](https://ai.engineer/talks/ai-developer-productivity)、[Proxify 要約](https://proxify.io/articles/stanford-study-of-100000-developers-on-engineering-productivity)）。**査読論文ではなく講演の二次要約**。
- **Shapiro & Varian『Information Rules』（1999）**: 情報財は固定費が高く限界費用がほぼゼロ。競争は価格を限界費用（ゼロ）に向けて押し下げるため、価値は差別化・ロックイン（スイッチングコスト）・ネットワーク外部性・標準の支配に移る（**要確認**: 原典未取得、背景知識）。
- **Spolsky「Strategy Letter V」（2002）「Commoditize your complements」**: 製品の需要は補完財の価格が下がると増えるため、企業は補完財を商品化（コモディティ化）するインセンティブを持つ（**要確認**: 原典 URL 未取得）。
- Thompson（Aggregation Theory、前節）: 流通コストゼロで価値が「需要の支配」に移る。
- クラウド・OSS・ノーコードのコスト曲線: **本調査では一次資料を取得していない**。

### Inferences
- 生産性エビデンスを総合すると「0 から作る単純なもの」はたしかに安くなり、「既存の大規模システムを拡張・保守する」コストはほぼ変わらない。これは**新興側に有利**（新規参入の固定費が下がる）であると同時に、**巨大資本側にも有利**（模倣の固定費が下がる）で、方向は事前に決まらない。本テーマの Q3 はこの両面を区別して記述すべき。
- 「作るコスト→0」で理論が予測する価値の移動先（流通・データ・信頼・希少な補完財）は、コード表の DIST・NE-DATA・SC-DATA・BRAND・CR に対応する。H5 はこの予測の AI 期版。
- Spolsky の論理を AI 期に当てると、「モデル」はクラウド大手・OSS により商品化される補完財の側に置かれやすく、モデル提供者は自らアプリ層に進出するインセンティブを持つ（Cursor・Jasper 事例の解釈枠組み）。これは推論であり、事例側で確認する。

### Gaps
- クラウド単価（S3・EC2 の価格推移）、OSS の普及（GitHub Octoverse 等）、ノーコードの採用率について、一次資料を取る。
- Cui ほか (2024) の原論文、Shapiro & Varian、Spolsky の原典 URL。
- 「作りやすさ」が**模倣の速度**（巨大資本が機能を追随するまでの月数）を短くしたかを直接測った研究は見つかっていない。事例ノートで「新興の機能公開 → 巨大資本の同等機能公開」のラグを記録し、時代別に比較することで代替する。

---

## 4. 両面労働市場（人材業界）に固有の理論

### Takeaway
Rochet–Tirole の両面市場理論は「両側の価格構造が重要」「マルチホーミングが winner-take-all を弱める」と予測する。求人市場は求職者・企業の双方がマルチホーミングしやすく、Indeed のようなアグリゲータが流通（SEO）を握る構造になった。人材マーケットプレイス（Hired・Triplebyte）の商品化・縮小は観察されるが、本調査では一次資料が薄い。system of record（Workday 等）は 97〜99% のリテンションが報告される一方、求人メディアは流通依存が高い。

### Cited Findings
- **Rochet & Tirole「Platform Competition in Two-Sided Markets」（JEEA 2003）**: 両面市場では総価格水準だけでなく両側への配分（価格構造）が需要を決める。マルチホーミングが可能な側には競争圧力がかかり、シングルホーミング側を囲い込んだプラットフォームが交渉力を持つ（**要確認**: 原典未取得、背景知識）。
- **Indeed と Google for Jobs（2017〜）**: Indeed のトラフィックの過半は自然検索由来とされる（[Medium 解説](https://medium.com/marketing-102/the-initial-impact-of-google-for-jobs-bd47b16b4a16)）。Indeed は Google for Jobs に求人を提供しない方針を取った。CareerBuilder・LinkedIn は提供（[ERE](https://ere.net/what-the-hell-does-indeed-com-do-now-that-google-for-jobs-is-a-reality)）。Snagajob は Google for Jobs 経由でトラフィック +17%、Recruitics の提携 3 サイトは最初の 6 ヶ月で求人あたり自然閲覧 +11% の後に平準化（[Recruitics](https://info.recruitics.com/blog/the-impact-of-google-for-jobs)）。SHRM 引用のアナリストは「10〜20% のトラフィック減でも Indeed の売上には響かない。すでに求職者の大半を握っている」（[SHRM](https://www.shrm.org/in/topics-tools/news/talent-acquisition/google-jobs-part-larger-plan-to-challenge-microsofts-linkedin)）。これらは**ベンダー・業界メディアの数字**で、学術研究ではない。
- SHRM 引用（2015 年）: Indeed は外部採用の面接ソースで 52%、採用ソースで 43% のシェア（[SHRM](https://www.shrm.org/in/topics-tools/news/talent-acquisition/indeed-dominates-external-sources-hire-survey-finds)）。
- **Triplebyte**: 2023 年 3 月 16 日、Karat が Triplebyte のアセスメント製品とチームを買収。候補者マーケットプレイス（Magnet・タレントネットワーク）は 3 月 31 日で終了。Triplebyte の累計調達は 5,000 万ドル弱、買収額は非開示（[Business Wire](https://www.businesswire.com/news/home/20230316005225/en)、[TechCrunch](https://techcrunch.com/?p=2502886)）。
- **Hired / Vettery（Adecco）**: 2020 年統合と評価額は**要確認**（本調査で未取得）。
- HR system of record のリテンション: 前節（TD Cowen 2023、Workday 99%・Oracle HCM 97%、二次引用）。ADP は「給与計算を system of record とし、HCM をその周囲に構築」、Workday は「HCM・給与・タレントを一つのプラットフォームとして扱う」とコンサルティング系の記述がある（[Consulting Edge](https://consultingedge.substack.com/api/v1/file/97c4fc64-bbac-4e62-8990-a9ab18686ddb.pdf)、販促性あり）。

### Inferences
- 求人市場では**求職者側がマルチホーミングしやすく、企業側は ATS 等への統合でシングルホーミング化しやすい**。両面市場理論に従えば、堀は求職者数（NE-X）そのものより、企業側のワークフロー（SC-WF: ATS 連携・請求・応募者管理）に宿る。H4 は NE-X・CR を 7 割と予測するが、理論からは SC-WF が人材 SaaS 側で主 MOAT になる余地がある。集計時に「求人メディア」と「HR SaaS」を分けて H4 を判定する。
- Indeed の事例は「流通（Google SEO）への依存」を持ちながら、求職者側の規模で Google 自身の参入を凌いだ事例として読める。これは DIST 依存 ＝ F-PLATFORM リスクとは限らないことを示す候補で、事例ノートで一次資料（Recruit Holdings の開示）により確認する。
- 人材マーケットプレイス（Hired・Triplebyte）の縮小は、Aggregation Theory の「供給側が商品化される」予測と整合的に読める。評価・スクリーニングという価値が ATS・LinkedIn・既存大手に吸収された（F-SINGLE）のか、単位経済（F-ECON）が成り立たなかったのかは事例ノートで切り分ける。

### Gaps
- Rochet–Tirole 原典、求人市場のマルチホーミングを測った実証研究（求職者 1 人あたりの利用サイト数等）が未取得。
- Indeed の Google for Jobs 以後のトラフィック推移（Similarweb・Recruit Holdings IR）。
- Hired/Vettery/Adecco の統合条件。

---

## 5. 比較事例分析の方法論上の注意

### Takeaway
成功事例から堀を読み取る作業は、生存者バイアス・後知恵・従属変数での選択（Geddes 1990）の 3 点で歪む。事前登録済みの枠組みはこれを部分的に防いでいるが、「同じ堀を持って失敗した事例」「参入を受けなかった事例」を明示的に入れないと、堀の有無と結果の相関すら言えない。

### Cited Findings
- [Geddes「How the Cases You Choose Affect the Answers You Get」(Political Analysis 2, 1990, 131–150)](https://www.cambridge.org/core/journals/political-analysis/article/abs/how-the-cases-you-choose-affect-the-answers-you-get-selection-bias-in-comparative-politics/05E854AA55C1BF090B56CEC73ACEFC6B): 従属変数の値（結果が生じた事例のみ）で事例を選ぶと説明の論理が崩れる。比較政治の著名な 3 研究を、従属変数と無関係に選んだ事例で再検証すると結論が変わった。
- Zhu & Liu (2018)（前節）: 巨大資本は人気・高評価の製品空間を選んで参入する。参入を受けること自体が初期成功の関数。
- METR (2025)（前節）: 開発者は自分が速くなったと**事後も**信じていたが、実測は遅かった。自己報告・経営者発言は結果の方向すら外す。
- Ederer ほか (2026) と Kamepalli ほか (2020) の食い違い（前節）: 標本の大小で結論が反転した例。

### Inferences
- 本テーマ固有のバイアス源は 4 つ。(1) **生存者バイアス**: 成功事例が持つ堀は、失敗事例も同じ堀を主張していた可能性がある（S-1 の Competitive Strengths はほぼ常に network effects と brand を挙げる）。(2) **後知恵**: 2026 年時点の結果を知った上で過去の堀を評価するため、成功企業には堀を多く、失敗企業には少なく付与しがち。(3) **従属変数での選択**: 母集団を「巨大資本の参入を受けた企業」に限ると、Zhu & Liu の通り、すでに成功した企業に偏る。「参入を受けなかった同カテゴリの企業」は観察されない。(4) **自己報告**: 経営者発言・S-1 の主張は堀の証拠ではなく、「主張された堀」のデータとして別列に置く。
- 事例分析で因果は言えない。言えるのは「事前に定義した堀コードと結果の関連が、事前の仮説と整合するか」まで。report ではこの範囲に表現を抑える。

### 本 report が実行する具体的チェック（提案、5 件）
1. **堀ごとの対照探索（ペアリング）**: 成功事例の主 MOAT 1 コードごとに、同じ主 MOAT を持ちながら失敗した事例を最低 1 件探し、見つからなければ「探したが見つからない」と記録する。見つかった場合、両者を分けた副 MOAT・失敗原因コードを比較表にする。
2. **主張と実測の分離**: 各事例で「企業が主張した堀」（S-1・経営者発言）と「分析者が一次資料から認めた堀」を別列にし、一致率を成功・失敗別に集計する。失敗事例の主張一致率が成功事例と同程度なら、主張は予測力を持たない。
3. **参入前時点での盲検コーディング**: 堀の付与は「巨大資本参入**時点**までの資料」だけで行い、結果（成功／失敗）を伏せた状態で付与する手順を取る（担当を分けるか、資料の日付で機械的に切る）。参入後の資料から読み取った堀は「事後」とラベルし、H1〜H6 の判定には使わない。
4. **落選事例の台帳**: 候補に挙げたが条件（資本差 10 倍・5 年・創業 2005 年以降）を満たさず落とした事例を、理由つきで一覧化し、落選理由の分布を report に載せる（Geddes 対策の可視化）。
5. **非参入対照**: 同カテゴリで巨大資本の参入を**受けなかった**企業（または参入が小規模だった企業）を各区分 1〜2 件挙げ、その企業の堀コードを同じ手順で付与する。「参入を受けた成功例」と「受けなかった企業」で堀の分布が違えば、参入自体が選択的である証拠として記録する。

### Gaps
- Geddes 本文の 3 研究の具体内容は未確認（要旨レベル）。
- 比較事例分析でのプロセス・トレーシング（Bennett & Checkel 等）の規約を参照すれば、チェック 3 の手順を精緻化できる（未調査）。

---

## 本テーマへの含意

### (a) 事前登録仮説 H1〜H6 への文献の予測
| 仮説 | 文献の予測 | 根拠 | 注意 |
|---|---|---|---|
| **H1** 機能・SPEED は堀にならない（成功の 8 割以上が NE/SC/CP/DIST/ECO） | **支持側に傾く**が、SPEED の扱いで枠組みが割れる | Helmer・Greenwald は実行力を Power から外す。Rampell は「流通を先に得る競争」として速度を位置づける（第 1 節） | 成功事例で SPEED が「副」に頻出するなら、「堀ではないが堀を築く時間を買う手段」として別集計する。METR・Stanford の結果（第 3 節）は「作る速度」の優位が持続しにくいことを示唆するが、間接証拠 |
| **H2** 失敗の最多原因は F-BUNDLE ＋ F-SINGLE（≥50%） | **部分的に支持**。バンドルは理論・規制事例ともに強い（Nalebuff 2004、Teams/Slack） | 第 2 節 | 文献上、F-PLATFORM（Zynga・Twitter API）と F-COPY（Amazon・Google 参入）も体系的に確認されており、4 類型が分散する可能性がある。≥50% の閾値は厳しめ |
| **H3** CP は参入前に築かれる | **支持側**。Helmer の定義上、CP は「既存企業が追随すると自社を傷める」モデル差であり、参入後に作る余地は小さい | 第 1 節 | 参入後に価格モデルを変えて生き残った例（混合に分類される Dropbox 等）が出た場合、CP ではなく SC-* の作用と区別する |
| **H4** 人材業界は NE-X／CR が決定的（成功の 7 割、失敗の F-SUPPLY 5 割） | **求人メディアでは支持、HR SaaS では不支持の可能性** | 両面市場理論は求職者側のマルチホーミングを予測し、堀は企業側ワークフロー（SC-WF）や記録（SC-DATA）に宿る。Workday 97〜99% リテンションは SC-DATA の証拠（二次） | 判定を「求人メディア／スキマバイト」と「HR SaaS／採用管理」に分けて行うことを**事後追加の注記つき**で検討する。元の 7 割閾値は変えない |
| **H5** AI 期はモデル優位が堀にならず、DIST・SC が残る | **支持側**（Shapiro & Varian、Spolsky、Aggregation Theory の予測と整合） | 第 3 節 | 生産性エビデンスは「複雑な既存システム」では AI の効果が小さく、SC-WF を持つ既存製品が有利になる方向。ただし Gans の供給側破壊が起きていれば逆転しうる。Cursor 等は暫定 |
| **H6** 成功の半数以上で巨大資本側の構造的制約がある | **支持側**。Helmer の CP、Christensen の需要側破壊、Teams の規制介入が制約の 3 類型 | 第 1・2 節 | 「制約があった」の証明は後知恵に陥りやすい。巨大資本側の一次資料（10-K のリスク記述・経営者発言・規制文書）で、参入時点に制約が認識されていたかを確認する |

### (b) 方法論チェック（第 5 節の 5 件を report の必須手順にする）
1. 堀ごとの対照探索（成功の各主 MOAT に失敗の同 MOAT を 1 件以上）。
2. 「主張された堀」と「認めた堀」の分離と一致率の集計。
3. 参入時点までの資料による盲検コーディング（事後資料は H 判定に使わない）。
4. 落選事例の台帳と落選理由の分布。
5. 非参入対照（参入を受けなかった同カテゴリ企業）の堀コード付与。

加えて、第 2 節の知見から、「巨大資本の参入」を**買収・複製・バンドル**の 3 種に分けて記録し、各種で成功・失敗の比率を別に出す（F-BUNDLE・F-COPY・F-PLATFORM の切り分けと対応）。

### 本ノートの限界
- Web 検索の回数制限により、Greenwald・Porter・NFX・Shapiro & Varian・Spolsky・Rochet–Tirole・Christensen 2015・Cui ほか 2024・Hired/Vettery・Slack の買収額などの一次出典を取得できていない。該当箇所は「（要確認）」として残した。事例ノート作成前に、これらの URL を補う調査を行う。
- 取得した学術論文は要旨・二次要約レベルの確認が多く、本文の標本・識別戦略を精査していない。効果量を report に引用する場合は原論文を再確認する。
