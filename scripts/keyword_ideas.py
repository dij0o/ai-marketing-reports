"""Keyword Planner: ideas from seeds, and per-country monthly history for a keyword list."""
import json
import time
from datetime import date
from pathlib import Path

import pandas as pd

from ads_client import API, CUSTOMER, session

ENGLISH = "languageConstants/1000"
MARKETS = {"US": ["geoTargetConstants/2840"], "UK": ["geoTargetConstants/2826"]}
SEEDS = {"core": ["keyword one", "keyword two"]}            # replace; max 20 keywords per request
SEED_SITE = "https://www.example.com/"
RANGE = {"start": {"year": 2022, "month": "SEPTEMBER"}, "end": {"year": 2026, "month": "AUGUST"}}
MONTHS = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]


def post_with_retry(s, url, body):
    for attempt in range(5):
        r = s.post(url, json=body)
        if r.status_code != 429:        # 429 = rate limited; wait and retry
            break
        time.sleep(5 * (attempt + 1))
    r.raise_for_status()
    return r.json()


def ideas(s, geos, seed):
    body = {"language": ENGLISH, "geoTargetConstants": geos, "keywordPlanNetwork": "GOOGLE_SEARCH",
            "includeAdultKeywords": False, "pageSize": 1000, **seed}
    out = []
    while True:
        j = post_with_retry(s, f"{API}/customers/{CUSTOMER}:generateKeywordIdeas", body)
        out += j.get("results", [])
        if not j.get("nextPageToken"):
            return out
        body["pageToken"] = j["nextPageToken"]
        time.sleep(1.2)


def pull_ideas():
    s = session()
    raw = {}
    for market, geos in MARKETS.items():
        for group, kws in SEEDS.items():
            for i in range(0, len(kws), 20):
                raw[f"{market}|{group}|{i}"] = ideas(s, geos, {"keywordSeed": {"keywords": kws[i:i + 20]}})
                time.sleep(1.2)
        raw[f"{market}|site"] = ideas(s, geos, {"siteSeed": {"site": SEED_SITE}})
    return raw


def history(s, geo_id, keywords):
    """Monthly volumes per keyword for one country. Close variants share one result, so attach it to each requested variant."""
    out = {}
    for i in range(0, len(keywords), 1000):
        chunk = keywords[i:i + 1000]
        j = post_with_retry(s, f"{API}/customers/{CUSTOMER}:generateKeywordHistoricalMetrics", {
            "keywords": chunk, "language": ENGLISH, "geoTargetConstants": [f"geoTargetConstants/{geo_id}"],
            "keywordPlanNetwork": "GOOGLE_SEARCH",
            "historicalMetricsOptions": {"yearMonthRange": RANGE, "includeAverageCpc": True}})
        wanted = set(chunk)
        for x in j.get("results", []):
            m = x.get("keywordMetrics", {})
            monthly = {f"{v['year']}-{MONTHS.index(v['month']) + 1:02d}": int(v.get("monthlySearches", 0) or 0)
                       for v in m.get("monthlySearchVolumes", [])}
            rec = {"avg": int(m.get("avgMonthlySearches", 0) or 0), "competition": m.get("competition"),
                   "bid_low": int(m.get("lowTopOfPageBidMicros", 0) or 0) / 1e6,
                   "bid_high": int(m.get("highTopOfPageBidMicros", 0) or 0) / 1e6,
                   "cpc": int(m.get("averageCpcMicros", 0) or 0) / 1e6,
                   "monthly": [monthly.get(k, 0) for k in sorted(monthly)]}
            for k in {x["text"], *x.get("closeVariants", [])} & wanted:
                out[k] = rec
        time.sleep(1.2)
    return out


if __name__ == "__main__":
    Path("snapshots").mkdir(exist_ok=True)
    raw = pull_ideas()
    f = Path("snapshots") / f"keyword_ideas_{date.today()}.json"
    f.write_text(json.dumps(raw, indent=1))
    print("wrote", f)
