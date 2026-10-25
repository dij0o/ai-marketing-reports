"""Collect Google/Bing/Yandex search and GA4 into inspectable JSON + Markdown."""
import json
from datetime import date
from pathlib import Path

import bing_pull
import google_webmaster_pull
import webmaster_clients as wc
import yandex_pull

COLLECTORS = {"gsc": google_webmaster_pull.collect_gsc, "bing": bing_pull.collect, "yandex": yandex_pull.collect, "ga4": google_webmaster_pull.collect_ga4}


def collect(settings, period, providers=None):
    report = {"schema_version": 1, "generated_at": wc.now(), "requested": period, "providers": {}}
    for provider in providers or COLLECTORS:
        try:
            report["providers"][provider] = COLLECTORS[provider](settings, period)
        except Exception:
            report["providers"][provider] = {**wc.envelope(provider, period), "status": "error", "message": "Provider collection failed; other sources are preserved."}
    return wc.scrub(report)


def cell(value):
    if value is None:
        return "unavailable"
    if isinstance(value, (list, dict)):
        value = json.dumps(value, ensure_ascii=False)
    # Keep provider strings as inert Markdown table content.
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "&#124;").replace("`", "&#96;").replace("[", "&#91;").replace("]", "&#93;").replace("\r", " ").replace("\n", " ")


def dataset(report, provider, name):
    item = report["providers"].get(provider, {}).get("datasets", {}).get(name, {})
    return item if item.get("status") == "ok" else {}


def overview(report, provider):
    if provider == "gsc":
        rows = dataset(report, provider, "totals").get("rows", [])
        return rows[0] if rows else {}
    if provider == "bing":
        rows = dataset(report, provider, "traffic").get("rows", [])
        if not rows:
            return {}
        return {m: sum(r[m] for r in rows) if all(r.get(m) is not None for r in rows) else None for m in ("clicks", "impressions")}
    return {}  # Yandex popular queries are a sample, never full-site totals.


def markdown(report, json_name):
    period = report["requested"]
    lines = ["# Search visibility and analytics report", "", f"Requested: {cell(period['start'])} to {cell(period['end'])}; calendar timezone {cell(period['timezone'])}.", f"Collected: {cell(report['generated_at'])}. Full datasets: `{json_name}`.", "", "Dates, populations and metric definitions differ by provider. Search clicks, GA4 sessions/users and keyword demand must not be added together. Missing data is not measured zero.", "", "## Search overview", "", "| Source | Connection | Clicks | Impressions | Scope |", "| --- | --- | ---: | ---: | --- |"]
    for provider in ("gsc", "bing", "yandex"):
        source = report["providers"].get(provider)
        if source is None:
            continue
        totals = overview(report, provider)
        scope = "Popular-query sample only; no site totals" if provider == "yandex" else "Ungrouped final web-search totals" if provider == "gsc" else "Available returned traffic dates; inspect coverage"
        lines.append("| " + " | ".join(cell(x) for x in (provider, source["status"], totals.get("clicks"), totals.get("impressions"), scope)) + " |")
    for provider, source in report["providers"].items():
        lines += ["", f"## {provider.upper()}", "", f"Status: **{cell(source['status'])}**."]
        if source.get("message"):
            lines += ["", cell(source["message"])]
        for name, data in source.get("datasets", {}).items():
            metadata = {k: v for k, v in data.items() if k not in ("rows", "source")}
            origin = data.get("source", {})
            lines += ["", f"### {name}", "", f"JSON path: `providers.{provider}.datasets.{name}`; status: **{cell(data['status'])}**.", "", cell(origin.get("note", "")), "", "Source and coverage: " + cell(origin), "", "Dataset metadata: " + cell(metadata), ""]
            rows = data.get("rows", [])
            if not rows:
                lines += ["No rows available. See status and metadata above; do not infer zero traffic."]
                continue
            columns = list(dict.fromkeys(k for row in rows for k in row))
            lines += ["| " + " | ".join(cell(k) for k in columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
            lines += ["| " + " | ".join(cell(row.get(k)) for k in columns) + " |" for row in rows[:20]]
            if len(rows) > 20:
                lines += ["", f"Showing 20 of {len(rows)} collected rows. All collected rows remain in the JSON; any API truncation is disclosed separately in metadata."]
    return "\n".join(lines) + "\n"


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=28)
    parser.add_argument("--start", type=date.fromisoformat)
    parser.add_argument("--end", type=date.fromisoformat)
    parser.add_argument("--timezone", default="Asia/Karachi")
    parser.add_argument("--providers", nargs="+", choices=list(COLLECTORS), default=list(COLLECTORS))
    parser.add_argument("--from-json", type=Path, help="Render a saved combined report without API calls or config.")
    options = parser.parse_args()
    try:
        if options.from_json:
            report = wc.scrub(json.loads(options.from_json.read_text(encoding="utf-8-sig")))
            if report.get("schema_version") != 1 or not isinstance(report.get("providers"), dict):
                raise wc.ReportError("Unsupported saved report format.")
            path = options.from_json
        else:
            period = wc.window(options)
            report = collect(wc.config(), period, options.providers)
            stamp = report["generated_at"].replace(":", "-")
            path = wc.save_json(f"webmaster_report_{stamp}.json", report)
        path.with_suffix(".md").write_text(wc.scrub(markdown(report, path.name)), encoding="utf-8")
        for name, source in report["providers"].items():
            print(f"{name}: {source['status']}")
        print(f"Saved report: {path.with_suffix('.md')}")
        return 0 if all(s["status"] == "connected" for s in report["providers"].values()) else 1
    except (wc.ReportError, OSError, ValueError, KeyError, TypeError):
        print("Cannot collect or render report; check config, date range and saved JSON format. No raw errors are printed.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
