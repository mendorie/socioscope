# theme: essential-work-wages
設計: `design/themes/essential-work-wages.md`（2026-10-29、H0〜H6 事前登録。結果の記録節に R1〜R4 の判定）。
```bash
uv run socioscope run essential-work-wages fetch   # 賃金構造基本統計調査 職種別 2009–2025、Census ACS B24121–26 2021–2024、Dingel–Neiman、職業別労働市場関係指標（2 ファイル）、Eurostat SES（4）・nama（2）、OECD 医療職報酬、ILOSTAT 争議（4 指標）、法人企業統計 FY2012–22、国勢調査 2020 職業×性、労働組合基礎調査 PDF 2012–2025、労働争議統計 2012–2024
uv run socioscope run essential-work-wages stage   # → data/staged/{bsws,acs,dingel_neiman,jobs,ses,nama,oecd_health_remun,ilo_strikes,mof_hojin,estat_census2020,mhlw_unions,mhlw_disputes}/*.parquet
uv run socioscope run essential-work-wages mart    # → data/marts/{bsws_occupation_wages,acs_occupation_earnings,us_occupation_teleworkable,jobs_occupation_{monthly,annual},ses_occupation_{industry_,}earnings,nama_industry_value_added_employment,oecd_health_remuneration,ilo_strikes_by_industry,hojin_industry_annual,jp_census2020_occupation_sex,jp_union_density_by_industry,jp_labour_disputes_by_industry}.parquet
uv run socioscope run essential-work-wages fetch --only estat_bsws   # ソースを絞る（estat_bsws / census_acs1 / dingel_neiman / mhlw_jobs / eurostat_ses / eurostat_nama / oecd_health_remun / ilo_strikes / mof_hojin / estat_census2020 / mhlw_unions / mhlw_disputes / wdi_health）
uv run python themes/essential-work-wages/src/theme_essential_work_wages/analysis/a20261029_r1_paradox.py      # R1（H1・H1b・H2・H5・H0、日本・米国）
uv run python themes/essential-work-wages/src/theme_essential_work_wages/analysis/a20261029_r2_rents.py        # R2（H6、欧州 SES × 国民経済計算、日本の規模プレミアム）
uv run python themes/essential-work-wages/src/theme_essential_work_wages/analysis/a20261030_r3_admin_price.py  # R3（H3・H3b、日本の求人倍率 × 賃金、介護職の差分の差分）
uv run python themes/essential-work-wages/src/theme_essential_work_wages/analysis/a20261030_r4_strikes.py      # R4（H4・H4b、争議）
uv run python themes/essential-work-wages/src/theme_essential_work_wages/analysis/a20261030_r5_mechanisms.py   # R5（事後追加 H7〜H10: 女性化・定員制限・介護の構成・変化どうし）
uv run python themes/essential-work-wages/src/theme_essential_work_wages/analysis/a20261030_r6_public_share.py # R6（H3c: 公的シェア × 看護師相対賃金、WDI）
```
定義表（賃金を見る前に固定）: `src/theme_essential_work_wages/{jp_occupation_flags,jp_occupation_flags_2009,us_occupation_flags}.csv`、区分対応 `jp_jobs_category_map.csv`、改定日 `jp_care_policy_events.csv`、最低賃金 `jp_minimum_wage.csv`、国勢調査対応 `jp_bsws2020_census_map.csv`。
