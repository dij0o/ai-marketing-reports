"""Read-only Search Console pull: performance by several dimensions, sitemaps and URL inspection -> snapshots/."""
import json
from datetime import date, timedelta
from pathlib import Path

import google_clients as gc

SITE = gc.CONFIG["search_console"]["property"]
svc = gc.gsc_client()
end = date.today() - timedelta(days=3)  # GSC data lags ~2-3 days
Path("snapshots").mkdir(exist_ok=True)


def query(days, dims, offset=0, limit=250):
    e = end - timedelta(days=offset)
    body = {"startDate": str(e - timedelta(days=days - 1)), "endDate": str(e), "dimensions": dims, "rowLimit": limit}
    return svc.searchanalytics().query(siteUrl=SITE, body=body).execute().get("rows", [])


def query_all(days, dims):
    """Paginate: up to 25,000 rows per request. Use for page x query exports."""
    out, start = [], 0
    while True:
        body = {"startDate": str(end - timedelta(days=days - 1)), "endDate": str(end), "dimensions": dims,
                "rowLimit": 25000, "startRow": start}
        rows = svc.searchanalytics().query(siteUrl=SITE, body=body).execute().get("rows", [])
        out += rows
        if len(rows) < 25000:
            return out
        start += 25000


out = {
    "totals_28d": query(28, []), "totals_prev_28d": query(28, [], offset=28),   # period-over-period
    "totals_16m_by_date": query(480, ["date"], limit=500),                     # 16 months is the retention limit
    "queries_90d": query(90, ["query"], limit=500), "pages_90d": query(90, ["page"], limit=500),
    "countries_90d": query(90, ["country"], limit=25), "devices_90d": query(90, ["device"]),
    "page_query_90d": query_all(90, ["page", "query"]),
    "sitemaps": svc.sitemaps().list(siteUrl=SITE).execute().get("sitemap", []),
}

# URL Inspection API: index status of specific URLs (limited to ~2,000 per day per property)
KEY_URLS = ["https://www.example.com/"]  # replace
inspect = {}
for url in KEY_URLS:
    try:
        r = svc.urlInspection().index().inspect(body={"inspectionUrl": url, "siteUrl": SITE}).execute()
        inspect[url] = r["inspectionResult"].get("indexStatusResult", {})
    except Exception as ex:
        inspect[url] = {"error": str(ex)[:200]}
out["inspection"] = inspect

f = f"snapshots/gsc_{date.today()}.json"
Path(f).write_text(json.dumps(out, indent=2))
print("wrote", f)
