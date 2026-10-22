# theme: bicycle-industry
設計: `design/themes/bicycle-industry.md`。
```bash
uv run socioscope run bicycle-industry fetch   # 経産省 生産動態統計 年報 xlsx 2021–2025 → data/raw/bicycle-industry/meti_seidou/
uv run socioscope run bicycle-industry stage   # → data/staged/meti/seidou_annual.parquet
uv run socioscope run bicycle-industry mart    # → data/marts/meti_production.parquet, bicycle_industry_panel.parquet（空）
```
