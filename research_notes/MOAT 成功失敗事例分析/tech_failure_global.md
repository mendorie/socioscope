# テック失敗・混合事例（海外）— 巨大資本の参入後に市場を失った企業

- 調査日: 2026-11-15
- 枠組み: `design/themes/moat-cases.md`（事前登録済みの問い Q2・事例選定基準・MOAT コード表・失敗原因 F コード表）に従う。コード付与は分析者の判断を含むため、根拠となる出典を各事例に残し、別の読み方があるものは併記した。
- 出典の品質メモ:
  - 一次資料（SEC の S-1・10-K・F-1、公式ブログ、創業者本人の post-mortem）を優先した。Slack S-1、Dropbox S-1、Zynga S-1（2012 年版）、Fitbit 10-K（2015・2019 年度）、Dropbox 10-K（2024・2025 年度）、Bending Spoons F-1 を直接参照した。
  - 報道は TechCrunch・VentureBeat・CNBC・Stratechery・Harvard D3 などを用いた。WSJ・FT・The Information は有料壁のため本文を直接確認できず、二次報道経由または見出しのみの参照になっている箇所がある（各所に明記）。
  - Wikipedia は「最後の手段」として、年表の骨格確認にのみ用い、`[Wikipedia]` と明示した。Wikipedia 由来の数値は一次資料で裏取りできたものを優先し、できなかったものは Gaps に残した。
  - 本調査中に Web 検索の回数上限に達したため、一部の数値（Fitbit の年次売上、Zynga の 2012 年株価底値、Twitter Spaces の正確な公開日、Lotus 1-2-3 の年次シェア等）は裏取りが不完全。該当箇所は「未確認」と明記し Gaps に列挙した。
- 事実（Cited Findings）と解釈（Inferences）は節を分けた。Inferences は分析者の推論であり、出典に直接書かれていることではない。

---

## Slack vs Microsoft Teams（混合）

### Takeaway
Slack は「増加収益の力学（increasing returns）」「開発者エコシステム」「顧客の愛着による粘着性」を堀と主張したが、Microsoft は Office 365 への Teams 同梱（実質無料）と既存営業網で 2019 年 7 月に DAU で逆転、2023 年には MAU 3.2 億で Slack の約 10 倍に達した。Slack は 2020 年に Salesforce へ 277 億ドルで売却され（ピーク評価額は上回った）、ブランドと製品は存続しているため「失敗」ではなく「混合」。主因は F-BUNDLE、副因は F-SINGLE（チャット単体がスイート内の一機能として吸収）。EU への申し立て（2020 年 7 月）は 2025 年 9 月の Teams 分離コミットメント受理で決着したが、シェアを取り戻す効果は乏しいと当時から見られていた。

