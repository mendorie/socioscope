# parliament-size 追加分析への引き継ぎ（2026-10-27 時点）

次セッションで追加分析を始める人（エージェント）向けのメモ。このテーマの現状、使えるもの、未着手の論点、落とし穴を一枚にまとめる。読む順は `design/themes/parliament-size.md` → 本書 → `themes/parliament-size/CLAUDE.md`。

## 0. 追加分析の進捗（2026-10-28）
- 論点 2（比例試算の 7 選挙への拡張。行動変化の識別は 2017 年の 4 減では不可能と判明、記述のみ）→ **R6** `themes/parliament-size/reports/2026-10-28-r6-pr-history.md`（H3d 頑健・H3e 記述）。結果調 Excel を第 45〜49 回に拡張（第 42〜44 回は Excel 無し）。
- 論点 3（選挙区単位の格差）→ **R6**（H4c 整合: 都道府県単位の下限は 230 まで 2 倍未満だが、2022 年区割りの上乗せ係数 1.19 で 260 は 2.26 倍）。
- 論点 5（H5b の対 GDP 比）→ **R7** `themes/parliament-size/reports/2026-10-28-r7-roles-gdp.md`（H5c 整合、4/17 位）。WDI `NY.GDP.MKTP.CN` を `worldbank.py` で結線。
- 論点 6（役割指標の補強）→ **R7**（H2c 不支持 ρ = 0.06。質問主意書は議員数と無関係）。IPU に 5 属性を追加。
- 論点 1（議員立法シェアの国際比較）→ **R8** `themes/parliament-size/reports/2026-10-28-r8-member-bills.md`（H2d 不支持: 英 21.5% ≈ 日 21.8% < 仏 50.9%）。UK Bills API と仏 AN ドシエ zip を結線。独（DIP）・米（Congress.gov）・韓は API 鍵が要り未着手。
- 論点 4（ParlGov）→ **R9** `themes/parliament-size/reports/2026-10-28-r9-seats-history.md`（H6b 不支持 r = 0.51。**R4 の各国判定を撤回**）。parlgov.org は 403 だが Harvard Dataverse の 2024 Release（CC0）から取れた。
- 論点 7（記事の仕上げ）→ 2026-10-28 に R6〜R9 を反映して `.final.md` とヘッダー画像を作成。
- 追加（立場の根拠、2026-10-29）→ **R11**（H8 整合・H9・H10）、**R12**（H11 整合）、**R13**（H7 イタリア不支持・ハンガリー判定不能）。立場の文書 `themes/parliament-size/reports/2026-10-29-position-parliament-size.md`。H3f（2000 年の前後）は第 42・43 回の資料が無く対象外。
- 追加（ユーザー提起「少数政党保護は原則か」H14、2026-10-29 夜）→ **R15** `themes/parliament-size/reports/2026-10-29-r15-small-parties.md`（H14a・H14b 整合）。立場文書とレポートのキーメッセージを「人数ではなく報酬・手当の水準と透明性」に改め、削減そのものは方式次第で問題ない可能性を明記。
- 追加（世論の検証 H12・H13、2026-10-29 夕）→ **R14** `themes/parliament-size/reports/2026-10-29-r14-pay-and-workload.md`（整合・整合）。国会会議録 API・ILOSTAT 賃金・WDI 1 人当たり GDP を結線。記事（論点 7・8、総括）に R11〜R14 と立場を反映済み。
- 追加（ユーザー提起 H2e、2026-10-28 夜）→ **R10** `themes/parliament-size/reports/2026-10-28-r10-bureaucracy.md`（ILOSTAT 公務就業者 × 議員数、ρ = +0.33 で向きは逆、判定は中間）。記事（論点 2・総括）にも反映済み。
- 事後追加の仮説と判定基準は `design/themes/parliament-size.md`「事後追加の仮説（2026-10-28）」に、結果の計算前に固定した。

## 1. 現状

