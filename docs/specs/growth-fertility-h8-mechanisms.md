# H8 分析プラン: 死亡率低下と女子教育は「どの仕組みで」出生率を下げるのか（growth-fertility、最終回）

状態: **承認済み（2026-10-17、ユーザーは part3 を自律的に進めてよいと明示）**。「仮説と判定基準」節を `design/themes/growth-fertility.md` に H8 として事前登録し、plan manifest（`growth-fertility-h8-mechanisms.plan.yaml`）を起こす。
作成: 2026-10-17。前提記事: `docs/articles/2026-10-13-note-why-rich-countries-have-fewer-children.final.md`（part2）、前提レポート: `themes/growth-fertility/reports/2026-10-13-h7-between-gradient.md`。

---

## 0. 問いと、この記事が出す「答えの形」

### 問い（1 文）
**子どもの死亡率の低下と女子の就学の広がりが出生率低下の先行指標になるのは、どの仕組みを通じてか。そしてその仕組みは、出生率を「2 人程度」までではなく「2 人未満」まで下げることを説明できるか。**

### 出発点の仮説（part2 の「先行指標の背景にある仕組み」節より）
| 記号 | 仕組み | 要するに | 予測されること |
|---|---|---|---|
| **M1** | 保険としての多産が要らなくなる | 子どもが死ななくなれば、望む数を得るための出生数が減る。望む数そのものは下げないので 2 人程度までしか説明できない | 同じ国の中で死亡率が下がると、「理想の子ども数」または「理想を超える出生」が減る。死亡率が低い調査では TFR が理想を下回る（＝理想だけでは低出生率を説明できない） |
| **M2** | 結婚しなくても収入を得られる女性が増える | 女子の就学 → 晩婚・非婚 → 出産できる期間が短くなる | 学歴が高いほど初婚年齢が高い。同じ国の中で女性の学歴が上がると結婚（同棲含む）している女性の割合が下がり、TFR 低下の一部は「結婚している割合の低下」で説明できる |
| **M3** | 子育ての機会費用が上がり「数より質」へ | 学歴が高いほど望む数が少ない | 学歴勾配は「望む出生」（wanted TFR）に現れ、「望まない出生」（TFR − wanted）には現れない |
| **M4** | M1 × M3 の相互作用 | 子どもが確実に育つと教育投資が報われ、「数より質」が進む | 死亡率が低い社会ほど、学歴による望む数の差が大きい |
| **M5**（対抗仮説、設計時に追加） | 家族計画の普及 | 教育は「望む数」ではなく避妊の知識・アクセスを通じて望まない出生を減らしているだけかもしれない | TFR 低下の大半が「望まない出生」の減少。学歴勾配は望まない出生に現れる |

M5 は part2 の仮説リストには無かったが、M2〜M3 の対抗仮説として**データを見る前に**加える。M1〜M5 は排他的ではなく、答えは「どの仕組みがどの段階でどれだけ」の形で書く。

### 答えの形（事前に固定する最終仮説のテンプレート）
最終回なので、要約の第 1 文は次の型で **断定形** に書く（数値は結果で置換）:

> 「出生率が 6 人から 3 人前後へ下がる段階は、子どもの死亡率の低下（M1）と女子教育による『望む数』の低下（M3）が担い、望まない出生の減少（M5）は △割にとどまる。3 人前後から 2 人未満へ下がる段階は、女子教育が結婚を遅らせ減らすこと（M2）が □割を担い、死亡率はもう効いていない。」

段階（6→3、3→2 未満）ごとに、主役の仕組みと量（割合）を 1 つずつ名指しする。「どちらとも言えない」を第 1 文に置かない。各仕組みの「支持／部分的支持／不支持」は §3 の判定基準で機械的に決める。

### 執筆規律（part2 と同じ）
1. 見出しと要約第 1 文は上のテンプレートで断定形。
2. 判定は §3 の基準で決め、結果を見てから動かさない。追加の検定は「探索的」と明記する。
3. 限界は「結論を覆しうる条件」に限り 3 項目以内。
4. 因果語: 識別戦略は固定効果・調査内の学歴比較・分解に限る。「最も整合的な仕組み」として断定し、「因果を証明した」とは書かない。
5. 読者向け記事では事前登録・方法論の手続きを強調しない（レポートには残す）。

