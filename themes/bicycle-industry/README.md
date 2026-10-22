# theme: bicycle-industry
設計: `design/themes/bicycle-industry.md`。
```bash
uv run socioscope run bicycle-industry fetch   # 経産省 生産動態統計 年報 xlsx 2021–2025、UN Comtrade 2010–2024、Eurostat HICP、BLS CPI
uv run socioscope run bicycle-industry stage   # → data/staged/{meti,comtrade,eurostat,bls}/*.parquet
uv run socioscope run bicycle-industry mart    # → data/marts/{meti_production,bicycle_trade,price_indices}.parquet
uv run socioscope run bicycle-industry fetch --only un_comtrade   # ソースを絞る（meti_seidou / un_comtrade / eurostat_hicp / bls_cpi）
```
