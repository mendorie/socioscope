# themes/bicycle-industry
設計（問い・事前登録仮説 H1〜H6・指標・採用順）: `design/themes/bicycle-industry.md`。規約: root `CLAUDE.md`、`.claude/rules/themes.md`。

## 構成
```
src/theme_bicycle_industry/
  pipeline.py   fetch / stage / mart（Port 経由。I/O はここだけ）。ソースごとに `# ---- <source>` ブロックを足す。
                `build_panel`: long 形式 mart（iso3, year, product, metric, value, source）のソート・キー重複検査
  wiring.py     PIPELINE（entry point）。stage 関数の登録のみ
  <source>.py   （予定）ソースごとの URL 組み立てと ファイル → 行 の純粋変換（決定的・fail-closed）:
                meti.py 生産動態統計 xlsx / customs.py 貿易統計 CSV / cpi.py・kakei.py e-Stat Excel /
                jbpi.py JBPI PDF / shimano.py EDINET PDF / comtrade.py / hicp.py / bls.py / census_jp.py 経済センサス
queries/        DuckDB 用 SQL（? バインド）
reports/        <yyyy-mm-dd>-<slug>.md ＋ figures/
tests/          fixtures/（実レスポンスの縮約）＋ Fake による状態テスト
```

## テーブル
| name | 粒度 | 列 |
|---|---|---|
| `marts/bicycle_industry_panel` | iso3×year×product×metric×source（long） | iso3, year, product（bicycle_total / e_assist / sports / city / parts / car_kei / car_registered / moto_lt125 / moto_126_250 / moto_251p …）, metric（units / value_jpy / value_usd / price_index / avg_price_jpy …）, value, source。現在は空 |

## テーマ固有の規約
- 「スポーツ車」の定義はソースごとに違う（JBPI 車種分類・POS 小売分類）。`product` に出典別の値を使い、混ぜない。
- 電動アシスト車の輸入（HS 8711.60）は原付・電動バイクを含む。国内生産（生産動態統計）を主とする。
- 協会系ソース（JBPI・JAMA・自販連・全軽自協・JAIA）は利用規約がない。出典明記・raw 非コミット。
- ボット UA を拒否するサイト（METI・shimano.com・JBPI）は fetcher 側で UA を設定し、HTML が返ったら fail-closed。
