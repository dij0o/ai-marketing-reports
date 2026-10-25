"""Read-only daily pull: GA4 sessions by channel group, chosen events by channel group, plus Search Console totals.
Usage: python ga4_report_pull.py [--start=YYYY-MM-DD]"""
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import google_clients as gc
import bing_pull
import yandex_pull
import webmaster_clients as wc

TZ = timezone(timedelta(hours=0))          # set to your reporting timezone, e.g. timedelta(hours=4)
START = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--start=")), "2026-01-01")
END = str(datetime.now(TZ).date() - timedelta(days=1))
LEAD = ["generate_lead"]
ACTIONS = ["whatsapp_click", "phone_click", "email_click"]       # your micro-conversion events
PROP = f"properties/{gc.CONFIG['ga4']['property_id']}"
Path("snapshots").mkdir(exist_ok=True)


def ga4_rows(svc, body):
    """runReport returns max 10,000 rows per call: page with offset until rowCount is reached."""
    out, offset = [], 0
    while True:
        r = svc.properties().runReport(property=PROP, body={**body, "limit": 10000, "offset": offset}).execute()
        rows = r.get("rows", [])
        out += rows
        offset += len(rows)
        if not rows or offset >= int(r.get("rowCount", 0)):
            return out


def ga4():
    svc = gc.ga4_data()
    rng = [{"startDate": START, "endDate": END}]
    sessions = ga4_rows(svc, {"dateRanges": rng,
                              "dimensions": [{"name": "date"}, {"name": "sessionDefaultChannelGroup"}],
                              "metrics": [{"name": "sessions"}]})
    events = ga4_rows(svc, {"dateRanges": rng,
                            "dimensions": [{"name": "date"}, {"name": "sessionDefaultChannelGroup"}, {"name": "eventName"}],
                            "metrics": [{"name": "eventCount"}],
                            "dimensionFilter": {"filter": {"fieldName": "eventName",
                                                           "inListFilter": {"values": LEAD + ACTIONS}}}})
    days = {}
    for r in sessions:
        d, ch = (v["value"] for v in r["dimensionValues"])
        day = days.setdefault(f"{d[:4]}-{d[4:6]}-{d[6:]}", {"sessions": {}, "events": {}})
        day["sessions"][ch] = int(r["metricValues"][0]["value"])
    for r in events:
        d, ch, ev = (v["value"] for v in r["dimensionValues"])
        day = days.setdefault(f"{d[:4]}-{d[4:6]}-{d[6:]}", {"sessions": {}, "events": {}})
        day["events"].setdefault(ev, {})[ch] = int(r["metricValues"][0]["value"])
    return dict(sorted(days.items()))


def gsc():
    svc = gc.gsc()
    body = {"startDate": START, "endDate": END, "dimensions": ["date"], "rowLimit": 1000}
    rows = svc.searchanalytics().query(siteUrl=gc.CONFIG["search_console"]["property"], body=body).execute().get("rows", [])
    return {r["keys"][0]: {k: r[k] for k in ("clicks", "impressions", "ctr", "position")} for r in rows}


def main():
    out = {"generated": datetime.now(TZ).isoformat(timespec="minutes"), "start": START, "end": END,
           "lead_events": LEAD, "action_events": ACTIONS}
    for name, fn in (("ga4", ga4), ("gsc", gsc)):
        try:
            out[name] = fn()
        except Exception as e:  # keep whatever half succeeded
            out[name + "_error"] = str(e)[:300]
    # New providers preserve their own datasets, coverage and errors; neither
    # credential is the Google service-account key. Existing Google fields remain.
    period = {"start": START, "end": END, "timezone": str(TZ)}
    for name, collector in (("bing", bing_pull.collect), ("yandex", yandex_pull.collect)):
        try:
            out[name] = collector(gc.CONFIG, period)
        except Exception:
            out[name] = {"status": "error", "message": "Provider collection failed.", "datasets": {}}
    f = Path("snapshots") / f"report_data_{date.today()}.json"
    f.write_text(json.dumps(wc.scrub(out), indent=1), encoding="utf-8")
    g = out.get("ga4", {})
    leads = sum(sum(v.values()) for d in g.values() for e, v in d["events"].items() if e in LEAD)
    print(f"{START} to {END}: {len(g)} GA4 days, {leads} lead events, {len(out.get('gsc', {}))} GSC days. "
          f"Errors: {[k for k in out if k.endswith('_error')] or 'none'}")
    print("wrote", f)
    print("Webmaster status:", {name: out[name]["status"] for name in ("bing", "yandex")})


if __name__ == "__main__":
    main()
