"""Google Ads REST helper (service account, scope adwords)."""
import os

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

import google_clients as gc

API = "https://googleads.googleapis.com/v24"       # bump when Google retires the version
CUSTOMER = gc.CONFIG["google_ads"]["customer_id"]   # 10 digits, no dashes


def session():
    key = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or str(gc.SECRETS / "sa.json")
    creds = service_account.Credentials.from_service_account_file(key, scopes=gc.SCOPES["ads"])
    s = AuthorizedSession(creds)
    # If your account needs them, add:
    #   s.headers["developer-token"] = "<DEVELOPER_TOKEN>"
    #   s.headers["login-customer-id"] = "<MANAGER_CUSTOMER_ID>"
    return s


def gaql(s, query):
    """Run a Google Ads Query Language query, following pagination. Returns the list of result rows."""
    out, token = [], None
    while True:
        r = s.post(f"{API}/customers/{CUSTOMER}/googleAds:search",
                   json={"query": query, **({"pageToken": token} if token else {})})
        if not r.ok:
            raise RuntimeError(f"Google Ads API {r.status_code}: {r.text[:400]}")
        j = r.json()
        out += j.get("results", [])
        token = j.get("nextPageToken")
        if not token:
            return out
