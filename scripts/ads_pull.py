"""Read-only Google Ads pull + GA4 Paid Search sessions by campaign, so ad clicks reconcile with sessions.
Usage: python ads_pull.py [--start=YYYY-MM-DD]"""
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import google_clients as gc
from ads_client import gaql, session

TZ = timezone(timedelta(hours=0))
START = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--start=")), "2026-01-01")
END = str(datetime.now(TZ).date())            # Ads reports are same-day, unlike Search Console
PROP = f"properties/{gc.CONFIG['ga4']['property_id']}"
ACTIONS = ["whatsapp_click", "phone_click", "email_click"]
Path("snapshots").mkdir(exist_ok=True)


def ads():
    s = session()
    rng = f"segments.date BETWEEN '{START}' AND '{END}'"
    cust = gaql(s, "SELECT customer.currency_code, customer.descriptive_name, customer.auto_tagging_enabled FROM customer")[0]["customer"]
    camps = [{"id": r["campaign"]["id"], "name": r["campaign"]["name"], "status": r["campaign"]["status"],
              "start": (r["campaign"].get("startDateTime") or "")[:10] or None,   # newer API versions use start_date_time
              "budget": int(r["campaignBudget"]["amountMicros"]) / 1e6,
              "bidding": r["campaign"].get("biddingStrategyType"),
              "search_network": r["campaign"].get("networkSettings", {}).get("targetSearchNetwork", False),
              "display_network": r["campaign"].get("networkSettings", {}).get("targetContentNetwork", False)}
             for r in gaql(s, "SELECT campaign.id, campaign.name, campaign.status, campaign.start_date_time, campaign.bidding_strategy_type, "
                              "campaign.network_settings.target_search_network, campaign.network_settings.target_content_network, "
                              "campaign_budget.amount_micros FROM campaign WHERE campaign.status != 'REMOVED'")]
    daily = [{"date": r["segments"]["date"], "campaign": r["campaign"]["name"], "id": r["campaign"]["id"],
              "impressions": int(r["metrics"].get("impressions", 0)), "clicks": int(r["metrics"].get("clicks", 0)),
              "cost": int(r["metrics"].get("costMicros", 0)) / 1e6, "conversions": float(r["metrics"].get("conversions", 0)),
              "all_conversions": float(r["metrics"].get("allConversions", 0))}
             for r in gaql(s, f"SELECT segments.date, campaign.id, campaign.name, metrics.impressions, metrics.clicks, metrics.cost_micros, "
                              f"metrics.conversions, metrics.all_conversions FROM campaign WHERE {rng} AND campaign.status != 'REMOVED'")]
    convs = [{"name": r["conversionAction"]["name"], "type": r["conversionAction"]["type"],
              "category": r["conversionAction"].get("category"), "primary": r["conversionAction"].get("primaryForGoal", False)}
             for r in gaql(s, "SELECT conversion_action.name, conversion_action.type, conversion_action.category, conversion_action.primary_for_goal "
                              "FROM conversion_action WHERE conversion_action.status = 'ENABLED'")]
    terms = [{"term": r["searchTermView"]["searchTerm"], "campaign": r["campaign"]["name"], "clicks": int(r["metrics"].get("clicks", 0)),
              "impressions": int(r["metrics"].get("impressions", 0)), "cost": int(r["metrics"].get("costMicros", 0)) / 1e6,
              "conversions": float(r["metrics"].get("conversions", 0))}
             for r in gaql(s, f"SELECT search_term_view.search_term, campaign.name, metrics.clicks, metrics.impressions, metrics.cost_micros, "
                              f"metrics.conversions FROM search_term_view WHERE {rng} ORDER BY metrics.clicks DESC LIMIT 50")]
    return {"customer": {"currency": cust.get("currencyCode"), "name": cust.get("descriptiveName"),
                         "auto_tagging": cust.get("autoTaggingEnabled")},
            "campaigns": camps, "daily": daily, "conversion_actions": convs, "search_terms": terms}


def ga4_paid():
    svc = gc.ga4_data()
    paid = {"filter": {"fieldName": "sessionDefaultChannelGroup", "stringFilter": {"value": "Paid Search"}}}
    rng = [{"startDate": START, "endDate": END}]

    def run(dims, mets, extra=None):
        flt = paid if not extra else {"andGroup": {"expressions": [paid, extra]}}
        rows = svc.properties().runReport(property=PROP, body={"dateRanges": rng, "dimensions": [{"name": x} for x in dims],
                                                               "metrics": [{"name": x} for x in mets], "dimensionFilter": flt,
                                                               "limit": 10000}).execute().get("rows", [])
        return [[v["value"] for v in r["dimensionValues"]] + [float(v["value"]) for v in r["metricValues"]] for r in rows]

    ev = {"filter": {"fieldName": "eventName", "inListFilter": {"values": ["generate_lead"] + ACTIONS}}}
    return {"sessions": run(["date", "sessionSourceMedium", "sessionCampaignName", "landingPage", "deviceCategory"], ["sessions", "engagedSessions"]),
            "events": run(["date", "sessionCampaignName", "eventName"], ["eventCount"], ev)}


def main():
    out = {"generated": datetime.now(TZ).isoformat(timespec="minutes"), "start": START, "end": END}
    for name, fn in (("ads", ads), ("ga4_paid", ga4_paid)):
        try:
            out[name] = fn()
        except Exception as e:
            out[name + "_error"] = str(e)[:300]
    f = Path("snapshots") / f"ads_{date.today()}.json"
    f.write_text(json.dumps(out, indent=1), encoding="utf-8")
    a = out.get("ads", {})
    spend = sum(d["cost"] for d in a.get("daily", []))
    clicks = sum(d["clicks"] for d in a.get("daily", []))
    print(f"{START} to {END}: {len(a.get('campaigns', []))} campaigns, spend {spend:.2f} {a.get('customer', {}).get('currency')}, "
          f"{clicks} ad clicks. Errors: {[k for k in out if k.endswith('_error')] or 'none'}")
    print("wrote", f)


if __name__ == "__main__":
    main()