- PR: https://github.com/mendorie/socioscope/pull/118（ブランチ `claude/japan-parliament-reduction-analysis-d74n37`、main 未マージ）。追加分析は **main にマージされた後に新ブランチで** 行う。マージ前に着手するなら同ブランチの先頭から派生する。
- 設計書 `design/themes/parliament-size.md` に H1〜H6 を事前登録し、6 本すべての結果と「事後の具体化」を追記済み。判定基準は変えていない。
- レポート 5 本 ＋ 総括 ＋ note 記事ドラフト:
  - R1 `themes/parliament-size/reports/2026-10-27-r1-ratio.md`（H1・H1b・H1c 整合）
  - R2 `.../2026-10-27-r2-pr-blocks.md`（H3・H3b・H3c 整合、H4・H4b 不支持）
  - R3 `.../2026-10-27-r3-cost.md`（H5・H5b 整合）
  - R4 `.../2026-10-27-r4-history.md`（H6 日本は 0.601 倍で基準 0.6 を僅差で不支持、各国は r = 0.24 で整合）
  - R5 `.../2026-10-27-r5-roles.md`（H2 (a) 整合 ρ = −0.42、(b) 判定不能）
  - 総括 `.../2026-10-27-summary-parliament-size.md`、記事 `docs/articles/2026-10-27-note-parliament-size.md`（yomiyasu 91/100、`.final.md` 未作成、ヘッダー画像未作成）
- 品質ゲート（ruff / mypy strict / pytest 259 件）green。各 analysis スクリプトは決定的で、2 回実行して stdout 一致を確認済み。

## 2. 使えるデータ（すべて fetch 済み、manifest に sha256 付き）

| mart | 中身 | 出典・ライセンス |
|---|---|---|
| `marts/ipu_parliaments`（281 行） | 議院ごとの定数・現員・職員数・予算（現地通貨と PPP）・基本給・本会議日数・委員会数・選挙制度、国の人口・OECD 加盟・議会予算÷政府予算 | IPU Parline API、**CC BY-NC-SA 4.0（非商用）** |
| `staged/ipu/chamber_attributes`・`country_attributes` | 上の元になる属性 × 期間のレコード（人口は 1950– 年次、定数の履歴は 2005– のみ） | 同上 |
| `marts/jp_hr_pr_results`（224 行） | 第 50・51 回衆院選の比例ブロック × 党派: 得票・公式議席・ブロック定数 | 総務省 結果調 Excel、政府標準利用規約 2.0 |
| `marts/jp_hr_seats_by_party`（28 行） | 党派別の小選挙区・比例当選人数（無所属含む） | 同上 |
| `marts/jp_hr_electorate`（94 行） | 都道府県別 有権者数（小選挙区・比例、ブロック付き） | 同上 |
| `marts/jp_census2020_prefecture`（47 行） | 2020 国勢調査 都道府県別 総人口・日本人人口（アダムズ方式の基礎。現行 289・176 を再現できることを検算済み） | e-Stat |
| `marts/jp_population_longterm`（81 行） | 総人口 1920–2000（日本人 1950–） | e-Stat 人口推計 長期時系列 |
| `marts/jp_budget_by_organ`（46 行） | 令和 7 年度 一般会計歳出 所管別（国会 1,315 億円、合計 115.2 兆円） | 財務省 PDF |
| `marts/jp_bill_counts`（39 行） | 第 183〜221 回国会の閣法・議員立法の提出・成立 | 内閣法制局 HTML |
| `src/theme_parliament_size/jp_member_costs.csv` | 議員 1 人当たり法定経費（出典列付き手入力） | 歳費法・秘書給与法ほか |
| `src/theme_parliament_size/jp_seats_history.csv` | 衆参定数の変遷 1890–2022（出典列付き手入力） | 法令・衆議院 HP |

純粋関数 `apportion.py`（ドント・修正サンラグ・アダムズ・Gallagher・参入閾値）は再利用できる。再現コマンドは `themes/parliament-size/README.md`。

## 3. 未着手の論点（優先度順の提案）

