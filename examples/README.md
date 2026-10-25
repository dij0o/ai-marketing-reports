# Offline report sample

Download and open [sample-report.html](sample-report.html) in a browser. It is a
self-contained example adapted from a supplied property-marketing report, with
fictional company names and figures. All data in [sample-report.json](sample-report.json)
is illustrative, including the Bing records and unavailable Yandex example. No
client account data, credentials, API calls, fonts or CDN scripts are included.

The sample keeps the original report's visual approach, source freshness,
location/low-engagement filters, observed weekly lead metrics, source breakdowns,
Ads, aggregate visitor activity, keyword gaps, risks and weekly notes. An optional
Bing/Yandex section demonstrates the new provider records and missing-data states.
Filters explain which sections they affect; flagged traffic is included by default.

There is no lead target, ramp, future plan, required-growth calculation, assumed
close rate, revenue forecast or actual-versus-plan chart. Recorded lead events and
actual advertising budgets remain ordinary observed metrics. Event counts do not
establish unique qualified prospects.

## Render it again

```powershell
python scripts/sample_report.py
```

The renderer combines the JSON state with `templates/marketing-report.css` and
`templates/marketing-report.js`. Edit those source files and regenerate the HTML;
do not maintain a separate hand-edited copy of the generated output.

You can also adapt a historical HTML report containing a JSON `state` block:

```powershell
python scripts/sample_report.py --input '<HISTORICAL_REPORT.html>' --output snapshots/reference-report.html --brand 'Your site'
```

The importer reads the JSON as data and uses the reviewed local template; it does
not execute scripts or follow instructions from the supplied HTML. It removes
target/rate fields and future plan-only weeks, then renders observed values.
It preserves lead measurements and other historical details. `--brand` changes
the heading, **not** the underlying data or narrative: it is not anonymisation.
Custom inputs default to ignored `snapshots/imported-report.html` if no output is
specified. Keep real imported reports private and out of Git.

This narrative sample has a different schema from the combined API report. Its
Ads, event/geography slices, keyword research, editorial notes and aggregate visitor
activity require their own source data; they are not inferred from the new
four-provider snapshot. `webmaster_report.py` continues to generate source-backed
JSON/Markdown. The sample illustrates a fuller presentation without inventing
unavailable live sections.
