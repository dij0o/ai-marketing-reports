"""Render the supplied report layout without lead targets, ramps or forecasts."""
import argparse
import copy
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StateParser(HTMLParser):
    """Read the JSON state as data; never run scripts in a supplied document."""
    def __init__(self):
        super().__init__()
        self.reading = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("id") == "state":
            self.reading = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.reading = False

    def handle_data(self, data):
        if self.reading:
            self.parts.append(data)


def read_state(path):
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() in (".html", ".htm"):
        parser = StateParser()
        parser.feed(text)
        text = "".join(parser.parts)
    return json.loads(text)


def without_targets(source, brand=None):
    state = copy.deepcopy(source)
    if not isinstance(state, dict) or not isinstance(state.get("weeks"), list):
        raise ValueError("Expected the sample report's JSON state, not a combined API snapshot.")
    state.pop("rates", None)
    state.pop("targetWeek", None)
    measured = ("leads", "intent", "sessions", "clicks", "impressions", "indexed")
    state["weeks"] = [week for week in state["weeks"] if any(week.get(key) is not None for key in measured)]
    for week in state["weeks"]:
        week.pop("plan", None)
    if brand:
        state["brand"] = brand
    state.setdefault("brand", "Example site")
    for risk in state.get("visuals", {}).get("risks", []):
        if risk.get("id") == "ctr":
            rates = [100 * week["clicks"] / week["impressions"] for week in state["weeks"] if isinstance(week.get("clicks"), (int, float)) and isinstance(week.get("impressions"), (int, float)) and week["impressions"] > 0]
            risk["big"] = f"{rates[-1]:.2f}%" if rates else "Unavailable"
            risk["title"] = "Search click-through by week"
            risk["bigNote"] = "Observed click-through; no assumed benchmark"
            risk["text"] = "Search clicks divided by impressions for each observed week. Compare compatible periods and inspect query coverage before interpreting a change."
    for key, text in state.get("notes", {}).items():
        lines = [line for line in text.splitlines() if not re.search(r"10 (?:leads |a )day|100k|planned close|December target|lead target", line, re.I)]
        state["notes"][key] = "\n".join(lines).replace("before lead numbers drive the ramp", "before interpreting lead counts")
    return state


def render(state):
    css = (ROOT / "templates" / "marketing-report.css").read_text(encoding="utf-8")
    app = (ROOT / "templates" / "marketing-report.js").read_text(encoding="utf-8")
    data = json.dumps(state, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    title = html.escape(state.get("brand", "Example site") + " | Marketing report sample")
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title><style id="css">{css}</style></head>
<body><script type="application/json" id="state">{data}</script><main id="root"></main><script id="app">{app}</script></body></html>
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "examples" / "sample-report.json", help="Sample state JSON or a historical HTML report with a JSON state block.")
    parser.add_argument("--output", type=Path, help="Custom input defaults to an ignored private snapshots output.")
    parser.add_argument("--brand", help="Display name; does not anonymise values or narrative in an imported report.")
    options = parser.parse_args()
    try:
        if options.output is None:
            options.output = ROOT / ("examples/sample-report.html" if options.input.resolve() == (ROOT / "examples/sample-report.json").resolve() else "snapshots/imported-report.html")
        if options.input.resolve() == options.output.resolve():
            raise ValueError("Use a different output path to preserve the source report.")
        state = without_targets(read_state(options.input), options.brand)
        options.output.parent.mkdir(parents=True, exist_ok=True)
        options.output.write_text(render(state), encoding="utf-8")
        print(f"Saved offline report: {options.output}")
        return 0
    except (OSError, ValueError, TypeError, KeyError):
        print("Cannot render report. Check input state, template files and the output path.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
