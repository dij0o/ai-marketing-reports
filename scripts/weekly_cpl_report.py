"""Weekly cost-per-lead report. Usage: python weekly_cpl_report.py [--week-ending=YYYY-MM-DD]"""
import csv
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

import google_clients as gc
from ads_client import gaql, session

TZ = timezone(timedelta(hours=0))
HISTORY = Path("snapshots") / "weekly_cpl_history.json"
CRM_CSV = Path("crm_qualified_leads.csv")          # columns: week_start,qualified_leads,notes (filled by sales)
OUT = Path("Weekly_CPL_Report.xlsx")
LEAD_EVENTS = ["generate_lead", "whatsapp_click", "phone_click", "email_click"]
EXPECTED_RATE = (0.02, 0.06)                        # assumed lead rate per click, for sanity estimates
PAUSE_KEYWORD, PAUSE_ADGROUP = 300, 600             # spend (account currency) with zero leads before flagging
LOOKBACK_START = "2026-01-01"
Path("snapshots").mkdir(exist_ok=True)


def week_bounds():
    arg = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--week-ending=")), None)
    end = date.fromisoformat(arg) if arg else None
    if not end:
        today = datetime.now(TZ).date()
        end = today - timedelta(days=today.weekday() + 1)        # last Sunday
    return end - timedelta(days=6), end


def ads_week(s, start, end):
    rng = f"segments.date BETWEEN '{start}' AND '{end}'"
    groups = [{"campaign": r["campaign"]["name"], "ad_group": r["adGroup"]["name"],
               "cost": int(r["metrics"].get("costMicros", 0)) / 1e6, "clicks": int(r["metrics"].get("clicks", 0)),
               "impressions": int(r["metrics"].get("impressions", 0)), "leads": float(r["metrics"].get("conversions", 0))}
              for r in gaql(s, f"SELECT campaign.name, ad_group.name, metrics.cost_micros, metrics.clicks, metrics.impressions, metrics.conversions "
                               f"FROM ad_group WHERE {rng} AND metrics.impressions > 0")]
    actions = [{"campaign": r["campaign"]["name"], "action": r["segments"]["conversionActionName"], "leads": float(r["metrics"].get("conversions", 0))}
               for r in gaql(s, f"SELECT campaign.name, segments.conversion_action_name, metrics.conversions FROM campaign "
                                f"WHERE {rng} AND metrics.conversions > 0")]
    terms = [{"search_term": r["searchTermView"]["searchTerm"], "cost": int(r["metrics"].get("costMicros", 0)) / 1e6,
              "clicks": int(r["metrics"].get("clicks", 0)), "leads": float(r["metrics"].get("conversions", 0))}
             for r in gaql(s, f"SELECT search_term_view.search_term, metrics.cost_micros, metrics.clicks, metrics.conversions "
                              f"FROM search_term_view WHERE {rng} ORDER BY metrics.cost_micros DESC LIMIT 30")]
    return groups, actions, terms


def keywords_to_pause(s, end):
    rng = f"segments.date BETWEEN '{LOOKBACK_START}' AND '{end}'"
    kws = [{"campaign": r["campaign"]["name"], "ad_group": r["adGroup"]["name"], "keyword": r["adGroupCriterion"]["keyword"]["text"],
            "match": r["adGroupCriterion"]["keyword"]["matchType"], "cost": int(r["metrics"].get("costMicros", 0)) / 1e6,
            "clicks": int(r["metrics"].get("clicks", 0)), "leads": float(r["metrics"].get("conversions", 0))}
           for r in gaql(s, f"SELECT campaign.name, ad_group.name, ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type, "
                            f"metrics.cost_micros, metrics.clicks, metrics.conversions FROM keyword_view "
                            f"WHERE {rng} AND ad_group_criterion.status = 'ENABLED'")]
    return [k for k in kws if k["leads"] == 0 and k["cost"] >= PAUSE_KEYWORD]


def ga4_week(start, end):
    svc = gc.ga4_data_as_user()
    body = {"dateRanges": [{"startDate": str(start), "endDate": str(end)}],
            "dimensions": [{"name": "sessionSourceMedium"}, {"name": "eventName"}], "metrics": [{"name": "eventCount"}],
            "dimensionFilter": {"filter": {"fieldName": "eventName", "inListFilter": {"values": LEAD_EVENTS}}}, "limit": 1000}
    rows = svc.properties().runReport(property=f"properties/{gc.CONFIG['ga4']['property_id']}", body=body).execute().get("rows", [])
    out = {"paid": {e: 0 for e in LEAD_EVENTS}, "all": {e: 0 for e in LEAD_EVENTS}}
    for r in rows:
        sm, ev = r["dimensionValues"][0]["value"], r["dimensionValues"][1]["value"]
        n = int(r["metricValues"][0]["value"])
        out["all"][ev] += n
        if sm == "google / cpc":
            out["paid"][ev] += n
    return out


