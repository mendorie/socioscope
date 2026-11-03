# theme: public-debt
設計: `design/themes/public-debt.md`。データソースは未採用（採用順は設計書の「データ候補」。最初は Jordà–Schularick–Taylor Macrohistory Database R6）。
```bash
uv run socioscope themes                      # public-debt が出る
uv run socioscope run public-debt fetch       # まだソースが無い旨の note を出すだけ
uv run socioscope run public-debt stage
uv run socioscope run public-debt mart        # → data/marts/public_debt_panel.parquet（ソース採用後）
```
