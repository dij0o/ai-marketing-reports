"""Read-only Google datasets for the combined report; no Admin or GTM writes."""
import os
from pathlib import Path

import webmaster_clients as wc


def client(api, version, scope):
    # Lazy imports let Bing/Yandex work without a Google credential or config section.
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from google_auth_httplib2 import AuthorizedHttp
    from httplib2 import Http

    key = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or str(Path.home() / ".secrets" / "sa.json")
    credentials = service_account.Credentials.from_service_account_file(key, scopes=[scope])
    return build(api, version, http=AuthorizedHttp(credentials, http=Http(timeout=25)), cache_discovery=False)


def collect_gsc(settings, period):
    report = wc.envelope("gsc", period)
    site = settings.get("search_console", {}).get("property")
    if not site:
        report["message"] = "Configure search_console.property and a Google service-account key."
        return report
    try:
        svc = client("searchconsole", "v1", "https://www.googleapis.com/auth/webmasters.readonly")
    except Exception:
        report.update(status="error", message="Cannot initialise Search Console read-only client; check key and dependencies.")
        return report
    report["site"] = site

    def query(dimension):
        body = {"startDate": period["start"], "endDate": period["end"], "type": "web", "dataState": "final", "rowLimit": 1000}
        if dimension:
            body["dimensions"] = [dimension]
        raw = svc.searchanalytics().query(siteUrl=site, body=body).execute()
        rows = []
        for row in wc.rows_field({"rows": raw.get("rows", [])}, "rows"):
            item = {k: wc.number(row.get(k)) for k in ("clicks", "impressions", "ctr", "position")}
            if dimension:
                item[dimension] = row["keys"][0]
            rows.append(item)
        return {"rows": rows, "limit": 1000, "possibly_truncated": len(rows) == 1000}

    for name, dim in (("totals", None), ("daily", "date"), ("queries", "query"), ("pages", "page"), ("countries", "country"), ("devices", "device")):
        wc.capture(report, name, "searchanalytics.query", lambda d=dim: query(d), grain="site-wide period totals" if dim is None else dim, note="Final web-search data only; provider processing lag may leave gaps. Top 1,000 rows. Anonymized queries omitted; query sums need not match ungrouped totals. Position is the provider's average.")

    def sitemaps():
        data = svc.sitemaps().list(siteUrl=site).execute()
        rows = [{"url": x.get("path"), "last_downloaded": x.get("lastDownloaded"), "pending": x.get("isPending"), "warnings": wc.number(x.get("warnings")), "errors": wc.number(x.get("errors"))} for x in wc.rows_field({"sitemaps": data.get("sitemap", [])}, "sitemaps")]
        return {"rows": rows}

    wc.capture(report, "sitemaps", "sitemaps.list", sitemaps, grain="current sitemap", note="Current status independent of performance dates.")
    return wc.finish(report)


def collect_ga4(settings, period):
    report = wc.envelope("ga4", period)
    prop = str(settings.get("ga4", {}).get("property_id", ""))
    if not prop or not prop.isdigit():
        report["message"] = "Configure the numeric ga4.property_id, not the G- measurement ID."
        return report
    try:
        svc = client("analyticsdata", "v1beta", "https://www.googleapis.com/auth/analytics.readonly")
    except Exception:
        report.update(status="error", message="Cannot initialise GA4 read-only client; check key and dependencies.")
        return report

    def run(dims, metrics):
        body = {"dateRanges": [{"startDate": period["start"], "endDate": period["end"]}], "dimensions": [{"name": x} for x in dims], "metrics": [{"name": x} for x in metrics], "limit": 1000}
        raw = svc.properties().runReport(property="properties/" + prop, body=body).execute()
        rows = []
        for x in wc.rows_field({"rows": raw.get("rows", [])}, "rows"):
            row = {d: x["dimensionValues"][i]["value"] for i, d in enumerate(dims)}
            if "date" in row:
                d = row["date"]
                row["date"] = f"{d[:4]}-{d[4:6]}-{d[6:]}"
            row.update({m: wc.number(x["metricValues"][i]["value"]) for i, m in enumerate(metrics)})
            rows.append(row)
        metadata = raw.get("metadata", {})
        return {"rows": rows, "row_count": raw.get("rowCount"), "truncated": int(raw.get("rowCount", 0)) > len(rows), "property_timezone": metadata.get("timeZone"), "subject_to_thresholding": metadata.get("subjectToThresholding"), "data_loss_from_other_row": metadata.get("dataLossFromOtherRow"), "sampling": metadata.get("samplingMetadatas", [])}

    specs = (
        ("totals", [], ["totalUsers", "sessions", "screenPageViews", "engagedSessions", "engagementRate", "keyEvents"]),
        ("daily", ["date"], ["sessions", "totalUsers", "screenPageViews"]),
        ("pages", ["pagePath"], ["screenPageViews", "sessions", "userEngagementDuration"]),
        ("channels", ["sessionDefaultChannelGroup"], ["sessions", "engagedSessions", "keyEvents"]),
        ("countries", ["country"], ["totalUsers", "sessions"]),
        ("devices", ["deviceCategory"], ["totalUsers", "sessions"]),
        ("events", ["eventName"], ["eventCount", "totalUsers"]),
    )
    for name, dims, metrics in specs:
        wc.capture(report, name, "properties.runReport", lambda d=dims, m=metrics: run(d, m), grain="distinct period totals" if not dims else " x ".join(dims), note="Consented collected activity, not all visitors. Users are distinct period/group counts: never sum them across days or groups. Key events include all configured key events, not only enquiries. Maximum 1,000 rows per breakdown; inspect metadata.")
    return wc.finish(report)
