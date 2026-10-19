"""Read-only connection test. Run this first: it tells you which product still lacks access.
All four products use the service account. A 403 means the robot's email has not been added as a user in that product."""
from googleapiclient.errors import HttpError

import google_clients as gc


def check_gtm():
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
    except HttpError as e:
        print(f"  Live version: none published ({e.status_code})")


def check_gsc():
    sites = gc.gsc().sites().list().execute().get("siteEntry", [])
    print("  Sites visible:", ", ".join(f"{s['siteUrl']} ({s['permissionLevel']})" for s in sites) or "none")


def check_ga4():
    summaries = gc.ga4_admin().accountSummaries().list().execute().get("accountSummaries", [])
    for a in summaries:
        for p in a.get("propertySummaries", []):
            print(f"  {a['displayName']} -> {p['displayName']} ({p['property']})")
    if not summaries:
        print("  No GA4 properties visible")


def check_ads():
    from ads_client import API, session
    r = session().get(f"{API}/customers:listAccessibleCustomers")
    print(f"  HTTP {r.status_code}: {r.text[:300]}")


CHECKS = [("Tag Manager", check_gtm),
          ("Search Console", check_gsc),
          ("GA4", check_ga4),
          ("Google Ads", check_ads)]

for name, fn in CHECKS:
    print(f"\n[{name}]")
    try:
        fn()
    except HttpError as e:
        print(f"  ERROR {e.status_code}: {e.reason}")
    except Exception as e:
        print(f"  ERROR: {e}")
