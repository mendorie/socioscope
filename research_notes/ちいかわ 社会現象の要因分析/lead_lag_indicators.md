# キャラクター IP ブームの先行／遅行指標（lead/lag）と検索インタレスト

調査日: 2026-10-24。対象 8 IP（ちいかわ・鬼滅の刃・すみっコぐらし・妖怪ウォッチ・ポケモン・アナと雪の女王・SPY×FAMILY・推しの子）。
既存ノート（`comparison_past_booms.md`・`ip_growth_timeline.md`・`children_surveys.md`）の日付を再利用し、不足分を Web 検索で補った。**確認済み（confirmed）**と**推定（inferred）**を分けて記す。
出力: 表 → `reports/figures/chiikawa/data/lead_lag.csv`、検索インタレスト → `reports/figures/chiikawa/data/google_trends.csv`・`fig7_search_interest.png`（`make_fig7.py`、取得は `fetch_trends.py`）。

## Takeaway
- 「大人側の指標（番付・トレンディ・SNS 流行語・キャラクター大賞）」→「子ども調査 1 位」の順序で見ると、ちいかわは **大人側 2022 → 子ども側（女児 1 位）2025 で 3 年**、映画ピーク（2026）まで 4 年と、比較集合のなかで最も遅い。鬼滅（1〜2 年）、妖怪ウォッチ（0〜1 年）、ポケモン（1 年）は大人側と子ども側がほぼ同時で、すみっコぐらしは子ども側（2018 女児 1 位）が大人側（2019）に**先行**する唯一の例。
- 映画は妖怪ウォッチ・アナ雪・鬼滅では「大人側シグナルと同年」に来るが、ちいかわは 4 年後。ちいかわの映画は「ブームの着火点」ではなく「長い台地の末尾に乗せた山」と読める。
- Google Trends（pytrends、取得成功）: ちいかわは 2022 以降 2025 まで年平均 14〜15（鬼滅 2020-10=100 の同一スケール）で**ほぼ平坦**、2026-08 に 76 へ急伸。鬼滅（2020-10 に 100、翌年に 1/4 以下）、妖怪ウォッチ（2014 に山、2 年で 1/3）と対照的に、「急騰→減衰」の形をしていない。Google 年間検索ランキング（2022〜2025）と Yahoo! 検索大賞（2019〜2025）には、確認できた範囲でちいかわは一度も入っていない。

## 1. Lead/lag 表

列の定義: (1) 起点、(2) 大人・オンライン側の最初の主流シグナル、(3) 日本キャラクター大賞グランプリ、(4) 代表的な子ども調査で初めて 1 位（総合／男児／女児のいずれか）、(5) 映画ピーク年と興収、(6) 新語・流行語大賞トップテン。
ラグ＝(4)−(2)、(4)−(3)、(5)−(2)、(5)−(3)（年）。

