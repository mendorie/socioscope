# theme: parliament-size
設計: `design/themes/parliament-size.md`。データソースは未採用（採用順は設計書の「データ候補」）。
```bash
uv run socioscope themes                        # parliament-size が出る
uv run socioscope run parliament-size fetch     # まだソースが無い旨の note を出すだけ
uv run socioscope run parliament-size stage
uv run socioscope run parliament-size mart      # → data/marts/parliament_size_panel.parquet（ソース採用後）
```
