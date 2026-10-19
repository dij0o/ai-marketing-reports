"""Read-only: organic-search session behaviour from GA4 plus Search Console query/page data -> snapshots/journey_<date>.json"""
import json, sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import google_clients as gc

TZ = timezone(timedelta(hours=0))
START = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--start=")), "2026-01-01")
END = str(datetime.now(TZ).date() - timedelta(days=1))
PROP = f"properties/{gc.CONFIG['ga4']['property_id']}"
ORG = {"filter": {"fieldName": "sessionDefaultChannelGroup", "stringFilter": {"value": "Organic Search"}}}
R = [{"startDate": START, "endDate": END}]
Path("snapshots").mkdir(exist_ok=True)


def run(svc, dims, mets, flt=None, limit=1000):
    body = {"dateRanges": R, "dimensions": [{"name": x} for x in dims], "metrics": [{"name": x} for x in mets], "limit": limit}
    if flt: body["dimensionFilter"] = flt
    rows = svc.properties().runReport(property=PROP, body=body).execute().get("rows", [])
    return [[v["value"] for v in r["dimensionValues"]] + [float(v["value"]) for v in r["metricValues"]] for r in rows]


def main():
    ga = gc.ga4_data()
    out = {"generated": datetime.now(TZ).isoformat(timespec="minutes"), "start": START, "end": END}
    steps = {
        "landing": lambda: run(ga, ["landingPage"], ["sessions", "engagedSessions", "averageSessionDuration", "screenPageViewsPerSession"], ORG),
        "events_by_landing": lambda: run(ga, ["landingPage", "eventName"], ["eventCount"], ORG),
        "events": lambda: run(ga, ["eventName"], ["eventCount", "totalUsers"], ORG),
        "transitions": lambda: run(ga, ["pageReferrer", "pagePath"], ["screenPageViews"],
                                   {"andGroup": {"expressions": [ORG, {"filter": {"fieldName": "eventName", "stringFilter": {"value": "page_view"}}}]}}),
        "device": lambda: run(ga, ["deviceCategory"], ["sessions", "engagedSessions"], ORG),
        "daily": lambda: run(ga, ["date"], ["sessions", "engagedSessions", "averageSessionDuration"], ORG),
    }
    for k, fn in steps.items():
        try: out[k] = fn()
        except Exception as e: out[k + "_error"] = str(e)[:300]
    try:
        gs = gc.gsc()
        site = gc.CONFIG["search_console"]["property"]
        q = lambda dims: gs.searchanalytics().query(siteUrl=site, body={"startDate": START, "endDate": END, "dimensions": dims, "rowLimit": 1000}).execute().get("rows", [])
        out["gsc_query_page"] = [[*r["keys"], r["clicks"], r["impressions"], r["position"]] for r in q(["query", "page"])]
        out["gsc_device"] = [[*r["keys"], r["clicks"], r["impressions"]] for r in q(["device"])]
    except Exception as e: out["gsc_error"] = str(e)[:300]
    f = Path("snapshots") / f"journey_{date.today()}.json"
    f.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote", f, {k: len(v) for k, v in out.items() if isinstance(v, list)}, [k for k in out if k.endswith("_error")] or "no errors")


if __name__ == "__main__":
    main()
