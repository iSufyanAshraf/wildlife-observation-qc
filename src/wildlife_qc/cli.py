"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .render import render_html, render_json, render_text
from .validator import PROFILES, validate_file
from .web import start_dashboard


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wildlife-qc",
        description="Check wildlife occurrence or camera-trap data without modifying source files.",
    )
    parser.add_argument("--version", action="version", version=f"wildlife-qc {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="validate a CSV, TSV, or XLSX data file")
    validate.add_argument("input", type=Path, help="path to a UTF-8 CSV/TSV file or an Excel .xlsx workbook")
    validate.add_argument("--profile", choices=PROFILES, default="occurrence", help="validation profile (default: occurrence)")
    validate.add_argument("--required-field", action="append", default=[], metavar="FIELD", help="require an additional column; repeat as needed")
    validate.add_argument("--sheet", help="Excel worksheet name or zero-based index (default: first worksheet)")
    validate.add_argument(
        "--boundary",
        type=Path,
        help="optional local WGS84 GeoJSON Polygon/MultiPolygon boundary (requires the gis extra)",
    )
    validate.add_argument("--format", choices=("text", "json", "html"), default="text", help="report format written to stdout")
    validate.add_argument("--output", type=Path, help="optional report output path (.json or .html)")
    validate.add_argument("--fail-on", choices=("error", "warning", "never"), default="error", help="exit with code 1 at or above this severity")

    web = subparsers.add_parser("web", help="open the local browser dashboard")
    web.add_argument("--port", type=int, default=8765, help="local dashboard port (default: 8765)")
    web.add_argument("--max-upload-mb", type=int, default=20, help="maximum upload size in MB (default: 20)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "web":
        start_dashboard(port=args.port, max_upload_mb=args.max_upload_mb)
        return 0
    if args.command != "validate":
        return 2
    sheet: str | int | None = args.sheet
    if isinstance(sheet, str) and sheet.isdecimal():
        sheet = int(sheet)
    report = validate_file(
        args.input,
        profile=args.profile,
        required_fields=args.required_field,
        sheet=sheet,
        boundary_path=args.boundary,
    )
    renderers = {"text": render_text, "json": render_json, "html": render_html}
    output = renderers[args.format](report)
    if args.output:
        suffix = args.output.suffix.lower()
        if suffix == ".json":
            output = render_json(report)
        elif suffix in {".html", ".htm"}:
            output = render_html(report)
        elif suffix == ".txt":
            output = render_text(report)
        else:
            print("Output file extension must be .json, .html, or .txt", file=sys.stderr)
            return 2
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"Could not write report: {exc}", file=sys.stderr)
            return 2
    else:
        print(output)

    if args.fail_on == "never":
        return 0
    if report.errors > 0:
        return 1
    if args.fail_on == "warning" and report.warnings > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

