"""Human-readable, JSON, and HTML report renderers."""

from __future__ import annotations

import json
from html import escape

from .models import ValidationReport


def render_json(report: ValidationReport) -> str:
    """Render the report as indented JSON."""
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)


def render_text(report: ValidationReport) -> str:
    """Render a readable console report without copying source values."""
    status = "PASS" if report.passed else "FAIL"
    lines = [
        f"Wildlife Data QC — {status}",
        f"Source: {report.source}",
        f"Profile: {report.profile}",
        f"Rows checked: {report.rows_checked}",
        f"Issues: {report.errors} error(s), {report.warnings} warning(s), {report.info} info",
        "",
    ]
    if not report.issues:
        lines.append("No issues found.")
    else:
        for issue in report.issues:
            location = []
            if issue.row is not None:
                location.append(f"row {issue.row}")
            if issue.field:
                location.append(issue.field)
            suffix = f" ({', '.join(location)})" if location else ""
            lines.append(f"[{issue.severity.upper()}] {issue.code}{suffix}: {issue.message}")
            lines.append(f"  Suggested action: {issue.suggestion}")
    lines.extend(["", "Note: This report contains issue metadata only; source records and coordinate values are not copied into it."])
    return "\n".join(lines)


def render_html(report: ValidationReport) -> str:
    """Render a self-contained HTML report with escaped user-controlled text."""
    status = "PASS" if report.passed else "FAIL"
    rows = []
    for issue in report.issues:
        row = "—" if issue.row is None else str(issue.row)
        field_name = issue.field or "—"
        rows.append(
            "<tr>"
            f"<td>{escape(issue.severity.upper())}</td>"
            f"<td><code>{escape(issue.code)}</code></td>"
            f"<td>{escape(row)}</td>"
            f"<td>{escape(field_name)}</td>"
            f"<td>{escape(issue.message)}</td>"
            f"<td>{escape(issue.suggestion)}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="6">No issues found.</td></tr>')

    status_class = "pass" if report.passed else "fail"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Wildlife Data QC — {escape(report.source)}</title>
<style>
:root {{ color-scheme: light; --ink:#17251f; --muted:#64736c; --line:#dce5df; --green:#176b4b; --red:#a72f37; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; padding:32px; font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; color:var(--ink); background:#f4f7f4; }}
main {{ max-width:1200px; margin:auto; }}
header,.panel {{ background:#fff; border:1px solid var(--line); border-radius:16px; padding:24px; margin-bottom:18px; }}
h1 {{ margin:0 0 6px; font-size:27px; }}
.muted {{ color:var(--muted); }}
.status {{ display:inline-block; padding:4px 10px; border-radius:999px; font-weight:700; }}
.status.pass {{ background:#e4f4eb; color:var(--green); }}
.status.fail {{ background:#fde9e9; color:var(--red); }}
.stats {{ display:flex; gap:12px; flex-wrap:wrap; margin-top:18px; }}
.stat {{ border:1px solid var(--line); padding:12px 18px; border-radius:12px; min-width:130px; }}
.stat strong {{ display:block; font-size:22px; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th,td {{ text-align:left; vertical-align:top; padding:11px; border-bottom:1px solid var(--line); }}
th {{ background:#f6f8f6; }}
code {{ font-size:12px; }}
footer {{ color:var(--muted); font-size:12px; margin:16px 4px; }}
@media(max-width:700px) {{ body {{ padding:14px; }} header,.panel {{ padding:16px; }} .panel {{ overflow:auto; }} table {{ min-width:760px; }} }}
</style>
</head>
<body><main>
<header>
<div class="status {status_class}">{status}</div>
<h1>Wildlife Data Quality Report</h1>
<div class="muted">{escape(report.source)} · profile: {escape(report.profile)} · {report.rows_checked} row(s) checked</div>
<div class="stats">
<div class="stat"><strong>{report.errors}</strong><span class="muted">Errors</span></div>
<div class="stat"><strong>{report.warnings}</strong><span class="muted">Warnings</span></div>
<div class="stat"><strong>{report.info}</strong><span class="muted">Information</span></div>
</div>
</header>
<section class="panel"><h2>Findings</h2><table><thead><tr><th>Severity</th><th>Rule</th><th>Row</th><th>Field</th><th>Finding</th><th>Suggested action</th></tr></thead><tbody>{''.join(rows)}</tbody></table></section>
<footer>Generated locally by Wildlife Observation QC. Source records and coordinate values are not embedded in this report. Review findings with field and taxonomy experts before making changes.</footer>
</main></body></html>"""
