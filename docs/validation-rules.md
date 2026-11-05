# Validation rule reference

This reference covers the rules in the v0.3.0 release and unreleased Phase 2 checks currently on `main`. A warning is an advisory completeness or consistency concern; an error means the supplied value violates a rule implemented by this tool. The severity is not a judgement about the ecological importance of the observation.

## Occurrence profile

| Rule | Severity | Meaning |
|---|---|---|
| `occurrence_id_missing` | Error | Every occurrence row needs a stable identifier. |
| `occurrence_id_duplicate` | Error | An `occurrenceID` is repeated within the input file. |
| `scientific_name_missing` | Error | `scientificName` is blank. |
| `scientific_name_placeholder` | Warning | The value is a generic placeholder such as `unknown` or `unidentified`. |
| `basis_of_record_missing` | Warning | `basisOfRecord` is blank. |
| `basis_of_record_unknown` | Error | The value is not one of the recognised Darwin Core class terms in this version. |
| `event_date_missing` | Warning | `eventDate` is blank. |
| `event_date_invalid` | Error | The value is not a supported ISO 8601 date, partial date, datetime, or interval. |
| `occurrence_status_unusual` | Warning | `occurrenceStatus` is not `present` or `absent`. |
| `individual_count_invalid` | Error | A supplied `individualCount` is negative, non-numeric, non-finite, or not a whole number. |
| `country_code_format` | Warning | A supplied `countryCode` is not two uppercase letters. This is a format check, not a country-code lookup. |

## Shared coordinate checks

| Rule | Severity | Meaning |
|---|---|---|
| `coordinates_missing` | Warning | Both decimal coordinate values are empty. |
| `coordinate_pair_incomplete` | Error | Only latitude or longitude is supplied. |
| `coordinates_not_numeric` | Error | Coordinates are not finite numeric values. |
| `latitude_out_of_range` | Error | Latitude is outside -90 to +90 degrees. |
| `longitude_out_of_range` | Error | Longitude is outside -180 to +180 degrees. |
| `geodetic_datum_missing` | Warning | Coordinates exist but `geodeticDatum` is empty. |
| `coordinate_uncertainty_invalid` | Error | Supplied uncertainty is non-numeric, non-finite, zero, or negative. |

## Optional project-specific spatial check

| Rule | Severity | Meaning |
|---|---|---|
| `spatial_outside_boundary` | Warning | A valid WGS84 point is not covered by the user-supplied GeoJSON Polygon or MultiPolygon. |
| `spatial_boundary_invalid` | Error | The supplied boundary is malformed, uses a legacy CRS member, is not a polygon, or is geometrically invalid. |
| `spatial_boundary_unreadable` | Error | The CLI could not read the selected boundary path. |
| `spatial_dependency_missing` | Error | The optional Shapely package is unavailable for the requested boundary check. |

This check is project-specific and is not a Darwin Core or GBIF conformance rule. Boundary GeoJSON must follow RFC 7946 WGS84 longitude/latitude coordinate order and omit a legacy `crs` member. The input may be a `Polygon`, `MultiPolygon`, `Feature`, or polygon-only `FeatureCollection`, up to 10 MB. Polygon holes are excluded; a point on an exterior or hole edge is treated as covered by the boundary. Records without a valid coordinate pair are skipped by this check and retain their existing coordinate findings. The result is only a comparison with the selected boundary; it cannot establish ecological validity or the correctness of that boundary.

## Camera-trap profile

| Rule | Severity | Meaning |
|---|---|---|
| `event_id_missing` | Error | The survey/deployment row has no `eventID`. |
| `event_date_missing` | Warning | `eventDate` is blank. |
| `event_date_invalid` | Error | `eventDate` is not in a supported format. |
| `location_id_missing` | Warning | No stable `locationID` is supplied. |
| `sampling_protocol_missing` | Warning | No sampling protocol is documented. |
| `sample_size_invalid` | Error | Supplied `sampleSizeValue` is non-numeric, non-finite, or not positive. |
| `sample_size_unit_missing` | Warning | An effort value is supplied without its unit. |
| `sample_size_value_missing` | Warning | A unit is supplied without a value. |
| `event_duration_invalid` | Error | Supplied event duration is non-numeric, non-finite, or not positive. |
| `event_duration_unit_missing` | Warning | An event duration is supplied without its unit. |

## Input formats and workbook handling

- A header-only input is an error (`no_data_rows`); at least one data record is required.
- CSV and TSV files are read as UTF-8 (with or without a byte-order mark).
- All inputs are limited to 100 MB, 100,000 data rows, and 250 columns. Files exceeding a limit are rejected rather than partially validated.
- Excel `.xlsx` support is optional and uses `openpyxl`; the default is the first worksheet. A worksheet can also be selected by exact name or zero-based index.
- Formula cells are read using cached values when available. A formula without a saved result may be treated as an empty cell.
- Excel workbook archive size and compression limits are applied as a defensive check before parsing. Legacy `.xls` and macro-enabled `.xlsm` files are not supported.
- Optional GeoJSON boundary checks require `python -m pip install "wildlife-observation-qc[gis]"`; the base install remains dependency-light.

## Interpretation notes

- Without a supplied boundary, the tool cannot compare coordinates with a reserve or survey polygon. With one, an outside warning only reports the geometric comparison and does not establish whether a species identification is taxonomically correct, whether an observation is biologically plausible, or whether the selected boundary is correct.
- The accepted `basisOfRecord` values are based on the Darwin Core term vocabulary. The vocabulary can evolve; review the current standard when upgrading the tool.
- `countryCode` validation checks shape only. It does not verify whether a code is officially assigned or matches the coordinates.
- ISO date support covers common full dates, partial year/month values, datetimes, and common intervals. It is not a complete ISO 8601 parser.
- Missing coordinates are warnings because some records intentionally have withheld or unavailable locations. Do not publish restricted locations to silence a warning.

