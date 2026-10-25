"""Shared configuration, safe read-only HTTP and source-aware report envelopes."""
import argparse
import json
import math
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOTS = ROOT / "snapshots"


class ReportError(Exception):
    """A deliberately safe message: never include a request URL or response body."""


def config():
    try:
        result = json.loads((ROOT / "config.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        raise ReportError("Create a valid local config.json from config.example.json.") from None
    if not isinstance(result, dict):
        raise ReportError("config.json must contain an object.")
    return result


def args(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--days", type=int, default=28)
    parser.add_argument("--start", type=date.fromisoformat)
    parser.add_argument("--end", type=date.fromisoformat)
    parser.add_argument("--timezone", default="Asia/Karachi")
    return parser.parse_args()


def window(options):
    try:
        today = datetime.now(ZoneInfo(options.timezone)).date()
    except ZoneInfoNotFoundError:
        raise ReportError("Unknown reporting timezone; install tzdata on Windows.") from None
    if options.days < 1:
        raise ReportError("--days must be positive.")
    end = options.end or today - timedelta(days=1)
    start = options.start or end - timedelta(days=options.days - 1)
    if start > end or end >= today:
        raise ReportError("Choose a completed reporting window with start <= end < today.")
    return {"start": start.isoformat(), "end": end.isoformat(), "timezone": options.timezone}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def number(value):
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def ratio(a, b):
    return a / b if a is not None and b is not None and b != 0 else None


def day(value):
    if not isinstance(value, str) or not value:
        return None
    match = re.fullmatch(r"/Date\((-?\d+)([+-]\d{4})?\)/", value)
    if match:
        offset = match[2]
        zone = timezone.utc
        if offset:
            minutes = int(offset[1:3]) * 60 + int(offset[3:])
            try:
                zone = timezone(timedelta(minutes=minutes if offset[0] == "+" else -minutes))
            except ValueError:
                return None
        try:
            return datetime.fromtimestamp(int(match[1]) / 1000, zone).date().isoformat()
        except (ValueError, OverflowError, OSError):
            return None
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        return None


def site_url(settings, provider):
    value = settings.get(provider, {}).get("site_url") or settings.get("site", "")
    if value and "://" not in value:
        value = "https://" + value
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        raise ReportError("Configure a valid public site URL.")
    return value


def get_json(session, url, *, params=None, headers=None):
    try:
        response = session.get(url, params=params, headers=headers, timeout=(8, 25), allow_redirects=False)
    except requests.ConnectTimeout:
        raise ReportError("Connection timed out before an HTTP response; credential validity is unverified.") from None
    except requests.Timeout:
        raise ReportError("Provider response timed out; authentication and report availability are unverified.") from None
    except requests.RequestException:
        raise ReportError("Cannot reach provider API; check DNS, network and provider availability.") from None
    code = response.status_code
    if not 200 <= code < 300:
        if code in (401, 403):
            raise ReportError(f"HTTP {code}: access denied; check credential, scopes and property permissions.")
        if code == 429:
            raise ReportError("HTTP 429: provider rate limit; retry later.")
        raise ReportError(f"Provider request failed (HTTP {code}); redirects are not followed.")
    try:
        data = response.json()
    except ValueError:
        raise ReportError("Provider returned invalid JSON.") from None
    if not isinstance(data, dict):
        raise ReportError("Provider returned an unexpected JSON shape.")
    if any(data.get(k) for k in ("error", "error_code", "ErrorCode")) or (
        isinstance(data.get("d"), dict) and data["d"].get("ErrorCode")
    ):
        raise ReportError("Provider returned an API error; check its dashboard and permissions.")
    return data


def rows_field(data, key):
    rows = data.get(key)
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ReportError("Provider returned a missing or invalid row collection.")
    return rows


def envelope(provider, period):
    return {"provider": provider, "generated_at": now(), "requested": dict(period), "status": "not_configured", "datasets": {}}


def capture(report, name, endpoint, collect, *, grain, note):
    source = {"endpoint": endpoint, "grain": grain, "note": note, "requested": report["requested"]}
    try:
        payload = collect()
        if not isinstance(payload, dict) or not isinstance(payload.get("rows"), list):
            raise ReportError("Provider returned an invalid dataset.")
        dates = sorted({r["date"] for r in payload["rows"] if r.get("date")})
        source["coverage"] = {"start": dates[0] if dates else None, "end": dates[-1] if dates else None}
        report["datasets"][name] = {"status": "ok", "fetched_at": now(), "source": source, **payload}
    except Exception as error:
        message = str(error) if isinstance(error, ReportError) else "Unexpected provider response or client failure."
        report["datasets"][name] = {"status": "error", "fetched_at": now(), "source": source, "rows": [], "error": message}


def finish(report):
    states = [s["status"] for s in report["datasets"].values()]
    good = states.count("ok")
    report["status"] = "partial" if good and "error" in states else "connected" if good else "error"
    return report


def scrub(value):
    """Defence in depth for saved output; normal error handling already omits bodies/URLs."""
    secrets = [os.environ.get(k, "") for k in ("BING_API_KEY", "YANDEX_TOKEN")]
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if isinstance(value, str):
        for secret in filter(None, secrets):
            value = value.replace(secret, "[REDACTED]")
    return value


def save_json(name, payload):
    SNAPSHOTS.mkdir(exist_ok=True)
    path = SNAPSHOTS / name
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(scrub(payload), indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)
    return path
