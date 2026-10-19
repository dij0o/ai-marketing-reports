"""GA4, daily: sessions + engaged sessions by date x country x channel, chosen events by the same, and bot-like groups.
Bot-like: >= MIN_SESSIONS sessions in the period and engagement rate < MAX_ENGAGED.
Usage: python ga4_slices.py [--start=YYYY-MM-DD]"""
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import google_clients as gc

TZ = timezone(timedelta(hours=0))
START = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--start=")), "2026-01-01")
END = str(datetime.now(TZ).date() - timedelta(days=1))
PROP = f"properties/{gc.CONFIG['ga4']['property_id']}"
LEAD, ACTIONS = ["generate_lead"], ["whatsapp_click", "phone_click", "email_click"]
MIN_SESSIONS, MAX_ENGAGED = 15, 0.08
Path("snapshots").mkdir(exist_ok=True)


def run(svc, dims, mets, flt=None):
    out, offset = [], 0
    while True:
        body = {"dateRanges": [{"startDate": START, "endDate": END}], "dimensions": [{"name": x} for x in dims],
                "metrics": [{"name": x} for x in mets], "limit": 10000, "offset": offset}
        if flt:
            body["dimensionFilter"] = flt
        r = svc.properties().runReport(property=PROP, body=body).execute()
        rows = r.get("rows", [])
        out += [[v["value"] for v in x["dimensionValues"]] + [float(v["value"]) for v in x["metricValues"]] for x in rows]
        offset += len(rows)
        if not rows or offset >= int(r.get("rowCount", 0)):
            return out


def main():
    svc = gc.ga4_data()
    iso = lambda d: f"{d[:4]}-{d[4:6]}-{d[6:]}"
    sess = [[iso(r[0]), r[1], r[2], int(r[3]), int(r[4])] for r in
            run(svc, ["date", "country", "sessionDefaultChannelGroup"], ["sessions", "engagedSessions"])]
    ev = [[iso(r[0]), r[1], r[2], r[3], int(r[4])] for r in
          run(svc, ["date", "country", "sessionDefaultChannelGroup", "eventName"], ["eventCount"],
              {"filter": {"fieldName": "eventName", "inListFilter": {"values": LEAD + ACTIONS}}})]
    pair, chan = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    for _, c, ch, s, e in sess:
        pair[(c, ch)][0] += s; pair[(c, ch)][1] += e
        chan[ch][0] += s; chan[ch][1] += e
    bots = [{"country": c, "channel": ch, "sessions": s, "engaged": e}
            for (c, ch), (s, e) in sorted(pair.items(), key=lambda x: -x[1][0])
            if s >= MIN_SESSIONS and e / s < MAX_ENGAGED]
    bots += [{"country": "*", "channel": ch, "sessions": s, "engaged": e}
             for ch, (s, e) in chan.items() if s >= MIN_SESSIONS and e / s < MAX_ENGAGED]
    out = {"generated": datetime.now(TZ).isoformat(timespec="minutes"), "start": START, "end": END,
           "rule": {"min_sessions": MIN_SESSIONS, "max_engaged": MAX_ENGAGED},
           "sessions": sess, "events": ev, "bots": bots}
    f = Path("snapshots") / f"ga_slices_{date.today()}.json"
    f.write_text(json.dumps(out), encoding="utf-8")
    print(f"{START} to {END}: {len(sess)} session rows, {len(ev)} event rows, {len(bots)} bot-like groups; wrote {f}")
    for b in bots:
        print("  bot-like:", b)


if __name__ == "__main__":
    main()