---

## 1. データ

### 1a. DHS Program Indicator Data API（既存 adapter `dhs.py` を複数指標・複数内訳に拡張。新 mart `marts/dhs_mechanisms`）
対象は低・中所得 86〜87 か国、1985〜2025 年の 320〜368 調査（DHS/MIS/AIS）。API キー不要、**引用義務**（`dhs.LICENSE`）。1 リクエスト = 1 指標（群）× 1 内訳で、`perpage=5000` を超えるページ分割は fail-closed。既存 raw・mart（`dhs_tfr_by_wealth_quintile`）は変更しない。

| metric（mart の `metric` 列） | IndicatorId | 内訳（CharacteristicCategory） | 用途 |
|---|---|---|---|
| `tfr` | `FE_FRTR_W_TFR` | Total / Education / Wealth quintile | 全検定 |
| `asfr_15` … `asfr_45` | `FE_FRTR_W_A15` … `FE_FRTR_W_A45` | Total | T3 の結婚指数（Bongaarts Cm） |
| `wanted_tfr` | `PR_WTFR_W_WFR` | Total / Education / Wealth quintile | T1・T4・T5 |
| `ideal_children` | `PR_IDLC_W_MNA` | Total | T2 |
| `want_no_more` | `PR_DESC_W_WNM` | Total 15-49 | T2 の補助 |
| `u5mr` | `CM_ECMR_C_U5M` | Total / Education / Wealth quintile（`by_variable` = 調査前 5 年／10 年、`is_preferred` を保持） | T2・T5 |
| `age_first_marriage` | `MA_AAFM_W_M2B`（女性 25–49 の中央値） | Total / Education / Wealth quintile | T3 |
| `never_married_25_49` | `MA_MBAG_W_NMA` | Total 25-49 / Age (5-year groups) | T3 の補助 |
| `in_union` | `MA_MSTA_W_UNI` | Total 15-49 / Age (5-year groups) | T3 の結婚指数 |
| `women_secondary_plus` | `ED_EDUC_W_SEH` | Total 15-49 | 調査レベルの女性学歴（within 回帰の説明変数） |
| `modern_contraception_married` | `FP_CUSM_W_MOD` | Total / Education | T4 の M5 補助 |

mart の列: `iso3, country, dhs_country_code, survey_id, survey_year, survey_type, indicator_id, metric, characteristic_category, characteristic_label, by_variable, is_preferred, value, ci_low, ci_high, denominator_weighted, source`。long 形式、`survey_year, iso3, survey_id, metric, characteristic_category, characteristic_label, by_variable` でソート。学歴ラベルは `No education / Primary / Secondary / Higher`（4 群）をそのまま保持する。

### 1b. WDI（`worldbank.INDICATORS` に 4 本追加。adapter 追加なし）
| 列 | コード | 用途 | 注意 |
|---|---|---|---|
| `smam_fe` | `SP.DYN.SMAM.FE`（女性の平均初婚年齢、UN World Marriage Data 由来） | T6（全世界パネルの結婚チャネル） | 2,073 国・年、212 か国、1970–2018 が中心。**出典混在で跳ぶ値がある**（例: フランス 2005 31.0 → 2008 22.7 → 2012 32.0）。事前固定の整形規則: 同一国に 3 観測以上あるとき、その国の中央値から 4 年以上離れた値を落とし、落とした件数を報告する |
| `wanted_tfr_wdi` | `SP.DYN.WFRT` | T1 の照合（DHS 由来のはず） | 323 国・年、95 か国 |
| `married_by18` | `SP.M18.2024.FE.ZS`（20–24 歳女性のうち 18 歳未満で結婚した割合） | T6 の結婚チャネルの頑健性 | 465 国・年、173 か国 |
| `contraceptive_any` | `SP.DYN.CONU.ZS`（既婚女性の避妊実行率、全方法） | T6 の M5 チャネル | 1,366 国・年、222 か国 |

