from pathlib import Path

from wildlife_qc.render import render_html, render_json, render_text
from wildlife_qc.validator import validate_file, validate_rows


def test_valid_occurrence_passes_without_findings():
    report = validate_rows(
        [
            {
                "occurrenceID": "survey-001",
                "scientificName": "Axis axis",
                "basisOfRecord": "HumanObservation",
                "eventDate": "2026-10-12",
                "decimalLatitude": "31.5204",
                "decimalLongitude": "74.3587",
                "geodeticDatum": "WGS84",
                "coordinateUncertaintyInMeters": "15",
                "individualCount": "2",
                "countryCode": "PK",
            }
        ]
    )
    assert report.passed
    assert report.rows_checked == 1
    assert report.issues == []


def test_duplicate_occurrence_id_is_an_error():
    base = {
        "occurrenceID": "same-id",
        "scientificName": "Axis axis",
        "basisOfRecord": "HumanObservation",
        "eventDate": "2026-10-12",
    }
    report = validate_rows([base, base])
    assert report.errors == 1
    duplicate = next(issue for issue in report.issues if issue.code == "occurrence_id_duplicate")
    assert duplicate.row == 3


def test_invalid_coordinates_and_zero_uncertainty_are_reported():
    report = validate_rows(
        [
            {
                "occurrenceID": "x-1",
                "scientificName": "Panthera pardus",
                "basisOfRecord": "HumanObservation",
                "eventDate": "2026-10-12",
                "decimalLatitude": "91",
                "decimalLongitude": "74",
                "geodeticDatum": "WGS84",
                "coordinateUncertaintyInMeters": "0",
            }
        ]
    )
    codes = {issue.code for issue in report.issues}
    assert "latitude_out_of_range" in codes
    assert "coordinate_uncertainty_invalid" in codes


def test_incomplete_coordinate_pair_is_error():
    report = validate_rows(
        [
            {
                "occurrenceID": "x-1",
                "scientificName": "Panthera pardus",
                "decimalLatitude": "31.5",
            }
        ]
    )
    assert "coordinate_pair_incomplete" in {issue.code for issue in report.issues}


def test_iso_date_partial_date_and_interval_are_supported():
    report = validate_rows(
        [
            {"occurrenceID": "a", "scientificName": "A", "eventDate": "2026"},
            {"occurrenceID": "b", "scientificName": "B", "eventDate": "2026-04"},
            {"occurrenceID": "c", "scientificName": "C", "eventDate": "2026-04-11/15"},
        ]
    )
    assert "event_date_invalid" not in {issue.code for issue in report.issues}


def test_camera_trap_effort_requires_units():
    report = validate_rows(
        [
            {
                "eventID": "cam-01-deploy-01",
                "eventDate": "2026-10-12",
                "locationID": "site-01",
                "samplingProtocol": "motion-triggered camera trap",
                "sampleSizeValue": "12",
            }
        ],
        profile="camera-trap",
    )
    assert "sample_size_unit_missing" in {issue.code for issue in report.issues}


def test_required_field_checks_for_column_presence():
    report = validate_rows(
        [{"occurrenceID": "a", "scientificName": "A"}],
        required_fields=["eventDate", "decimalLatitude"],
    )
    missing = [issue.field for issue in report.issues if issue.code == "required_column_missing"]
    assert missing == ["eventDate", "decimalLatitude"]


def test_file_validation_and_report_renderers(tmp_path: Path):
    source = tmp_path / "observations.csv"
    source.write_text(
        "occurrenceID,scientificName,basisOfRecord,eventDate\n"
        "obs-1,Axis axis,HumanObservation,2026-10-12\n",
        encoding="utf-8",
    )
    report = validate_file(source)
    assert report.rows_checked == 1
    assert "Wildlife Data QC" in render_text(report)
    assert '"rows_checked": 1' in render_json(report)
    assert "<!doctype html>" in render_html(report)


def test_sensitive_coordinate_values_are_not_echoed_in_report():
    report = validate_rows(
        [
            {
                "occurrenceID": "private-observation",
                "scientificName": "Panthera tigris",
                "basisOfRecord": "private-site-code-742",
                "eventDate": "private-site-code-742",
                "decimalLatitude": "30.123456",
                "decimalLongitude": "71.654321",
            }
        ]
    )
    rendered = render_json(report) + render_text(report) + render_html(report)
    assert "30.123456" not in rendered
    assert "71.654321" not in rendered
    assert "private-site-code-742" not in rendered


def test_not_recorded_datum_is_an_explicit_value_not_a_missing_field():
    report = validate_rows(
        [
            {
                "occurrenceID": "x-2",
                "scientificName": "Axis axis",
                "basisOfRecord": "HumanObservation",
                "eventDate": "2026-10-12",
                "decimalLatitude": "31.5",
                "decimalLongitude": "74.3",
                "geodeticDatum": "not recorded",
            }
        ]
    )
    assert "geodetic_datum_missing" not in {issue.code for issue in report.issues}