1. **H2 (b) 議員立法シェアの国際比較**（判定不能のまま）。候補: 各国議会の年報・統計（英 House of Commons Library「Acts and Statutory Instruments」、独 Bundestag「Datenhandbuch」、米 Congress.gov の sponsor 別統計、韓 국회 의안정보시스템）。構造化 API は無いので、国ごとに PDF／HTML の adapter が要る。取るなら「成立法律のうち議員提出の比率」に定義を揃え、委員長提出の扱いを明記する。
2. **比例試算への行動変化の織り込み**（R2 の最大の限界）。過去の定数変更（2000 年 比例 200→180、2017 年 176）の前後で小政党の擁立・得票がどう変わったかを第 42〜48 回の結果調で見る（第 42〜49 回の Excel は同じ `main_content/<id>` 形式で、`soumu.ELECTIONS` に id を足せば取れる。id は `senkyo/senkyo_s/data/shugiin<N>/index.html` を Shift_JIS で読んで解決）。
3. **一票の格差を選挙区単位で**（H4b は都道府県単位のみ）。小選挙区の区割りと選挙区別有権者数は結果調の「候補者別得票数」PDF または 3(13)、区割り改定後の格差は画定審の勧告 PDF。アダムズ 260 配分の下で区割りをどう引いても最小の最大格差（県内で均等に割った下限）は、都道府県別定数 ÷ 県内人口の最大最小から計算できる。
4. **H6 各国の定数履歴の深掘り**。IPU の記録は 2005 年以降で 1 件の国が 31 か国。各国の選挙法改正史（ParlGov の election データで議席総数の推移が取れる。CC BY 4.0）に置き換えると、1990 年代以降の定数変更と人口の関係を 30 年で見られる。
5. **H5b の対 GDP 比**。IPU の `chamber_budget` と WDI の GDP（現地通貨）で対 GDP 比を出せる（growth-fertility の `worldbank.py` と同じ URL 規約。テーマ間 import はしない）。COFOG 01.1 は執行機関と合算で使えなかった。
6. **H2 の役割指標の補強**。IPU に `num_written_question_ask`（質問主意書の数）、`is_carry_out_inquiries`、`members_government_number`（政府に入っている議員数）がある（`ipu.CHAMBER_ATTRS` に足せば staged に入る）。「議員の仕事の広さ」の代理として追加できる。
7. **記事の仕上げ**: `docs/articles/2026-10-27-note-parliament-size.md` を `/yomiyasu` で推敲して `.final.md` を作り、`docs/articles/headers/make_headers.py` にヘッダー画像を追加。画像挿入の指示は `reports/figures/r1〜r5_*.png` を指す。

## 4. 落とし穴（本セッションで踏んだもの）

- **IPU Parline の日本の定数履歴は誤り**（2005 年から 465 と記録。実際は 480 → 475 → 465）。R4 では手入力表で置き換えた。他国も疑って見る。
- **IPU の人口系列は 2016–2020 年を欠く**（日本）。判定年を 2020 年にしたい場合は e-Stat 人口推計を足す。
- **IPU の `country_name` は `{"en","fr"}` の辞書、`chamber_budget` は `{"type": 通貨, "value": 額}`、`other_groupings` は `[{"term": …}]`**。`ipu._text`/`_num`/`_unwrap` が処理する。sparse fieldset（`fields[...]`）は効かない。
- **結果調 Excel は第 50 回が .xls（得票が "694,578.943" の文字列）、第 51 回が .xlsx（数値）**。議席配分表は党が多いと同じブロックが複数チャンクに分かれる。公式議席は**名簿登載者不足の移転を含む**（2024 国民 3 議席、2026 自民 14 議席）ので、純ドントとの差を必ず併記する。
- **財務省 PDF は AES 暗号化**だが pypdf で空パスワード復号できる。所管別内訳は数値行が所管名より先に出るので順序依存（`mof.ORGANS`）。ページ番号「－ 2 －」が数値行に見える。
- **e-Gov 法令 API**: v1 `https://laws.e-gov.go.jp/api/1/lawdata/<law_id>` は XML を返す（歳費法 `322AC1000000080`、秘書給与法 `402AC1000000049`）。立法事務費交付法の ID は特定できず（328AC1000000112 / 328AC0000000112 とも 404）、65 万円/月は衆議院 HP の説明で確認した。HTML ページ（`/law/<id>`）は JS 描画で WebFetch では読めない。
- **サイトの挙動**: `data.ipu.org` の HTML ページはボット UA に 403 だが API は 200。`soumu.go.jp` は 200（robots は ia_archiver のみ拒否）。
- **設計時の誤り**: 「定数 2 の県は現行 0 県」と書いたが実際は 8 県（鳥取・島根・高知・徳島・福井・山梨・佐賀・和歌山）。設計書で訂正済み。
- **H6 の閾値**: 0.6 倍に対し実測 0.601〜0.605 で判定が割れた。事前基準は変えていないが、記事では「連動していない」と内容で説明している。追加分析で基準を見直すなら「事後」と明記する。
- **コンテナの制約**（このセッション固有）: Bash からの直接の curl／httpx は許可されず、`uv run socioscope run <theme> fetch` 経由だけがネットワークに出られた。WebFetch は要約を返し生 JSON は取れない。新ソースの様式確認は「adapter の fetch を先に書いて raw を取り、ローカルで dump する」順が早い。

## 5. 報道ベースの前提（分析時に再確認すること）

2026-10-27 時点: 比例 45 減（420）法案は与党了承・未成立、折衷案は比例 31 減（434）＋ 修正サンラグ式。成立・修正があれば `design/themes/parliament-size.md` の動機節と R2 の `PR_SCENARIOS` を更新する。