### 1c. 既存 mart（追加取得なし）
`growth_fertility_panel`（WDI）、`eu_tfr_by_education`（欧州の学歴別 TFR、H5）、`eu_census_marital_by_education`（欧州 2021 センサスの学歴別有配偶率、H5）、`jp_income_age_marital`（日本、H3b）。2 人未満の段階（T6）の補助記述に使う。

---

## 2. 推定したい量（事前固定）
1. **望む／望まないの分解**: 同じ国の隣り合う調査の間の ΔTFR = Δwanted + Δ(TFR − wanted)。望む出生の減少が占める割合 s_w（低下した組を合算）。
2. **結婚の分解**: Bongaarts の結婚指数 Cm = Σ_a m_a f_a / Σ_a f_a（m_a = 5 歳階級 a で「結婚または同棲中」の女性割合、f_a = ASFR）。Δln TFR = Δln Cm + Δln(TFR/Cm)。結婚の割合低下が占める割合 s_m。
3. **死亡率の within 係数**: 同じ国の調査間で ln U5MR が 1 下がるとき（ほぼ 1/e = 63% 低下）の TFR・理想数・（TFR − 理想）の変化。
4. **学歴勾配**: 調査内の Secondary − No education（主）、Higher − No education（補助）の wanted TFR・unwanted・初婚年齢・避妊実行率の差。
5. **交互作用**: 学歴勾配（wanted TFR）が調査の U5MR 水準でどう変わるか。
6. **全世界パネルの標準化係数**: 10 年長期差分で ΔTFR に対する Δln U5MR・Δ女子中等就学率・Δ初婚年齢・Δln GDP の標準化係数を、TFR ≥ 3 の段階と < 3 の段階で分けて推定。

---

## 3. 検定（T1〜T6）と判定基準

全検定は `analysis/a20261017_h8_mechanisms.py`（仮）で決定的に実行し、各判定を標準出力に出す。SE は国クラスタ（DHS は国、WDI は国）。「学歴」は DHS の女性本人の学歴 4 群。DHS の within 回帰は国 FE ＋ 調査年の線形トレンドを含む。

### T1. TFR 低下は「望む出生」と「望まない出生」のどちらで起きたか（M5 を切り分ける）
- 対象: 同じ国の隣り合う調査の組で、TFR と wanted TFR が両方あり、調査間隔 ≥ 3 年。
- 出力: s_w = Σ Δwanted / Σ ΔTFR（ΔTFR < 0 の組を合算）。組ごとの比の中央値も併記。first→last（≥ 8 年）版を頑健性に。
- **判定**: s_w ≥ 0.6 → 「望む数の低下が主」（M1/M3 が主役、M5 は従）。s_w ≤ 0.4 → M5「支持」（望まない出生の減少が主）。0.4–0.6 → 混合と記述し、M5 は「部分的支持」。

### T2. 死亡率低下は「望む数」と「余分な出生」のどちらを減らすか（M1）
- (a) within 回帰: `ideal_children ~ ln u5mr + women_secondary_plus + 国 FE + 年トレンド`（U5MR は `is_preferred` = 調査前 5 年の Total）。
- (b) `tfr − ideal_children ~` 同じ右辺。
- (c) `tfr ~ ln u5mr + women_secondary_plus + 国 FE + 年トレンド`（(a)+(b) の合計に等しい）。
- (d) M1 の上限: U5MR < 40（出生千対）の調査に絞り、理想数の中央値・TFR の中央値・TFR < 理想数 の調査の割合。
- **判定**: (c) の ln U5MR 係数が正で 95% CI が 0 を含まず、係数 ≥ +0.25（ln U5MR が 1 下がると TFR が 0.25 以上下がる）→ M1「支持」。0.10 ≤ 係数 < 0.25（CI は 0 を含まない）→ 「部分的支持」。それ以外 → 「不支持」。
- 補足記述（判定に入れない）: 係数の大半が (a) に乗るなら「望む数そのものが下がる（蓄え行動）」、(b) に乗るなら「望む数は変わらず余分な出生が減る（補充行動）」と書く。(d) で TFR < 理想数 の割合 ≥ 50% なら「死亡率が低い社会では望む数より少なく産んでおり、M1 だけでは低出生率を説明できない」と書く（part2 の『2 人程度まで』の主張の検証）。