| IP | (1) 起点 | (2) 大人側シグナル | (3) キャラ大賞 | (4) 子ども調査 初 1 位 | (5) 映画ピーク | (6) 流行語 | (4)−(2) | (4)−(3) | (5)−(2) | (5)−(3) |
|---|---|---|---|---|---|---|---|---|---|---|
| ちいかわ | 2020（X 連載 2020-01） | 2022（トレンディ 2 位・SNS 流行語大賞・MJ 西前頭①） | 2022 | 2025（Kids/ex 女児 1 位） | 2026 / 181.0 億 | — | **3** | **3** | **4** | **4** |
| 鬼滅の刃 | 2016（WJ 2016-02-15） | 2019（Yahoo! 検索大賞 アニメ 1 位） | 2020 | 2021（Kids/ex 総合 1 位）※2020 調査未確認 | 2020 / 407.5 億 | 2020 | ≤2 | ≤1 | 1 | 0 |
| すみっコぐらし | 2012（2012-09） | 2019（MJ 西前頭） | 2019 | 2018（Kids/ex 女児 1 位、同率） | 2019 / 14.5 億 | — | **−1** | **−1** | 0 | 0 |
| 妖怪ウォッチ | 2013（3DS 2013-07-11） | 2014（MJ 西横綱・トレンディ 2 位） | 2015 | 2015（バンダイ 総合 1 位） | 2014 / 78.0 億 | 2014 | 1 | 0 | 0 | −1 |
| ポケモン | 1996（赤緑 1996-02-27） | 1997（トレンディ 7 位、二次） | 2009（第 1 回） | 1998（バンダイ 総合 1 位） | 1998 / 72.4 億 | 2016（ポケモンGO） | 1 | −11※ | 1 | −11※ |
| アナと雪の女王 | 2014（日本公開 2014-03-14） | 2014（トレンディ 1 位・MJ 上期 西横綱） | なし | 1 位なし（バンダイ 2015 総合 3 位、Kids/ex 2023 女児 2 位） | 2014 / 254.7 億 | 2014 | n/a | n/a | 0 | n/a |
| SPY×FAMILY | 2019（Jump+ 2019-03-25） | 2022（トレンディ 21 位・Yahoo! アニメ 1 位・MJ 東前頭⑤） | なし | 1 位なし（Kids/ex 2023 女児 6 位） | 2023 / 63.2 億 | — | n/a | n/a | 1 | n/a |
| 推しの子 | 2020（YJ 2020-04-23） | 2023（トレンディ 12 位・MJ 東関脇「アイドル」・Google/Yahoo! アニメ 1 位） | なし | 1 位なし | 2024 / 5.8 億（実写） | — | n/a | n/a | 1 | n/a |

※ポケモンの日本キャラクター大賞は賞の創設（2009）が IP の初期ブームより後なので、ラグとしての意味はない。

### 各セルの出典（確認済み）

