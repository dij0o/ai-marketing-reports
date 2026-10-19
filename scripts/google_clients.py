"""Shared auth + API client helpers. Credentials come from GOOGLE_APPLICATION_CREDENTIALS (never stored in the project)."""
import json
import os
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text())

SCOPES = {
    "gtm": [
        "https://www.googleapis.com/auth/tagmanager.edit.containers",
        "https://www.googleapis.com/auth/tagmanager.edit.containerversions",
        "https://www.googleapis.com/auth/tagmanager.publish",   # requested, but in practice the robot could not publish
        "https://www.googleapis.com/auth/tagmanager.readonly",
    ],
    "gsc": ["https://www.googleapis.com/auth/webmasters.readonly"],
    "ga4": [
        "https://www.googleapis.com/auth/analytics.edit",
        "https://www.googleapis.com/auth/analytics.readonly",
    ],
    "ads": ["https://www.googleapis.com/auth/adwords"],
}

SECRETS = Path.home() / ".secrets"


def _creds(service):
    key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or str(SECRETS / "sa.json")
    return service_account.Credentials.from_service_account_file(key_path, scopes=SCOPES[service])


def gtm():
    return build("tagmanager", "v2", credentials=_creds("gtm"), cache_discovery=False)


def gsc():
    return build("searchconsole", "v1", credentials=_creds("gsc"), cache_discovery=False)


def ga4_admin():
    return build("analyticsadmin", "v1beta", credentials=_creds("ga4"), cache_discovery=False)


def ga4_admin_alpha():
    """Some admin features (channel groups, key events variants) live in v1alpha."""
    return build("analyticsadmin", "v1alpha", credentials=_creds("ga4"), cache_discovery=False)


def ga4_data():
    return build("analyticsdata", "v1beta", credentials=_creds("ga4"), cache_discovery=False)


def gtm_container_path():
    g = CONFIG["gtm"]
    return f"accounts/{g['account_id']}/containers/{g['container_id']}"