### T3. 女子教育は結婚を遅らせ減らし、それが TFR 低下の何割か（M2）
- (a) 調査内の学歴勾配: 初婚年齢中央値（25–49 歳）の Secondary − No education、Higher − No education。全調査の中央値と、Secondary − None ≥ +2 年の調査の割合。
- (b) 結婚指数: Cm を ASFR（7 階級）と「結婚または同棲中」割合（5 歳階級）から計算。同じ国の first→last 調査（≥ 8 年、TFR 低下）で Δln TFR = Δln Cm + Δln(TFR/Cm)。s_m = Σ Δln Cm / Σ Δln TFR。
- (c) within 回帰: `Cm ~ women_secondary_plus + ln u5mr + 国 FE + 年トレンド`。
- **判定**: (a) の割合 ≥ 70% かつ s_m ≥ 0.25 → M2「支持」。(a) の割合 ≥ 50% かつ 0.10 ≤ s_m < 0.25 → 「部分的支持」。s_m < 0.10 または (a) の割合 < 50% → 「不支持」。
- 注意: Cm は「結婚」ではなく「結婚または同棲」。婚外出生の多い中南米・南部アフリカを除いた版を頑健性に。

### T4. 教育の学歴勾配は「望む数」に出るか「望まない出生」に出るか（M3 vs M5）
- 調査 × 学歴セル（4 群）のパネル。`wanted_tfr_{s,e} = 調査 FE + 学歴ダミー`、`unwanted_{s,e} = tfr_{s,e} − wanted_tfr_{s,e} = 調査 FE + 学歴ダミー`。g_w, g_u = Secondary − No education の係数。Higher − No education も併記。
- 補助: `modern_contraception_married` の学歴勾配（M5 の経路の確認）。
- **判定**: g_w ≤ −1.0（CI は 0 を含まない）かつ |g_w| ≥ 2|g_u| → M3「支持」。g_w ≤ −0.5 かつ |g_w| > |g_u| → 「部分的支持」。|g_u| ≥ |g_w| → M3「不支持」かつ M5 に「支持」を追加（T1 と合わせて M5 の最終判定は、T1 と T4 の両方で支持なら「支持」、片方なら「部分的支持」、どちらも無ければ「不支持」）。

### T5. 死亡率が低い社会ほど学歴による望む数の差は大きいか（M4）
- 調査 × 学歴セル: `wanted_tfr_{s,e} = 調査 FE + 学歴ダミー + 学歴ダミー × ln u5mr_s`（u5mr_s は調査の Total、preferred）。
- 出力: (γ_Secondary − γ_None) の点推定と CI、U5MR 150 → 30 の間で学歴勾配が何人分広がるか。
- **判定**: (γ_Sec − γ_None) > 0 で CI が 0 を含まず、U5MR 150→30 で勾配が ≥ 0.3 人分広がる → M4「支持」。符号が正で CI が 0 を含む、または広がりが 0.1–0.3 → 「部分的支持」。それ以外 → 「不支持」。
- 頑健性: ln u5mr の代わりに富裕五分位の u5mr を使わない（学歴と富の混同を避けるため Total のみ）。WDI パネル版: Δ₁₀TFR ~ Δ₁₀fem_sec_enrol × 1[U5MR 開始値 < 50] + 国 FE + 期間 FE。

