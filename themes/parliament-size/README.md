# theme: parliament-size
設計: `design/themes/parliament-size.md`。
```bash
uv run socioscope run parliament-size fetch   # IPU Parline API、総務省 結果調 Excel（第 50・51 回 × 5 表）、e-Stat 国勢調査 2020 表 2-1 ＋ 長期人口、財務省 予算書 PDF、内閣法制局 HTML
uv run socioscope run parliament-size stage   # → data/staged/{ipu,soumu,estat,mof,clb}/*.parquet
uv run socioscope run parliament-size mart    # → data/marts/{ipu_parliaments,jp_hr_*,jp_census2020_prefecture,jp_population_longterm,jp_budget_by_organ,jp_bill_counts}.parquet
uv run socioscope run parliament-size fetch --only ipu_parline   # ソースを絞る（ipu_parline / soumu_senkyo / estat_census / mof_budget / clb_bills）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261027_r1_ratio.py      # R1（H1・H1b・H1c）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261027_r2_pr_blocks.py  # R2（H3・H3b・H3c・H4・H4b）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261027_r3_cost.py       # R3（H5・H5b）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261027_r4_history.py    # R4（H6）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261027_r5_roles.py      # R5（H2）
```
