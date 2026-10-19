"""Create/update GTM variables, triggers and tags in a dedicated workspace. NEVER publishes.
Usage: python gtm_sync.py                         (dry run)
       python gtm_sync.py --apply                 (write to the workspace)
       python gtm_sync.py --apply --version "Name" (also create a container version for a human to publish)"""
import sys
import time

from googleapiclient.errors import HttpError

import google_clients as gc

APPLY = "--apply" in sys.argv
VERSION_NAME = sys.argv[sys.argv.index("--version") + 1] if "--version" in sys.argv else None
WORKSPACE = "Working copy"            # dedicated workspace; created if missing
GA4_MEASUREMENT_ID = "G-XXXXXXXXXX"   # placeholder


def t(key, value):  # template parameter
    return {"type": "template", "key": key, "value": value}


def run(req, tries=6):
    """Execute a request, backing off on quota errors (429 / rateLimitExceeded)."""
    for i in range(tries):
        try:
            time.sleep(0.5)
            return req.execute()
        except HttpError as e:
            if e.status_code in (429, 503) or "rateLimitExceeded" in str(e):
                time.sleep(5 * (i + 1))
                continue
            raise
    raise RuntimeError("GTM quota: gave up after retries")


def log(msg):
    print(("APPLY  " if APPLY else "PLAN   ") + msg)


# ---------- desired state (examples; replace with your own) ----------
VARIABLES = {
    "Constant - GA4 ID": {"type": "c", "parameter": [t("value", GA4_MEASUREMENT_ID)]},
    "DLV - page_type": {"type": "v", "parameter": [t("name", "page_type"), t("dataLayerVersion", "2")]},
}
TRIGGERS = {
    "CE - lead_submitted": {"type": "customEvent",
                            "customEventFilter": [{"type": "equals", "parameter": [
                                t("arg0", "{{_event}}"), t("arg1", "lead_submitted")]}]},
}
TAGS = {   # tag name -> body (firingTriggerId lists trigger NAMES, resolved to IDs below)
    "GA4 - Event - lead_submitted": {
        "type": "gaawe",   # GA4 Event tag
        "parameter": [t("eventName", "lead_submitted"), t("measurementIdOverride", "{{Constant - GA4 ID}}")],
        "firingTriggerId": ["CE - lead_submitted"],
    },
}

svc = gc.gtm()
ctr = svc.accounts().containers()
ws_api = ctr.workspaces()
container = gc.gtm_container_path()

workspaces = run(ws_api.list(parent=container)).get("workspace", [])
ws = next((w for w in workspaces if w["name"] == WORKSPACE), None)
if not ws:
    log(f"create workspace '{WORKSPACE}'")
    if not APPLY:
        print("\nDry run only (workspace missing). Re-run with --apply.")
        sys.exit(0)
    ws = run(ws_api.create(parent=container, body={"name": WORKSPACE}))
W = ws["path"]


def listing(resource, key):
    return run(getattr(ws_api, resource)().list(parent=W)).get(key, [])


def upsert(resource, key, desired, compare_keys, normalise=lambda o: o):
    existing = {o["name"]: o for o in listing(resource, key)}
    ids = {}
    for name, body in desired.items():
        cur = existing.get(name)
        pick = lambda o: normalise({k: o.get(k) for k in compare_keys if o.get(k) not in (None, [])})
        if not cur:
            log(f"create {key} {name}")
            if APPLY:
                created = run(getattr(ws_api, resource)().create(parent=W, body={"name": name, **body}))
                ids[name] = created.get(f"{key}Id")
        else:
            ids[name] = cur.get(f"{key}Id")
            if pick(cur) != pick(body):
                log(f"update {key} {name}")
                if APPLY:
                    run(getattr(ws_api, resource)().update(path=cur["path"], fingerprint=cur["fingerprint"],
                                                            body={"name": name, **body}))
    return ids


sort_params = lambda o: {**o, "parameter": sorted(o["parameter"], key=lambda p: p["key"])} if "parameter" in o else o
upsert("variables", "variable", VARIABLES, ("type", "parameter"), sort_params)
trigger_ids = upsert("triggers", "trigger", TRIGGERS, ("type", "customEventFilter", "filter", "parameter"), sort_params)

# Tags reference triggers by ID: resolve names -> IDs
resolved = {n: {**b, "firingTriggerId": [trigger_ids.get(x, x) for x in b["firingTriggerId"]]} for n, b in TAGS.items()}
upsert("tags", "tag", resolved, ("type", "parameter", "firingTriggerId"), sort_params)

if APPLY:
    status = run(ws_api.getStatus(path=W))
    print(f"\nWorkspace changes: {len(status.get('workspaceChange', []))}, conflicts: {len(status.get('mergeConflict', []))}")
    if VERSION_NAME:
        v = run(ws_api.create_version(path=W, body={"name": VERSION_NAME, "notes": "Created by script. Not published."}))
        print("Created version:", v.get("containerVersion", {}).get("containerVersionId"),
              "| compiler errors:", v.get("compilerError"))
    print("NOT published. Preview/QA first, then a human publishes in the GTM UI.")
else:
    print("\nDry run only. Re-run with --apply.")
