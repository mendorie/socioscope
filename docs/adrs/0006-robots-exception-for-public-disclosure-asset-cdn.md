# 公開開示文書を配信する資産 CDN は、robots.txt の全面 Disallow があっても例外として取得してよい

- **Status**: Accepted
- **Date**: 2026-10-22
- **関連**: `design/data-sources.md`（ルール「スクレイピングは利用規約・robots.txt を確認し、許される場合のみ」）、ADR 0002（raw の manifest）、`docs/specs/bicycle-sportsbike-drilldown.md`（Phase 3）、`themes/bicycle-industry` の `merida.py`

## Context
bicycle-industry テーマの H14（Merida が持分法で開示する Specialized の損益）は、Merida 自社の投資家向けページ（`www.merida-bikes.com`、robots.txt は空＝許可）からリンクされた年報・四半期財務報告 PDF が唯一の鍵なしソースである。しかし PDF の実体はウェブ制作会社の資産ホスト `merida-cdn.m-c-g.net` に置かれ、その robots.txt は `User-agent: * / Disallow: /`（LinkChecker のみ許可）である。本リポジトリの従来ルール（robots.txt を守る）を字義どおり適用すると、会社が公開を意図して自社サイトからリンクしている開示文書を取得できない。

同じ構図は他の上場企業 IR でも起こりうる（IR ツール業者や CDN が一律に Disallow を置く）。一方で、`mopsov.twse.com.tw`・`doc.twse.com.tw` のように**サイト運営者自身が**全面 Disallow を置いている場合は、運営者の意思として尊重すべきである。

## Decision
次の条件をすべて満たすときに限り、robots.txt の Disallow にかかわらず取得してよい。
1. 文書が**法定または取引所規則に基づく公開開示**（年報・財務報告・決算短信・有価証券報告書など）であること。
2. 開示主体（会社）自身の、robots.txt で許可されたページから**直接リンク**されていること（リンクの到達経路を `design/data-sources.md` に記録する）。
3. Disallow を置いているのが**資産ホスト・CDN・IR ツール業者**であり、開示主体のサイトそのものではないこと。開示主体のサイト（または取引所の開示サイト）が Disallow を置いている場合は例外にしない。
4. 取得は文書単位で件数が小さく（数十件以下）、逐次・低頻度（年次〜四半期）であること。クロール（リンクをたどる走査）はしない。
5. raw は manifest（URL・sha256・取得日時・ライセンス）付きで保存し、再配布しない。

運用: 例外を使うソースは `design/data-sources.md` の記録節に「ADR 0006 の例外」と明記し、満たした条件 1〜4 を書く。本決定でまず `merida-cdn.m-c-g.net`（Merida の年報・四半期財務報告）を例外とする（2026-10-22、ユーザー承認）。

## Alternatives considered
- **robots.txt を一律に守る（従来ルールのまま）**: 単純で安全だが、開示主体の意図（公開）と資産ホストの設定（一律 Disallow）を区別できず、公開開示文書が取れない。H14 を断念することになる。
- **人がブラウザで PDF を保存し raw に置く**: robots には触れないが、再現性（manifest の URL から再取得できる）が失われ、ADR 0002 の前提に反する。
- **取引所の開示サイト（doc.twse）から取る**: サイト運営者自身が全面 Disallow を置いているため条件 3 を満たさない。不採用。
- **robots を一切見ない**: 運営者の意思を無視することになり、既存のルールと衝突する。不採用。

## Consequences
**良い点**: 会社が公開を意図した開示文書を、資産ホストの一律設定に妨げられずに再現可能な形で取得できる。例外の条件が明文化され、適用のたびに記録が残る。
**コスト・リスク**: 条件 3 の判定（誰が Disallow を置いたか）に人の判断が要る。資産ホストが取得を拒否（403）するようになった場合は従い、代替を探す。例外を広げすぎないよう、適用は data-sources.md で一覧できる状態を保つ。
