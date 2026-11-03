"""A tiny local-only browser interface using Python's standard library."""

from __future__ import annotations

import base64
import html
import json
import re
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from .render import render_html
from .validator import PROFILES, validate_bytes

_DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>Wildlife Observation QC — Local dashboard</title>
<style>
:root{color-scheme:light;--ink:#182820;--muted:#627168;--line:#dce5de;--green:#176b4b;--deep:#103d2c;--paper:#f3f6f2;--white:#fff;--gold:#d7a84a}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
.shell{max-width:960px;margin:0 auto;padding:38px 22px 54px}
.hero{background:linear-gradient(125deg,#103d2c,#1c6749);color:#fff;border-radius:22px;padding:32px 34px;box-shadow:0 16px 36px rgba(16,61,44,.14)}
.kicker{font-size:11px;letter-spacing:.15em;text-transform:uppercase;color:#c8e1d2;font-weight:700}
h1{font-size:clamp(28px,5vw,42px);line-height:1.12;margin:10px 0 10px;letter-spacing:-.035em}
.hero p{max-width:660px;color:#e1eee6;margin:0}
.local{display:inline-flex;align-items:center;gap:8px;margin-top:20px;border:1px solid rgba(255,255,255,.26);border-radius:99px;padding:6px 11px;font-size:12px;color:#eaf5ee}
.dot{width:7px;height:7px;border-radius:50%;background:#8de1ae;display:inline-block}
.panel{margin-top:22px;background:var(--white);border:1px solid var(--line);border-radius:18px;padding:27px;box-shadow:0 8px 22px rgba(21,49,34,.035)}
h2{margin:0 0 6px;font-size:21px;letter-spacing:-.02em}
.sub{color:var(--muted);margin:0 0 23px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.field{display:flex;flex-direction:column;gap:7px}
label{font-size:13px;font-weight:700}
input,select{font:inherit;color:var(--ink);border:1px solid #cbd7ce;border-radius:10px;padding:11px 12px;background:#fff;min-width:0}
input[type=file]{padding:9px;background:#fbfcfa}
input:focus,select:focus{outline:3px solid rgba(35,124,82,.16);border-color:var(--green)}
.hint{font-size:12px;color:var(--muted)}
.actions{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-top:24px}
button{appearance:none;border:0;border-radius:10px;background:var(--green);color:#fff;padding:12px 18px;font:700 14px system-ui,sans-serif;cursor:pointer}
button:hover{background:var(--deep)}
.privacy{margin-top:20px;border-left:3px solid var(--gold);background:#fbf8ef;border-radius:0 10px 10px 0;padding:12px 14px;color:#655a3d;font-size:13px}
footer{padding:20px 4px 0;color:var(--muted);font-size:12px}
.error{margin-top:18px;padding:12px 14px;border:1px solid #efc7c7;background:#fff4f4;color:#8c2525;border-radius:10px}
@media(max-width:650px){.shell{padding:18px 13px 36px}.hero{padding:25px 22px}.panel{padding:20px}.grid{grid-template-columns:1fr}}
</style>
</head>
<body><main class="shell">
<header class="hero">
<div class="kicker">Wildlife data · quality control</div>
<h1>Check the data before it reaches the map.</h1>
<p>Run a local pre-flight check on occurrence records or camera-trap survey effort. Review clear findings and export a shareable report.</p>
<div class="local"><span class="dot"></span> Runs on this computer · no cloud upload</div>
</header>
<section class="panel">
<h2>Validate a dataset</h2>
<p class="sub">Choose a CSV, TSV, or Excel workbook. Your original file is not edited.</p>
<form method="post" action="/validate" enctype="multipart/form-data">
<div class="field">
<label for="file">Dataset file</label>
<input id="file" name="file" type="file" accept=".csv,.tsv,.xlsx,text/csv,text/tab-separated-values,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" required>
<span class="hint">Supported formats: UTF-8 CSV/TSV and .xlsx. Maximum upload size is enforced by the local server.</span>
</div>
<div class="grid" style="margin-top:19px">
<div class="field">
<label for="profile">Validation profile</label>
<select id="profile" name="profile">
<option value="occurrence">Species occurrence records</option>
<option value="camera-trap">Camera-trap events and effort</option>
</select>
</div>
<div class="field">
<label for="sheet">Excel worksheet (optional)</label>
<input id="sheet" name="sheet" type="text" placeholder="First sheet by default">
<span class="hint">Use an exact worksheet name or a zero-based index such as 0. Applies to .xlsx files only.</span>
</div>
</div>
<div class="field" style="margin-top:19px">
<label for="required">Additional required columns (optional)</label>
<input id="required" name="required_fields" type="text" placeholder="e.g. recordedBy, taxonRank">
<span class="hint">Separate project-specific column names with commas.</span>
</div>
<div class="actions"><button type="submit">Validate dataset</button><span class="hint">The report contains issue metadata, not raw records or coordinate values.</span></div>
</form>
<div class="privacy"><strong>Wildlife privacy:</strong> use access-controlled source files. The dashboard processes uploads in memory and does not save or transmit the uploaded dataset.</div>
</section>
<footer>Wildlife Observation QC · Advisory checks only. Review findings with field, GIS, and taxonomy specialists before changing or publishing records.</footer>
</main></body></html>"""


def _parse_multipart(content_type: str, body: bytes) -> dict[str, tuple[str | None, bytes]]:
    message = BytesParser(policy=default).parsebytes(
        b"Content-Type: " + content_type.encode("ascii", "strict")
        + b"\r\nMIME-Version: 1.0\r\n\r\n" + body
    )
    if not message.is_multipart():
        raise ValueError("Expected a multipart form submission.")

    fields: dict[str, tuple[str | None, bytes]] = {}
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        filename = part.get_filename()
        payload = part.get_payload(decode=True) or b""
        if name not in fields:
            fields[name] = (filename, payload)
    return fields


def _field_text(fields: dict[str, tuple[str | None, bytes]], name: str, default: str = "") -> str:
    if name not in fields:
        return default
    return fields[name][1].decode("utf-8", "replace").strip()


def _report_page(report) -> str:
    document = render_html(report)
    json_payload = json.dumps(report.to_dict(), ensure_ascii=False, indent=2).encode("utf-8")
    encoded = base64.b64encode(json_payload).decode("ascii")
    toolbar = (
        '<nav style="display:flex;gap:10px;flex-wrap:wrap;margin:0 0 18px">'
        '<a href="/" style="display:inline-block;padding:10px 14px;border-radius:9px;background:#176b4b;color:#fff;text-decoration:none;font-weight:700">Validate another file</a>'
        f'<a download="wildlife-qc-report.json" href="data:application/json;base64,{encoded}" '
        'style="display:inline-block;padding:10px 14px;border-radius:9px;border:1px solid #b8c9bd;color:#176b4b;text-decoration:none;font-weight:700">Download JSON report</a>'
        '</nav>'
    )
    return document.replace("<body><main>", "<body><main>" + toolbar, 1)


def _error_page(message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> tuple[int, bytes]:
    page = (
        "<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Wildlife QC — Unable to validate</title><body style='font:16px system-ui;max-width:720px;margin:50px auto;padding:0 18px;color:#182820'>"
        "<h1>Unable to validate this upload</h1><p>" + html.escape(message) + "</p>"
        "<p><a href='/'>Return to the local dashboard</a></p></body></html>"
    )
    return int(status), page.encode("utf-8")


def _parse_sheet_value(value: str) -> str | int | None:
    if not value:
        return None
    if re.fullmatch(r"\d+", value):
        return int(value)
    return value


def make_handler(max_upload_bytes: int = 20 * 1024 * 1024) -> type[BaseHTTPRequestHandler]:
    """Create a request handler with a fixed, bounded in-memory upload size."""

    class DashboardHandler(BaseHTTPRequestHandler):
        server_version = "WildlifeQC/0.2"
        sys_version = ""

        def log_message(self, format: str, *args: object) -> None:
            # Avoid logging client IPs, filenames, or request metadata.
            return

        def _send(self, status: int, body: bytes, content_type: str = "text/html; charset=utf-8") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def _is_local_request(self) -> bool:
            # Require a loopback TCP peer and a local Host to mitigate remote
            # access and DNS-rebinding attempts.
            try:
                from ipaddress import ip_address

                if not ip_address(self.client_address[0]).is_loopback:
                    return False
                host = urlsplit("//" + self.headers.get("Host", ""))
                host_name = (host.hostname or "").lower().rstrip(".")
            except (ValueError, TypeError):
                return False
            return host_name in {"127.0.0.1", "localhost"}

        def _is_same_origin_post(self) -> bool:
            # Browsers normally send Origin on form POSTs. When present, require
            # an exact local origin (including port). For non-browser clients
            # that omit Origin, reject an explicit cross-site Fetch Metadata flag.
            origin = self.headers.get("Origin")
            if not origin:
                return self.headers.get("Sec-Fetch-Site", "").lower() != "cross-site"
            try:
                parsed_origin = urlsplit(origin)
                host = urlsplit("//" + self.headers.get("Host", ""))
                origin_port = parsed_origin.port or (80 if parsed_origin.scheme == "http" else None)
                host_port = host.port or 80
                return (
                    parsed_origin.scheme == "http"
                    and (parsed_origin.hostname or "").lower().rstrip(".") in {"127.0.0.1", "localhost"}
                    and parsed_origin.hostname == host.hostname
                    and origin_port == host_port
                )
            except ValueError:
                return False

        def do_GET(self) -> None:  # noqa: N802
            if not self._is_local_request():
                self._send(HTTPStatus.FORBIDDEN, b"Local requests only", "text/plain; charset=utf-8")
                return
            path = urlsplit(self.path).path
            if path == "/":
                self._send(HTTPStatus.OK, _DASHBOARD_HTML.encode("utf-8"))
            elif path == "/healthz":
                self._send(HTTPStatus.OK, b"ok", "text/plain; charset=utf-8")
            else:
                self._send(HTTPStatus.NOT_FOUND, b"Not found", "text/plain; charset=utf-8")

        def do_POST(self) -> None:  # noqa: N802
            if not self._is_local_request() or not self._is_same_origin_post():
                self._send(HTTPStatus.FORBIDDEN, b"Local same-origin requests only", "text/plain; charset=utf-8")
                return
            if urlsplit(self.path).path != "/validate":
                self._send(HTTPStatus.NOT_FOUND, b"Not found", "text/plain; charset=utf-8")
                return

            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                status, body = _error_page("The request size could not be read.")
                self._send(status, body)
                return
            if content_length <= 0:
                status, body = _error_page("Choose a file before submitting the form.")
                self._send(status, body)
                return
            if content_length > max_upload_bytes + 1024 * 1024:
                status, body = _error_page("The upload exceeds the configured size limit.", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
                self._send(status, body)
                return

            try:
                fields = _parse_multipart(self.headers.get("Content-Type", ""), self.rfile.read(content_length))
                filename, file_data = fields.get("file", (None, b""))
                if not filename or not file_data:
                    raise ValueError("Choose a non-empty CSV, TSV, or .xlsx file.")
                if len(file_data) > max_upload_bytes:
                    status, body = _error_page("The selected file exceeds the configured size limit.", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
                    self._send(status, body)
                    return
                profile = _field_text(fields, "profile", "occurrence")
                if profile not in PROFILES:
                    raise ValueError("Choose a supported validation profile.")
                required_fields = [
                    field.strip()
                    for field in _field_text(fields, "required_fields").split(",")
                    if field.strip()
                ]
                sheet = _parse_sheet_value(_field_text(fields, "sheet"))
                report = validate_bytes(
                    file_data,
                    filename=filename,
                    profile=profile,
                    required_fields=required_fields,
                    sheet=sheet,
                )
                self._send(HTTPStatus.OK, _report_page(report).encode("utf-8"))
            except (ValueError, UnicodeError, OSError) as exc:
                status, body = _error_page(str(exc))
                self._send(status, body)

    return DashboardHandler


def start_dashboard(port: int = 8765, max_upload_mb: int = 20) -> None:
    """Start the dashboard on loopback only; it is not exposed to the network."""
    if not 1 <= port <= 65535:
        raise ValueError("Port must be between 1 and 65535.")
    if max_upload_mb < 1 or max_upload_mb > 500:
        raise ValueError("Maximum upload size must be between 1 and 500 MB.")
    max_upload_bytes = max_upload_mb * 1024 * 1024
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(max_upload_bytes))
    print(f"Wildlife Observation QC is running locally: http://127.0.0.1:{port}")
    print(f"Maximum upload size: {max_upload_mb} MB. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Wildlife Observation QC dashboard.")
    finally:
        server.server_close()
