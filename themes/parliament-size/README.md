# theme: parliament-size
設計: `design/themes/parliament-size.md`。
```bash
uv run socioscope run parliament-size fetch   # IPU Parline API（chambers 3 ページ・countries 2 ページ）、総務省 結果調 Excel（第 50・51 回 × 5 表）、e-Stat 国勢調査 2020 表 2-1
uv run socioscope run parliament-size stage   # → data/staged/{ipu,soumu,estat}/*.parquet
uv run socioscope run parliament-size mart    # → data/marts/{ipu_parliaments,jp_hr_electorate,jp_hr_pr_results,jp_hr_seats_by_party,jp_census2020_prefecture}.parquet
uv run socioscope run parliament-size fetch --only ipu_parline   # ソースを絞る（ipu_parline / soumu_senkyo / estat_census）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261027_r1_ratio.py      # R1（H1・H1b・H1c）
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261027_r2_pr_blocks.py  # R2（H3・H3b・H3c・H4・H4b）
```
