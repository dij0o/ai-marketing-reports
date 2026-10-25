# Customise the reports for your site's events

Start with the actions that matter on **your** site. The repository's lead,
WhatsApp and phone events are examples from a property site, not a required event
model. A portfolio might measure project opens, completed article reads and accepted
enquiries. A shop might measure purchases; a product might measure completed sign-ups.
Choose event names and definitions before changing the report's labels.

## 1. Write a small event contract

For each event, record the exact name sent to GA4, when it fires, what it means,
which parameters accompany it and how it should be counted. Separate outcomes,
intent and content interest. For example:

| Role | Example event | Trigger and interpretation | Useful context |
| --- | --- | --- | --- |
| Outcome | `enquiry_sent` | The enquiry API reports successful acceptance. This does not establish inbox delivery or a qualified prospect. | `origin_section`, `article_slug` |
| Intent | `enquiry_open` | Someone opens the enquiry form. An open is not a submission. | `origin_section` |
| Content interest | `project_open` | Someone opens a project. | `project_id` |
| Content interest | `note_read_complete` | Your defined reading-time and article-progress rule is met. This does not prove comprehension. | `article_slug` |

These are illustrative definitions. Adapt them to the actual implementation. A
click, event, session, user and accepted transaction are different units. Multiple
events from one person are not multiple qualified leads. Do not add a purchase,
form open and article read into one conversion total simply because all three
are useful.

## 2. Align the website, GTM and GA4

Use the site's existing consent-aware tracking function where one exists. In a
GTM/data-layer implementation, a conceptual outcome event could look like this:

```javascript
// After the agreed success condition, through your consent-aware tracking path:
window.dataLayer = window.dataLayer || [];
window.dataLayer.push({
  event: 'enquiry_sent',
  origin_section: 'article',
  article_slug: 'example-article'
});
```

This snippet alone does not enforce consent or send an event to GA4. Configure the
matching GTM Custom Event trigger and GA4 event tag, map the parameters, and retain
your consent and hostname gates. If your site's payload nests context under
`analytics`, the GTM variable path must match, for example
`analytics.article_slug` rather than `article_slug`. GTM can translate an internal
event name into a different GA4 name, but the Python queries must use the name GA4
actually receives.

