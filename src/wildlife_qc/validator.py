"""CSV loading and deterministic wildlife survey data checks.

The checks are advisory quality controls, not a complete implementation of
Darwin Core, GBIF validation, taxonomic reconciliation, or spatial analysis.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import math
import re
from pathlib import Path
from typing import Iterable, Mapping

from .models import Issue, ValidationReport, Severity

PROFILES = ("occurrence", "camera-trap")

# Case- and punctuation-insensitive aliases make common spreadsheet exports easier
# to validate while keeping Darwin Core's canonical field names in reports.
_CANONICAL_FIELDS = {
    "occurrenceid": "occurrenceID",
    "scientificname": "scientificName",
    "basisofrecord": "basisOfRecord",
    "eventdate": "eventDate",
    "eventid": "eventID",
    "parenteventid": "parentEventID",
    "decimallatitude": "decimalLatitude",
    "decimallongitude": "decimalLongitude",
    "geodeticdatum": "geodeticDatum",
    "coordinateuncertaintyinmeters": "coordinateUncertaintyInMeters",
    "individualcount": "individualCount",
    "occurrencestatus": "occurrenceStatus",
    "countrycode": "countryCode",
    "recordedby": "recordedBy",
    "locationid": "locationID",
    "samplingprotocol": "samplingProtocol",
    "samplesizevalue": "sampleSizeValue",
    "samplesizeunit": "sampleSizeUnit",
    "eventdurationvalue": "eventDurationValue",
    "eventdurationunit": "eventDurationUnit",
    "habitat": "habitat",
    "fieldnotes": "fieldNotes",
    "taxonrank": "taxonRank",
    "kingdom": "kingdom",
}

_BASIS_OF_RECORD = {
    "MaterialEntity",
    "PreservedSpecimen",
    "FossilSpecimen",
    "LivingSpecimen",
    "MaterialSample",
    "Event",
    "HumanObservation",
    "MachineObservation",
    "Taxon",
    "Occurrence",
    "MaterialCitation",
}

_MISSING_VALUES = {"", "na", "n/a", "null", "none", "unknown", "not recorded"}


def _canonical_header(value: str) -> str:
    key = re.sub(r"[^a-z0-9]", "", value.casefold())
    return _CANONICAL_FIELDS.get(key, value.strip())


def _blank(value: object) -> bool:
    return value is None or str(value).strip().casefold() in _MISSING_VALUES


def _number(value: object) -> float | None:
    if _blank(value):
        return None
    try:
        result = float(str(value).strip())
    except (TypeError, ValueError):
        return math.nan
    return result if math.isfinite(result) else math.nan


def _valid_event_date(value: str) -> bool:
    """Accept common ISO 8601 date, partial-date, datetime, and interval forms."""
    value = value.strip()
    if not value:
        return False
    if "/" in value:
        parts = value.split("/")
        if len(parts) != 2 or not all(parts):
            return False
        start, end = parts
        # Darwin Core permits compact day intervals such as 2007-11-13/15.
        if re.fullmatch(r"\d{1,2}", end) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", start):
            try:
                start_date = dt.date.fromisoformat(start)
                end_day = int(end)
                return start_date.day <= end_day <= 31
            except ValueError:
                return False
        return _valid_event_date(start) and _valid_event_date(end)
    if re.fullmatch(r"\d{4}", value):
        year = int(value)
        return 1 <= year <= 9999
    if re.fullmatch(r"\d{4}-\d{2}", value):
        try:
            dt.date.fromisoformat(value + "-01")
            return True
        except ValueError:
            return False
    try:
        dt.date.fromisoformat(value)
        return True
    except ValueError:
        pass
    try:
        dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _issue(
    report: ValidationReport,
    severity: Severity,
    code: str,
    message: str,
    suggestion: str,
    row: int | None = None,
    field: str | None = None,
) -> None:
    report.issues.append(Issue(severity, code, message, suggestion, row, field))


def _check_coordinates(
    row_data: Mapping[str, str], report: ValidationReport, row_number: int
) -> None:
    lat_raw = row_data.get("decimalLatitude", "")
    lon_raw = row_data.get("decimalLongitude", "")
    lat_blank, lon_blank = _blank(lat_raw), _blank(lon_raw)

    if lat_blank and lon_blank:
        _issue(
            report,
            "warning",
            "coordinates_missing",
            "No decimal latitude or longitude was supplied.",
            "Add decimalLatitude and decimalLongitude where sharing coordinates is safe and permitted.",
            row_number,
            "decimalLatitude/decimalLongitude",
        )
        return
    if lat_blank != lon_blank:
        _issue(
            report,
            "error",
            "coordinate_pair_incomplete",
            "Latitude and longitude must be supplied together.",
            "Provide both coordinate fields or leave both empty.",
            row_number,
            "decimalLatitude/decimalLongitude",
        )
        return

    lat, lon = _number(lat_raw), _number(lon_raw)
    if lat is None or lon is None or math.isnan(lat) or math.isnan(lon):
        _issue(
            report,
            "error",
            "coordinates_not_numeric",
            "Latitude and longitude must be finite numeric values.",
            "Use decimal degrees as numbers; do not include degree symbols or hemisphere letters.",
            row_number,
            "decimalLatitude/decimalLongitude",
        )
        return
    if not -90 <= lat <= 90:
        _issue(
            report,
            "error",
            "latitude_out_of_range",
            "Latitude is outside the valid range of -90 to 90 degrees.",
            "Check the latitude value and confirm the source coordinate reference system.",
            row_number,
            "decimalLatitude",
        )
    if not -180 <= lon <= 180:
        _issue(
            report,
            "error",
            "longitude_out_of_range",
            "Longitude is outside the valid range of -180 to 180 degrees.",
            "Check the longitude value and confirm the source coordinate reference system.",
            row_number,
            "decimalLongitude",
        )
    if not str(row_data.get("geodeticDatum", "")).strip():
        _issue(
            report,
            "warning",
            "geodetic_datum_missing",
            "Coordinates are present but geodeticDatum is empty.",
            "Record the datum used by the source survey (for example, WGS84) when known.",
            row_number,
            "geodeticDatum",
        )

    uncertainty_raw = row_data.get("coordinateUncertaintyInMeters", "")
    if not _blank(uncertainty_raw):
        uncertainty = _number(uncertainty_raw)
        if uncertainty is None or math.isnan(uncertainty) or uncertainty <= 0:
            _issue(
                report,
                "error",
                "coordinate_uncertainty_invalid",
                "coordinateUncertaintyInMeters must be a positive number when provided; zero is not valid.",
                "Enter a positive uncertainty in metres, or leave the field empty when unknown.",
                row_number,
                "coordinateUncertaintyInMeters",
            )


def _validate_occurrence(rows: list[dict[str, str]], report: ValidationReport) -> None:
    ids: dict[str, int] = {}
    for row_number, row in enumerate(rows, start=2):
        occurrence_id = row.get("occurrenceID", "").strip()
        scientific_name = row.get("scientificName", "").strip()
        basis = row.get("basisOfRecord", "").strip()
        event_date = row.get("eventDate", "").strip()

        if _blank(occurrence_id):
            _issue(report, "error", "occurrence_id_missing", "occurrenceID is missing.", "Assign a stable, dataset-unique identifier to each occurrence record.", row_number, "occurrenceID")
        elif occurrence_id in ids:
            _issue(report, "error", "occurrence_id_duplicate", f"occurrenceID duplicates the value first seen on row {ids[occurrence_id]}.", "Make occurrenceID unique while preserving the link to the original field record.", row_number, "occurrenceID")
        else:
            ids[occurrence_id] = row_number

        if _blank(scientific_name):
            _issue(report, "error", "scientific_name_missing", "scientificName is missing.", "Supply the best-supported scientific name, or use an explicit identification status in a separate field.", row_number, "scientificName")
        elif scientific_name.casefold() in {"unknown", "unidentified", "n/a", "na", "sp.", "species"}:
            _issue(report, "warning", "scientific_name_placeholder", "scientificName contains a generic placeholder.", "Use the lowest defensible taxonomic identification and record uncertainty separately.", row_number, "scientificName")

        if _blank(basis):
            _issue(report, "warning", "basis_of_record_missing", "basisOfRecord is empty.", "Choose the appropriate Darwin Core record type, such as HumanObservation or MachineObservation.", row_number, "basisOfRecord")
        elif basis not in _BASIS_OF_RECORD:
            _issue(report, "error", "basis_of_record_unknown", f"basisOfRecord '{basis}' is not in the recognized Darwin Core class vocabulary used by this validator.", "Check the current Darwin Core vocabulary and use the exact controlled term.", row_number, "basisOfRecord")

        if _blank(event_date):
            _issue(report, "warning", "event_date_missing", "eventDate is empty.", "Record the observation date or the best-supported date interval.", row_number, "eventDate")
        elif not _valid_event_date(event_date):
            _issue(report, "error", "event_date_invalid", f"eventDate '{event_date}' is not a supported ISO 8601 date or interval.", "Use an ISO 8601 date, partial date, datetime, or valid interval.", row_number, "eventDate")

        status = row.get("occurrenceStatus", "").strip()
        if status and status.casefold() not in {"present", "absent"}:
            _issue(report, "warning", "occurrence_status_unusual", "occurrenceStatus is not 'present' or 'absent'.", "Use the Darwin Core occurrenceStatus vocabulary where applicable.", row_number, "occurrenceStatus")

        count_raw = row.get("individualCount", "")
        if not _blank(count_raw):
            count = _number(count_raw)
            if count is None or math.isnan(count) or count < 0:
                _issue(report, "error", "individual_count_invalid", "individualCount must be a non-negative number when supplied.", "Enter a valid count; use an empty value when the count is unknown.", row_number, "individualCount")

        country_code = row.get("countryCode", "").strip()
        if country_code and not re.fullmatch(r"[A-Z]{2}", country_code):
            _issue(report, "warning", "country_code_format", "countryCode should use a two-letter uppercase country code.", "Use an ISO 3166-1 alpha-2 code such as PK; verify the country independently.", row_number, "countryCode")

        _check_coordinates(row, report, row_number)


def _validate_camera_trap(rows: list[dict[str, str]], report: ValidationReport) -> None:
    for row_number, row in enumerate(rows, start=2):
        if _blank(row.get("eventID", "")):
            _issue(report, "error", "event_id_missing", "eventID is missing for this camera-trap survey row.", "Assign a stable identifier to the deployment or sampling event.", row_number, "eventID")
        if _blank(row.get("eventDate", "")):
            _issue(report, "warning", "event_date_missing", "eventDate is empty.", "Record the deployment, sampling, or detection date as appropriate for this table.", row_number, "eventDate")
        elif not _valid_event_date(row["eventDate"].strip()):
            _issue(report, "error", "event_date_invalid", f"eventDate '{row['eventDate']}' is not a supported ISO 8601 date or interval.", "Use an ISO 8601 date, partial date, datetime, or valid interval.", row_number, "eventDate")
        if _blank(row.get("locationID", "")):
            _issue(report, "warning", "location_id_missing", "locationID is empty.", "Use a stable site or camera location identifier; avoid exposing sensitive site names publicly.", row_number, "locationID")
        if _blank(row.get("samplingProtocol", "")):
            _issue(report, "warning", "sampling_protocol_missing", "samplingProtocol is empty.", "Document the survey protocol, camera setup, or deployment method.", row_number, "samplingProtocol")

        value_raw = row.get("sampleSizeValue", "")
        unit_raw = row.get("sampleSizeUnit", "")
        if not _blank(value_raw):
            value = _number(value_raw)
            if value is None or math.isnan(value) or value <= 0:
                _issue(report, "error", "sample_size_invalid", "sampleSizeValue must be a positive number when supplied.", "Use a positive duration or effort quantity.", row_number, "sampleSizeValue")
            if _blank(unit_raw):
                _issue(report, "warning", "sample_size_unit_missing", "sampleSizeValue is supplied without sampleSizeUnit.", "Add the unit, such as camera-days or trap-nights.", row_number, "sampleSizeUnit")
        elif not _blank(unit_raw):
            _issue(report, "warning", "sample_size_value_missing", "sampleSizeUnit is supplied but sampleSizeValue is empty.", "Provide the corresponding effort value or clear the unused unit.", row_number, "sampleSizeValue")

        duration_raw = row.get("eventDurationValue", "")
        duration_unit = row.get("eventDurationUnit", "")
        if not _blank(duration_raw):
            duration = _number(duration_raw)
            if duration is None or math.isnan(duration) or duration <= 0:
                _issue(report, "error", "event_duration_invalid", "eventDurationValue must be a positive number when supplied.", "Use a positive duration and specify its unit.", row_number, "eventDurationValue")
            if _blank(duration_unit):
                _issue(report, "warning", "event_duration_unit_missing", "eventDurationValue is supplied without eventDurationUnit.", "Add a duration unit such as hours or days.", row_number, "eventDurationUnit")

        _check_coordinates(row, report, row_number)


def validate_rows(
    rows: Iterable[Mapping[str, object]],
    profile: str = "occurrence",
    source: str = "<memory>",
    columns: Iterable[str] | None = None,
    required_fields: Iterable[str] = (),
) -> ValidationReport:
    """Validate already-loaded records. Row numbers start at 2, like CSV files."""
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile '{profile}'. Choose one of: {', '.join(PROFILES)}")
    normalized_rows = [
        {_canonical_header(str(key)): "" if value is None else str(value).strip() for key, value in row.items()}
        for row in rows
    ]
    report = ValidationReport(source=source, profile=profile, rows_checked=len(normalized_rows))
    report.columns = list(columns or (normalized_rows[0].keys() if normalized_rows else []))

    for field_name in required_fields:
        canonical = _canonical_header(field_name)
        if canonical not in report.columns:
            _issue(report, "error", "required_column_missing", f"Required column '{canonical}' is missing.", f"Add a '{canonical}' column to the CSV header.", None, canonical)

    if profile == "occurrence":
        _validate_occurrence(normalized_rows, report)
    else:
        _validate_camera_trap(normalized_rows, report)
    return report


def validate_file(
    path: str | Path,
    profile: str = "occurrence",
    required_fields: Iterable[str] = (),
) -> ValidationReport:
    """Read a CSV file and return a report without modifying or uploading the source."""
    file_path = Path(path)
    report = ValidationReport(source=file_path.name, profile=profile)
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile '{profile}'. Choose one of: {', '.join(PROFILES)}")
    if not file_path.is_file():
        _issue(report, "error", "file_not_found", f"Input file '{file_path}' does not exist.", "Check the path and try again.")
        return report

    try:
        text = file_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        _issue(report, "error", "encoding_unsupported", "The file is not valid UTF-8 text.", "Export the CSV as UTF-8 or UTF-8 with BOM.")
        return report
    except OSError as exc:
        _issue(report, "error", "file_unreadable", f"Could not read the input file: {exc}", "Check file permissions and whether another process is locking the file.")
        return report

    if not text.strip():
        _issue(report, "error", "file_empty", "The input file is empty.", "Provide a CSV with a header row and at least one data row.")
        return report

    try:
        sample = text[:8192]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
            delimiter = dialect.delimiter
        except csv.Error:
            delimiter = ","
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        raw_headers = reader.fieldnames or []
        if not raw_headers:
            _issue(report, "error", "header_missing", "No CSV header row was found.", "Add a header row containing Darwin Core or camera-trap field names.")
            return report

        headers = [_canonical_header(header or "") for header in raw_headers]
        report.columns = headers
        if len(set(headers)) != len(headers):
            _issue(report, "error", "duplicate_columns", "Two or more CSV columns resolve to the same field name.", "Rename duplicate columns so every field has one unambiguous header.")
            return report

        rows: list[dict[str, str]] = []
        for row_number, raw_row in enumerate(reader, start=2):
            if None in raw_row:
                _issue(report, "error", "row_has_extra_values", "A row contains more values than the header has columns.", "Check commas, quotes, and line breaks in the source CSV.", row_number)
            row = {}
            for raw_key, value in raw_row.items():
                if raw_key is not None:
                    row[_canonical_header(raw_key)] = "" if value is None else value.strip()
            rows.append(row)
        validated = validate_rows(rows, profile=profile, source=file_path.name, columns=headers, required_fields=required_fields)
        validated.issues[:0] = report.issues
        return validated
    except csv.Error as exc:
        _issue(report, "error", "csv_parse_error", f"CSV parsing failed: {exc}", "Check the source file for broken quoting or malformed rows.")
        return report
