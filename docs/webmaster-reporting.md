# Google, Bing and Yandex: access, collection and report details

The repository originally contained Google tooling created for another site. The
same approach can be reused on a portfolio or another site: grant API access,
collect into private files, then let a person or assistant inspect the evidence.
The new Bing and Yandex Python collectors make those integrations available here.
They do not require a browser login page on your website or a visitor tracking tag.

## Ownership is separate from reporting access

First add your site to the appropriate Webmaster portal and complete its ownership
verification. This code reads reports; it does not verify domains, alter DNS,
submit sitemaps or request indexing. Keep existing verification and email DNS
records when adding a new TXT record.

For Yandex, one ownership method is a root TXT record containing the exact
`yandex-verification` value provided by the portal. Confirm public DNS visibility,
then confirm verification in Webmaster. For Bing, verify the exact property URL
in Webmaster Tools. The collector checks the API's returned property record rather
than inferring ownership from a successful HTTP request.

A verified property, a processed sitemap and search impressions are separate facts.
None should be substituted for another in an assistant's report.

## Local setup

From the repository root:

```powershell
python -m pip install -r requirements.txt
Copy-Item config.example.json config.json
```

Edit local `config.json` with the exact URLs and IDs shown by the providers.
`bing.site_url` preserves scheme, hostname, path and trailing slash; do not replace
an apex property with a www property. Set `yandex.host_id` from the hosts endpoint
or leave it blank to discover an exact matching `yandex.site_url`. Host IDs are
provider identifiers, for example `https:example.com:443`, rather than a normal URL.
Existing Google-only config files remain compatible; new provider sections are
optional until you enable those connections.

Keys and tokens come only from process environment variables. These examples use
placeholders, not real values; avoid putting secrets in shell history or chat.
An approved local launcher/secret manager can populate the process environment.
The scripts do not automatically load `.env` files.

```powershell
$env:BING_API_KEY = '<BING_API_KEY>'
$env:YANDEX_TOKEN = '<YANDEX_OAUTH_TOKEN>'
$env:GOOGLE_APPLICATION_CREDENTIALS = '<PRIVATE_KEY_FILE_OUTSIDE_REPO>'
```

### Bing

Retrieve your key in Bing Webmaster Tools' Webmaster API access settings and expose
it as `BING_API_KEY`. The key may permit writes elsewhere; these scripts allow only
the seven GET methods listed below. Do not share it or place it in `config.json`.

```powershell
python scripts/check_access.py --providers bing
python scripts/bing_pull.py --start 2026-10-01 --end 2026-10-24
```

An API connection with no search records is a valid empty response, not zero
traffic. The property and sitemap endpoints can succeed while performance endpoints
return no rows. Compare `returned_rows` before filtering with the selected rows and
`available` dates before blaming the report's date window.

### Yandex

Register an OAuth application using Yandex's Webmaster authorisation instructions,
authorise it for your own Webmaster account, and store the raw token in
`YANDEX_TOKEN`, without an `OAuth` or `Bearer` prefix. Follow the provider's current
scope instructions; `webmaster:hostinfo` concerns reading site information and
`webmaster:verify` concerns ownership operations. This collector makes no verification
or management writes. Logging into Yandex through Google is not an API credential.

```powershell
python scripts/check_access.py --providers yandex
python scripts/yandex_pull.py --days 28
```

The collector requests `/v4/user`, then lists hosts, resolves the configured host,
and retrieves popular queries, diagnostics and sitemaps. If the initial request
times out without an HTTP response, credentials remain unverified. Check DNS and
network reachability before replacing a token. A response timeout is distinguished
from a connection timeout; neither is reported as a confirmed credential rejection.
Requests have bounded timeouts and do not follow redirects. Rate limits are reported
explicitly; rerun later instead of repeatedly refreshing.

## Google and Google Ads access

For the combined report, enable Search Console API and Analytics Data API, supply a
local service-account key and grant access on the actual properties. Use GA4 Viewer
for reporting and an appropriate Search Console property user. A GA4 numeric
property ID is different from its `G-` measurement ID. The combined report requests
only `webmasters.readonly` and `analytics.readonly`; configuration scripts elsewhere
in the repository have different scope and product-permission requirements.

