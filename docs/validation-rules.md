# Validation rule reference

This reference describes the rules shipped in version 0.2.0. A warning is an advisory completeness or consistency concern; an error means the supplied value violates a rule implemented by this tool. The severity is not a judgement about the ecological importance of the observation.

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
| `individual_count_invalid` | Error | A supplied `individualCount` is negative or non-numeric. |
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

- CSV and TSV files are read as UTF-8 (with or without a byte-order mark).
- Excel `.xlsx` support is optional and uses `openpyxl`; the default is the first worksheet. A worksheet can also be selected by exact name or zero-based index.
- Formula cells are read using cached values when available. A formula without a saved result may be treated as an empty cell.
- Excel workbook archive size and compression limits are applied as a defensive check before parsing. Legacy `.xls` and macro-enabled `.xlsm` files are not supported.

## Interpretation notes

- The tool validates the input rows in isolation. It cannot establish whether a species identification is taxonomically correct, whether an observation is biologically plausible, or whether a coordinate falls inside the correct reserve or survey polygon.
- The accepted `basisOfRecord` values are based on the Darwin Core term vocabulary. The vocabulary can evolve; review the current standard when upgrading the tool.
- `countryCode` validation checks shape only. It does not verify whether a code is officially assigned or matches the coordinates.
- ISO date support covers common full dates, partial year/month values, datetimes, and common intervals. It is not a complete ISO 8601 parser.
- Missing coordinates are warnings because some records intentionally have withheld or unavailable locations. Do not publish restricted locations to silence a warning.
