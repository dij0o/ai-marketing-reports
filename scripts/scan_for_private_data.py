"""Pre-publish safety scan. Fails (exit 1) if any file that git would commit contains something that looks private.
Run it before every commit/push:  python scripts/scan_for_private_data.py
Install as a pre-commit hook:     git config core.hooksPath .githooks
It checks tracked and not-ignored files, so files listed in .gitignore are not scanned (and not committed)."""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = Path(__file__).resolve()

PATTERNS = {
    "Bing or Yandex credential assigned": r'''(?:BING_API_KEY|YANDEX_TOKEN)["']?\s*[:=]\s*["']?(?!<)[A-Za-z0-9_-]{16,}''',
    "private key block": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "service-account JSON field": r'"(private_key|private_key_id|client_secret|refresh_token)"\s*:',
    "service-account type": r'"type"\s*:\s*"service_account"',
    "real service-account email": r"[\w.-]+@(?!<)[\w-]+\.iam\.gserviceaccount\.com",
    "Google OAuth client secret": r"GOCSPX-[\w-]{10,}",
    "Google OAuth access token": r"ya29\.[\w-]{20,}",
    "Google API key": r"AIza[\w-]{30,}",
    "developer token assigned": r"developer-token[\"']?\s*[:=]\s*[\"'](?!<)[\w-]{10,}",
    "GA4 measurement ID": r"\bG-(?!X{6,})[A-Z0-9]{8,12}\b",
    "GTM container ID": r"\bGTM-(?!X{4,})[A-Z0-9]{6,8}\b",
    "Google Ads customer id (10 digits, dashed or not)": r"customers?[/\"': =]+(?!0{10})\d{3}-?\d{3}-?\d{4}\b",
    "email address": r"\b[\w.+-]+@(?!example\.com|<)[\w-]+\.(?:com|org|net|io|co|pk|ae)\b",
}
FORBIDDEN_NAMES = re.compile(r"(sa\.json|service-account.*\.json|oauth-(client|token).*\.json|client_secret.*\.json|^config\.json$|^\.env$|\.xlsx$|^crm_.*\.csv$)")


def files():
    out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True, check=True)
    return [ROOT / f for f in out.stdout.splitlines() if f]


def main():
    problems = []
    for f in files():
        rel = f.relative_to(ROOT).as_posix()
        if FORBIDDEN_NAMES.search(f.name) and f.name != "config.example.json":
            problems.append((rel, 0, "forbidden file name", f.name))
        if f.resolve() == SELF or not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            problems.append((rel, 0, "binary/unreadable file - check by hand", ""))
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for label, pat in PATTERNS.items():
                m = re.search(pat, line)
                if m:
                    problems.append((rel, n, label, m.group(0)[:60]))
    if problems:
        print("PRIVATE-DATA SCAN FAILED - do not commit or push until these are resolved:\n")
        for rel, n, label, hit in problems:
            print(f"  {rel}:{n}  {label}: {hit}")
        return 1
    print(f"Scan clean: {len(files())} files checked, nothing that looks private.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
