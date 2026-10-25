"""Read-only Bing Webmaster property, search, crawl and sitemap reports."""
import os

import requests

import webmaster_clients as wc

API = "https://ssl.bing.com/webmaster/api.svc/json/"
METHODS = ("GetUserSites", "GetUrlInfo", "GetRankAndTrafficStats", "GetQueryStats", "GetPageStats", "GetCrawlStats", "GetFeeds")


def collect(settings, period, session=None):
    report = wc.envelope("bing", period)
    key = os.environ.get("BING_API_KEY")
    if not key:
        report["message"] = "Set BING_API_KEY in the environment."
        return report
    try:
        site = wc.site_url(settings, "bing")
    except wc.ReportError as error:
        report.update(status="error", message=str(error))
        return report
    session = session or requests.Session()
    report["site"] = site

    def call(method, **extra):
        if method not in METHODS:
            raise wc.ReportError("Only read-only Bing report methods are allowed.")
        return wc.get_json(session, API + method, params={"apikey": key, **({"siteUrl": site} if method != "GetUserSites" else {}), **extra})

    def properties():
        all_sites = wc.rows_field(call("GetUserSites"), "d")
        rows = [{"url": s.get("Url"), "verified": s.get("IsVerified")} for s in all_sites if s.get("Url") == site]
        if not rows:
            raise wc.ReportError("Exact configured Bing property not returned; check URL and access.")
        return {"rows": rows, "message": "" if rows else "Exact configured property not returned; check URL and access."}

    wc.capture(report, "property", "GetUserSites", properties, grain="current property", note="Exact URL match; verification is not proof of traffic or indexing.")

    def url_info():
        x = call("GetUrlInfo", url=site).get("d")
        if not isinstance(x, dict):
            raise wc.ReportError("Bing returned invalid URL information.")
        code = wc.number(x.get("HttpStatus"))
        return {"rows": [{"url": x.get("Url", site), "discovered": wc.day(x.get("DiscoveryDate")), "last_crawled": wc.day(x.get("LastCrawledDate")), "http_status": code if code and code > 0 else None, "is_page": x.get("IsPage")} ]}

    wc.capture(report, "url_info", "GetUrlInfo", url_info, grain="current homepage", note="HTTP status 0 is unavailable; a crawl date does not prove current index inclusion.")

    def history(method, dimension=None, crawl=False):
        raw = wc.rows_field(call(method), "d")
        rows = []
        for x in raw:
            row = {"date": wc.day(x.get("Date"))}
            if crawl:
                row.update({k: wc.number(x.get(field)) for k, field in {"crawled_pages": "CrawledPages", "in_index": "InIndex", "blocked_by_robots": "BlockedByRobotsTxt", "http_4xx": "Code4xx", "http_5xx": "Code5xx"}.items()})
            else:
                row.update(clicks=wc.number(x.get("Clicks")), impressions=wc.number(x.get("Impressions")), position=wc.number(x.get("AvgImpressionPosition")))
                row["ctr"] = wc.ratio(row["clicks"], row["impressions"])
                if dimension:
                    row[dimension.lower()] = x.get(dimension)
            rows.append(row)
        dates = sorted({r["date"] for r in rows if r["date"]})
        selected = [r for r in rows if r["date"] and period["start"] <= r["date"] <= period["end"]]
        return {"rows": selected, "returned_rows": len(raw), "undated_rows": sum(r["date"] is None for r in rows), "available": {"start": dates[0] if dates else None, "end": dates[-1] if dates else None}, "message": "" if selected else "No provider records in this window; missing records are not measured zero traffic."}

    for name, method, dimension in (("traffic", "GetRankAndTrafficStats", None), ("queries", "GetQueryStats", "Query"), ("pages", "GetPageStats", "Page"), ("crawl", "GetCrawlStats", None)):
        wc.capture(report, name, method, lambda m=method, d=dimension: history(m, d, m == "GetCrawlStats"), grain="weekly query/page bucket" if dimension else "provider record date", note="Window selects provider date labels, not exact weekly overlap. No missing-day zero filling; returned_rows is before filtering.")

    def sitemaps():
        return {"rows": [{"url": x.get("Path") or x.get("Url"), "status": x.get("Status"), "submitted": wc.day(x.get("Submitted")), "last_crawled": wc.day(x.get("LastCrawled")), "url_count": wc.number(x.get("UrlCount")), "type": x.get("Type")} for x in wc.rows_field(call("GetFeeds"), "d")]}

    wc.capture(report, "sitemaps", "GetFeeds", sitemaps, grain="current sitemap feed", note="Independent of performance dates. Feed URL counts are not indexed-page totals.")
    return wc.finish(report)


def main():
    options = wc.args(__doc__)
    try:
        period = wc.window(options)
        report = collect(wc.config(), period)
        path = wc.save_json(f"bing_{period['end']}.json", report)
        print(f"Bing: {report['status']}; saved {path}")
        return 0 if report["status"] == "connected" else 1
    except wc.ReportError as error:
        print(str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
