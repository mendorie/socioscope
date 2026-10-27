# theme: parliament-size
設計: `design/themes/parliament-size.md`。
```bash
uv run socioscope run parliament-size fetch   # IPU Parline API: chambers 3 ページ・countries 2 ページ（鍵不要、CC BY-NC-SA 4.0）
uv run socioscope run parliament-size stage   # → data/staged/ipu/{chamber_attributes,country_attributes}.parquet
uv run socioscope run parliament-size mart    # → data/marts/ipu_parliaments.parquet
uv run socioscope run parliament-size fetch --only ipu_parline   # ソースを絞る
uv run python themes/parliament-size/src/theme_parliament_size/analysis/a20261027_r1_ratio.py   # R1（H1・H1b・H1c）
```
