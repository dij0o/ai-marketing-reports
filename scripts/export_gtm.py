"""Read-only export of the GTM live version and first workspace to snapshots/ for review and diffing."""
import json
from datetime import date
from pathlib import Path

import google_clients as gc

out_dir = Path("snapshots")
out_dir.mkdir(exist_ok=True)

svc = gc.gtm()
path = gc.gtm_container_path()
c = svc.accounts().containers()

live = c.versions().live(parent=path).execute()
ws = c.workspaces().list(parent=path).execute()["workspace"][0]
w = c.workspaces()
workspace = {
    "workspace": ws,
    "status": w.getStatus(path=ws["path"]).execute(),
    "tags": w.tags().list(parent=ws["path"]).execute().get("tag", []),
    "triggers": w.triggers().list(parent=ws["path"]).execute().get("trigger", []),
    "variables": w.variables().list(parent=ws["path"]).execute().get("variable", []),
    "builtInVariables": w.built_in_variables().list(parent=ws["path"]).execute().get("builtInVariable", []),
}

stamp = date.today().isoformat()
for name, data in [("live", live), ("workspace", workspace)]:
    f = out_dir / f"gtm_{name}_{stamp}.json"
    f.write_text(json.dumps(data, indent=2))
    print(f"wrote {f}")
