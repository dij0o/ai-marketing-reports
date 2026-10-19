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
        "https://www.googleapis.com/auth/tagmanager.publish",   # requested, but the robot still could not publish
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
USER_TOKEN = SECRETS / "oauth-token.json"
USER_CLIENT = SECRETS / "oauth-client.json"
# Read-only scopes used when running as your own work account (see oauth_login.py).
USER_SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/tagmanager.readonly",
]
# Optional: lets ga4_configure.py change GA4 settings as YOU (you must be an Editor on the property).
# Only requested when you run: python scripts/oauth_login.py --ga4-admin
GA4_ADMIN_SCOPE = "https://www.googleapis.com/auth/analytics.edit"


def user_creds():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if not USER_TOKEN.exists():
        raise RuntimeError("No user token yet - run oauth_login.py first")
    # No scopes passed: the token keeps whatever scopes it was granted at sign-in.
    creds = Credentials.from_authorized_user_file(str(USER_TOKEN))
    if not creds.valid:
        creds.refresh(Request())
        USER_TOKEN.write_text(creds.to_json())
    return creds


def gsc_as_user():
    return build("searchconsole", "v1", credentials=user_creds(), cache_discovery=False)


def ga4_admin_as_user():
    return build("analyticsadmin", "v1beta", credentials=user_creds(), cache_discovery=False)


def ga4_admin_alpha_as_user():
    """Admin API v1alpha as the signed-in user (channel groups etc.). Needs the --ga4-admin sign-in."""
    return build("analyticsadmin", "v1alpha", credentials=user_creds(), cache_discovery=False)


def ga4_data_as_user():
    return build("analyticsdata", "v1beta", credentials=user_creds(), cache_discovery=False)


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


# ---- Mode-aware clients: the scripts call these, so one config setting switches the sign-in route ----
# config.json -> "auth": {"search_console": "user" | "service_account", "ga4": "user" | "service_account"}
# "user" (default): your own read-only sign-in. Use it when your organisation will not let you add a robot user.
# "service_account": the robot key. Use it when you own the property and can add the robot as a user.
def _mode(product):
    mode = CONFIG.get("auth", {}).get(product, "user")
    if mode not in ("user", "service_account"):
        raise ValueError(f'config.json auth.{product} must be "user" or "service_account", got {mode!r}')
    return mode


def gsc_client():
    return gsc() if _mode("search_console") == "service_account" else gsc_as_user()


def ga4_data_client():
    return ga4_data() if _mode("ga4") == "service_account" else ga4_data_as_user()


def ga4_admin_client():
    return ga4_admin() if _mode("ga4") == "service_account" else ga4_admin_as_user()


def ga4_admin_alpha_client():
    return ga4_admin_alpha() if _mode("ga4") == "service_account" else ga4_admin_alpha_as_user()