### Cited Findings
- 創業・製品: Tiny Speck として 2009 年設立、2014 年 8 月に Slack Technologies へ改称。社内ツールから Slack が生まれた（[Wikipedia: Slack Technologies](https://en.wikipedia.org/wiki/Slack_Technologies)）。
- 資金調達・評価額: 2014 年 10 月に評価額 12 億ドル、2015 年 3 月 27.6 億ドル、2016 年 4 月 38 億ドル、2017 年 9 月 51 億ドル（[Wikipedia: Slack Technologies](https://en.wikipedia.org/wiki/Slack_Technologies)）。2019 年 6 月 20 日に NYSE で直接上場、初日評価額約 230 億ドル（[VentureBeat 2021-07-21](https://venturebeat.com/2021/07/21/salesforce-completes-27-7b-slack-acquisition/)）。
- S-1（2019 年 4 月）での自己主張（"What Sets Us Apart"）: 単一のミッションへの集中、規模と市場リーダーシップ、「強い増加収益の力学（ユーザーや組織が増えるほど既存メンバーの価値が増す）」、「顧客の愛着による粘着性と有機的拡大」、口コミ主導のセルフサービス GTM。「組織間の共有チャネルが Slack ネットワーク全体の価値を高める」と記載。App Directory 1,500 アプリ超、登録開発者 50 万人超。スイッチングコストについての直接の記述はない（[Slack S-1, 2019](https://www.sec.gov/Archives/edgar/data/1764925/000162828019004786/slacks-1.htm)）。
- S-1 の競合リスク: 「現在の主要競合は Microsoft Corporation」。大手競合は「製品のバンドルやゼロ・マイナスマージンでの販売」で圧力をかけうると明記（同 S-1）。
- 業績: FY2017 売上 1.052 億ドル、FY2018 2.205 億ドル、FY2019 4.006 億ドル（純損失 1.389 億ドル）、2020 年（FY2021）売上約 9.03 億ドル（[Slack S-1](https://www.sec.gov/Archives/edgar/data/1764925/000162828019004786/slacks-1.htm)、[Wikipedia: Slack Technologies](https://en.wikipedia.org/wiki/Slack_Technologies)）。
- Microsoft の参入: 2016 年 11 月 2 日に Teams を発表。Slack は同日 NYT に全面広告「Dear Microsoft」を掲載した（[Stratechery 2016](https://stratechery.com/2016/slack-and-the-macintosh-microsoft-teams-slacks-ad/)、[Quartz 2016-11](https://qz.com/825617/slack-vs-microsoft-teams-slack-took-out-a-full-page-ad-in-the-new-york-times-to-welcome-its-new-competitor)）。Teams の GA は 2017 年 3 月、無料版は 2018 年 7 月 12 日に 40 言語で提供開始（[Quartz 2018-07](https://qz.com/1325993/microsoft-is-offerring-a-free-version-of-its-slack-competitor-teams)、[SiliconANGLE](https://siliconangle.com/?p=445307)）。
- 資本差: Microsoft の FY2017 売上は 965.7 億ドル（[StockAnalysis: MSFT revenue](https://stockanalysis.com/stocks/msft/revenue/)）。Slack の FY2017 売上 1.05 億ドルに対し約 900 倍。
- 利用者数の推移: Slack DAU は 2019 年 1 月時点 1,000 万超、2019 年 9 月 1,200 万（前年比 +37%）。Microsoft は 2019 年 7 月に Teams DAU 1,300 万・MAU 1,900 万を発表（[CIO Dive 2019-10-11](https://ciodive.com/news/slack-hits-12m-daily-active-users-on-the-heels-of-microsoft-teams/564841)、[Crunchbase News 2019-07-11](https://news.crunchbase.com/?p=19421)）。Teams DAU は 2020 年 3 月初に 3,200 万、2020 年半ばに 7,500 万（[Stratechery 2020](https://stratechery.com/2020/the-slack-social-network/)）。2023 年秋に Teams MAU 3.2 億（[Windows Central](https://www.windowscentral.com/software-apps/microsoft-teams-surpasses-320-million-active-monthly-users-amid-pressure-from-rivals-to-unbundle-the-service-from-office)）。2024 年 4 月時点で Slack は約 3,200 万ユーザー、Teams の約 10%（計測定義は異なる）（[TechCrunch 2024-04-01](https://techcrunch.com/2024/04/01/as-microsoft-unbundles-teams-it-might-not-have-the-impact-on-slack-you-think)）。
- Slack 側の反論（2019 年）: 「すべての DAU が同じ価値ではない」、エンゲージメントが Teams の約 10 倍（Productiv 調査）、週 50 億回のインタラクション、アプリ 1,800 超・カスタムアプリ 50 万（[CIO Dive 2019-10-11](https://ciodive.com/news/slack-hits-12m-daily-active-users-on-the-heels-of-microsoft-teams/564841)、[Fool 2019-09](https://www.fool.com/investing/2019/09/06/slack-tries-to-dispel-microsoft-fears.aspx)）。
- 結末: 2020 年 12 月 1 日に Salesforce が 277 億ドルでの買収を発表、2021 年 7 月 21 日に完了。Butterfield は CEO 継続、ブランド維持（[Salesforce news](https://salesforce.com/news/salesforce-in-the-news/salesforce-completes-27-7b-slack-acquisition)、[VentureBeat 2021-07-21](https://venturebeat.com/2021/07/21/salesforce-completes-27-7b-slack-acquisition/)）。
- 反トラスト: Slack は 2020 年 7 月に欧州委員会へ申し立て（Teams を Office に抱き合わせ、強制インストール・削除不可・価格の不透明化）。2023 年に正式調査、2024 年 4 月に Microsoft が Teams の分離販売を世界展開、2025 年 9 月に EC が Microsoft のコミットメント（Teams 抜き Office の低価格提供、相互運用性・データ移行、7〜10 年の履行義務）を受理し制裁金なしで終結（[Thurrott 2025](https://www.thurrott.com/office/326539/microsoft-settles-office-teams-bundling-case-with-eu)、[Windows Central 2025](https://www.windowscentral.com/microsoft/microsoft-teams/microsoft-dodges-eu-antitrust-fine-unbundles-teams-from-office-365)、[TechCrunch 2024-04-01](https://techcrunch.com/2024/04/01/as-microsoft-unbundles-teams-it-might-not-have-the-impact-on-slack-you-think)）。
- 同時代の評価（後知恵でない代替戦略の手がかり）: Ben Thompson は 2016 年時点で「Teams は無料で Slack は有料」「Teams は Microsoft 顧客が Slack を試すことすら防ぐ」と指摘。2020 年には「チャット機能で競うのをやめ、Shared Channels／Slack Connect で社外の相手を巻き込む水平の企業間ネットワークを堀にすべき」と論じた。Shared Channels はベータ約 2 年を経て 2019 年に GA（[Stratechery 2016](https://stratechery.com/2016/slack-and-the-macintosh-microsoft-teams-slacks-ad/)、[Stratechery 2020](https://stratechery.com/2020/the-slack-social-network/)）。
- 分離販売の効果への同時代評価: アナリストは「ピュロスの勝利」「大企業は既にプラットフォームを選んでおり、シェアはほとんど動かない」「むしろ Microsoft が非 Office 顧客に Teams を売りやすくなる」と評した（[TechCrunch 2024-04-01](https://techcrunch.com/2024/04/01/as-microsoft-unbundles-teams-it-might-not-have-the-impact-on-slack-you-think)）。

### Inferences
- 主張した堀は NE-D（社内ユーザー増による価値増）と ECO（アプリ・開発者）だが、NE-D は**組織単位で閉じていた**ため、組織の外に出る堀（組織間ネットワーク）になっていなかった。Shared Channels の GA（2019 年）は Teams 発表（2016 年）から 3 年後で、Teams の DAU 逆転（2019 年 7 月）と同時期。「参入前に組織間 NE を築けていたか」で言えば、築けていなかった。
- 欠けていた MOAT: DIST（Microsoft は Office 365 の既存顧客基盤と営業・パートナー網を持ち、Slack は口コミとセルフサービス中心）、および SC-WF（Slack は「統合層」を標榜したが、Office・Outlook・SharePoint との統合深度で Teams に劣った）。「エンゲージメント 10 倍」は機能優位（SPEED）の指標であり、堀の指標ではなかった。
- F コード: 主 F-BUNDLE（S-1 自身がリスクとして予見していた形で現実化）、副 F-SINGLE（チャットがスイートの一機能として吸収された）。F-COPY は副次的（Teams はチャット UX で劣るという評価が長く続いたため、模倣による差分消失は主因でない）。
- 代替戦略の有無（同時代の論評に基づく）: 2016〜2020 年に Thompson らが提案した「企業間ネットワーク化」は当時から入手可能な戦略だった。Slack は実行したが遅かった。もう一つは反トラスト申し立てで、実行したが 5 年かかり、決着時にはシェアが固定化していた。価格で対抗する選択肢（無料枠拡大）は、Slack の売上がサブスク 100% であるため構造的に取りにくかった（CP が逆向きに働いた）。
- 「混合」判定の根拠: 売却額 277 億ドルは直接上場時の評価額（約 230 億ドル）を上回り、ブランド・製品は存続。一方でシェアは Teams の約 1/10 に落ちた。事前登録の定義どおり「存続したがシェアを明確に失った」に該当。

### Gaps
- Slack の 2021 年以降の DAU・売上は Salesforce の開示に埋もれており、独立した数値を確認できなかった。「約 3,200 万」は報道の推計。
- Teams の DAU→MAU への指標変更（2021 年）で、時系列の直接比較が途中で切れている。
- EU 申し立て書面の原文は入手できず、報道経由。

---

## Dropbox vs Google Drive / OneDrive（混合）

### Takeaway
Dropbox は「5 億人の登録ユーザーが最良の営業」「バイラルな共有によるネットワーク効果」「売上の 90% 超がセルフサービス」を強みとして上場したが、2012 年 4 月の Google Drive 参入（無料 5GB）以降、ストレージは OS・スイートの付属機能として同梱され、個人向けのシェアは Google Drive・OneDrive の後塵を拝した。2014 年の評価額 100 億ドルに対し 2018 年 IPO 後の企業価値は横ばい〜下回り、2024〜2025 年には有料ユーザーが減少に転じた（1,822 万 → 1,808 万）。独立企業として売上約 25 億ドルで存続しており「混合」。主因は F-BUNDLE（OS・スイートへの同梱）、副因は F-SINGLE（同期ストレージが単機能として吸収）。

### Cited Findings
- 創業: 2007 年 5 月、Evenflow, Inc. として Drew Houston と Arash Ferdowsi が設立（Y Combinator）。2009 年 10 月に Dropbox, Inc. へ改称。登録ユーザー 100 万（2009 年 4 月）、5,000 万（2011 年 10 月）、1 億（2012 年 11 月）、5 億（2016 年）、7 億（2021 年）（[Wikipedia: Dropbox](https://en.wikipedia.org/wiki/Dropbox)）。
- 評価額: 2011 年の 2.5 億ドル調達で約 40 億ドル（[eWeek 2012](https://www.eweek.com/cloud/google-drive-to-launch-next-week-report/)）、2014 年の BlackRock 主導 2.5 億ドルで約 100 億ドル（[Red Herring, WSJ 引用](https://www.redherring.com/internet/dropboxs-10-billion-valuation-raises-more-bubble-concerns)、[Wikipedia: Dropbox](https://en.wikipedia.org/wiki/Dropbox)）。
- 巨大資本の参入: Google Drive は 2012 年 4 月 24 日に無料 5GB で開始（[MIT Technology Review 2012-04-24](https://www.technologyreview.com/2012/04/24/186582/googles-drive-adds-to-a-complicated-cloud/)、[Bloomberg 2012-05-03](https://www.bloomberg.com/news/articles/2012-05-03/hard-drives-that-stretch-to-infinity)）。
- 資本差: Google の 2012 年売上 460.4 億ドル（[StockAnalysis: GOOG revenue](https://stockanalysis.com/stocks/goog/revenue/)）。Dropbox の 2011 年売上は Forbes の予測で約 2.4 億ドル（[Wikipedia: Dropbox, Forbes 2011 引用](https://en.wikipedia.org/wiki/Dropbox)）。約 190 倍。
- S-1（2018 年 2 月）の自己主張: 「5 億人の登録ユーザーは最良の営業担当」「売上の 90% 超はアプリ・Web 経由のセルフサービス」。競合として Amazon・Apple・Atlassian・Box・Google・Microsoft を列挙。登録ユーザー 5 億超のうち有料は約 1,100 万（約 2.2%）、2017 年売上約 11 億ドル（[Dropbox S-1, 2018](https://www.sec.gov/Archives/edgar/data/0001467623/000119312518055809/d451946ds1.htm)、[Meritech S-1 breakdown](https://meritech.substack.com/p/dropbox-ipo-s-1-breakdown)、[Fox Business](https://www.foxbusiness.com/markets/dropbox-is-going-public-what-you-need-to-know)）。
- 同時代の批評: Stratechery は Box（有料率 17%）との対比で Dropbox の有料率 2% を指摘した（[Stratechery 2018](https://stratechery.com/2018/the-dropbox-comp/)）。
- 上場: 2018 年 3 月 23 日 Nasdaq 上場、初日 +42% で 29.89 ドル（[Wikipedia: Dropbox](https://en.wikipedia.org/wiki/Dropbox)）。
- 業績の停滞: 2024 年売上 25.48 億ドル（+1.9%）、有料ユーザー 1,822 万（前年 1,812 万）。経営陣は「有料ユーザーの成長率は低下しており今後も低下しうる」と記載。2023 年に 16%、2024 年 10 月に 20% の人員削減。2025 年末の有料ユーザーは 1,808 万へ減少（理由: 人員削減後の外勤営業縮小、Teams プランへの継続的な圧力、FormSwift 投資縮小）（[Dropbox 10-K FY2024](https://www.sec.gov/Archives/edgar/data/1467623/000146762325000011/dbx-20241231.htm)、[Dropbox 10-K FY2025](https://www.sec.gov/Archives/edgar/data/1467623/000146762326000008/dbx-20251231.htm)、[TipRanks](https://www.tipranks.com/news/dbx-earnings-dropbox-dropped-on-user-decline-forecast)）。
- 個人向けシェア（業界調査・低品質注意）: Backlinko の調査で個人クラウドストレージ利用は Google Drive 40%、OneDrive 20%、Dropbox 18%（[Backlinko](https://backlinko.com/dropbox-users)。同ページ内で数値の不整合があり参考値）。
- 製品戦略の揺れ: Mailbox 買収（2013 年 3 月、約 1 億ドル）・Carousel（2014 年 4 月）をともに 2015 年 12 月に終了。HelloSign を 2019 年 1 月に約 2.3 億ドルで買収（[Wikipedia: Dropbox](https://en.wikipedia.org/wiki/Dropbox)）。

### Inferences
- 主張した堀は NE-D／バイラル（共有リンクが新規登録を生む）と BRAND。しかしストレージ同期は OS（iCloud・OneDrive）・スイート（Google Workspace・Microsoft 365）に無料同梱されると「使う理由」が消える。NE は共有相手がすでに別のストレージを持っている場合に効かない。
- 欠けていた MOAT: SC-DATA／SC-WF。Dropbox 上のファイルは移行コストが低く、業務記録としてのロックインが弱い。Google Docs・Office は「ファイルの中身を編集するアプリ」を持ち、Dropbox は持たなかった（Paper は定着せず）。
- 2024〜2025 年の有料ユーザー減は、Teams プラン（中小企業）での Microsoft 365 との競合圧力を 10-K が明示しており、F-BUNDLE が 10 年以上にわたり継続的に効いていると読める。
- F コード: 主 F-BUNDLE、副 F-SINGLE。F-ECON ではない（Dropbox は 2015 年以降 FCF 黒字で、資本戦で持久できなかったわけではない）。
- 代替戦略（同時代の論評）: 2018 年 IPO 時に有料化率 2% 問題が指摘され、「Box 型の企業向けへ寄せる」「文書編集（Paper）やワークフローへ拡張する」が議論されていた。Dropbox は後者を試みたが Paper・Carousel・Mailbox はいずれも終了し、HelloSign（電子署名）・FormSwift（文書テンプレート）の買収で隣接へ出た。実行の遅れと一貫性の欠如は観察事実だが、「別の戦略なら勝てた」とは言えない（巨大資本の同梱は戦略を問わず作用する）。

### Gaps
- IPO 時の企業価値（約 90 億〜120 億ドルと報道）を一次資料で確認できなかった。2014 年の 100 億ドルとの比較は報道値どうしの比較。
- Steve Jobs が 2009 年に Houston へ「Dropbox は製品ではなく機能だ」と述べたとされる Forbes 2011 年記事は取得できず（403）。引用は未確認。
- 個人向け・法人向けのシェア時系列（2012〜2024）は信頼できる業界調査を見つけられなかった。

---

## Evernote（失敗）

### Takeaway
Evernote は 2012 年に評価額 10 億ドル超の「初期ユニコーン」となり、CEO Phil Libin は「100 年続く会社」を掲げたが、Apple Notes・OneNote（OS・スイート同梱、無料）と後発の Notion に挟まれ、2015 年以降は人員削減・経営陣交代・価格引き上げを繰り返した。2022 年 11 月に Bending Spoons へ売却され、売却対価は約 1.94〜1.997 億ドル（F-1 開示）で、ピーク評価額の約 1/5〜1/10。主因は F-BUNDLE（OS 標準ノートの無料化）、副因は F-SINGLE（ノート単機能が OS・コラボ製品のサブ機能に吸収）と F-SELF（焦点の喪失・物販への拡張）。

### Cited Findings
- 創業: 2007 年、Stepan Pachikov が設立。2008 年 6 月 24 日に初の公開版。2010 年 10 月に Sequoia 主導で 2,000 万ドル調達（[Wikipedia: Evernote](https://en.wikipedia.org/wiki/Evernote)）。
- 評価額: 2012 年 5 月に約 10 億ドル、同年 11 月に 20 億ドルとする資料もある（[multiples.vc](https://multiples.vc/private-comps/evernote)。報道では「約 10 億ドル」が主流）。2013 年時点で「10 億ドル近く」（CB Insights 引用、[TechCrunch 2022-11-16](https://techcrunch.com/2022/11/16/bending-spoons-acquires-evernote-marking-the-end-of-an-era/)）。累計調達は約 2.9 億ドル（[SiliconANGLE 2022-11-16](https://siliconangle.com/2022/11/16/22-years-founded-evernote-acquired-italian-technology-company/)）。
- ユーザー: 2018 年に Ian Small が CEO に就いた時点で 2.5 億ユーザー超（[TechCrunch 2022-11-16](https://techcrunch.com/2022/11/16/bending-spoons-acquires-evernote-marking-the-end-of-an-era/)）。
- 自己主張した堀: Libin は 2013 年のインタビューで「100 年続く会社」を語り、同時にユーザーが「機能の 5% しか使っていない」「人ごとに違う 5%」であることを認めていた（「5% 問題」）（[VentureBeat 2016-01-05](https://venturebeat.com/business/evernotes-5-problem-offers-a-cautionary-lesson-to-tech-companies)）。
- 転落の経過: 2015 年 7 月に Google Glass 出身の Chris O'Neill が CEO 就任、約 10 週間で 47 人を削減し 3 拠点閉鎖（13% 削減）。「Evernote の強みはコアにある。そこに集中する」と発言。2015 年 10 月に 18% 削減・10 拠点中 3 拠点閉鎖。2016 年 6 月に無料プランを 2 台に制限し有料プランを値上げ。2018 年 8 月に幹部が相次ぎ退任、同年 9 月に 54 人（15%）を削減、O'Neill は「現金 3,000 万ドル、2018 年中にキャッシュフロー黒字化」と社内説明（[VentureBeat 2016-01-05](https://venturebeat.com/business/evernotes-5-problem-offers-a-cautionary-lesson-to-tech-companies)、[Axios 2018-09-19](https://www.axios.com/2018/09/19/evernote-app-layoffs-future)、[TechCrunch 2022-11-16](https://techcrunch.com/2022/11/16/bending-spoons-acquires-evernote-marking-the-end-of-an-era/)、[Wikipedia: Evernote](https://en.wikipedia.org/wiki/Evernote)）。
- 製品の迷走: Moleskine（2012 年 8 月）などの物販提携、Skitch 買収（2011 年）と 2016 年の終了、2020 年の Electron ベース v10 への刷新で速度低下・機能削減の批判（[Wikipedia: Evernote](https://en.wikipedia.org/wiki/Evernote)、[TechCrunch 2022-11-16](https://techcrunch.com/2022/11/16/bending-spoons-acquires-evernote-marking-the-end-of-an-era/)）。
- 競合: TechCrunch は「Notion に追いつけなかった」「消費者向けフリーミアムに頼りコラボ機能を欠いた」と総括（[TechCrunch 2022-11-16](https://techcrunch.com/2022/11/16/bending-spoons-acquires-evernote-marking-the-end-of-an-era/)）。
- 結末: 2022 年 11 月 16 日に Bending Spoons が買収を発表、2023 年 1 月 3 日完了。価格は非公表だったが、Bending Spoons の F-1 は 2023 年の買収総額（当年は Evernote のみ）を企業価値 1.94 億ドル、総対価 1.997 億ドルと開示（[Bending Spoons F-1](https://www.sec.gov/Archives/edgar/data/0002004711/000110465926071170/tm2613674-7_f1.htm)、[SiliconANGLE](https://siliconangle.com/2022/11/16/22-years-founded-evernote-acquired-italian-technology-company/)）。買収後、無料プランは 2023 年 12 月に 50 ノートへ制限（[Wikipedia: Evernote](https://en.wikipedia.org/wiki/Evernote)）。F-1 は Evernote の買収後 NRR を 99%（2023Q1〜2026Q1 平均）とし、「組織を再構築し、技術を刷新し、マネタイズを見直した」と記載（[Bending Spoons F-1](https://www.sec.gov/Archives/edgar/data/0002004711/000110465926071170/tm2613674-7_f1.htm)）。

### Inferences
- 主張した堀は BRAND（カルト的ファン）と SC-DATA（蓄積したノート）。SC-DATA は確かに存在し、買収後の NRR 99% と大幅値上げが通ったことは「残ったユーザーの移行コストが高い」ことの間接証拠。しかし新規獲得の入口は OS 標準ノート（無料）と Notion（コラボ）に奪われ、SC-DATA は「出て行かせない」だけで「入ってこさせる」堀にはならなかった。
- 欠けていた MOAT: DIST（Apple・Microsoft は OS 同梱）、NE-D／ECO（個人ノートはネットワーク効果を持たない。Notion はテンプレート共有とチーム利用で ECO を作った）。
- F コード: 主 F-BUNDLE（Apple Notes・OneNote の無料同梱）、副 F-SINGLE（ノートはコラボ製品の一機能）。F-SELF も相当程度（物販・多機能化・v10 の品質問題）。巨大資本の参入時点（iOS 標準 Notes の強化は 2015 年の iOS 9、OneNote の全面無料化は 2014〜2015 年）を一次資料で特定できておらず、「参入後 5 年以内」の判定は Gaps 参照。
- 代替戦略（同時代）: 2016 年の VentureBeat は「コア体験に集中せよ」、2018 年の Axios は「永久アプリの幻想」と論じた。チーム・コラボへの転換（Evernote Business は 2012 年に開始）は選択肢として存在し、実行したが定着しなかった。

### Gaps
- Apple Notes 強化（iOS 9、2015 年 9 月）と OneNote 無料化（2014 年 3 月に Mac／Windows 無料、2015 年 2 月に全機能無料）の正確な日付・出典は本調査で取得できず、一般知識による。要確認。
- Evernote の売上は非公開企業のため確認できない。有料転換率も未確認。
- 「2.25 億ユーザー」（2016〜2017 年頃の報道値）は確認できず、TechCrunch の「2.5 億超（2018 年）」を採用した。
- Bending Spoons F-1 の 1.94 億ドルが Evernote 単独か（当年の買収が 1 件のみという文脈からの推定）は F-1 が明示していない。

---

## Meerkat vs Periscope / Twitter（失敗）

### Takeaway
Meerkat は 2015 年 2 月末に公開、SXSW で話題となり 3 月 26 日に Greylock 主導で約 1,200〜1,400 万ドルを調達した。しかし Twitter は 3 月 13 日に Meerkat のソーシャルグラフ（フォロワーへの自動通知）へのアクセスを遮断し、同日に Periscope の買収を発表、3 月 26 日に公開した。Meerkat はユーザー約 200 万（2015 年 7 月）で頭打ち、Periscope は 8 月に 1,000 万。Meerkat は 2016 年 10 月 4 日に終了し、同じ会社の Houseparty へ転換した。純粋な F-PLATFORM の典型例。

### Cited Findings
- 開発元: Life On Air, Inc.（2012 年設立、CEO Ben Rubin）。前身アプリ Yevvo（2013 年 8 月）は不発（[productmint: Houseparty](https://productmint.com/what-happened-to-houseparty/)）。Meerkat は 2015 年 2 月末に公開、Product Hunt で注目され 2015 年 3 月の SXSW で多用された（[Wikipedia: Meerkat](https://en.wikipedia.org/wiki/Meerkat_(app))）。
- 自己主張したモデル: 創業者は「Meerkat で起きることはすべて Twitter で起きる」と説明（[Harvard D3 2015-10-05](https://d3.harvard.edu/platform-digit/submission/shut-out-can-meerkat-win-the-mobile-live-streaming-war/index.html)）。Rubin は成功の秘訣を「我々は多くをしなくてよかった（配信は Twitter が担った）」と語った（[VentureBeat](https://venturebeat.com/business/meerkat-ceo-explains-the-secret-to-the-apps-success-we-didnt-have-to-do-a-lot)）。
- プラットフォーム遮断: 2015 年 3 月 13 日（SXSW 初日）、Twitter は Meerkat のソーシャルグラフへのアクセスを制限。Meerkat の配信はフォロワーへの自動通知ができなくなった（Twitter ログインと動画共有は可）。Twitter 広報「社内ポリシーに沿った措置」。同日 Twitter は未公開の Periscope 買収を発表。Rubin は「小さな後退」「革命はライブ配信される」と反応（[VentureBeat 2015-03-13](https://venturebeat.com/business/twitter-cripples-meerkat-by-cutting-off-access-to-its-social-graph)）。Periscope は 3 月 26 日に公開、買収額は約 1 億ドルと報道（[VentureBeat](https://venturebeat.com/technology/meerkat-confirms-14m-raise-as-twitter-launches-competitor-periscope)、[Wikipedia: Twitter, Inc.](https://en.wikipedia.org/wiki/Twitter,_Inc.)）。
- 資金調達: 2015 年 3 月 26 日、Greylock 主導で「約 1,400 万ドル」（Rubin 発言）。1,200 万ドル・評価額 5,200 万ドル（post）とする報道もあり、Greylock は評価額を非公表（[Fortune 2015-03-26](https://fortune.com/2015/03/26/meerkat-funding)、[FinSMEs](https://www.finsmes.com/2015/03/meerkat-closes-12m-series-b-funding.html/)）。
- 資本差: Twitter の 2014 年売上 14.03 億ドル、2015 年 22.18 億ドル（[Wikipedia: Twitter, Inc.](https://en.wikipedia.org/wiki/Twitter,_Inc.)）。Meerkat は売上ゼロ（未収益化）。
- 推移: Meerkat は 2015 年 7 月に約 200 万ユーザーと主張、Periscope は 2015 年 8 月に約 1,000 万アクティブ（[Harvard D3 2015-10-05](https://d3.harvard.edu/platform-digit/submission/shut-out-can-meerkat-win-the-mobile-live-streaming-war/index.html)）。
- 結末: 2016 年 10 月 4 日にアプリ削除・サービス停止。Web は Houseparty へリダイレクト。Houseparty は「公開配信から私的な会話へ」と説明（[Fox Business](https://www.foxbusiness.com/features/streaming-app-meerkat-is-officially-dead)、[Wikipedia: Meerkat](https://en.wikipedia.org/wiki/Meerkat_(app))）。Periscope 自体も 2021 年 3 月 31 日に終了（利用減・保守コスト）（[Wikipedia: Twitter, Inc.](https://en.wikipedia.org/wiki/Twitter,_Inc.)）。
- 同時代の論評: Harvard D3 の分析（2015 年 10 月）は「ライブ配信は強い直接ネットワーク効果を持つが、Periscope は Twitter 連携で優位」とし、選択肢として「広いユーザー層で Periscope と争う」か「Twitch のようにニッチ（ゲーマー等）へ差別化する」を挙げた。コメント欄では Facebook グラフへのマルチホーミングも提案された（[Harvard D3 2015-10-05](https://d3.harvard.edu/platform-digit/submission/shut-out-can-meerkat-win-the-mobile-live-streaming-war/index.html)）。

### Inferences
- 主張した堀: 事実上なし。配信（DIST）を Twitter に全面依存し、自社に NE-D を蓄積する前にグラフを切られた。SPEED（8 週間で 1 人が開発）が唯一の優位。
- 欠けていた MOAT: 自前の DIST／NE-D。
- F コード: 主 F-PLATFORM（教科書的）、副 F-COPY（Periscope は機能的に同等で、Twitter 連携で上回った）。
- 代替戦略: 同時代の論評が挙げたのは「ニッチ特化」と「Facebook グラフへの多重化」。Meerkat は Facebook 連携を追加したが、Facebook 自身が 2015〜2016 年に Facebook Live を展開した。実質的に、巨大プラットフォームの上に配信を依存するモデルでは代替策が乏しかった。「私的な会話」への転換（Houseparty）は当時取れた実際の選択で、次節で扱う。

### Gaps
- Meerkat の正確な評価額（4,000 万〜5,200 万ドル）は報道のみで未確定。
- Twitter の 2015 年時価総額は本調査で確認できず（IPO 時 2013 年 11 月で約 310 億ドルのみ確認）。

---

## Clubhouse vs Twitter Spaces 他（失敗）

### Takeaway
2020 年 3 月公開の招待制音声 SNS。2021 年 2 月に週間アクティブ 1,000 万、同年 4 月に a16z 主導で評価額 40 億ドル（1 月の 10 億ドルから 3 か月で 4 倍）。Twitter は 2020 年 12 月に Spaces をベータ公開し、Facebook・LinkedIn・Spotify・Reddit も追随。Clubhouse の月間ダウンロードは 2021 年 2 月の 960 万から 4 月に約 90 万へ急落、2023 年 4 月に従業員の半数以上を削減。主因は F-COPY（中核機能が巨大 SNS に短期間で模倣され、Clubhouse 側にユーザーの友人グラフが無かった）、副因は F-SINGLE（音声ルームは既存 SNS の一機能に吸収）。Android 版の遅れ（2021 年 5 月）と招待制の長期化は同時代から批判されていた。

### Cited Findings
- 創業・公開: 2019 年秋に Paul Davison と Rohan Seth が Talkshow として開始、2020 年 3 月に iOS で Clubhouse として公開。2020 年 5 月に a16z 主導のシリーズ A 1,200 万ドル（評価額約 1 億ドル）（[Wikipedia: Clubhouse](https://en.wikipedia.org/wiki/Clubhouse_(app))、[CNBC 2023-04-27](https://www.cnbc.com/2023/04/27/clubhouse-layoffs-app-reached-4-billion-valuation-during-pandemic.html)）。
- ピーク: 登録ユーザー 2020 年 12 月約 60 万 → 2021 年 1 月 200 万（WAU）→ 2021 年 2 月 1,000 万 WAU（創業者発表）。累計ダウンロード 2021 年 3 月 1,740 万、6 月 2,910 万、2022 年 6 月 4,120 万（Appfigures・Sensor Tower）（[Wikipedia: Clubhouse](https://en.wikipedia.org/wiki/Clubhouse_(app))、[Business of Apps](https://www.businessofapps.com/?p=64491)、[Appfigures 2021-12](https://appfigures.com/resources/insights/20211210/amp?f=1)）。
- 評価額: 2021 年 1 月に約 10 億ドル（a16z）、2021 年 4 月に 40 億ドル（a16z・DST・Tiger）。累計調達 1 億ドル超。2021 年 4 月に Twitter が約 40 億ドルでの買収を検討（Bloomberg 報道）したが不成立（[CNBC 2023-04-27](https://www.cnbc.com/2023/04/27/clubhouse-layoffs-app-reached-4-billion-valuation-during-pandemic.html)、[SF Standard 2023-04-27](https://sfstandard.com/2023/04/27/whos-listening-once-buzzy-clubhouse-lays-off-half-its-employees)）。
- 巨大資本の参入: Twitter Spaces は 2020 年 11〜12 月にベータ公開（報道により日付が異なる）、2021 年に 600 フォロワー以上へ開放、2021 年 10 月に全ユーザーへ（[Wikipedia: Twitter Spaces](https://en.wikipedia.org/wiki/Twitter_Spaces)、[Business of Apps](https://www.businessofapps.com/?p=64491)）。Facebook Live Audio Rooms・Instagram Live・LinkedIn 音声イベント・Spotify Greenroom（2021 年 6 月）も追随（[Wikipedia: Clubhouse](https://en.wikipedia.org/wiki/Clubhouse_(app))）。
- 資本差: Twitter の 2020 年売上 37.16 億ドル、Meta の 2020 年売上 859.7 億ドル（[Wikipedia: Twitter, Inc.](https://en.wikipedia.org/wiki/Twitter,_Inc.)、[StockAnalysis: META](https://stockanalysis.com/stocks/meta/revenue/)）。Clubhouse は 2021 年 4 月まで売上ゼロ（決済機能のテストは 2021 年 4 月）。
- 参入後の推移: 月間ダウンロードは 2021 年 2 月 960 万 → 4 月約 90 万（Sensor Tower）（[Business Insider India 2021-05](https://www.businessinsider.in/Clubhouse-downloads-are-falling-off-a-cliff-The-app-was-downloaded-only-about-900000-times-in-April-down-from-Februarys-peak-of-9-6-million/articleshow/82377695.cms)）。WAU は 2021 年 2 月末から 3 月初に 21% 減（[Wikipedia: Clubhouse](https://en.wikipedia.org/wiki/Clubhouse_(app))）。Android 版は 2021 年 5 月 9 日（米）・5 月 21 日（世界）、招待制は 2021 年 7 月 21 日に終了（[Wikipedia: Clubhouse](https://en.wikipedia.org/wiki/Clubhouse_(app))）。ダウンロードは 2021 年上半期から 2022 年上半期で 80% 減（Protocol、[SF Standard 2023-04-27](https://sfstandard.com/2023/04/27/whos-listening-once-buzzy-clubhouse-lays-off-half-its-employees)）。
- 結末: 2023 年 4 月 27 日に従業員（約 200 人）の 50% 超を削減。創業者は「世界が再開するにつれ友人を見つけにくくなった」「2021 年末に『あまりに速く成長しすぎた』と認めていた」「滑走路は数年分残っている」と説明（[CNBC 2023-04-27](https://www.cnbc.com/2023/04/27/clubhouse-layoffs-app-reached-4-billion-valuation-during-pandemic.html)、[SF Standard](https://sfstandard.com/2023/04/27/whos-listening-once-buzzy-clubhouse-lays-off-half-its-employees)）。会社は存続しているが規模は縮小。
- 同時代の指摘: Android 版の遅れが「大手に追いつく時間を与えた」（[Voicebot.ai 2021-05](https://voicebot.ai/?p=22755)）。

### Inferences
- 主張した堀: 創業者・投資家の明示的な「堀」発言は本調査で確認できなかった。a16z の投資ロジックは NE-D（音声コミュニティ）と文化的ブランドだったと推定されるが出典不在。
- 欠けていた MOAT: 友人グラフは Twitter・Facebook 側にあり、Clubhouse は連絡先インポートで借りていた。音声ルームは「場」であって「記録」ではなく SC-DATA が生じない。クリエイター収益化（CP／ECO）は 2021 年 4 月以降で、Spaces 側が Ticketed Spaces（2021 年 8 月）で追随した。
- F コード: 主 F-COPY、副 F-SINGLE。自己要因（Android 遅延・招待制・パンデミック需要の反転）も大きく、F-SELF を三次要因として記録する。
- 代替戦略（同時代）: 2021 年 4 月の Twitter からの約 40 億ドル買収提案は、同時代に実在した選択肢。クリエイター収益化と番組化（[Business of Apps](https://www.businessofapps.com/?p=64491)が示唆）も当時から議論されていた。

### Gaps
- Twitter Spaces の正確なベータ公開日（2020 年 11 月か 12 月か）は Wikipedia にも記載がなく、報道が割れている。
- Clubhouse の 2024〜2026 年の状況（ユーザー数・売上・ピボット）は未調査。
- 創業者・a16z の「堀」に関する一次発言を見つけられなかった。

---

## Zynga（Facebook プラットフォーム依存、失敗→後年回復）

### Takeaway
Zynga は 2011 年に売上 11.4 億ドル・平均 DAU 5,700 万で上場（評価額約 70〜90 億ドル）したが、S-1 の時点で「売上・予約・プレイヤーの実質すべてを Facebook 経由で得ている」（四半期ベースで予約の 91〜94%）と開示していた。Facebook は 2010 年のバイラル制限・Credits 強制（30% 手数料）、2012 年 11 月の特別契約終了で Zynga の獲得チャネルと経済性を変え、株価は上場後 1 年で 80% 超下落、2013 年に 18% 削減。モバイル転換の遅れも重なった。その後 10 年かけてモバイル買収で再建し、2022 年 5 月に Take-Two へ 127 億ドルで売却された（IPO 時評価額は上回る）。巨大資本との「競合」ではなく「プラットフォーム供給者の方針変更」で崩れた F-PLATFORM の典型であり、副因は F-TECH（モバイル移行の遅れ）。長期的には「混合」とも読める。

### Cited Findings
- 創業: 2007 年 4 月（Presidio Media、7 月に Zynga へ）。2009 年 4 月に MAU 4,000 万で Facebook 最大のアプリ開発者。FarmVille は 2009 年 8 月に DAU 1,000 万、2010 年 2 月に 8,000 万プレイヤー（[Wikipedia: Zynga](https://en.wikipedia.org/wiki/Zynga)）。
- S-1（2012 年 3 月版）の開示: 2011 年売上 11.401 億ドル、予約 11.555 億ドル、純損失 4.043 億ドル、平均 DAU 5,700 万、平均 MAU 2.33 億。「現在、売上の実質すべては Facebook プラットフォーム経由でゲームにアクセスするプレイヤーから生じている」。四半期ごとの Facebook 経由予約比率は 2011 年各四半期で 93〜94%、2010 年で 91〜93%。Facebook は Credits 額面の 70% を Zynga に送金（30% を保持）。リスク要因「Facebook は利用規約を変更する広範な裁量を持ち、それは我々に不利になりうる」（[Zynga S-1 2012](https://www.sec.gov/Archives/edgar/data/0001439404/000119312512113668/d312579ds1.htm)）。
- 自己主張した強み（S-1）: Facebook 上で次の 15 社合計を超える MAU（AppData）、ポートフォリオ間のクロスプロモーション、1 日 15TB 超のゲームデータに基づく「高度なデータ分析」、「プレイヤーが増えるほどゲームが社会的で楽しくなる」ネットワーク効果（同 S-1）。
- Facebook 側の依存: Facebook の S-1 は 2011 年売上の 12% が Zynga 由来と開示（[Benton/TechCrunch](https://benton.org/headlines/facebook-and-zynga%E2%80%99s-co-dependent-relationship)）。
- 上場と下落: 2011 年 12 月 16 日に 10 ドルで上場（約 10 億ドル調達）、評価額約 70 億ドルとの報道。2 日後に 13% 下落。2012 年 10 月時点で「IPO 以来 80% 超下落」、株価が現金・資産価値を 9% 下回る水準（[netimperative 2011-12-21](https://netimperative.com/2011/12/21/zynga-shares-slide-13-in-second-trading-session)、[PocketGamer.biz 2012-10-08](https://www.pocketgamer.biz/feature/45585/opinion-as-zyngas-stock-falls-through-the-floor-is-the-social-giant-at-risk-of-being-acquired/)、[Wikipedia: Zynga](https://en.wikipedia.org/wiki/Zynga)）。
- プラットフォーム方針変更: 2012 年 11 月に Facebook が Zynga との特別契約を終了、2013 年 3 月 31 日以降は標準プラットフォーム規約へ。2013 年 6 月 3 日に 520 人（約 18%）削減（[Wikipedia: Zynga](https://en.wikipedia.org/wiki/Zynga)）。
- 資本差: Facebook の 2012 年売上 50.9 億ドル（[StockAnalysis: META](https://stockanalysis.com/stocks/meta/revenue/)）に対し Zynga 11.4 億ドル（約 4.5 倍）。ただし Facebook は Zynga の「競合」ではなく「配信・決済プラットフォーム」であり、時価総額ベースでは上場時（2012 年 5 月、約 1,040 億ドル）で 10 倍超。
- 結末: 2022 年 1 月 10 日に Take-Two が 1 株 9.86 ドル・総額 127 億ドルで買収発表、5 月 23 日完了（[Wikipedia: Zynga](https://en.wikipedia.org/wiki/Zynga)、[Houston Chronicle 2022-01-11](https://www.pressreader.com/usa/houston-chronicle/20220111/281908776499932)）。

### Inferences
- 主張した堀は NE-D（友人とのプレイ）、NE-DATA（15TB/日の分析）、SCALE（クロスプロモーション）。いずれも Facebook のグラフと通知チャネルの上に成立しており、Facebook がバイラル通知を制限した時点で NE-D とクロスプロモは機能を失った。NE-DATA は残ったが、ユーザー獲得チャネルを代替できなかった。
- 欠けていた MOAT: 自前の DIST。モバイル（App Store・Google Play）への移行は別のプラットフォーム依存だが、少なくとも Facebook 単一依存を解いた。
- F コード: 主 F-PLATFORM、副 F-TECH（モバイルシフト）。巨大資本が「競合製品」を出したわけではないため、本枠組みの「巨大資本の参入」の定義には注意が必要。Facebook は Zynga の売上の 30% を手数料として取る供給者であり、F-PLATFORM の原型として採用した。
- 結末の評価: 2011 年 IPO 評価額（約 70〜90 億ドル）に対し 2022 年の売却額 127 億ドルは上回る。ただし 2012〜2016 年の 5 年間で株価は 1/5 以下になり DAU も大幅減少したため、事前登録の失敗定義（参入後 5 年以内のシェア喪失・評価額の大幅下落）は満たす。10 年後の回復は「失敗後の再建」として別途記録する。
- 代替戦略（同時代）: S-1 は依存リスクを自認し「Zynga.com（自社プラットフォーム、2012 年 3 月開始）」とモバイルを戦略に掲げていた。つまり代替策は当時から認識されていたが、Zynga.com は定着せず、モバイルは 2013〜2015 年の買収（NaturalMotion 等）を経てようやく主力になった。

### Gaps
- 2012 年の株価底値（約 2.1 ドル、2012 年 10〜11 月とされる）と上場時の正確な評価額（70 億 vs 90 億ドル）は一次資料で確認できなかった。
- 2012〜2013 年の年次売上・Facebook 経由比率（10-K）は未取得。
- Zynga.com の利用実績は未調査。

---

## Vine vs Instagram Video（失敗）

### Takeaway
Vine は 2012 年 6 月に創業、公開前の 2012 年 10 月に Twitter が約 3,000 万ドルで買収し、2013 年 1 月公開。6 秒ループ動画で急成長し、2015 年 12 月時点で「2 億アクティブユーザー超」と称した。Facebook 傘下の Instagram は 2013 年 6 月 20 日に 15 秒動画を追加し、Twitter 上の Vine リンク共有は翌日に約 40%、1 週間で約 70% 減少（Topsy、ただし計測に異論あり）。Twitter は収益化を実装せず、2016 年前半にフォロワー 1.5 万人超のクリエイターの半数以上が投稿停止・離脱、2016 年 10 月 27 日に終了を発表、2017 年 1 月 17 日に閉鎖。主因は F-COPY（中核機能を Instagram が模倣、Vine 側にクリエイター囲い込みの収益分配がなかった）、副因は F-ECON（収益モデル不在）／F-SELF（親会社 Twitter の優先度低下）。

### Cited Findings
- 創業・買収: 2012 年 6 月に Rus Yusupov・Dom Hofmann・Colin Kroll が創業、2012 年 10 月に Twitter が約 3,000 万ドルで買収、2013 年 1 月 24 日 iOS 公開、6 月 2 日 Android（[Wikipedia: Vine](https://en.wikipedia.org/wiki/Vine_(service))、[Slidebean](https://slidebean.com/story/what-happened-to-vine)）。
- ピーク: 2015 年 12 月時点で 2 億アクティブユーザー超（Twitter 発表、[Wikipedia: Vine](https://en.wikipedia.org/wiki/Vine_(service))。2014 年に 2 億とする資料もあり [productmint](https://productmint.com/what-happened-to-vine/)）。
- 巨大資本の参入: Instagram は 2013 年 6 月 20 日に 15 秒動画を追加。Topsy のデータで Vine リンクの Twitter 共有は 6 月 19 日の約 250 万から 20 日に約 150 万（約 40% 減）、6 月 15 日の約 300 万から 1 週間後に 90 万未満（約 70% 減）。ただし Topsy は後に「正確なカウント」に基づく別のグラフを公表し、直前の Android 公開によるスパイクの反動も含まれるとされた（[MarTech 2013-06](https://martech.org/a-week-after-instagrams-video-launch-vine-sharing-tanks-on-twitter)、[AppAdvice 2013-06](https://appadvice.com/appnn/2013/06/following-instagram-video-twitter-powered-vine-shares-drop)）。
- 資本差: Facebook の 2013 年売上 78.7 億ドル、Twitter の 2013 年売上 6.65 億ドル（約 12 倍）（[StockAnalysis: META](https://stockanalysis.com/stocks/meta/revenue/)、[Wikipedia: Twitter, Inc.](https://en.wikipedia.org/wiki/Twitter,_Inc.)）。Vine 単体は売上ゼロ。
- 収益化の不在とクリエイター離脱: Twitter はスポンサードコンテンツ・広告を検討したが実装せず、2016 年にトップクリエイターが報酬を求めた際に分配できる収益がなかった。2016 年 1〜6 月に 1.5 万フォロワー超のユーザーの半数以上が投稿停止または退会し、YouTube・Instagram・Snapchat へ移った（[Slidebean](https://slidebean.com/story/what-happened-to-vine)、[Wikipedia: Vine](https://en.wikipedia.org/wiki/Vine_(service))、[bad.technology 2016-10-27](https://bad.technology/articles/twitter-kills-vine-200-million-user-video-platform-shut-down-in-three-months-notice.html)）。
- 結末: 2016 年 10 月 27 日に投稿終了を発表（約 90 日前通知）、2017 年 1 月 17 日に閉鎖し「Vine Camera」へ。アーカイブは 2018 年 4 月に終了（[Wikipedia: Vine](https://en.wikipedia.org/wiki/Vine_(service))）。Twitter は 2015 年に 300 人超を削減するなど自社の業績悪化（2016 年純損失 4.57 億ドル）にあった（[Slidebean](https://slidebean.com/story/what-happened-to-vine)、[Wikipedia: Twitter, Inc.](https://en.wikipedia.org/wiki/Twitter,_Inc.)）。

### Inferences
- 主張した堀: 独自フォーマット（6 秒ループ）とクリエイター文化（BRAND／ECO）。公式の「堀」主張は買収子会社のため少ない。
- 欠けていた MOAT: 供給側（クリエイター）を留める CP／ECO（収益分配）。Instagram は 2013 年に機能を模倣し、YouTube は収益分配を持っていた。Vine のクリエイターは「他へ移っても失うものがない」状態で、F-SUPPLY 的側面（供給側の流出）が強く出た。
- F コード: 主 F-COPY、副 F-ECON（収益化なし）。親会社 Twitter の資源配分（F-SELF）も無視できない。
- 代替戦略（同時代）: 2016 年のクリエイター側からの収益分配要求は、実行可能だった選択肢（YouTube パートナープログラムは既存）。Twitter の財務状況が障害だった。

### Gaps
- 2016 年のクリエイター会合（約 20 人が各 120 万ドルを要求したとされる Mic 報道）は一次ソースを取得できず未確認。
- Vine の MAU の年次推移（2014〜2016）は Twitter が開示しておらず、2 億という数字の定義（登録か月間か）も不明。

---

## Quibi（失敗、F-SELF 寄りの境界例）

### Takeaway
Quibi は 2018 年 8 月設立、2020 年 4 月 6 日に公開するまでに 17.5 億ドル（Disney・NBCU・Sony・WarnerMedia・Goldman・JPM 等）を集め、10 分以下の有料モバイル専用ショート動画を 10 億ドル超のコンテンツ費で用意した。初週 170 万ダウンロードの後、1 週間で無料アプリ上位 50 から脱落、初年度 740 万加入の計画に対し 6 月時点で約 200 万ペース、10 月 21 日に閉鎖を発表（加入者約 50 万）、12 月 1 日前後に終了。コンテンツは 2021 年 1 月に Roku が 1 億ドル未満で取得。巨大資本（YouTube・TikTok・Netflix）の「参入」があったわけではなく、無料で豊富な短尺動画が既に存在する市場に有料で後発参入した自滅であり、主 F-SELF・副 F-ECON。事前登録の定義では**母集団外**（巨大資本の参入による喪失ではない）だが、依頼により記録する。

### Cited Findings
- 設立・資金: 2018 年 8 月に NewTV として Katzenberg が設立、Whitman が CEO。2018 年に約 10 億ドル、2020 年 1〜6 月に追加 7.5 億ドル、累計 17.5 億ドル（[Wikipedia: Quibi](https://en.wikipedia.org/wiki/Quibi)、[Front Office Sports](https://frontofficesports.com/quibi-comes-to-a-close)）。
- 公開と初動: 2020 年 4 月 6 日に米加で公開。初日 30 万、初週 170 万ダウンロード。Sensor Tower は 5 月初時点 290 万インストール、Quibi は約 350 万・アクティブ 130 万と主張。1 週間以内に無料 iPhone アプリ上位 50 から脱落、5 月初に 125 位（[Wikipedia: Quibi](https://en.wikipedia.org/wiki/Quibi)）。
- 計画と実績: 初年度 740 万加入の計画に対し、2020 年 6 月時点で約 200 万ペース。7 月に Sensor Tower は無料トライアルからの有料転換を約 8% と推計（Antenna は 27%）、Quibi は否定（同）。
- 創業者の説明: Katzenberg は「うまくいかなかったことはすべてコロナのせいだと思う……だが責任は我々にある」と NYT に語った。閉鎖書簡では「アイデア自体が独立サービスを正当化するほど強くなかったか、タイミングか。おそらく両方」と述べた（[Hollywood Reporter 2020-10](https://www.hollywoodreporter.com/news/quibi-to-shut-down-six-months-after-launch)、[Looper](https://www.looper.com/265764/the-real-reason-quibi-is-shutting-down)）。
- 同時代の批判: 「無料の短尺動画がネットに溢れている中で 90 日無料でも届かなかった」「在宅ではスマホよりテレビが望まれたが、テレビ対応は遅く緩慢だった」（[Yahoo/Front Office Sports](https://au.news.yahoo.com/quibi-shuts-down-why-the-175-billion-streaming-app-failed-104534579.html)、[Looper](https://www.looper.com/265764/the-real-reason-quibi-is-shutting-down)）。
- 結末: 2020 年 10 月 21 日に WSJ が閉鎖を報道し同日確認、加入者約 50 万。12 月 1 日前後に終了。2021 年 1 月に Roku が 75 番組超の権利を 1 億ドル未満で取得（短尺維持が条件）。Quibi は番組の著作権を保有していなかった（[Wikipedia: Quibi](https://en.wikipedia.org/wiki/Quibi)、[ABC News/Roku](https://abcnews4.com/news/nation-world/roku-buys-library-of-the-short-lived-streaming-service-quibi)）。

### Inferences
- 主張した堀: ハリウッドのスター・プロデューサーとの関係（CR）、Turnstyle（縦横切替）技術、モバイル専用プレミアム（BRAND）。CR は「番組の著作権を保持しない」契約で堀にならず、Turnstyle は Eko との特許訴訟の対象になった。
- 欠けていた MOAT: ほぼすべて。NE・SC・DIST・ECO のいずれも設計に含まれない。
- F コード: 主 F-SELF（市場の読み違い・有料モデル）、副 F-ECON（コンテンツ費 10 億ドルに対し加入 50 万）。巨大資本の「参入」はなく、既存の無料供給（YouTube・TikTok）が市場を先取りしていた。
- 代替戦略（同時代）: 「無料・広告型」「テレビ対応」「シェア機能（スクリーンショット可）」は公開直後から求められ、2020 年 8〜10 月に部分的に実装したが遅かった。
- 母集団への扱い: 事前登録の「巨大資本の参入後 5 年以内」に該当しないため、集計表では F-SELF として「参照」扱いにする。

### Gaps
- 有料加入者「約 50 万」は WSJ 報道値で、Quibi は公式に開示していない。
- 月額料金（広告付き 4.99 ドル／広告なし 7.99 ドルと報道）は本調査で一次確認できず。

---

## Pebble vs Apple Watch（失敗）

### Takeaway
Pebble は 2012 年 4 月に Kickstarter で 1,027 万ドルを集めてスマートウォッチ市場を事実上定義し、2015 年 3 月の Pebble Time でも 2,034 万ドルを集めた（当時の Kickstarter 最高額）。累計約 200 万台・売上約 2.3 億ドル（2013 年 3,000 万、2014 年 6,000 万、2015 年 8,200 万ドル）。Apple は 2015 年 4 月に Apple Watch を発売し、Pebble は 2015 年に粗利率が 35% から 27% へ低下、在庫 1,500 万ドル超、2016 年 3 月に 25% 削減、2016 年 12 月 6 日に破産申請してソフトウェア・知財を Fitbit へ約 2,300 万ドルで売却。創業者 Migicovsky 自身の post-mortem は「市場の読み違い（生産性→フィットネスへの転換の遅れ）」「需要予測の失敗と在庫」「製品定義の曖昧さ」を主因とし、Apple の参入はそれを決定的にした。主 F-COPY（巨大資本が同カテゴリに参入し、Pebble の差別化＝通知・電池寿命・開発者コミュニティが価格差を正当化できなかった）、副 F-ECON（ハードウェアの在庫・粗利）。

### Cited Findings
- 創業・Kickstarter: YC W11 出身。2012 年 4 月 11 日に Kickstarter 開始、2 時間で 10 万ドル達成、5 月 18 日終了時に 68,929 人から 10,266,845 ドル。初出荷 2013 年 1 月 23 日（[Wikipedia: Pebble](https://en.wikipedia.org/wiki/Pebble_(watch))、[Migicovsky blog 2022-04-11](https://ericmigi.com/blog/success-and-failure-at-pebble)）。
- 販売・売上（創業者開示）: 累計約 200 万台・2.3 億ドル超（約 4 年）。売上 2013 年約 3,000 万ドル（純利益 900 万ドル）、2014 年約 6,000 万ドル（概ね損益分岐）、2015 年 8,200 万ドル（目標 1 億ドル）。2015 年は売上 +35% だが粗利率 35%→27%、営業費用倍増、年末在庫 1,500 万ドル超（[Migicovsky blog](https://ericmigi.com/blog/success-and-failure-at-pebble)）。販売台数は 2013 年 12 月 30 万、2014 年 12 月末 100 万（[Wikipedia: Pebble](https://en.wikipedia.org/wiki/Pebble_(watch))）。
- Pebble Time: 2015 年 2 月 24 日に Kickstarter 開始、17 分で 50 万ドル、3 月 27 日終了時に 78,471 人から 20,338,986 ドル（[Wikipedia: Pebble](https://en.wikipedia.org/wiki/Pebble_(watch))）。
- 巨大資本の参入: Apple Watch は 2015 年 4 月発売（Fitbit 10-K 2015 年度「Apple は 2015 年に Apple Watch を発表し、相当量を販売した」）（[Fitbit 10-K FY2015](https://www.sec.gov/Archives/edgar/data/1447599/000144759916000018/fitbit1231201510k.htm)）。Migicovsky は Apple が当初「最も正確な時計」「17,000 ドルの金モデル」と高級路線で訴求し、スポーツ・フィットネスへ転換するのに約 2 年かかったと述べる（[Migicovsky blog](https://ericmigi.com/blog/success-and-failure-at-pebble)）。
- 資本差: Apple の FY2015 売上は 2,337 億ドル（一般知識、本調査では未確認。Gaps 参照）。Pebble の 2015 年売上 8,200 万ドルに対し 1,000 倍超。
- 自己主張した強み: Migicovsky は「スマートウォッチが何をすべきかを Pebble が定義した」「ウォッチフェイス・アプリ・アクセサリの熱心なコミュニティ（アクセサリの Kickstarter 19 件）」を挙げるが、「堀」という枠では語っていない。同僚 Andrew Witte は「初代が成功した理由をチームが理解していなかった」と評した（[Migicovsky blog](https://ericmigi.com/blog/success-and-failure-at-pebble)）。
- 失敗要因（創業者本人）: 小売の需要予測失敗と在庫、ギーク向け→生産性→フィットネスと訴求を変えて顧客を混乱させたこと（「我々はフィットネス企業ではなかった」）、Pebble Time のベゼルが大きいと知りつつ変更する勇気がなかったこと、成長への過剰支出、「人が欲しがると期待した定義の曖昧な製品を作っていた」「長期ビジョンの定義が下手だった」（[Migicovsky blog](https://ericmigi.com/blog/success-and-failure-at-pebble)）。
- 結末: 2016 年 3 月に 160 人中 40 人（25%）削減。2016 年 12 月 6 日に破産申請し、ソフトウェア・知財等を Fitbit に売却。当初 3,400 万〜4,000 万ドルと報道されたが、後に Fitbit が 2,300 万ドルを支払ったと報告。ハードウェア・在庫・サーバー・負債は対象外。Fitbit は 2018 年 6 月 30 日に Pebble サーバーを停止（[Wikipedia: Pebble](https://en.wikipedia.org/wiki/Pebble_(watch))、[Wikipedia: Fitbit](https://en.wikipedia.org/wiki/Fitbit)）。
- 後日談: 2025 年 1 月に Google が PebbleOS をオープンソース化、Migicovsky が Core Devices を設立し 2025 年 7 月に Pebble 商標を回復（[Wikipedia: Pebble](https://en.wikipedia.org/wiki/Pebble_(watch))）。

### Inferences
- 主張した堀は BRAND（カテゴリ創出者）と ECO（開発者・ウォッチフェイス）。ECO は Apple の watchOS エコシステム（iPhone 開発者をそのまま取り込める）と比べ桁違いに小さかった。
- 欠けていた MOAT: DIST（Apple は iPhone 同梱の配布網・Apple Store を持つ）、SCALE（部品調達・在庫リスク）。Pebble の「電池 1 週間・両 OS 対応・低価格」は CP の芽だったが、Apple が追随する必要のない差分（Apple は iPhone ユーザーのみで足りた）だったため CP として機能しなかった。
- F コード: 主 F-COPY（同カテゴリ参入で差分が消失）、副 F-ECON（在庫・粗利）。創業者自身は自己要因を強調しており F-SELF 要素も大きい。
- 代替戦略（同時代）: 2015 年に社内からフィットネス特化を求められていた（創業者が抵抗）。「ハッカー向けスマートウォッチ」のニッチ維持は創業者が後悔として挙げる。2015〜2016 年に Citizen（約 7.4 億ドル）・Intel（約 7,000 万ドル）からの買収提案があったとする Backchannel 報道は取得できず未確認（Gaps）。

### Gaps
- Backchannel（2016 年 12 月）の買収提案額（Citizen 7.4 億ドル、Intel 7,000 万ドル）は 403 で取得できず、未確認。
- Apple の売上・Apple Watch の 2015 年販売台数は本調査で一次確認できなかった。
- 2016 年の売上は未開示。

---

## Houseparty（失敗）

### Takeaway
Meerkat の転換先として 2016 年 2 月に公開されたグループビデオチャット。2016 年 12 月に Sequoia 主導で 5,200 万ドル調達、2017 年末に累計 2,000 万ダウンロード。Facebook は 2017 年 10 月に類似アプリ Bonfire をテストし（本調査では一次確認できず）、Houseparty は 2019 年 6 月に Epic Games へ約 3,500 万ドル（報道）で売却された。パンデミック初期の 2020 年 3 月に 1 か月で 5,000 万サインアップと急伸したが、Facebook は 2020 年 4 月 24 日に Messenger Rooms（50 人・時間無制限・アカウント不要）を公開し、制限解除後に利用は減少、Epic は 2021 年 9 月 9 日に終了を発表し 10 月に閉鎖。主 F-COPY（Messenger Rooms 等による機能模倣と既存グラフ）、副 F-SINGLE（ビデオ通話は Messenger・FaceTime・Zoom の一機能）。

### Cited Findings
- 開発元・経緯: Life On Air（Meerkat 開発元）。Meerkat 停滞後の 2015 年に開発開始、2016 年 2 月に仮名で公開、2016 年 5 月に App Store 2 位、夏に負荷で成長停止、2016 年 9 月に正式発表・累計 100 万ダウンロード、2016 年 12 月に Sequoia 主導で 5,200 万ドル。2017 年末に 2,000 万ダウンロード超（[productmint: Houseparty](https://productmint.com/what-happened-to-houseparty/)、[Wikipedia: Houseparty](https://en.wikipedia.org/wiki/Houseparty_(app))）。
- 売却: 2019 年 3 月に Sima Sistani が CEO、2019 年 6 月に Epic Games が買収（条件非公表、約 3,500 万ドルと報道）（[TechCrunch 2021](https://techcrunch.com/?p=2200062)、[productmint](https://productmint.com/what-happened-to-houseparty/)）。
- ピーク: 2020 年 3 月に 1 か月で 5,000 万サインアップ、一部市場で通常の 70 倍、80 か国超で SNS カテゴリ 1 位。同月 1,700 万ダウンロード。ハッキング噂で 100 万人超が離脱したとの報道、Epic は否定し 100 万ドルの懸賞（[TechSpot 2020-04](https://www.techspot.com/news/84837-houseparty-added-50-million-new-users-past-month.html)、[SiliconANGLE 2020-04-15](https://siliconangle.com/2020/04/15/houseparty-adds-50-million-new-sign-ups-coronavirus-pandemic/)、[Wikipedia: Houseparty](https://en.wikipedia.org/wiki/Houseparty_(app))）。
- 巨大資本の参入: Facebook は 2020 年 4 月 24 日に Messenger Rooms を発表（最大 50 人、時間無制限、Facebook アカウント不要）。報道は「Zoom と Houseparty に対抗」と位置付けた（[Meta Newsroom 2020-04-24](https://about.fb.com/news/2020/04/introducing-messenger-rooms/)、[iClarified](https://www.iclarified.com/75558/facebook-launches-messenger-rooms-to-take-on-zoom-and-houseparty/comments)）。Messenger Rooms 自体も現在は終了（同 Meta ページ注記）。
- 資本差: Meta の 2020 年売上 859.7 億ドル（[StockAnalysis: META](https://stockanalysis.com/stocks/meta/revenue/)）。Houseparty は 2019 年にゲーム内課金で収益化を始めたばかり（[productmint](https://productmint.com/what-happened-to-houseparty/)）。
- 結末: 2020 年 11 月に Fortnite 連携、2021 年 4 月に Fortnite 配信機能。2021 年 9 月 9 日に Epic が終了を発表、10 月に閉鎖。Epic は「メタバース規模の社会的体験に取り組む」と説明。報道は「制限解除後に利用が大幅減少」を理由として挙げた（[Wikipedia: Houseparty](https://en.wikipedia.org/wiki/Houseparty_(app))、[PC Gamer](https://www.pcgamer.com/epic-is-closing-its-houseparty-video-chat-service)）。

### Inferences
- 主張した堀: NE-D（友人グループ）と「偶発的な集まり（in the house 通知）」という UX。ただし友人グラフは電話帳と Snapchat・Facebook 由来で、Houseparty 固有ではなかった。
- 欠けていた MOAT: DIST（Messenger・FaceTime は既にインストール済み）、SC-*（通話に記録はない）。
- F コード: 主 F-COPY、副 F-SINGLE。パンデミック需要の反転（F-SELF 的外生要因）も大きい。
- 代替戦略（同時代）: Epic への売却（2019 年）はピーク前に実行された「出口」。2020 年のピーク時に大手へ再売却する選択肢は理論上あったが、既に Epic 傘下だった。

### Gaps
- Facebook Bonfire（2017 年 10 月テスト）は本調査で一次確認できず、記述は分析者の記憶に基づく。要確認。
- Epic の買収額 3,500 万ドルは報道値（Bloomberg とされる）で未確認。
- 2021 年の利用者数は非開示。

---

## Foursquare vs Facebook Places（混合→企業向けへ転換）

### Takeaway
Foursquare は 2009 年 3 月の SXSW で公開、2010 年 4 月に 100 万ユーザー、2011 年 6 月に評価額 6 億ドル。Facebook は 2010 年 8 月に Places（チェックイン）を開始し、Crowley は「我々はまだ位置情報のプラットフォームだ」と応じたが、2013 年にユーザー成長が停止し売上が計画を下回り、2014 年にチェックインを Swarm へ分離、2016 年 1 月に評価額 2.5 億ドル（2013 年の半分以下）で 4,500 万ドルのダウンラウンド。その後、消費者アプリから位置データ・SDK（Pilgrim）の企業向け事業へ転換し、2019 年に売上 1.5 億ドル超、Factual・Placed と合併、2024 年 12 月に City Guide を終了。消費者向けチェックインとしては F-COPY／F-SINGLE で敗れたが、企業として存続・成長しており「混合」。

### Cited Findings
- 創業・初期: Dennis Crowley（前身 Dodgeball は 2005 年に Google が買収）と Naveen Selvadurai が 2008 年末に開発、2009 年 3 月 11 日公開。2009 年 9 月にシード 135 万ドル、2010 年 4 月に 100 万ユーザー、2010 年 6 月に a16z 主導でシリーズ B 2,000 万ドル、2010 年 12 月に約 1.4 億ドルの買収提案（Yahoo・Facebook・Microsoft と報道）を拒否（[Built In](https://builtin.com/articles/history-foursquare-checking-company-just-raised-45m-down-round)、[Slidebean](https://slidebean.com/story/what-happened-to-foursquare)、[Wikipedia: Foursquare City Guide](https://en.wikipedia.org/wiki/Foursquare_City_Guide)）。
- 巨大資本の参入: Facebook Places は 2010 年 8 月に米国から段階展開、パートナーに Gowalla・Foursquare・Yelp・Booyah。Crowley は「Foursquare はチェックイン・近隣推薦・ゲーム的仕組みを持つ位置情報プラットフォームであり続ける」「再設計と新機能の後で Facebook 連携に取り組む」とし、公開後「4 日連続で過去最大の利用、300 万に迫る」と述べた（[BGR 2010-08](https://www.bgr.com/general/foursquare-ceo-responds-to-facebooks-launch-of-places)、[TechRadar 2010-08](https://techradar.com/news/internet/foursquare-responds-to-facebook-places-threat-711373)）。Facebook は 1 年後に Places を独立機能として終了し位置情報を全体に組み込んだ（[TechCrunch 2011-08](https://techcrunch.com/?p=410375)）。
- 資本差: Facebook の 2010 年売上 19.7 億ドル（[StockAnalysis: META](https://stockanalysis.com/stocks/meta/revenue/)）。Foursquare の 2012 年売上は約 200 万ドル（[Slidebean](https://slidebean.com/story/what-happened-to-foursquare)）。
- ピークと停滞: 2011 年 6 月にシリーズ C 5,000 万ドル・評価額 6 億ドル。2011 年 6 月に累計チェックイン 7.5 億・1 日約 300 万。2012 年に 7.6 億ドル評価とする資料もある。2013 年 4 月にユーザー成長停止・売上減少、2013 年 12 月にシリーズ D 3,500 万ドル（約 4,500 万ユーザー）（[Built In](https://builtin.com/articles/history-foursquare-checking-company-just-raised-45m-down-round)、[review42](https://resources.review42.com/foursquare-statistics/)、[Wikipedia: Foursquare City Guide](https://en.wikipedia.org/wiki/Foursquare_City_Guide)）。
- 分割と転換: 2014 年 5 月に Swarm を公開、7 月末に本体からチェックインを除去、8 月 7 日に Foursquare 8.0（ローカル検索）。2016 年 1 月に USV 主導で 4,500 万ドル・評価額 2.5 億ドル（2013 年の半分以下）。Crowley は 2016 年に CEO を退き Jeff Glueck へ（[Built In](https://builtin.com/articles/history-foursquare-checking-company-just-raised-45m-down-round)、[Slidebean](https://slidebean.com/story/what-happened-to-foursquare)）。
- 企業向け事業: Pilgrim SDK（2018 年に約 2,500 万人が常時位置共有、2019 年に 15 万開発者）、2019 年売上 1.5 億ドル超、2020 年 Q4 に初の黒字四半期。Factual・Placed と合併（Slidebean は 2019 年、報道では 2020 年 4 月）。2024 年 10 月 21 日に City Guide 終了を発表、12 月 15 日にアプリ終了、2025 年 4 月 28 日に Web 終了。Swarm のみ消費者向けに残る（[Slidebean](https://slidebean.com/story/what-happened-to-foursquare)、[Wikipedia: Foursquare City Guide](https://en.wikipedia.org/wiki/Foursquare_City_Guide)）。

### Inferences
- 主張した堀: NE-D（友人のチェックイン）とゲーム的仕組み（メイヤー・バッジ）、後に NE-DATA（場所データ）。NE-D は Facebook のグラフの方が圧倒的に大きく、チェックインは Facebook の一機能になった。
- 実際に残ったのは NE-DATA／CR（6,000 万件の場所データベースとチェックインから学習した位置検出）で、企業向けに転用できた。これは「消費者向けでは堀にならなかったが、別の顧客には堀になった」例。
- F コード: 主 F-COPY（チェックインの模倣）、副 F-SINGLE（位置共有は SNS の一機能）。
- 代替戦略（同時代）: 2010 年の買収提案（1.4 億ドル）拒否は同時代の選択。Facebook 連携（マルチホーミング）は実行した。「データ企業への転換」は 2014 年以降に実行され、結果として存続につながった。

### Gaps
- Factual 合併の正確な時期（2019 年 vs 2020 年 4 月）と合併後の評価額は未確認。
- 2011〜2013 年の MAU 時系列と 2013 年の評価額（6.5 億ドルとする資料）は出典が弱い。

---

## 追加事例 1: Fitbit vs Apple Watch（失敗）

### Takeaway
Fitbit は 2007 年創業、2015 年 6 月に IPO（7.32 億ドル調達）し、同年に時価総額は約 100 億ドル近くまで上昇、2016 年売上約 22 億ドル（+17%）。10-K は「市場リーダーの地位と世界的ブランド」「大きく成長するコミュニティと強いネットワーク効果」「5 万店超の小売網」「オープン API」を強みに挙げ、競合リスクとして「Apple は 2015 年に Apple Watch を発表し相当量を販売した」と記した。2017 年以降売上は 3 年連続で減少（2019 年は前年比 −5%、純損失 3.207 億ドル）、Ionic（2017 年）・Versa（2018 年）で追随したが、2019 年 11 月 1 日に Google へ 1 株 7.35 ドル・約 21 億ドルで売却（ピーク時価総額の約 1/5）、2021 年 1 月 14 日完了。主 F-COPY（Apple が上位カテゴリで参入し、トラッカーの差分が消失）、副 F-ECON（ハードウェア単発販売のヒット依存）。

### Cited Findings
- 創業: 2007 年 3 月 26 日に James Park・Eric Friedman が Healthy Metrics Research として設立、同年 10 月に Fitbit へ改称（[Wikipedia: Fitbit](https://en.wikipedia.org/wiki/Fitbit)）。
- IPO とピーク: 2015 年 6 月に 20 ドルで IPO、7.32 億ドル調達。上場後に時価総額は「100 億ドル近く」まで上昇（2015 年 12 月時点では 64 億ドルとする資料もあり時点依存）（[Wareable](https://www.wareable.com/fitbit/youre-fitbit-and-you-know-it-how-a-wooden-box-became-a-dollar-4-billion-company)、[Yahoo Finance 2019](https://au.finance.yahoo.com/news/dont-forget-about-this-in-googles-21-billion-deal-for-fibit-160507239.html)）。
- 10-K（2015 年度）の自己主張: 「市場リーダーの地位と世界的ブランド（Fitbit はカテゴリの同義語）」「大きく成長するコミュニティと強いネットワーク効果」「63 か国 5 万店超の小売」「200 機種超との互換性とオープン API」。「市場シェア首位」と記すが数値は示していない。リスク要因「Apple は 2015 年に Apple Watch を発表し、発売以来相当量を販売した」。他に Garmin・Jawbone・Misfit・Xiaomi（[Fitbit 10-K FY2015](https://www.sec.gov/Archives/edgar/data/1447599/000144759916000018/fitbit1231201510k.htm)）。
- 業績推移: 2016 年売上約 22 億ドル（+17%）。2017・2018 年は前年比減、2019 年は −5%。純損失 2017 年 2.772 億、2018 年 1.858 億、2019 年 3.207 億ドル。累計 1 億台超、アクティブユーザー 2,800 万以上（2019 年）（[Fitbit 10-K FY2019](https://www.sec.gov/Archives/edgar/data/1447599/000144759920000016/fit-20191231.htm)、[MedTech Dive 2019-11-01](https://www.medtechdive.com/news/google-to-acquire-fitbit-in-21b-deal-challenging-apple/566438)）。2019 年の出荷台数は世界 5 位（[Wikipedia: Fitbit](https://en.wikipedia.org/wiki/Fitbit)）。
- 対応: 2016 年 12 月に Pebble の資産を 2,300 万ドルで取得、2017 年に Ionic、2018 年に低価格の Versa を投入（[Wikipedia: Fitbit](https://en.wikipedia.org/wiki/Fitbit)）。
- 結末: 2019 年 11 月 1 日に Google が 1 株 7.35 ドル・約 21 億ドルで買収合意（発表前の時価総額約 16 億ドル）、株主承認 2020 年 1 月 3 日、完了 2021 年 1 月 14 日（[Fitbit 10-K FY2019](https://www.sec.gov/Archives/edgar/data/1447599/000144759920000016/fit-20191231.htm)、[PBS 2019-11-01](https://www.pbs.org/newshour/amp/nation/google-buys-fitbit-for-2-1-billion)、[Yahoo Finance 2019](https://au.finance.yahoo.com/news/dont-forget-about-this-in-googles-21-billion-deal-for-fibit-160507239.html)）。
- 資本差: Apple の FY2015 売上約 2,337 億ドル（一般知識・未確認）に対し Fitbit 2015 年売上約 18.6 億ドル（一般知識・未確認、10-K 本文の該当箇所は取得範囲外）。100 倍超。

### Inferences
- 主張した堀は BRAND・NE-D（友人との歩数競争）・DIST（小売網）。NE-D は Apple Watch の「アクティビティ共有」で模倣可能で、BRAND は「カテゴリの同義語」であることが「トラッカー＝低価格帯」という位置づけに固定される逆効果もあった。小売網は Apple Store と iPhone の抱き合わせ販促に対して優位にならなかった。
- 欠けていた MOAT: ECO（watchOS のアプリ開発者）、SC-DATA（健康データは Apple Health に集約されやすい）、SCALE（Apple の部品調達力）。
- F コード: 主 F-COPY（上位カテゴリからの参入で差分消失）、副 F-ECON（単発ハードのヒット依存、2017 年以降赤字）。
- 代替戦略（同時代）: 2016〜2017 年に「スマートウォッチへ移行」（実行、Ionic・Versa）と「ヘルスケア・企業向けサービス（Fitbit Health Solutions）」（実行）が議論された。いずれも実行したが Apple の速度に追いつかなかった。

### Gaps
- 年次売上（2014〜2019）の正確な金額と IDC の年次シェア（2015 年首位 → 2017 年 Apple 首位）は、10-K の該当箇所が取得範囲外・IDC 報道が検索上限で未取得。要確認。
- ピーク時価総額の正確な日付・金額（2015 年 8 月に約 100 億ドル超とされる）は未確認。

---

## 追加事例 2: Jasper vs ChatGPT（生成 AI 期、失敗寄りの進行中事例）

### Takeaway
Jasper（旧 Jarvis／Conversion.ai、2021 年創業）は GPT-3 の上に UX とテンプレートを載せたマーケティング文章生成で、初年度 ARR 4,250 万ドル、2022 年に売上約 7,500 万〜8,000 万ドル、2022 年 10 月に 1.25 億ドル調達・評価額 15 億ドル。OpenAI が 2022 年 11 月 30 日に ChatGPT を無料公開すると、2023 年 1 月時点の ARR 計画（2023 年末 1.4 億ドル）は夏に 30% 以上下方修正、7 月に人員削減、9 月に社内評価額を 20% 切り下げ（約 12 億ドル）、CEO 交代（Timothy Young）。中堅・大企業のマーケティング部門向けへ転換して存続。主 F-COPY／F-PLATFORM の複合（依存していたモデル供給者自身が、より良い無料製品で直接参入）、副 F-SINGLE（文章生成が汎用チャットの一機能に吸収）。「AI 期のモデル優位は堀にならない」（H5）に整合する暫定例。

### Cited Findings
- 創業・初期: 2021 年創業。公開後 12 か月で ARR 4,250 万ドル（月 30% 成長）。2022 年売上 7,500 万ドル（前年比 +76.5%）。GPT-3 を再販する UX 層で、生成語数に応じて OpenAI に支払う（[Sacra: Jasper](https://sacra.com/c/jasper/)）。
- 資金: 累計 1.31 億ドル（Insight Partners・Coatue・Bessemer・YC）、直近評価額 15 億ドル（売上の約 20 倍）（[Sacra](https://sacra.com/c/jasper/)）。2022 年のシリーズ A で 15 億ドル評価（[Maginative 2023-09-29](https://www.maginative.com/article/jasper-cuts-internal-valuation-as-ai-growth-slows/)）。
- 巨大資本の参入: OpenAI は 2022 年秋に ChatGPT を公開し、「一夜で手強い低コスト競合」が生まれた（[Maginative](https://www.maginative.com/article/jasper-cuts-internal-valuation-as-ai-growth-slows/)）。ChatGPT の公開日 2022 年 11 月 30 日は一般知識（本調査では未確認）。
- 資本差: OpenAI の 2023 年初の評価額は約 290 億ドル（Microsoft 出資時、一般知識・未確認）。Jasper の 15 億ドルに対し約 20 倍。かつ OpenAI は Jasper のモデル供給者。
- 推移: 2022 年に ARR は倍増して 8,000 万ドル。2023 年 1 月時点で ARR 9,000 万ドル、2023 年末 1.4 億ドル・2024 年末 2.5 億ドルを計画していたが、2023 年夏に 2023 年計画を 30% 以上下方修正。2023 年 7 月に人員削減。2023 年 9 月に社内評価額を 20% 切り下げ（約 12 億ドル）、共同創業者 Dave Rogenmoser が会長へ、Dropbox 元社長 Timothy Young が CEO（[Maginative 2023-09-29](https://www.maginative.com/article/jasper-cuts-internal-valuation-as-ai-growth-slows/)、[The Information 2023（見出しのみ確認）](https://www.theinformation.com/articles/jasper-an-early-generative-ai-winner-cuts-internal-valuation-as-growth-slows)）。
- 自己主張: Rogenmoser は「中堅・大企業がブランドに沿った高性能なマーケティングコンテンツを任せられるプラットフォーム」、報道は「先行者優位と豊富な資金」を挙げた（[Maginative](https://www.maginative.com/article/jasper-cuts-internal-valuation-as-ai-growth-slows/)）。
- 2024 年以降の売上は資料間で大きく食い違う（3,500 万〜8,000 万ドル）ため採用しない（[SQ Magazine](https://sqmagazine.co.uk/jasper-ai-statistics) 等、低品質）。

### Inferences
- 主張した堀は SPEED（先行者優位）・BRAND・テンプレート（ECO の初期形）。モデル自体は OpenAI のもので CR ではなく、ChatGPT が無料で汎用に提供された時点で UX 層の価値が大きく縮んだ。
- 欠けていた MOAT: SC-WF（企業のブランドガイドライン・承認ワークフローへの埋め込み。転換後に目指している）、NE-DATA（利用データで自社モデルが改善する仕組み。GPT-3 再販では蓄積されない）。
- F コード: 主 F-COPY（供給者による直接参入で差分消失）＋ F-PLATFORM（モデル供給者への依存）、副 F-SINGLE。
- 進行中事例であり、2026 年時点の最終判定は保留。「失敗寄りの混合」として暫定記録する。

### Gaps
- 2023〜2025 年の売上・ARR は信頼できる開示がない。
- ChatGPT 公開日・OpenAI 評価額は本調査で一次確認していない（一般知識）。

---

## 参照事例（古典、母集団外）

### Netscape vs Internet Explorer
- 事実: 1994 年 4 月 4 日創業（Mosaic Communications）、1995 年 8 月 IPO で初日終値ベースの時価総額 29 億ドル。1990 年代半ばにブラウザシェア 80〜90% 超。Microsoft は IE 1.0 を Windows 95 Plus Pack に、以後 Windows に同梱・常時無料で提供し、1997 年には Apple が Mac OS の既定ブラウザを IE にすることで合意。Netscape は 1998 年 1 月に Navigator を無料化しオープンソース（Mozilla）へ。1998 年 5 月に米司法省が反トラスト提訴、1999 年 11 月 5 日の事実認定（Jackson 判事）は「Microsoft は IE を Windows に抱き合わせ、OEM とユーザーに IE の受け入れを条件とし、OS 独占力を用いて Navigator のシェアを減少させた」と認定。Navigator の米国インストールベースは 1996 年 1,500 万 → 1998 年 12 月 3,300 万に増えたが IE の方が大きく速く成長。AOL は 1998 年 11 月 24 日に 42 億ドル（株式交換）での買収を発表、1999 年 3 月 17 日の完了時には 100 億ドル相当（[Wikipedia: Netscape](https://en.wikipedia.org/wiki/Netscape)、[DOJ Findings of Fact 1999](https://webarchive.library.unt.edu/web/20090813044102/http:/justice.gov/atr/cases/f221300/221393.htm)、[Benzinga](https://www.benzinga.com/general/education/21/11/24274752/this-day-in-market-history-aol-buys-netscape-for-4-2b)、[Cato 1999](https://www.cato.org/regulation/winter-1999/all-facts-fit-square-pegs-round-holes-us-v-microsoft)）。
- コード: 主 F-BUNDLE（司法判断で認定された抱き合わせ）、副 F-ECON（有料ブラウザ vs 無料）。主張した堀は BRAND・SPEED・ECO（Web 標準の主導）。欠けていたのは DIST（OS 同梱）。売却額（42 億→100 億ドル）はピーク時価総額（1995〜96 年に 60〜70 億ドル台とされる、未確認）と同程度以上で、金銭的には「失敗」と言い切れないが、製品はシェアを失い 2008 年に開発終了。
- Slack との対比: 30 年を隔てて「無料同梱」「OS／スイート所有者が配布を支配」「反トラストで是正されたが遅い」が同型。Slack の「Dear Microsoft」広告は Apple の 1981 年 IBM 歓迎広告を模していた点でも歴史意識があった（[Vice](https://www.vice.com/en/article/slack-channels-steve-jobs-when-calling-out-microsoft)）。

### Lotus 1-2-3 / WordPerfect vs Microsoft Office
- 事実（Lotus）: 1983 年 1 月 26 日発売、初年度 17.5 万本。1988 年に 5 億ドルの表計算市場の約 70%。バージョン 3 の 1 年超の遅延、OS/2 への注力と Windows 対応の遅れ、製品ラインの分裂で、Windows 普及とともに Excel に抜かれ「1990 年代初頭に Microsoft に抜かれ、二度と回復しなかった」。IBM が 1995 年に 35 億ドルで買収（Notes 目的）。1-2-3 は 2013 年 6 月 11 日に終了発表、2014 年 9 月 30 日サポート終了（[Wikipedia: Lotus 1-2-3](https://en.wikipedia.org/wiki/Lotus_1-2-3)、[Silicon UK](https://silicon.co.uk/software/office-suites/lotus-software-history-219669)、[Deseret 1996](https://www.deseret.com/1996/1/31/19222369/corel-to-buy-wordperfect-from-novell/)）。
- 事実（WordPerfect）: 1989 年の 5.1 for DOS が標準となり、1990 年代初頭にシェア最大 60%。1992 年時点で DOS 市場の 85% を握るが Windows 市場では約 1/3（Microsoft が過半）。Windows 版は 5.1（1991 年）が不安定、成熟した 5.2 は 1992 年 11 月で Word for Windows 2 の 1 年以上後。1995 年時点でも世界市場で 50% 超とする資料があるが、2000 年には Word が最大 95%。Novell が 1994 年 6 月に 14 億ドル（Novell の届出では 8.55 億ドル）で買収、1996 年 1 月に Corel へ 1.86 億ドル（報道により 1.7〜1.81 億ドル）で売却。Novell は 2004 年 11 月に Microsoft を反トラストで提訴（Word と Windows の抱き合わせ等）したが 2012 年 7 月に棄却、2014 年に最高裁が上告不受理（[Wikipedia: WordPerfect](https://en.wikipedia.org/wiki/WordPerfect)、[eWeek: Office Suite Wars](https://www.eweek.com/enterprise-apps/eweek-at-30-how-microsoft-won-the-1990s-office-suite-wars)、[Novell press 1996](https://www.novell.com/news/press/archive/1996/01/pr96018.html)、[Nextgov 1996](https://nextgov.com/digital-government/1996/02/corel-buys-wordperfect-new-release-due-in-april/238776)）。
- コード: 主 F-TECH（DOS→Windows 移行の遅れ。両社とも Windows 版が遅く不安定）、副 F-BUNDLE（Office スイートの一括販売・企業向け契約）。主張した堀は SC-WF（マクロ・キーボード操作の習熟、法律事務所の 70% が WordPerfect）と BRAND。SC-WF は確かに強く DOS 市場では 85% を維持したが、プラットフォーム移行で「習熟」が無効化された。Netscape・Slack と異なり、プラットフォーム移行（F-TECH）が主因である点が本件の特徴。WordPerfect の売却額 1.86 億ドルは買収額の約 1/7。

---

## 落とした候補

| 候補 | 落とした理由 |
|---|---|
| WeWork | ソフトウェアではなく不動産リース。巨大資本の参入ではなく経営・ガバナンス問題（F-SELF）。母集団外。 |
| Theranos・Juicero・FTX | 不祥事・詐欺・製品不成立（F-SELF）。巨大資本の競合参入と無関係。 |
| Quibi | 上記のとおり巨大資本の「参入」が特定できず F-SELF 主因。依頼により本文に記録したが、集計表では「参照」扱い。 |
| Myspace vs Facebook | Myspace は 2005 年に News Corp（売上 250 億ドル超）傘下で、Facebook の方が資本で劣っていた。資本差の向きが逆で母集団外。 |
| Google+（vs Facebook） | 巨大資本側の失敗。本テーマは「資本で劣る側」を対象とするため除外。 |
| Snap vs Instagram Stories（2016） | Instagram が Stories を模倣（2016 年 8 月）し成長は鈍化したが、Snap は独立で存続しユーザー・売上を拡大し続けている。「失敗」「混合」のいずれでもなく、成功側候補として別ノートで扱う。 |
| Rdio・Grooveshark vs Apple Music／Spotify | Rdio は 2015 年 11 月に破産し Pandora へ資産売却。Apple Music（2015 年 6 月）は巨大資本の参入に該当するが、Rdio は参入前からカテゴリ首位ではなく（Spotify が首位）、「初期首位」条件を満たさない。 |
| Yik Yak・Secret・Path | ピーク後の衰退は自己要因（嫌がらせ対策・プライバシー問題）が主で、巨大資本の参入が特定できない。 |
| Chegg vs ChatGPT | 条件（10 倍以上の資本を持つ OpenAI の参入後、株価 90% 超下落）は満たすが、教育サービスでテック区分の母集団設計（SaaS・コンシューマ・開発者ツール・AI）から外れる。別途「AI 期の代替」として検討候補に残す。 |
| Otter・Loom・Calendly（AI・バンドル期） | 設計ドキュメントの候補だが、2026 年 11 月時点で売却・大幅縮小の事実が確認できず、進行中。失敗判定不能のため今回は収集せず。 |
| Mailbox・Sunrise・Wunderlist | いずれも巨大資本（Dropbox・Microsoft）に買収後に終了。買収側の判断による終了であり、参入によるシェア喪失ではない。 |
| Blue Apron | ソフトウェアでなく食品配送。巨大資本（Amazon）の参入はあったが、単位経済（F-ECON）が参入前から崩れていた。 |
| Fitbit（採用） | 条件を満たすため追加事例 1 として採用。ハードウェアを含むが、Pebble と同じカテゴリで「ソフトウェア＋デバイス」の比較対照になる。 |
| Jasper（採用） | 進行中だが設計ドキュメントの候補であり、H5（AI 期）の検証に必要なため暫定で追加事例 2 として採用。 |

---

## 事例×失敗原因コード一覧表

| 事例 | ピーク年・指標 | 巨大資本の参入年 | 資本差（売上ベース） | 主張していた堀 | 欠けていた MOAT | 主 F コード | 副 F コード | 結末 |
|---|---|---|---|---|---|---|---|---|
| Slack（混合） | 2019 直接上場 評価額約 230 億ドル・DAU 1,200 万 | 2016-11 Teams 発表、2018-07 無料版 | Microsoft FY2017 965.7 億 vs Slack FY2017 1.05 億（約 900 倍） | NE-D（増加収益）、ECO、BRAND（顧客の愛着） | DIST、SC-WF（スイート統合）、組織間 NE | F-BUNDLE | F-SINGLE | 2021 Salesforce へ 277 億ドルで売却（評価額は上回る）。シェアは Teams の約 1/10 |
| Dropbox（混合） | 2014 評価額 100 億ドル・2018 登録 5 億 | 2012-04 Google Drive | Google 2012 460 億 vs Dropbox 2011 約 2.4 億（約 190 倍） | NE-D（バイラル共有）、BRAND、セルフサービス GTM | SC-DATA／SC-WF、DIST（OS 同梱） | F-BUNDLE | F-SINGLE | 独立存続、売上 25 億ドルで横ばい、2025 有料ユーザー減少 |
| Evernote（失敗） | 2012 評価額約 10 億ドル・2018 ユーザー 2.5 億 | 2014〜2015 OneNote 無料化・iOS Notes 強化（要確認） | Apple・Microsoft（売上 1,000 倍超） | BRAND、SC-DATA、「100 年企業」 | DIST、NE／ECO（コラボ） | F-BUNDLE | F-SINGLE（＋F-SELF） | 2023-01 Bending Spoons へ約 1.94〜2.0 億ドルで売却（ピークの約 1/5〜1/10） |
| Meerkat（失敗） | 2015-03 評価額約 0.4〜0.5 億ドル・7 月 200 万ユーザー | 2015-03-13 グラフ遮断、03-26 Periscope | Twitter 2014 14 億 vs 売上ゼロ | なし（Twitter 配信依存）、SPEED | DIST、NE-D（自前） | F-PLATFORM | F-COPY | 2016-10 終了、Houseparty へ転換 |
| Clubhouse（失敗） | 2021-04 評価額 40 億ドル・2 月 WAU 1,000 万 | 2020-12 Twitter Spaces（2021 FB・LinkedIn・Spotify） | Twitter 2020 37 億・Meta 860 億 vs 売上ゼロ | NE-D（音声コミュニティ）、BRAND | 自前グラフ、SC-*、クリエイター CP | F-COPY | F-SINGLE（＋F-SELF） | 2023-04 人員半減、縮小存続。40 億ドル買収提案を逸す |
| Zynga（失敗→再建） | 2011-12 IPO 評価額約 70〜90 億ドル・DAU 5,700 万 | 2010 バイラル制限・Credits、2012-11 特別契約終了 | Facebook 2012 51 億 vs 11.4 億（売上 4.5 倍、時価総額 10 倍超） | NE-D、NE-DATA、SCALE（クロスプロモ） | 自前 DIST | F-PLATFORM | F-TECH | 株価 1 年で −80%。2022 Take-Two へ 127 億ドル（10 年後） |
| Vine（失敗） | 2015-12 「2 億アクティブ」 | 2013-06-20 Instagram 動画 | Facebook 2013 79 億 vs Twitter 6.65 億（約 12 倍） | 独自フォーマット、クリエイター文化（BRAND／ECO） | クリエイター収益分配（CP／ECO）、供給側の囲い込み | F-COPY | F-ECON | 2017-01 閉鎖 |
| Quibi（参照・F-SELF） | 2020 調達 17.5 億ドル | 該当なし（既存無料供給） | — | CR（ハリウッド）、BRAND、特許 | ほぼ全て | F-SELF | F-ECON | 2020-12 閉鎖、コンテンツ 1 億ドル未満で Roku へ |
| Pebble（失敗） | 2015 売上 8,200 万ドル・累計 200 万台 | 2015-04 Apple Watch | Apple FY2015 約 2,337 億（未確認）vs 0.82 億（1,000 倍超） | BRAND（カテゴリ創出）、ECO（開発者） | DIST、SCALE、CP が機能せず | F-COPY | F-ECON（＋F-SELF） | 2016-12 破産、Fitbit へ 2,300 万ドル |
| Houseparty（失敗） | 2020-03 月間 5,000 万サインアップ | 2020-04-24 Messenger Rooms | Meta 2020 860 億 vs ほぼゼロ | NE-D（友人グループ）、UX | DIST、SC-* | F-COPY | F-SINGLE | 2019 Epic へ約 3,500 万ドル、2021-10 閉鎖 |
| Foursquare（混合） | 2011 評価額 6 億ドル（2012 7.6 億とも） | 2010-08 Facebook Places | Facebook 2010 20 億 vs 2012 売上 200 万 | NE-D、ゲーム的仕組み | 大規模グラフ、消費者向け DIST | F-COPY | F-SINGLE | 2016 評価額 2.5 億のダウンラウンド→企業向けデータへ転換、2019 売上 1.5 億超。2024-12 消費者アプリ終了 |
| Fitbit（失敗・追加） | 2015 時価総額約 100 億ドル・2016 売上 22 億 | 2015-04 Apple Watch | Apple FY2015 約 2,337 億（未確認）vs 約 18.6 億（未確認、100 倍超） | BRAND、NE-D（コミュニティ）、DIST（小売 5 万店）、オープン API | ECO（watchOS）、SC-DATA、SCALE | F-COPY | F-ECON | 2019-11 Google へ 21 億ドル（ピークの約 1/5） |
| Jasper（AI 期・暫定） | 2022-10 評価額 15 億ドル・ARR 約 8,000 万 | 2022-11 ChatGPT | OpenAI 約 290 億（未確認）vs 15 億（20 倍）、かつ供給者 | SPEED（先行者）、BRAND、テンプレート | SC-WF、NE-DATA、自前モデル | F-COPY＋F-PLATFORM | F-SINGLE | 2023 評価額 −20%、CEO 交代、企業向けへ転換（進行中） |
| 参照: Netscape | 1995〜96 シェア 80〜90% | 1995 IE 同梱 | Microsoft FY1996 約 87 億（未確認）vs Netscape 1996 約 3.5 億（未確認） | BRAND、SPEED、ECO | DIST（OS 同梱） | F-BUNDLE | F-ECON | 1998-11 AOL へ 42 億ドル（完了時 100 億） |
| 参照: Lotus／WordPerfect | 1988 Lotus 70%、1990 年代初 WP 60% | 1990〜95 Office・Windows | Microsoft は 1990 年代前半に両社を上回る規模 | SC-WF（習熟・マクロ）、BRAND | Windows 対応、スイート DIST | F-TECH | F-BUNDLE | IBM へ 35 億（1995）、WP は Corel へ 1.86 億（1996、買収額の 1/7） |

### 集計メモ（母集団内 12 件、Quibi と古典 2 件を除く）
- 主 F コードの分布: F-COPY 7（Clubhouse・Vine・Pebble・Houseparty・Foursquare・Fitbit・Jasper）、F-BUNDLE 3（Slack・Dropbox・Evernote）、F-PLATFORM 2（Meerkat・Zynga、Jasper は複合）。
- 副 F コードの分布: F-SINGLE 7、F-ECON 3、F-COPY 1、F-TECH 1。
- H2（F-BUNDLE＋F-SINGLE が過半）の暫定評価: 主コードのみでは F-BUNDLE 3/12 = 25% で不支持域。主・副を合わせて「F-BUNDLE または F-SINGLE を含む」事例は 10/12 = 83% で整合。**判定基準が「主コードのみ」か「主副いずれか」かを事前登録で明確にしていなかった**ため、集約 report では両方を報告し、どちらを採用したかを明記する必要がある。
- F-COPY が主因となった 7 件のうち 6 件は消費者向けで、巨大資本側が「自社の既存グラフ・配布網に機能を足す」形で参入した。模倣そのものより、模倣先が持つ DIST／NE が決定的だったと読める（F-COPY と F-BUNDLE の境界は曖昧）。
- 「主張していた堀」として NE-D を挙げた事例は 8 件あるが、いずれも巨大資本側のネットワークの方が大きいか、ネットワークが組織・友人グループ内で閉じていた。NE-D の主張は失敗を予防していない。
- 存続した「混合」3 件（Slack・Dropbox・Foursquare）に共通するのは、消費者向けグラフ競争から B2B（企業顧客・企業間ネットワーク・企業向けデータ）へ重心を移したこと。SC-DATA／SC-WF／NE-DATA が後から効いた。
