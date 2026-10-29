# theme: essential-work-wages
設計: `design/themes/essential-work-wages.md`（2026-10-29、H0〜H6 事前登録）。
```bash
uv run socioscope run essential-work-wages fetch   # まだソース未結線（採用順 ①〜⑧ は design doc）
uv run socioscope run essential-work-wages stage
uv run socioscope run essential-work-wages mart    # → data/marts/essential_work_wages_panel.parquet（空）
```
