"""Read-only Yandex Webmaster ownership, query sample, diagnostics and sitemaps."""
import os
from urllib.parse import quote

import requests

import webmaster_clients as wc

API = "https://api.webmaster.yandex.net/v4"


def collect(settings, period, session=None):
    report = wc.envelope("yandex", period)
    token = os.environ.get("YANDEX_TOKEN")
    if not token:
        report["message"] = "Set YANDEX_TOKEN in the environment (raw OAuth token, no prefix)."
        return report
    session = session or requests.Session()
    headers = {"Authorization": "OAuth " + token, "Accept": "application/json"}

    def get(path, params=None):
        return wc.get_json(session, API + path, params=params, headers=headers)

    def user():
        data = get("/user")
        if not data.get("user_id"):
            raise wc.ReportError("Yandex did not return a user ID.")
        return {"rows": [{"user_id": data["user_id"]}]}

    wc.capture(report, "user", "/user", user, grain="token owner", note="Confirms an API response for the OAuth identity; website login alone does not supply an API token.")
    if report["datasets"]["user"]["status"] != "ok":
        return wc.finish(report)
    user_id = report["datasets"]["user"]["rows"][0]["user_id"]
    prefix = "/user/" + quote(str(user_id), safe="")

    def hosts():
        return {"rows": [{"host_id": x.get("host_id"), "url": x.get("host_url"), "verified": x.get("verified")} for x in wc.rows_field(get(prefix + "/hosts"), "hosts")]}

    wc.capture(report, "hosts", "/user/{user}/hosts", hosts, grain="current properties", note="Property verification and search performance are separate.")
    host_id = settings.get("yandex", {}).get("host_id")
    if not host_id:
        try:
            site = wc.site_url(settings, "yandex").rstrip("/")
            host_id = next((x["host_id"] for x in report["datasets"]["hosts"]["rows"] if (x.get("url") or "").rstrip("/") == site), None)
        except wc.ReportError:
            pass
    if not host_id:
        report.update(status="partial", message="Configure yandex.host_id using the host list; no matching property was found.")
        return report
    base = prefix + "/hosts/" + quote(str(host_id), safe="")
    report["host_id"] = host_id

    def popular():
        params = {"order_by": "TOTAL_CLICKS", "date_from": period["start"], "date_to": period["end"], "limit": 500, "query_indicator": ["TOTAL_CLICKS", "TOTAL_SHOWS", "AVG_SHOW_POSITION"]}
        data = get(base + "/search-queries/popular", params)
        rows = []
        for x in wc.rows_field(data, "queries"):
            metrics = x.get("indicators") or {}
            clicks, impressions = wc.number(metrics.get("TOTAL_CLICKS")), wc.number(metrics.get("TOTAL_SHOWS"))
            rows.append({"query": x.get("query_text"), "clicks": clicks, "impressions": impressions, "position": wc.number(metrics.get("AVG_SHOW_POSITION")), "ctr": wc.ratio(clicks, impressions)})
        count = wc.number(data.get("count"))
        return {"rows": rows, "actual_range": {"start": wc.day(data.get("date_from")), "end": wc.day(data.get("date_to"))}, "provider_count": count, "limit": 500, "truncated": count > len(rows) if count is not None else len(rows) == 500}

    wc.capture(report, "queries", "/user/{user}/hosts/{host}/search-queries/popular", popular, grain="popular query sample over provider range", note="At most 500 queries, not site-wide totals. Actual dates may be narrower than requested. No sample sums in overview.")

    def diagnostics():
        problems = get(base + "/diagnostics").get("problems")
        if not isinstance(problems, dict):
            raise wc.ReportError("Yandex returned invalid diagnostics.")
        return {"rows": [{"issue": issue, "severity": x.get("severity"), "state": x.get("state"), "last_updated": x.get("last_state_update")} for issue, x in problems.items()]}

    wc.capture(report, "diagnostics", "/user/{user}/hosts/{host}/diagnostics", diagnostics, grain="current issue state", note="UNDEFINED is insufficient evidence, not a passed check. Not filtered by performance window.")

    def sitemaps():
        rows, cursor, seen = [], None, set()
        for _ in range(100):
            params = {"limit": 100, **({"from": cursor} if cursor else {})}
            page = wc.rows_field(get(base + "/sitemaps", params), "sitemaps")
            rows.extend({"sitemap_id": x.get("sitemap_id"), "url": x.get("sitemap_url"), "last_access": x.get("last_access_date"), "errors": wc.number(x.get("errors_count")), "url_count": wc.number(x.get("urls_count")), "children": wc.number(x.get("children_count")), "sources": x.get("sources"), "type": x.get("sitemap_type")} for x in page)
            if len(page) < 100:
                return {"rows": rows, "truncated": False}
            cursor = page[-1].get("sitemap_id")
            if not cursor or cursor in seen:
                raise wc.ReportError("Yandex sitemap pagination did not advance.")
            seen.add(cursor)
        return {"rows": rows, "truncated": True}

    wc.capture(report, "sitemaps", "/user/{user}/hosts/{host}/sitemaps", sitemaps, grain="current top-level sitemap", note="Cursor pagination; at most 10,000 files. Child sitemap contents not expanded; no sitemap writes.")
    return wc.finish(report)


def main():
    options = wc.args(__doc__)
    try:
        period = wc.window(options)
        report = collect(wc.config(), period)
        path = wc.save_json(f"yandex_{period['end']}.json", report)
        print(f"Yandex: {report['status']}; saved {path}")
        return 0 if report["status"] == "connected" else 1
    except wc.ReportError as error:
        print(str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
