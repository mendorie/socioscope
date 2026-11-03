# theme: public-debt
設計: `design/themes/public-debt.md`。データソース: ① Jordà–Schularick–Taylor Macrohistory Database R6（CC BY-NC-SA 4.0）、② IMF DataMapper API（WEO・Fiscal Monitor・Global Debt Database、出典表示・商用は許可要）。残りの採用順は設計書の「データ候補」。
```bash
uv run socioscope themes                      # public-debt が出る
uv run socioscope run public-debt fetch       # → data/raw/public-debt/jst/JSTdatasetR6.xlsx
uv run socioscope run public-debt stage
uv run socioscope run public-debt mart        # → data/marts/public_debt_panel.parquet
```
