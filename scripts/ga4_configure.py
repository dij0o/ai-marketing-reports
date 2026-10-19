"""Apply GA4 admin config. Idempotent: skips what already exists.
Usage: python ga4_configure.py            (dry run, prints planned changes)
       python ga4_configure.py --apply
Runs as YOUR signed-in user (sign in with: python scripts/oauth_login.py --ga4-admin), so you must be Editor on the property.
If your organisation blocks service accounts on GA4, this is the route that works."""
import copy
import sys

import google_clients as gc

APPLY = "--apply" in sys.argv
P = f"properties/{gc.CONFIG['ga4']['property_id']}"
alpha = gc.ga4_admin_alpha_as_user()
props = alpha.properties()

# parameter name sent on events -> display name in reports (event-scoped custom dimensions)
CUSTOM_DIMENSIONS = {
    "page_type": "Page type", "cta_location": "CTA location", "form_id": "Form id",
    "link_type": "Link type", "list_name": "List name",
}
KEY_EVENTS = ["generate_lead", "contact_click"]          # events to mark as key events
ENHANCED_OFF = ["pageChangesEnabled", "scrollsEnabled", "siteSearchEnabled", "formInteractionsEnabled"]
AI_SOURCES = (r"chatgpt\.com|chat\.openai\.com|perplexity\.ai|copilot\.microsoft\.com|gemini\.google\.com"
              r"|claude\.ai|meta\.ai|you\.com|deepseek\.com|grok\.com|poe\.com")
CHANNEL_GROUP_NAME = "Custom Channels"


def src_filter(match_type, value, field="eachScopeSource"):
    return {"filter": {"fieldName": field, "stringFilter": {"matchType": match_type, "value": value}}}


def change(desc, fn):
    print(("APPLY  " if APPLY else "PLAN   ") + desc)
    if APPLY:
        fn()


# 1. Data retention -> 14 months (GA4 maximum for standard properties)
ret = props.getDataRetentionSettings(name=f"{P}/dataRetentionSettings").execute()
if ret["eventDataRetention"] != "FOURTEEN_MONTHS":
    change(f"data retention {ret['eventDataRetention']} -> FOURTEEN_MONTHS",
           lambda: props.updateDataRetentionSettings(name=ret["name"], updateMask="eventDataRetention",
                                                     body={"eventDataRetention": "FOURTEEN_MONTHS"}).execute())

# 2. Enhanced measurement: turn off what your own custom events replace (avoids double counting)
for s in props.dataStreams().list(parent=P).execute().get("dataStreams", []):
    em_name = f"{s['name']}/enhancedMeasurementSettings"
    em = props.dataStreams().getEnhancedMeasurementSettings(name=em_name).execute()
    on = [k for k in ENHANCED_OFF if em.get(k)]
    if on:
        change(f"enhanced measurement off on {s['displayName']}: {', '.join(on)}",
               lambda: props.dataStreams().updateEnhancedMeasurementSettings(
                   name=em_name, updateMask=",".join(on), body={k: False for k in on}).execute())

# 3. Custom dimensions
existing = {d["parameterName"] for d in props.customDimensions().list(parent=P, pageSize=200).execute().get("customDimensions", [])}
for param, name in CUSTOM_DIMENSIONS.items():
    if param not in existing:
        change(f"custom dimension {param} ({name})",
               lambda param=param, name=name: props.customDimensions().create(parent=P, body={
                   "parameterName": param, "displayName": name, "scope": "EVENT"}).execute())

# 4. Key events
existing = {k["eventName"] for k in props.keyEvents().list(parent=P).execute().get("keyEvents", [])}
for ev in KEY_EVENTS:
    if ev not in existing:
        change(f"key event {ev}", lambda ev=ev: props.keyEvents().create(parent=P, body={
            "eventName": ev, "countingMethod": "ONCE_PER_EVENT"}).execute())

# 5. Custom channel group: copy the default group's rules and insert an "AI Assistants" channel after Display
groups = props.channelGroups().list(parent=P).execute().get("channelGroups", [])
if not any(g["displayName"] == CHANNEL_GROUP_NAME for g in groups):
    default = next(g for g in groups if g.get("systemDefined"))
    rules = [r for r in copy.deepcopy(default["groupingRule"]) if r["displayName"] != "AI Assistant"]
    default_ai = next((r for r in default["groupingRule"] if r["displayName"] == "AI Assistant"), None)
    # The API requires and_group > or_group > filter; reuse the default AI rule's inner filters.
    ai_or = [src_filter("PARTIAL_REGEXP", AI_SOURCES)]
    if default_ai:
        for part in default_ai["expression"]["andGroup"]["filterExpressions"]:
            ai_or += part["orGroup"]["filterExpressions"]
    ai_rule = {"displayName": "AI Assistants",
               "expression": {"andGroup": {"filterExpressions": [{"orGroup": {"filterExpressions": ai_or}}]}}}
    names = [r["displayName"] for r in rules]
    rules.insert(names.index("Display") + 1, ai_rule)
    body = {"displayName": CHANNEL_GROUP_NAME, "description": "Default channels + AI Assistants",
            "groupingRule": rules, "primary": True}
    change(f"channel group '{CHANNEL_GROUP_NAME}' (primary): " + " > ".join(r["displayName"] for r in rules),
           lambda: props.channelGroups().create(parent=P, body=body).execute())

print("\nDone." if APPLY else "\nDry run only. Re-run with --apply.")