**ちいかわ**
- (1) X 連載開始 2020-01 — [note JW（二次）](https://note.com/junwatanabe72/n/n48318e98bbe2)、`ip_growth_timeline.md`
- (2) 日経トレンディ 2022 ヒット商品ベスト 30 で 2 位（1 位 Yakult1000、21 位 SPY×FAMILY） — [ORICON 2022-11-03](https://www.oricon.co.jp/news/2255646/full/)、[日経クロストレンド](https://xtrend.nikkei.com/atcl/contents/18/00732/00001/)、[全順位転載（二次）](https://www.fruitfuldays2017.com/entry/hit30-2022)；SNS 流行語大賞 2022 大賞「〇〇ってコト!?」 — [INTERNET Watch](https://internet.watch.impress.co.jp/docs/news/1461773.html)；日経MJ 2022 年ヒット商品番付 西前頭①（横綱は「コスパ&タイパ」「#3年ぶり」） — [日経 2022-12](https://www.nikkei.com/article/DGXZQOUC01AMQ0R01C22A2000000/)、[番付一覧（二次）](https://yorozu-do.com/hit-bandzuke/)
- (3) 日本キャラクター大賞 2022 グランプリ（以後 2024・2025・2026） — [Wikipedia 日本キャラクター大賞](https://ja.wikipedia.org/wiki/日本キャラクター大賞)、[eiga.com 2026-06-21](https://eiga.com/news/20260621/9/)
- (4) ビデオリサーチ Kids/ex 2025 年 10 月度調査（2026-01-28 発表）女の子 1 位 73.9%、総合 7 位。2024 年度まで調査対象外 — [ビデオリサーチ PDF](https://www.videor.co.jp/press/images/press_20260128.pdf)
- (5) 『映画ちいかわ 人魚の島のひみつ』2026-07-24 公開、公開 87 日で 181.0 億円（2026-10-18） — [granza.jp（興行通信社値の転記）](https://granza.jp/chiikawa-movie-box-office/)、[シネマトゥデイ 158.4 億時点](https://www.cinematoday.jp/news/N0157027)
- (6) 流行語大賞トップテン 2019〜2025 に該当なし — [Wikipedia 新語・流行語大賞](https://ja.wikipedia.org/wiki/新語・流行語大賞)

**鬼滅の刃**
- (1) 週刊少年ジャンプ 2016 年 11 号（2016-02-15） — [Wikipedia 鬼滅の刃](https://ja.wikipedia.org/wiki/鬼滅の刃)
- (2) Yahoo! 検索大賞 2019 アニメ部門 1 位（2020 もアニメ・映画 1 位） — [Wikipedia Yahoo!検索大賞](https://ja.wikipedia.org/wiki/Yahoo!検索大賞)；LINE リサーチ 2019 下期（15〜24 歳）漫画・アニメ 1 位 — [LINE リサーチ](https://www.lycbiz.com/jp/news/line-research/20200109/?page=47)。日経トレンディ 2019 ベスト 30 には入っていない（1〜30 位確認） — [日経クロストレンド 1〜15 位](https://xtrend.nikkei.com/atcl/contents/18/00242/00002/)、[16〜30 位](https://xtrend.nikkei.com/atcl/contents/18/00242/00002/?P=2)
- (3) 2020 グランプリ、2021 劇場版でグランプリ — [Wikipedia 日本キャラクター大賞](https://ja.wikipedia.org/wiki/日本キャラクター大賞)
- (4) Kids/ex 2021 年 10 月調査: 男女計 1 位 鬼滅の刃、2 位 ピカチュウ、3 位 ドラえもん。男児 5 位・女児 2 位 — [ビデオリサーチ Digest plus 2021 年版](https://www.videor.co.jp/digestplus/article/53282.html)
- (5) 『無限列車編』2020-10-16 公開、407.5 億円（歴代一覧） — [Wikipedia 歴代興収](https://ja.wikipedia.org/wiki/日本歴代興行収入上位の映画一覧)（作品ページは 404.3 億円と表記 — [Wikipedia 鬼滅の刃](https://ja.wikipedia.org/wiki/鬼滅の刃)）
- (6) 2020 トップテン — [Wikipedia 新語・流行語大賞](https://ja.wikipedia.org/wiki/新語・流行語大賞)；日経MJ 2020 東横綱・日経トレンディ 2020 1 位は `comparison_past_booms.md`

**すみっコぐらし**
- (1) サンエックス 2012-09 初登場 — [Wikipedia すみっコぐらし](https://ja.wikipedia.org/wiki/すみっコぐらし)
- (2) 日経MJ 2019 年ヒット商品番付 西前頭（横綱はラグビーW杯／キャッシュレス） — [lovely-lovely.net（WBS 転記）](https://lovely-lovely.net/business/nikkei-7/)、[Wikipedia ヒット商品番付](https://ja.wikipedia.org/wiki/ヒット商品番付)。日経トレンディ 2019 ベスト 30 には入っていない（上記 2 ページ確認）
- (3) 2019 グランプリ — [Wikipedia 日本キャラクター大賞](https://ja.wikipedia.org/wiki/日本キャラクター大賞)
- (4) Kids/ex 2018 年 10 月調査: 女児 1 位（ドラえもんと同率、前年 16 位から上昇） — [ビデオリサーチ Digest plus 2018 年版](https://www.videor.co.jp/digestplus/article/13057.html)。2021〜2024 女児 1 位（3 連覇・4 連覇表記） — [digitalpr 2023 年版](https://digitalpr.jp/r/82235)、[digitalpr 2024 年版](https://digitalpr.jp/r/103029)；2022 女児 1 位 80% 超 — [Digest plus 2022 年版](https://www.videor.co.jp/digestplus/article/76312.html)
- (5) 第 1 作（2019-11-08）累計 14.5 億円（2020-01 時点）、第 2 作（2021-11-05）11.69 億円（2022-01 時点） — [Wikipedia すみっコぐらし](https://ja.wikipedia.org/wiki/すみっコぐらし)；第 1 作 10.9 億（2019-12-19） — [fansvoice](https://fansvoice.jp/2019/12/20/sumikko-7th-week/)
- (6) 該当なし

**妖怪ウォッチ**
- (1) 3DS 2013-07-11、アニメ 2014-01-08 — [Wikipedia 妖怪ウォッチ](https://ja.wikipedia.org/wiki/妖怪ウォッチ)
- (2) 日経MJ 2014 西横綱 — [Wikipedia ヒット商品番付](https://ja.wikipedia.org/wiki/ヒット商品番付)；日経トレンディ 2014 2 位 — [Inside Games 2014-11](https://www.inside-games.jp/article/2014/11/04/82227.html)
- (3) 2015 グランプリ — [Wikipedia 日本キャラクター大賞](https://ja.wikipedia.org/wiki/日本キャラクター大賞)
- (4) バンダイ こどもアンケート Vol.222（2015-05-15〜18 調査、800 人、2015-06-25 発表）: 総合 1 位 妖怪ウォッチ 19.9%（前年 2 位）、2 位 アンパンマン 12.9%、3 位 アナと雪の女王。男児 1 位 25.5%・女児 1 位 14.3% — [バンダイ question222.pdf](https://www.bandai.co.jp/kodomo/pdf/question222.pdf)（取得時サーバメンテ中、内容は [Inside Games 2015-06-26](https://www.inside-games.jp/article/2015/06/26/88861.html) の転記で確認）。2016（Vol.228）も 1 位 — [question228.pdf](https://www.bandai.co.jp/kodomo/pdf/question228.pdf)
- (5) 第 1 作（2014-12-20）78.0 億円、第 2 作 55.3 億、第 3 作 32.6 億、以後 20.4→12.5→7.5 億 — [Wikipedia 妖怪ウォッチ](https://ja.wikipedia.org/wiki/妖怪ウォッチ)
- (6) 2014 トップテン — 同上

**ポケモン**
- (1) 赤・緑 1996-02-27 — [ファミ通](https://www.famitsu.com/news/202002/27193330.html)
- (2) 日経トレンディ 1997 ベスト 30: 1 位 たまごっち、7 位 ポケモン（**二次サイト**、誌面未確認） — [entamedata](https://entamedata.com/2020/11/08/%E3%83%92%E3%83%83%E3%83%88%E5%95%86%E5%93%81%E2%80%A5%E6%AD%B4%E4%BB%A3%E3%81%AE%E5%B9%B4%E9%96%93%E3%81%A7%E5%A3%B2%E3%82%8C%E3%81%9F%E5%95%86%E5%93%81%E3%81%A8%E4%BB%8A%E5%B9%B4%E3%81%AE%E3%83%92/)；たまごっち 1997 1 位は [日経クロストレンド](https://xtrend.nikkei.com/atcl/case/tre/18/00084/)
- (3) 2009 第 1 回グランプリ、2017 再受賞 — [Wikipedia 日本キャラクター大賞](https://ja.wikipedia.org/wiki/日本キャラクター大賞)
- (4) バンダイ こどもアンケート Vol.37（1998 年 6 月）「ポケモン人気 女児・幼児にも」総合 1 位 27.4% — [バンダイ question37.pdf](https://www.bandai.co.jp/kodomo/pdf/question37.pdf)（取得時サーバメンテ中、検索結果のタイトル・抜粋で確認）。1999-04 調査では男児 1 位 ウルトラマン 28.0%・ポケモン 2 位 25.8% — [バンダイ question49](https://www.bandai.co.jp/kodomo/question49.html)
- (5) 『ミュウツーの逆襲』1998 72.4 億 — [Wikipedia 歴代興収](https://ja.wikipedia.org/wiki/日本歴代興行収入上位の映画一覧)
- (6) 2016「ポケモンGO」 — [Wikipedia 新語・流行語大賞](https://ja.wikipedia.org/wiki/新語・流行語大賞)

**アナと雪の女王**
- (1)(5) 日本公開 2014-03-14、興収 254.7 億円（表では 255.0 億） — [Wikipedia アナと雪の女王](https://ja.wikipedia.org/wiki/アナと雪の女王)
- (2) 日経トレンディ 2014 1 位 — 同上、[Inside Games](https://www.inside-games.jp/article/2014/11/04/82227.html)；日経MJ 2014 上期 西横綱 — [三井住友DS](https://www.smd-am.co.jp/market/daily/keyword/archives/japan/1251100_1982/)
- (4) 1 位は確認できず: バンダイ 2015 総合 3 位（[Inside Games](https://www.inside-games.jp/article/2015/06/26/88861.html)）、Kids/ex 2023 女児 2 位（[digitalpr](https://digitalpr.jp/r/82235)）。アイリスオーヤマ会員調査 2014 で 2 位（非代表、[Inside Games 2015-11](https://www.inside-games.jp/article/2015/11/14/93024.html)）
- (6) 2014「ありのままで」 — Wikipedia 同上

**SPY×FAMILY**
- (1) 少年ジャンプ+ 2019-03-25 — [Wikipedia SPY×FAMILY](https://ja.wikipedia.org/wiki/SPY×FAMILY)
- (2) 日経トレンディ 2022 21 位（二次転載）、Yahoo! 検索大賞 2022 アニメ 1 位、Google 2022 アニメ 2 位、SNS 流行語大賞 2022 漫画アニメ部門 1 位、日経MJ 2022 東前頭⑤ — [Google 2022](https://blog.google/intl/ja-jp/products/explore-get-answers/2022_12_year-in-search-2022)、[Yahoo! 2022](https://about.yahoo.co.jp/pr/release/2022/12/05a/)、[番付一覧（二次）](https://yorozu-do.com/hit-bandzuke/)
- (4) Kids/ex 2023 女児 6 位 — [digitalpr](https://digitalpr.jp/r/82235)
- (5) 『CODE: White』2023-12-22 公開、最終 63.2 億円（2024 年邦画 4 位） — [Wikipedia 劇場版 SPY×FAMILY](https://ja.wikipedia.org/wiki/劇場版_SPY×FAMILY_CODE:_White)

**推しの子**
- (1) 週刊ヤングジャンプ 2020-04-23 — [Wikipedia 【推しの子】](https://ja.wikipedia.org/wiki/【推しの子】)
- (2) 日経トレンディ 2023 12 位 — [モデルプレス](https://mdpr.jp/news/detail/4033253)；日経MJ 2023 東関脇「YOASOBI『アイドル』」（二次） — [boke-pon](https://boke-pon.hatenablog.com/entry/HitBanduke2023-20231215)；Google 2023 アニメ 1 位 — [Google 2023](https://blog.google/intl/ja-jp/products/explore-get-answers/year-in-search-2023/)；Yahoo! 2023 アニメ 1 位 — [マイナビ](https://news.mynavi.jp/article/20231205-2832737/)
- (5) 実写『-The Final Act-』2024-12-20、45 日で 5.77 億円 — [MovieWalker 編集長 X](https://x.com/moviewalker_bce/status/1889104254142697717)、[映画の時間 5.8 億](https://movie.jorudan.co.jp/film/99499/)
- (6) 「アイドル」はトップテン外 — Wikipedia 同上

**参考: アンパンマンの支配期間（子ども調査のベースライン）**
- バンダイ こどもアンケート: 2001 年以降 2014 年まで総合 1 位（Vol.190 2011 年「10 年連続」、2014 年 1 位 11.9%） — [question190.pdf](https://www.bandai.co.jp/kodomo/pdf/question190.pdf)、[question202.pdf](https://www.bandai.co.jp/kodomo/pdf/question202.pdf)、[Inside Games 2015](https://www.inside-games.jp/article/2015/06/26/88861.html)
- ビデオリサーチ: 2016-12 以降 総合 1 位は原則ドラえもん（2022 ピカチュウ同率、2024 マリオ、2021 鬼滅） — [ビデオリサーチ 2017 PDF](https://www.videor.co.jp/press/images/cdca3fb1fe0dad00d1fe8fc247569e47.pdf)、Digest plus 各年

### 推定・留保（inferred）
- 鬼滅の (4): Kids/ex 2020 年 10 月調査（2021 年初発表）の資料が見つからず、2021 年版記事の「引き続き大人気」という表現から **2020 年調査でも 1 位だった可能性が高い**。その場合 (4)−(2)=1、(4)−(3)=0。表の値は上限。
- すみっコの (2): 日経MJ 2019 前頭は WBS 放送の転記（二次）。日経トレンディ 2019 には入っていないことは一次で確認。
- ポケモンの (2)(4): 1997 トレンディ 7 位は二次サイト、1998 バンダイ 1 位はバンダイサイトがメンテ中でタイトル・抜粋のみ。
- 日経MJ 前頭の東西・番号は二次（yorozu-do、個人ブログ）。横綱は Wikipedia で確認済み。
- 「子ども調査 1 位」は調査体系が異なる（バンダイ＝0〜12 歳の親・単一回答／Kids/ex＝3〜12 歳・複数回答・東京 50km 圏）ため、IP 間のラグは ±1 年の誤差を含む。
- 映画ちいかわの最終興収は未確定（2026-10-18 時点 181.0 億）。

## 2. 検索インタレスト（Task B）

### 方法
- `reports/figures/chiikawa/fetch_trends.py`（pytrends 4.9.2、`uv pip install pytrends` で venv に追加）。`TrendReq(hl="ja-JP", tz=-540)`、`geo="JP"`、2 リクエスト（①ちいかわ・すみっコぐらし・鬼滅の刃 2019-01-01〜2026-10-24、②妖怪ウォッチ 2013-01-01〜2016-12-31）、リクエスト間 20 秒 sleep、429 時は 30/60 秒待って最大 2 回再試行。
- 結果: **2026-10-24 に 429 なしで両方成功**。①は月次 94 行、②は 4 年未満のため週次 209 行で返ったので月平均（月初基準）に変換。CSV は `data/google_trends.csv`（month, ちいかわ, すみっコぐらし, 鬼滅の刃, 妖怪ウォッチ）。①と②は**別リクエストで別正規化**のため値を跨いで比較しない。
- 図: `make_fig7.py` → `fig7_search_interest.png`（左: 3 IP 同一スケール、右: 妖怪ウォッチ別スケール、ちいかわ #E4572E、他グレー、Hiragino Sans、dpi 150）。

### 結果（年平均／年内最大、鬼滅 2020-10＝100）
| 年 | ちいかわ | 鬼滅の刃 | すみっコぐらし |
|---|---|---|---|
| 2019 | 0 / 0 | 14.6 / 41 | 0.9 / 3 |
| 2020 | 0 / 0 | 54.3 / 100 | 1.1 / 2 |
| 2021 | 1.4 / 2 | 23.2 / 40 | 1.3 / 3 |
| 2022 | 7.6 / 13 | 9.2 / 23 | 1.4 / 2 |
| 2023 | 14.8 / 20 | 8.7 / 17 | 1.5 / 3 |
| 2024 | 14.1 / 18 | 7.2 / 16 | 1.2 / 2 |
| 2025 | 14.9 / 20 | 16.1 / 53 | 1.2 / 2 |
| 2026（〜10 月） | 30.9 / 76（8 月） | 6.2 / 8 | 1.0 / 1 |

妖怪ウォッチ（別スケール、2014-08＝100 付近）: 2013 年平均 0.9 → 2014 46.4（最大 86、12 月 81） → 2015 27.5 → 2016 18.3。

### 読み（inferred）
- ちいかわは 2022-04（アニメ開始）で段差を作った後、2023〜2025 の 3 年間を**ほぼ同じ高さの台地**で過ごし、2026-07 の映画で初めて「山」を作った。鬼滅（2020-10 の山から 1 年で 1/4）や妖怪ウォッチ（2014 の山から 2 年で 1/3）の「山→減衰」型とは形が異なる。
- すみっコぐらしは同スケールでは 1〜3 と小さく、検索量ではブームとして観測されない（雑貨中心・「調べる」動機が薄い IP）。子ども調査では女児 1 位を 2018〜2024 の長期にわたり取っており、検索インタレストと子ども人気は別の指標であることを示す。
- ちいかわの台地期（2023〜2025）の年平均 14〜15 は、鬼滅の 2022〜2024 の 7〜9 を上回る。「検索の山」はないが、日常的な検索量は鬼滅の余熱期より高い。

### 年間検索ランキングでの不在（確認済み）
- Google 日本 年間検索ランキング（急上昇）: 2022（総合・アニメ・映画含む 10 カテゴリと 47 都道府県）、2023（アニメ 1 位 推しの子）、2024（本文記載分）、2025（総合・映画 1〜2 位・アニメ 1〜2 位・ぬいぐるみ等）のいずれにも「ちいかわ」はテキストで確認できない。2024・2025 のアニメ・映画 3 位以下は画像のみで未確認 — [2022](https://blog.google/intl/ja-jp/products/explore-get-answers/2022_12_year-in-search-2022)、[2023](https://blog.google/intl/ja-jp/products/explore-get-answers/year-in-search-2023/)、[2024](https://blog.google/intl/ja-jp/products/explore-get-answers/year-in-search-2024)、[2025](https://blog.google/intl/ja-jp/products/explore-get-answers/year-in-search-2025/)、[2025 映画 3 位は「近畿地方のある場所について」（ORICON）](https://www.oricon.co.jp/news/2422344/full/)
- Yahoo! 検索大賞 2019〜2025（アニメ・映画・ネクストブレイク部門含む）: ちいかわ・すみっコぐらしは一度も登場しない。鬼滅は 2019・2020 アニメ 1 位、2020 映画 1 位。SPY×FAMILY 2022、推しの子 2023 アニメ 1 位 — [Wikipedia Yahoo!検索大賞](https://ja.wikipedia.org/wiki/Yahoo!検索大賞)、[2022 公式](https://about.yahoo.co.jp/pr/release/2022/12/05a/)
- SNS 流行語大賞（イー・ガーディアン）: 2019 大賞「平成最後の」、2020「StayHome」、2022 大賞「〇〇ってコト!?」（ちいかわ）。鬼滅は大賞ではない — [2019](https://www.e-guardian.co.jp/info/docs/df4ceb38fe278bc35fd58f55d278c584b3d65188.pdf)、[2020](https://www.e-guardian.co.jp/info/docs/222fdb043b52b1f85c1f710f8c4020e2159320fe.pdf)、[2022](https://internet.watch.impress.co.jp/docs/news/1461773.html)
- Twitter トレンド大賞 2022 はランキング形式をやめ複数トレンド列挙（アーニャ等）で、ちいかわの記載は確認できず — [ABEMA TIMES](https://times.abema.tv/articles/-/10007856)

## Gaps
- Kids/ex 2019・2020 年調査（2020-01・2021-01 発表）の一次資料は未取得（Digest plus の記事一覧に 2019・2020 年版なし）。鬼滅の子ども 1 位の初年が 2020 か 2021 か未確定。
- バンダイ こどもアンケートの原 PDF（Vol.37・142・190・222）は 2026-10-24 時点でサーバメンテナンスのため本文未読。検索抜粋・転記記事で代替。
- 日経MJ 番付の前頭（ちいかわ 2022・すみっコ 2019・SPY×FAMILY 2022）と日経トレンディ 1997 は二次情報。日経 MJ 紙面（2022-12-07 付ほか）での確認が必要。
- Google 年間ランキング 2024・2025 のアニメ・映画 3 位以下（画像）、ライセンシングアワード（LIMA Japan）のちいかわ受賞歴は未確認。
- Google Trends は「ちいかわ」1 語のみ。「映画ちいかわ」「ハチワレ」等の派生語を含めた合算は行っていない。
