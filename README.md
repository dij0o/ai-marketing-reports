# AI Marketing Reports: Google, Bing and Yandex reporting

Python scripts that let you (or an AI assistant) pull data from **Google Tag Manager, GA4, Search Console, Google Ads, Bing Webmaster Tools and Yandex Webmaster**. The Google scripts originated on another site; Bing and Yandex collectors and a combined search/analytics report extend that approach.

Start with [the full Webmaster reporting guide](docs/webmaster-reporting.md) for ownership verification, API access, environment variables, script inventory, output fields, date limits and troubleshooting.

An [offline sample report](examples/README.md) shows the fuller presentation: observed trends, Ads, visitor activity, keyword gaps, Bing/Yandex and source status, with **no lead target or revenue forecast**. Its names and figures are fictional. Download `examples/sample-report.html` and open it locally, or regenerate it with `python scripts/sample_report.py`.

Before reusing the scripts, follow [Customise the reports for your site's events](docs/customizing-events.md). It maps website/GTM/GA4 events and parameters to the exact script settings, outcome versus interest counts, and sample report inputs and labels. The shipped event names are examples, not automatic discovery of your site's conversion model.

The full walkthrough is in the companion blog post. This repo holds the code.

> **Nothing here contains credentials.** Keys, tokens, your IDs and generated data are git-ignored. Run `python scripts/scan_for_private_data.py` before every push.

## Easiest route: ask your AI assistant to set it up

You do not have to work through every settings screen yourself. Use an AI assistant
with browser access through its application's browser or a browser extension, and
ask it to carry out the setup. You create or sign into the necessary accounts and
handle any identity, consent or verification prompts; the assistant can then work
through the configuration and check the results wherever its tools support it.

Give it this repository and your site, then start with:

```text
Open your browser and help me set up the reporting tools in this repository
for my website. I will create or sign into the necessary accounts when asked.
Read the setup and event-customisation guides, inspect my site's existing
events, and configure GA4, Search Console, Tag Manager, Google Ads API access
for keyword research, Bing Webmaster Tools and Yandex Webmaster.
Adapt the scripts and sample report to my actual event definitions. Keep
credentials local and out of chat/Git. Set up reporting without launching
paid campaigns. Verify each connection and event, then generate the report
and clearly identify anything still waiting for provider approval or data.
```

See [Browser-assisted setup](docs/webmaster-reporting.md#browser-assisted-setup)
for the division of work. Browser and local-file capabilities vary by assistant;
an assistant without local access can prepare the files and commands for you to run.

## How access works

The Google scripts use a **service account** with a local JSON key and separate product-level permissions. Bing uses its own Webmaster API key from `BING_API_KEY`. Yandex uses an OAuth token from `YANDEX_TOKEN`. Neither new provider uses the Google identity. Keep all credentials outside Git; only non-secret site/property settings belong in local `config.json`.

| Product | Add the robot as | What the scripts do |
| --- | --- | --- |
| Search Console | A user on the property (Settings > Users and permissions) | Read queries, pages, sitemaps, URL inspection |
| GA4 | **Viewer** for reporting; **Editor** only for configuration | Read reports; optionally change settings with `ga4_configure.py` |
| Google Tag Manager | **Edit** (or Approve) on the container | Read, edit a workspace, create versions (a human publishes) |
| Google Ads | An authorised user on the account; appropriate Cloud project API access | Reporting and Keyword Planner |
| Bing Webmaster | Verify the exact site URL, then supply your Webmaster API key | Read property, URL, search, crawl and sitemap records |
| Yandex Webmaster | Verify the site, authorise a Webmaster OAuth application, then supply its token | Read host, popular-query sample, diagnostics and sitemap records |

You need the relevant owner/admin permission to grant product access. The new combined report requests read-only Google scopes. Existing Google helpers also request edit/publish scopes for configuration tasks; review both scopes and actual product permissions before using those scripts.

## Setup

1. Create a Google Cloud project and enable: Tag Manager API, Google Analytics Admin API, Google Analytics Data API, Google Search Console API, Google Ads API.
2. Create a service account (IAM & Admin > Service Accounts; no Cloud roles needed) and download a JSON key to `~/.secrets/sa.json`. Never put the key inside this folder. Delete the downloaded copy.
3. Add the service account's email as a user in each product (table above).
4. `pip install -r requirements.txt`
5. Copy `config.example.json` to `config.json` and fill in your IDs (`config.json` is git-ignored).
6. Set up Bing/Yandex as described in [the guide](docs/webmaster-reporting.md), then run `python scripts/check_access.py`. Use `--providers bing yandex` to check only those two without Google setup. A 403 can indicate permissions, scopes, API approval or credential problems; inspect the source status rather than assuming one cause.

Google's [current migration guide](https://developers.google.com/google-ads/api/docs/api-policy/developer-token) retires developer tokens in favour of Cloud-project API access. For the service-account workflow, the owning project needs the required access level. Keyword planning requires Basic or Standard access; new Basic applications require branding verification, an External audience and In production OAuth profile, even for a service-account integration without a visitor login page. Review Google's [brand verification instructions](https://developers.google.com/google-ads/api/docs/api-policy/brand-verification). The legacy `ads_client.py` comments retain old token advice; do not add a developer token to work around project approval. Review its API version before running Ads scripts.

## Run from the repo root

```bash
python scripts/check_access.py
python scripts/bing_pull.py --days 28
python scripts/yandex_pull.py --days 28
python scripts/webmaster_report.py --days 28  # GSC + Bing + Yandex + GA4, JSON and Markdown
python scripts/ga4_report_pull.py      # daily sessions, lead events, Search Console totals
python scripts/ga4_slices.py           # country x channel, bot-like traffic
python scripts/ga4_journey.py          # what organic visitors do after the click
python scripts/gsc_pull.py             # queries, pages, sitemaps, URL inspection
python scripts/ads_pull.py             # campaigns, spend, search terms, paid sessions
python scripts/weekly_cpl_report.py    # cost per lead + Excel workbook
python scripts/keyword_ideas.py        # Keyword Planner ideas
```

Write scripts are **dry-run by default** and never publish anything:

```bash
python scripts/gtm_sync.py             # prints the plan; add --apply to write to a GTM workspace
python scripts/ga4_configure.py        # prints the plan; add --apply to change GA4 settings
```

The new collectors save dated JSON in `snapshots/`. The combined report saves timestamped JSON plus a Markdown companion containing source paths, coverage, metadata, errors and up to 20 displayed rows per dataset; all collected rows remain in JSON. The existing `ga4_report_pull.py` now also includes structured `bing` and `yandex` sections without changing its Google fields.

The new commands default to the last 28 completed days in `Asia/Karachi`; use `--start`, `--end`, `--days` and `--timezone` explicitly when needed. Bing weekly buckets and Yandex's actual returned range retain their original meaning. Empty responses and failed connections remain distinct; no report invents search traffic. The new commands exit nonzero on partial/missing connections **after saving available data**. They never submit URLs, alter sitemaps or publish tags. The legacy daily pull retains its existing exit behaviour; inspect its new provider statuses.

Existing Google scripts have their own event examples, dates and UTC defaults: adapt them to your site. Most pulls write JSON; `weekly_cpl_report.py` also produces an Excel workbook. The combined Webmaster report covers search and GA4, while Ads spend, keyword research and cost-per-lead remain separate scripts. No scheduler is installed.

## Validate changes

```bash
python -m unittest discover -s tests -v
python -m compileall -q scripts tests
python scripts/scan_for_private_data.py
```

Tests use isolated responses, never real credentials or live account data. Successful tests do not establish provider connectivity.

## Before you push anything public

```bash
python scripts/scan_for_private_data.py
git config core.hooksPath .githooks   # run the scan automatically on every commit
```

## Licence

MIT. See `LICENSE`.