Register appropriate custom parameters as event-scoped custom dimensions when
needed in reports, and mark only the intended outcomes as key events. Sending a
parameter, registering it, collecting it and querying it are separate steps.
Registration does not make these scripts automatically add a new breakdown.
Review built-in/recommended events before defining a custom equivalent, and check
automatic measurement for overlap with your own events. Google's references:
[data layer](https://developers.google.com/tag-platform/tag-manager/datalayer),
[custom event triggers](https://support.google.com/tagmanager/answer/7679219?hl=en),
[event parameters](https://developers.google.com/analytics/devguides/collection/ga4/event-parameters),
and [custom events](https://support.google.com/analytics/answer/12229021?hl=en).

## 3. Update the actual script definitions

Event mappings are currently defined in code, **not** in `config.json`. Changing a
property ID or editing a report heading will not change the event queries. Review
each script you run:

| File | What to customise |
| --- | --- |
| `scripts/gtm_sync.py` | `VARIABLES`, `TRIGGERS` and `TAGS`, including trigger event names, the GA4 event name and parameter mappings. The shipped `lead_submitted` example must be replaced or deliberately translated. |
| `scripts/ga4_configure.py` | `CUSTOM_DIMENSIONS` and `KEY_EVENTS`. Also review the other proposed property changes before using `--apply`. |
| `scripts/ga4_report_pull.py` | `LEAD` and `ACTIONS`, which determine the events included in the daily query and outcome count. |
| `scripts/ga4_slices.py` | `LEAD` and `ACTIONS` in the country/channel event query. Keep this mapping consistent with the daily pull. |
| `scripts/ads_pull.py` | `ACTIONS` **and** the `generate_lead` literal inside the GA4 paid-event filter. Rename it to the chosen outcome event; editing `ACTIONS` alone is insufficient. |
| `scripts/weekly_cpl_report.py` | `LEAD_EVENTS`, the GA4 sums/labels and the Google Ads conversion definition. The example sums the listed events, including contact clicks; split outcomes from micro-actions before presenting a qualified-lead total or comparable cost per lead. |
| `scripts/ga4_journey.py` | The event/landing-page queries and any custom dimensions or selected event filters you add. It currently reads event names generally rather than using the other scripts' `LEAD` list. |
| `scripts/google_webmaster_pull.py` | The combined report's GA4 `events` dataset reads event names generally, up to its disclosed row limit. Add parameter breakdowns explicitly when needed. `keyEvents` totals cover all property key events and are not automatically your chosen outcome. |

For the portfolio example, the first two reporting scripts could use:

```python
LEAD = ["enquiry_sent"]
ACTIONS = ["enquiry_open"]
```

Keep `project_open` and `note_read_complete` in separate interest views unless you
explicitly decide they belong in an action total. The sample renderer treats every
event row outside its outcome list as an intent action, so feeding all GA4 events
into that list would also count page views and unrelated events as intent.

Search Console, Bing and Yandex measure search-engine activity independently of
your GA4 event names. Their query, crawl and sitemap collectors do not need an event
rename. Google Ads conversion actions and campaign goals also need their own review;
renaming a GA4 query does not reconfigure Ads.

## 4. Adapt the HTML sample's input and labels

Copy `examples/sample-report.json` into the ignored `snapshots/` directory for your
own site. Its `slices` input uses these shapes:

```json
{
  "leadEvents": ["enquiry_sent"],
  "events": [
    ["2026-10-18", "Example country", "Organic Search", "enquiry_sent", 1],
    ["2026-10-18", "Example country", "Organic Search", "enquiry_open", 3]
  ]
}
```

This is an illustrative fragment of `slices`, not a complete report. Each event row
is `[date, country, channel, eventName, eventCount]`. Its separate session rows are
`[date, country, channel, sessions, engagedSessions]`. Populate both from real,
compatible queries; do not derive sessions by adding event counts. Include only
the selected outcome/intent events in `slices.events` and set `slices.leadEvents`
to the exact outcome names. Keep content-interest events in their own datasets.

In `templates/marketing-report.js`, update `FIELDS`, headings, explanatory text and
the labels in `sourceSection`, `adsSection`, `journeySection` and `render` to match
your event meanings. In particular, the sample Ads label mentions `generate_lead`;
replace it when the outcome differs. Rebuild paid totals, weekly figures, activity
steps, notes and risk text from their own sources. Changing labels or
`slices.leadEvents` does not recalculate those independent sections.

For a shop or subscription product, change the outcome unit and relevant sections
too: a purchase or activated account should not still be labelled a lead. Optional
sections should be omitted when their source data does not exist. Keep freshness
and coverage aligned with each source. Render your private copy with:

```powershell
python scripts/sample_report.py --input snapshots/my-report.json --output snapshots/my-report.html --brand 'Your site'
```

The narrative sample schema differs from the combined API snapshot. A file from
`webmaster_report.py` is not a direct input to `sample_report.py`; supplying the
narrative sections requires an explicit transformation and their source datasets.

## 5. Check one action end to end

Perform one controlled action and inspect its website/data-layer payload, GTM
Preview firing, and receipt in GA4 Realtime or DebugView. Check event name,
parameters, consent behaviour and duplicate firing against the contract. Then
inspect the saved script output and report classification for that same event.
Use comparable completed periods and check property/report timezones. Keep test
activity identifiable before drawing audience or conversion conclusions.

Event renaming does not rewrite historical collection. A new name can split a
time series; document its introduction and translate old/new names only when the
underlying meaning is equivalent. Missing events or unavailable dimensions are
not evidence of zero activity. Do not include enquiry text, email addresses or
other form contents in the illustrative context parameters.