def crm_qualified(start):
    if not CRM_CSV.exists():
        return None
    with CRM_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("week_start") == str(start) and row.get("qualified_leads", "").strip():
                return int(row["qualified_leads"])
    return None


def main():
    start, end = week_bounds()
    s = session()
    groups, actions, terms = ads_week(s, start, end)
    to_pause = keywords_to_pause(s, end)
    try:
        ga4 = ga4_week(start, end)
    except Exception as e:           # keep the Ads half of the report if GA4 fails
        ga4 = {"error": str(e)[:200]}
    cost = sum(g["cost"] for g in groups)
    clicks = sum(g["clicks"] for g in groups)
    leads = sum(g["leads"] for g in groups)
    qualified = crm_qualified(start)
    week = {
        "week_start": str(start), "week_end": str(end), "generated": datetime.now(TZ).isoformat(timespec="minutes"),
        "cost": round(cost, 2), "clicks": clicks, "impressions": sum(g["impressions"] for g in groups),
        "avg_cpc": round(cost / clicks, 2) if clicks else None,
        "leads_ads": round(leads, 1), "cpl_ads": round(cost / leads, 2) if leads else None,
        "lead_rate": round(leads / clicks, 4) if clicks else None,
        "expected_leads": [round(clicks * EXPECTED_RATE[0], 1), round(clicks * EXPECTED_RATE[1], 1)],
        "ga4_paid_leads": sum(ga4["paid"].values()) if "paid" in ga4 else None,
        "ga4_paid_by_event": ga4.get("paid"), "ga4_error": ga4.get("error"),
        "qualified_leads": qualified, "cost_per_qualified": round(cost / qualified, 2) if qualified else None,
        "leads_by_action": actions, "ad_groups": sorted(groups, key=lambda g: -g["cost"]),
        "pause_keywords": to_pause, "pause_ad_groups": [g for g in groups if g["leads"] == 0 and g["cost"] >= PAUSE_ADGROUP],
        "top_search_terms": terms,
    }
    hist = json.loads(HISTORY.read_text()) if HISTORY.exists() else []
    hist = [w for w in hist if w["week_start"] != week["week_start"]] + [week]
    hist.sort(key=lambda w: w["week_start"])
    HISTORY.write_text(json.dumps(hist, indent=1))

    cols = ["week_start", "week_end", "cost", "clicks", "avg_cpc", "leads_ads", "cpl_ads", "lead_rate", "ga4_paid_leads",
            "qualified_leads", "cost_per_qualified"]
    summary = pd.DataFrame([{k: w[k] for k in cols} | {"expected_leads": f"{w['expected_leads'][0]}-{w['expected_leads'][1]}"} for w in hist])
    with pd.ExcelWriter(OUT, engine="openpyxl") as xw:
        summary.to_excel(xw, sheet_name="Weeks", index=False)
        pd.DataFrame(week["ad_groups"]).to_excel(xw, sheet_name="Ad groups this week", index=False)
        pd.DataFrame(week["leads_by_action"]).to_excel(xw, sheet_name="Leads by action", index=False)
        pd.DataFrame(week["pause_keywords"]).to_excel(xw, sheet_name="Keywords to pause", index=False)
        pd.DataFrame(week["top_search_terms"]).to_excel(xw, sheet_name="Top search terms", index=False)
        for ws in xw.book.worksheets:
            ws.freeze_panes = "A2"
    if not CRM_CSV.exists():
        CRM_CSV.write_text("week_start,qualified_leads,notes\n", encoding="utf-8")
    print(json.dumps({k: week[k] for k in ["week_start", "week_end", "cost", "clicks", "leads_ads", "cpl_ads", "lead_rate",
                                           "ga4_paid_leads", "qualified_leads", "ga4_error"]}, indent=1))
    print(f"{len(week['pause_keywords'])} keywords past {PAUSE_KEYWORD} spend with no lead; wrote {OUT}")


if __name__ == "__main__":
    main()