For site-specific event definitions, parameters, outcome classification and sample
labels, follow [Customise the reports for your site's events](customizing-events.md).
This covers the exact script settings; changing a property ID alone does not adapt
the example event model.

Google Ads and Keyword Planner remain separate scripts. API enablement, service
account identity, account permissions and project API approval are different gates.
For new Basic access applications, Google's Ads-specific instructions require brand
verification and an External, In production OAuth profile. Branding includes public
application information and policy URLs. On a site without visitor sign-in, this
still concerns project branding and API approval; it does not add visitor login.
Review and supply your actual terms/privacy pages as appropriate for your application.

Google's developer-token migration documentation states that access moved to the
Cloud project owning the service account. Do not follow old manager-account token
instructions as a substitute for the project's required approval. API versions and
access policies change; consult the official links below before using Ads scripts.

## Combined report

```powershell
python scripts/webmaster_report.py --days 28
# No Google credential/config section is required for these two sources:
python scripts/webmaster_report.py --providers bing yandex --days 28
# Regenerate Markdown from an existing combined snapshot without API calls:
python scripts/webmaster_report.py --from-json snapshots/<SAVED_REPORT>.json
```

The new collectors default to the previous 28 completed calendar days in
`Asia/Karachi`. `--start` and `--end` are inclusive ISO dates. Current/future end
dates and inverted windows are rejected. `--timezone` changes calendar boundaries,
not the underlying providers' reporting timezone or weekly bucket meaning.
`tzdata` supplies IANA zones on Windows.

Standalone collectors write `bing_<end>.json` and `yandex_<end>.json`. A later pull
for the same end date replaces that standalone file. The combined command writes
timestamped `webmaster_report_<UTC-time>.json` and `.md` files into `snapshots/`.
The JSON preserves every collected row and source status. Markdown displays up to
20 rows per dataset and explicitly points to the full JSON and dataset path.
It discloses provider truncation independently of this display limit.

Each provider has `generated_at`, `requested`, `status` and `datasets`. Each dataset
includes `status`, `fetched_at`, `rows`, source endpoint/grain/coverage/notes and
applicable returned counts, actual dates, privacy/truncation metadata or a safe
error. Provider failures preserve successful sections and produce a nonzero exit
after saving available results. `not_configured`, `error`, `partial` and `connected`
are distinct. Connected means requests worked, not that traffic exists.

## What is collected and how to read it

| Source | Datasets | Important boundaries |
| --- | --- | --- |
| Search Console | Ungrouped totals; daily, query, page, country and device breakdowns; sitemaps | Final web-search data; processing lag; at most 1,000 rows per breakdown. Query sums need not match site totals. |
| GA4 | Period totals; daily, page, channel, country, device and event breakdowns | Consented activity; distinct users cannot be summed across groups/days. Key events are not automatically enquiries. Metadata retains timezone, thresholding, sampling and row-count truncation. |
| Bing | `GetUserSites`, `GetUrlInfo`, `GetRankAndTrafficStats`, `GetQueryStats`, `GetPageStats`, `GetCrawlStats`, `GetFeeds` | Query/page buckets update weekly. Selected record labels are not exact daily windows. Current property/sitemap status is separate from date-filtered search data. |
| Yandex | Token owner, hosts, popular queries, diagnostics, detected sitemaps | Query sample capped at 500, not site-wide totals. Actual returned dates may narrow the requested period. Sitemaps use cursor pagination, capped at 10,000 top-level records; children are not expanded. |

Bing date values preserve their supplied timezone offset when converted from its
legacy `/Date(...)` format. Missing dates are excluded from windowed history and
counted as undated. Missing metrics stay null; HTTP status 0 is unavailable.
Sitemap feed counts are not indexed-page totals. The overview only sums returned
Bing traffic rows when every contributing value exists and never invents a zero
for an empty report.

Yandex `UNDEFINED` diagnostic states remain unknown, not passes. No sum of popular
queries is displayed as site-wide traffic. Search clicks, GA4 sessions/users and
Keyword Planner demand describe different populations and must not be added.
Compare equal completed periods with compatible coverage before attributing change.

## Script inventory and existing workflows

- `webmaster_clients.py`: dates, configuration, safe HTTP, null preservation, source envelopes and output redaction.
- `bing_pull.py`: standalone read-only Bing collection.
- `yandex_pull.py`: standalone read-only Yandex collection and host discovery.
- `google_webmaster_pull.py`: read-only GSC/GA4 collectors for the combined report.
- `webmaster_report.py`: collect all four sources, generate JSON/Markdown, or render a saved snapshot offline.
- `check_access.py`: Google, Bing and Yandex checks; select providers explicitly; nonzero on failure.
- `ga4_report_pull.py`: existing daily Google output plus new `bing` and `yandex` sections and status summary. It retains its original UTC defaults, event examples and exit behaviour; inspect nested statuses.
- `tests/test_webmaster.py`: isolated schema, access-failure, timeout, pagination, privacy and reporting tests.

Existing Ads, keyword, GTM, GA4 journey/slice/configuration, GSC inspection and weekly
CPL scripts remain available as described in the README. Those Google scripts were
created for another site's event names and defaults. Align events across website,
tags, GA4 and report queries before reusing them. An enquiry event's meaning must
come from your implementation, not an assistant's assumption.

## Private output and verification

`config.json`, `.env`, keys, `snapshots/`, CRM inputs and workbooks remain ignored.
The credential scanner now also recognises Bing/Yandex credential assignments.
New HTTP errors never persist request URLs, headers, raw bodies or exception text;
output redaction also removes configured Bing/Yandex secrets. Snapshots still
contain private analytics/property data: do not publish them or attach them to a PR.
The examples and tests contain no live account data. No scheduler is installed.

```powershell
python -m unittest discover -s tests -v
python -m compileall -q scripts tests
python scripts/scan_for_private_data.py
```

These checks validate implementation with synthetic responses. Validate live access
separately in your own environment and retain unavailable data as unavailable.

## Official references

- [Bing API key and HTTP interface](https://blogs.bing.com/webmaster/2019/11/Accessing-Bing-webmaster-tools-api-using-cURL/)
- [Bing query statistics and weekly updates](https://learn.microsoft.com/en-us/dotnet/api/microsoft.bing.webmaster.api.interfaces.iwebmasterapi.getquerystats?view=bing-webmaster-dotnet)
- [Yandex OAuth authorisation](https://yandex.ru/dev/webmaster/doc/ru/tasks/how-to-get-oauth)
- [Yandex user lookup](https://yandex.ru/dev/webmaster/doc/ru/reference/user)
- [Yandex popular queries](https://yandex.ru/dev/webmaster/doc/ru/reference/host-search-queries-popular)
- [Yandex diagnostics](https://yandex.ru/dev/webmaster/doc/ru/reference/host-diagnostics-get)
- [Yandex sitemap pagination](https://yandex.ru/dev/webmaster/doc/ru/reference/host-sitemaps-get)
- [Google Ads API access levels](https://developers.google.com/google-ads/api/docs/api-policy/access-levels)
- [Google Ads branding verification](https://developers.google.com/google-ads/api/docs/api-policy/brand-verification)
- [Google Ads developer-token migration](https://developers.google.com/google-ads/api/docs/api-policy/developer-token)
