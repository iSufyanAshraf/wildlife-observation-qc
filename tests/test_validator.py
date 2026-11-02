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
                "decimalLatitude": "30.123456",
                "decimalLongitude": "71.654321",
            }
        ]
    )
    rendered = render_json(report) + render_text(report) + render_html(report)
    assert "30.123456" not in rendered
    assert "71.654321" not in rendered


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