def test_cli_exit_codes_respect_fail_on_setting(tmp_path: Path):
    from wildlife_qc.cli import main

    source = tmp_path / "warning.csv"
    source.write_text(
        "occurrenceID,scientificName,basisOfRecord,eventDate\n"
        "obs-1,Axis axis,HumanObservation,2026-10-12\n",
        encoding="utf-8",
    )
    assert main(["validate", str(source), "--fail-on", "error"]) == 0
    assert main(["validate", str(source), "--fail-on", "warning"]) == 1
    assert main(["validate", str(source), "--fail-on", "never"]) == 0


def _sample_workbook_bytes() -> bytes:
    from io import BytesIO

    from openpyxl import Workbook

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Occurrences"
    worksheet.append(
        ["occurrenceID", "scientificName", "basisOfRecord", "eventDate", "decimalLatitude", "decimalLongitude", "geodeticDatum"]
    )
    worksheet.append(["obs-1", "Axis axis", "HumanObservation", "2026-10-12", 31.5, 74.3, "WGS84"])
    extra = workbook.create_sheet("Notes")
    extra.append(["note"])
    extra.append(["not a survey table"])
    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()
    return buffer.getvalue()


def test_xlsx_validation_by_first_sheet_name_and_index():
    from wildlife_qc.validator import validate_bytes

    data = _sample_workbook_bytes()
    by_default = validate_bytes(data, filename="survey.xlsx")
    by_name = validate_bytes(data, filename="survey.xlsx", sheet="Occurrences")
    by_index = validate_bytes(data, filename="survey.xlsx", sheet=0)

    for report in (by_default, by_name, by_index):
        assert report.rows_checked == 1
        assert report.columns[0] == "occurrenceID"
        assert report.passed


def test_xlsx_unknown_sheet_returns_actionable_issue():
    from wildlife_qc.validator import validate_bytes

    report = validate_bytes(_sample_workbook_bytes(), filename="survey.xlsx", sheet="Missing")
    issue = next(issue for issue in report.issues if issue.code == "worksheet_not_found")
    assert "Occurrences" in issue.suggestion
    assert report.rows_checked == 0


def test_xlsx_required_columns_and_coordinate_values_are_not_echoed():
    from wildlife_qc.validator import validate_bytes

    report = validate_bytes(
        _sample_workbook_bytes(),
        filename="private-survey.xlsx",
        required_fields=["recordedBy"],
    )
    rendered = render_json(report) + render_text(report) + render_html(report)
    assert "required_column_missing" in rendered
    assert "31.5" not in rendered
    assert "74.3" not in rendered


def test_validate_file_reads_xlsx_without_modifying_it(tmp_path: Path):
    source = tmp_path / "observations.xlsx"
    original = _sample_workbook_bytes()
    source.write_bytes(original)

    report = validate_file(source, sheet="Occurrences")

    assert report.rows_checked == 1
    assert source.read_bytes() == original


def test_unsupported_file_type_returns_issue():
    from wildlife_qc.validator import validate_bytes

    report = validate_bytes(b"contents", filename="old-workbook.xls")
    assert "file_type_unsupported" in {issue.code for issue in report.issues}


def test_local_dashboard_serves_form_and_validates_upload_in_memory():
    import threading
    from http.server import ThreadingHTTPServer
    from urllib.request import Request, urlopen

    from wildlife_qc.web import make_handler

    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(max_upload_bytes=1024 * 1024))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        with urlopen(base_url) as response:
            page = response.read().decode("utf-8")
            assert response.status == 200
            assert "no cloud upload" in page
            assert "127.0.0.1" not in page

        rejected_host = Request(base_url, headers={"Host": "example.com"})
        try:
            urlopen(rejected_host)
            raise AssertionError("The dashboard should reject non-local Host headers.")
        except Exception as exc:
            assert getattr(exc, "code", None) == 403

        boundary = "----wildlife-qc-test-boundary"
        csv_data = (
            b"occurrenceID,scientificName,basisOfRecord,eventDate\n"
            b"obs-1,Axis axis,HumanObservation,2026-10-12\n"
        )
        body = b"".join(
            [
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"profile\"\r\n\r\noccurrence\r\n".encode(),
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"observations.csv\"\r\nContent-Type: text/csv\r\n\r\n".encode(),
                csv_data,
                f"\r\n--{boundary}--\r\n".encode(),
            ]
        )
        request = Request(
            base_url + "/validate",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urlopen(request) as response:
            result = response.read().decode("utf-8")
            assert response.status == 200
            assert "Wildlife Data Quality Report" in result
            assert "Download JSON report" in result
            assert "obs-1" not in result
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_cli_can_select_excel_worksheet(tmp_path: Path, capsys):
    from wildlife_qc.cli import main

    source = tmp_path / "survey.xlsx"
    source.write_bytes(_sample_workbook_bytes())
    exit_code = main(["validate", str(source), "--sheet", "Occurrences"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Rows checked: 1" in output

