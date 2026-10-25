"""Read-only checks for Google, Bing and Yandex. Failures produce a nonzero exit.
Use --providers bing yandex without configuring Google credentials.
"""
import argparse

import webmaster_clients as wc


def check_gtm():
    import google_clients as gc
    path = gc.gtm_container_path()
    svc = gc.gtm()
    container = svc.accounts().containers().get(path=path).execute()
    print(f"  Container: {container['name']} ({container['publicId']})")
    workspaces = svc.accounts().containers().workspaces().list(parent=path).execute().get("workspace", [])
    print(f"  Workspaces: {', '.join(w['name'] for w in workspaces) or 'none'}")
    for ws in workspaces[:1]:
        p = ws["path"]
        w = svc.accounts().containers().workspaces()
        tags = w.tags().list(parent=p).execute().get("tag", [])
        triggers = w.triggers().list(parent=p).execute().get("trigger", [])
        variables = w.variables().list(parent=p).execute().get("variable", [])
        print(f"  In '{ws['name']}': {len(tags)} tags, {len(triggers)} triggers, {len(variables)} variables")
    try:
        live = svc.accounts().containers().versions().live(parent=path).execute()
        print(f"  Live version: {live.get('containerVersionId')} {live.get('name', '')}")
    except Exception:
        print("  Live version unavailable; do not infer that nothing is published.")


def check_gsc():
    import google_clients as gc
    sites = gc.gsc().sites().list().execute().get("siteEntry", [])
    if not sites:
        raise wc.ReportError("No Search Console properties visible; check property access.")
    print("  Sites visible:", ", ".join(f"{s['siteUrl']} ({s['permissionLevel']})" for s in sites) or "none")


def check_ga4():
    import google_clients as gc
    summaries = gc.ga4_admin().accountSummaries().list().execute().get("accountSummaries", [])
    for a in summaries:
        for p in a.get("propertySummaries", []):
            print(f"  {a['displayName']} -> {p['displayName']} ({p['property']})")
    if not summaries:
        raise wc.ReportError("No GA4 account summaries visible; check property access.")


def check_ads():
    from ads_client import API, session
    r = session().get(f"{API}/customers:listAccessibleCustomers", timeout=(8, 25), allow_redirects=False)
    if not r.ok:
        raise wc.ReportError(f"Ads access check failed (HTTP {r.status_code}); check project access and account permissions.")
    print(f"  HTTP {r.status_code}: Ads API responded successfully")



def check_webmaster(provider):
    from datetime import date, timedelta
    import bing_pull
    import yandex_pull
    period = {"start": (date.today() - timedelta(days=28)).isoformat(),
              "end": (date.today() - timedelta(days=1)).isoformat(), "timezone": "local calendar"}
    collector = bing_pull.collect if provider == "bing" else yandex_pull.collect
    result = collector(wc.config(), period)
    print(f"  {result['status']}")
    for name, data in result["datasets"].items():
        print(f"  {name}: {data['status']}; rows: {len(data['rows'])}")
        if data.get("error"):
            print("   ", data["error"])
    if result["status"] != "connected":
        raise wc.ReportError(result.get("message", "One or more provider checks failed."))


def main():
    checks = {"gtm": check_gtm, "gsc": check_gsc, "ga4": check_ga4, "ads": check_ads,
              "bing": lambda: check_webmaster("bing"), "yandex": lambda: check_webmaster("yandex")}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--providers", nargs="+", choices=list(checks), default=list(checks))
    options = parser.parse_args()
    failed = False
    for name in options.providers:
        print(f"\n[{name}]")
        try:
            checks[name]()
        except Exception as error:
            failed = True
            print("  ERROR:", str(error) if isinstance(error, wc.ReportError)
                  else "Access/client failure; check API enablement, credential, scopes and property permissions.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