### T6. 2 人未満への段階では何が効いているか（全世界 WDI パネル）
- 10 年長期差分（1970–2020 の重ならない区間）、国 FE ＋ 期間 FE、国クラスタ SE: `Δ₁₀tfr ~ Δ₁₀ln u5mr + Δ₁₀fem_sec_enrol + Δ₁₀smam_fe + Δ₁₀ln gdp_pcap_const`。標準化係数を報告。
- 段階で分割: 区間開始時の TFR ≥ 3（第 1 段階）と < 3（第 2 段階）。
- 補助記述: `eu_tfr_by_education`（ED5-8 − ED0-2 の TFR 差の最新年）、`eu_census_marital_by_education`（女性 25–39 の学歴別有配偶率、H5 再掲）、日本（H3b 再掲）。新しい推定はしない。
- **判定**（段階 2 の主役を決める）: 第 2 段階で標準化係数の絶対値が最大の変数を主役とする。初婚年齢が最大（CI は 0 を含まない） → 「2 人未満の段階は M2 が主役」。女子就学率が最大 → 「M3 が主役」。死亡率が最大 → 「M1 がまだ効いている」。所得が最大 → 「段階 2 では豊かさの効果が残る」。どの係数も CI が 0 を含むとき → 「段階 2 は本データの変数では説明できない」と書く（これも断定）。
- 頑健性: 5 年・20 年差分、SMAM 整形規則なし、`married_by18` を SMAM の代わりに、`contraceptive_any` を追加、2020–24 除外、産油国除外、人口 100 万未満除外。

### スコアカード（事前固定）
| 仕組み | 検定 | 支持 | 部分的支持 | 不支持 |
|---|---|---|---|---|
| M1 保険としての多産 | T2(c) | 係数 ≥ +0.25 | 0.10–0.25 | 他 |
| M2 結婚の遅れ・減少 | T3 | 勾配 ≥ 70% かつ s_m ≥ 0.25 | ≥ 50% かつ 0.10–0.25 | 他 |
| M3 望む数の低下 | T4 | g_w ≤ −1.0 かつ \|g_w\| ≥ 2\|g_u\| | g_w ≤ −0.5 かつ \|g_w\| > \|g_u\| | \|g_u\| ≥ \|g_w\| |
| M4 相互作用 | T5 | γ 差 > 0、CI 0 含まず、広がり ≥ 0.3 | 符号正で CI 0 含む／広がり 0.1–0.3 | 他 |
| M5 家族計画 | T1 + T4 | 両方で支持 | 片方 | どちらも無し |

最終仮説の文は §0 のテンプレートに、段階 1 の主役（T1・T2・T4 の結果で M1/M3/M5 から選ぶ）、段階 2 の主役（T6 の判定）、各割合（s_w, s_m, T6 の標準化係数の比）を埋めて書く。段階 1 の主役は「支持」を得た仕組みのうち、T1 の分解で量が大きい側（s_w ≥ 0.5 なら M1/M3 側、< 0.5 なら M5）。M1 と M3 の優劣は T2(c) の ln U5MR 係数 × 典型的な ln U5MR の低下幅（1990→最新の中央値）と、T4 の g_w × 女性の中等以上学歴割合の典型的な上昇幅（同期間の中央値）を比べて量で書く（どちらが大きいかで「主」「従」）。

### 見出し文のテンプレート（結果を見る前に用意）
- M1・M3 支持、M2 が段階 2 の主役: 「出生率が 6 人から 3 人へ下がる局面では、子どもが死ななくなって『保険としての多産』が要らなくなり、学校に行った女性ほど望む数が減った。2 人を切る局面を動かしているのは結婚の遅れで、死亡率はもう関係ない。」
- M5 支持: 「出生率を下げた主役は望まない出生の減少、つまり避妊の普及だった。教育は望む数を変えるより先に、望まない出生を減らしている。」
- M2 不支持: 「女子教育は結婚を遅らせるが、出生率を下げた経路はそこではない。結婚している女性の中で望む数が減ったことが主で、結婚の減少は □割にすぎない。」
- 段階 2 がどの変数でも説明できない場合: 「2 人未満への低下は、死亡率・教育・初婚年齢・所得のどれでも説明できない。この段階では本シリーズの変数の外にある要因（H6 で見た理想の低下など）が動いている。」

---

