# theme: parliament-size
設計: `design/themes/parliament-size.md`。
```bash
uv run socioscope run parliament-size fetch   # IPU Parline API、総務省 結果調 Excel（第 45〜51 回 × 5 表）、e-Stat 国勢調査 2020 表 2-1 ＋ 長期人口、財務省 予算書 PDF、内閣法制局 HTML、World Bank WDI 名目 GDP・人口、ParlGov 2024、UK Bills API（41 ページ）、仏 AN ドシエ zip（第 16・17 期）、ILOSTAT 公務就業者・平均月収、IPSS 将来推計人口、イタリア下院 SPARQL、国会会議録 API（84 ページ）、OECD Government at a Glance 2025（SDMX-JSON、公的財政＋信頼）
uv run socioscope run parliament-size stage   # → data/staged/{ipu,soumu,estat,mof,clb,worldbank,parlgov,ukbills,fran,ilostat,ipss,camera,kokkai,oecd}/*.parquet
uv run socioscope run parliament-size mart    # → data/marts/{ipu_parliaments,jp_hr_*,jp_census2020_prefecture,jp_population_longterm,jp_budget_by_organ,jp_bill_counts,wdi_gdp_lcu,wdi_population,parlgov_elections,uk_acts,fr_laws,ilo_emp_public_admin,ilo_emp_public_sector,jp_prefecture_projection,it_laws_by_year,it_sittings_by_year,wdi_gdp_pcap_lcu,ilo_earnings_monthly,jp_hr_sitting_days,oecd_gov_finance,oecd_gov_trust}.parquet
uv run socioscope run parliament-size fetch --only ipu_parline   # ソースを絞る（ipu_parline / soumu_senkyo / estat_census / mof_budget / clb_bills / worldbank_wdi / parlgov / uk_bills / fr_an_dossiers / ilostat / ipss_regional / camera_it / kokkai_ndl / oecd_gov_glance）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261027_r1_ratio.py      # R1（H1・H1b・H1c）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261027_r2_pr_blocks.py  # R2（H3・H3b・H3c・H4・H4b）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261027_r3_cost.py       # R3（H5・H5b）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261027_r4_history.py    # R4（H6）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261027_r5_roles.py      # R5（H2）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261028_r6_pr_history.py # R6（事後追加 H3d・H3e・H4c・H4d: 7 選挙の比例試算、小選挙区の格差の下限）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261028_r7_roles_gdp.py  # R7（事後追加 H2c・H5c: 質問主意書、議会費の対 GDP 比）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261028_r8_member_bills.py # R8（事後追加 H2d: 日英仏の議員立法シェア）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261028_r9_seats_history.py # R9（事後追加 H6b: 1990 年以降の定数変更 × 人口変化）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261028_r10_bureaucracy.py # R10（事後追加 H2e: 公務就業者 × 議員数）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261029_r11_alternatives.py # R11（事後追加 H8・H9・H10: 代替案の数字）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261029_r12_future_disparity.py # R12（事後追加 H11: 将来人口での格差）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261029_r13_after_cuts.py # R13（事後追加 H7: 削減後の議会）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261029_r14_pay_and_workload.py # R14（事後追加 H12・H13: 基本給の相対水準、稼働日数）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261029_r15_small_parties.py # R15（事後追加 H14: 小政党の入口機能・阻止条項・泡沫政党の票）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261029_r16_government_size.py # R16（番外編 H15: 議会の大きさ × 政府の大きさ、図 2 枚）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261030_r17_system_oversight_trust.py # R17（番外編 H16: 選挙制度・議員 1 人当たりの監視対象・信頼、図 3 枚）
```
