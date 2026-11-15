"""pytrends で Google Trends（geo=JP）を取得し月次 CSV に保存する。429 なら 2 回リトライして停止。

注意: Google Trends は 1 リクエスト内で相対正規化（最大=100）される。
  job1: ちいかわ・すみっコぐらし・鬼滅の刃（2019-01〜2026-10、同一スケール）
  job2: 妖怪ウォッチ（2013-01〜2016-12、別スケール）
実行: venv/bin/python reports/figures/chiikawa/fetch_trends.py \
        reports/figures/chiikawa/data/google_trends.csv
実行日 2026-10-24: 429 なしで 2 リクエストとも成功。
"""

import sys
import time

import pandas as pd
from pytrends.exceptions import TooManyRequestsError
from pytrends.request import TrendReq

out = sys.argv[1]
jobs = [
    (["ちいかわ", "すみっコぐらし", "鬼滅の刃"], "2019-01-01 2026-10-24"),
    (["妖怪ウォッチ"], "2013-01-01 2016-12-31"),
]
frames = []
pt = TrendReq(hl="ja-JP", tz=-540, timeout=(10, 30))
for kws, tf in jobs:
    for attempt in range(3):
        try:
            pt.build_payload(kws, timeframe=tf, geo="JP")
            df = pt.interest_over_time()
            print("OK", kws, df.shape)
            frames.append(df.drop(columns=["isPartial"], errors="ignore"))
            break
        except TooManyRequestsError as e:
            print(f"429 attempt {attempt + 1}: {e}", file=sys.stderr)
            if attempt == 2:
                print("GIVE_UP_429")
                sys.exit(2)
            time.sleep(30 * (attempt + 1))
        except Exception as e:
            print("ERR", type(e).__name__, e, file=sys.stderr)
            sys.exit(3)
    time.sleep(20)
res = pd.concat(frames, axis=1, sort=True)
# 4 年未満の timeframe は週次で返るため、月初基準の月平均に揃える
res = res.resample("MS").mean().round(1)
res.index.name = "month"
res.to_csv(out)
print(res.tail())