## 4. 頑健性（事前リスト。全部報告する）
- DHS: 調査種別を DHS に限定（MIS/AIS 除外）、隣接組 vs first→last、調査間隔 ≥ 8 年、U5MR の 10 年版、中南米・南部アフリカ除外（Cm）、国ごとの等加重（調査数で加重しない）、1990 年以降に限定、学歴 2 群版（Education (2 groups)）。
- WDI: 5 年・20 年差分、SMAM 整形なし、`married_by18`、`contraceptive_any` 追加、2020–24 除外、産油国除外（H1 の `OIL_STATES`）、人口 100 万未満除外、段階の境界を TFR 2.5 / 3.5。

## 5. 言えないこと（事前固定。記事では 3 項目以内に圧縮）
- 調査内の学歴比較は自己選択を含む（望む数が少ない女性が学校に残る）。学歴の「効果」ではなく「学歴差」。
- 理想・希望の子ども数は事後の合理化を含む（産んだ数に理想を合わせる）。wanted TFR の定義（妊娠時点の生存子数 < 理想数なら望む出生）に依存する。
- Cm は結婚ではなく「結婚または同棲」。婚外出生の多い地域では結婚の寄与を過小評価する。
- DHS は低・中所得国のみ。2 人未満の段階は WDI の国レベル（初婚年齢系列は出典混在）と欧州・日本の既存集計に頼る。
- 識別戦略は固定効果・分解・調査内比較のみ。家族計画プログラムや規範の変化が死亡率・教育・出生率を同時に動かしうる。

## 6. 成果物と PR 分割（plan manifest）
| id | 内容 | agent | depends_on |
|---|---|---|---|
| `h8-design` | design に H8 を事前登録、本 spec、plan manifest | （本セッション） | — |
| `h8-wdi-marriage` | `worldbank.INDICATORS` に 4 本追加、fixture・テスト、CLAUDE.md、`design/data-sources.md`、再取得・再生成 | pipeline-dev | h8-design |
| `h8-dhs-mechanisms` | `dhs.py` を複数指標 × 内訳に一般化（既存関数は維持）、`pipeline.py` に `# ---- H8` ブロック、staged `staged/dhs/mechanisms`、mart `marts/dhs_mechanisms`、fixture・テスト、CLAUDE.md、`design/data-sources.md`、取得・生成 | pipeline-dev | h8-design |
| `h8-analysis` | `analysis/a20261017_h8_mechanisms.py`、T1〜T6・スコアカード・最終仮説の文、図、report、methodology-reviewer | analyst | h8-wdi-marriage, h8-dhs-mechanisms |
| `h8-summary-figs` | `analysis/s20261017_h8_summary.py`、一般読者向け日本語図 6 枚以内 | analyst | h8-analysis |
| `h8-article` | note 記事（part3、最終回）＋ ヘッダー画像（`docs/articles/headers/make_headers.py`） | analyst → yomiyasu | h8-summary-figs |

`h8-wdi-marriage` と `h8-dhs-mechanisms` は並列（`pipeline.py` は WDI 側が触らない。CLAUDE.md・data-sources.md は両方が追記するので merge 時に手で解決）。

## 7. 記事の構成案（結論を先に）
1. 答え（最終仮説の文）。
2. part2 で残した 4 つの仮説と、今回加えた対抗仮説（避妊の普及）。それぞれなら何が見えるはずか。
3. 証拠 1: 低下の内訳 — 望む出生の減少か、望まない出生の減少か（T1）。
4. 証拠 2: 子どもが死ななくなると何が変わるか — 望む数か余分な出生か（T2）。死亡率が低い国では望む数より少なく産んでいる。
5. 証拠 3: 学校に行った女性は遅く結婚し、結婚の減少は低下の何割か（T3）。
6. 証拠 4: 学歴の差は「望む数」に出る（T4）。死亡率が低いほどその差は大きい（T5）。
7. 証拠 5: 2 人未満へ下がる局面で効いているもの（T6、欧州・日本の再掲）。
8. 最終仮説の再掲、覆しうる条件 3 つ、シリーズの締め（part1〜3 で分かったことの 5 行）。
