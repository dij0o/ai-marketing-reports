"""One-time sign-in as your own (work) Google account. Saves a token to ~/.secrets, never to the project.
Usage: python scripts/oauth_login.py              (read-only: Search Console, GA4 reports, GTM read)
       python scripts/oauth_login.py --ga4-admin  (also allows ga4_configure.py to change GA4 settings as you)"""
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

import google_clients as gc

scopes = list(gc.USER_SCOPES)
if "--ga4-admin" in sys.argv:
    scopes.append(gc.GA4_ADMIN_SCOPE)

gc.SECRETS.mkdir(exist_ok=True)
flow = InstalledAppFlow.from_client_secrets_file(str(gc.USER_CLIENT), scopes)
creds = flow.run_local_server(
    port=0,
    open_browser=True,
    prompt="select_account consent",
    authorization_prompt_message="Opening browser for Google sign-in - choose your WORK account...",
    success_message="Signed in. You can close this tab and return to the terminal.",
)
gc.USER_TOKEN.write_text(creds.to_json())
print(f"Saved token to {gc.USER_TOKEN} with scopes: {', '.join(s.rsplit('/', 1)[-1] for s in scopes)}")
