# Wildlife Observation QC

[![CI](https://github.com/iSufyanAshraf/wildlife-observation-qc/actions/workflows/ci.yml/badge.svg)](https://github.com/iSufyanAshraf/wildlife-observation-qc/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**A small, local-first quality checker for wildlife occurrence records and camera-trap survey effort.**

Wildlife census and biodiversity datasets often combine field sheets, GPS exports, camera-trap logs, and species observations collected by multiple teams. Before those records are mapped, analysed, or shared, basic problems need to be caught: duplicate identifiers, missing event metadata, malformed dates, incomplete coordinate pairs, coordinates outside geographic ranges, and effort values without units.

`wildlife-qc` checks CSV/TSV files on your own computer, produces an actionable report, and never edits the source file or sends records to a server.

## What it checks

| Check | Occurrence profile | Camera-trap profile |
|---|:---:|:---:|
| Required/stable record identifiers | `occurrenceID` | `eventID` |
| Scientific name presence | ✓ | — |
| Recognized `basisOfRecord` terms | ✓ | — |
| ISO 8601-style event dates and intervals | ✓ | ✓ |
| Duplicate occurrence identifiers | ✓ | — |
| Latitude/longitude supplied together | ✓ | ✓ |
| Numeric coordinate values and geographic ranges | ✓ | ✓ |
| Geodetic datum and coordinate uncertainty | ✓ | ✓ |
| Individual count sanity check | ✓ | — |
| Sampling protocol and location metadata | — | ✓ |
| Sampling effort and duration units | — | ✓ |
| Additional project-specific required columns | ✓ | ✓ |

The validator intentionally reports issues rather than attempting automatic repairs. It is a practical pre-flight check, not a complete Darwin Core or GBIF conformance validator, a taxonomic authority, or a substitute for expert review.

## Install

Python 3.10 or newer is required.

```bash
python -m pip install .
```

For development:

```bash
python -m pip install -e ".[dev]"
```

## Quick start

Validate Darwin Core-style occurrence data:

```bash
wildlife-qc validate samples/occurrences.csv --profile occurrence
```

Validate camera-trap event and effort data:

```bash
wildlife-qc validate samples/camera_trap_events.csv --profile camera-trap
```

Require project-specific fields and generate a report:

```bash
wildlife-qc validate observations.csv \
  --profile occurrence \
  --required-field taxonRank \
  --required-field recordedBy \
  --format json \
  --output reports/occurrence-qc.json
```

Create a shareable HTML report (the included edge-case file demonstrates the kinds of findings the tool can flag):

```bash
wildlife-qc validate samples/edge_cases.csv --profile occurrence \
  --format html --output reports/demo-report.html --fail-on never
```

Use it as a CI gate. This command exits with code `1` if it finds an error or warning:

```bash
wildlife-qc validate observations.csv --profile occurrence --fail-on warning
```

## Validation profiles

### `occurrence`

For species-observation records using common Darwin Core fields, including `occurrenceID`, `scientificName`, `basisOfRecord`, `eventDate`, `decimalLatitude`, `decimalLongitude`, `geodeticDatum`, and `coordinateUncertaintyInMeters`.

The validator recognises common Darwin Core `basisOfRecord` class values. It does not attempt taxonomic name matching or infer species identity from common names.

### `camera-trap`

For event/deployment tables using `eventID`, `eventDate`, `locationID`, `samplingProtocol`, `sampleSizeValue`, `sampleSizeUnit`, `eventDurationValue`, and related location fields. A project may use a separate occurrence file linked to these events by `eventID`.

## Reports and privacy

Reports include the source filename, validation profile, row numbers, field names, rule identifiers, severity, and suggested actions. They do **not** copy field values or coordinate values into the report. Input files are read locally, never modified, and never uploaded. There is no telemetry or network code in the package.

Wildlife locations can be sensitive, especially for threatened species, breeding sites, and anti-poaching operations. Keep source datasets and generated reports in access-controlled storage. Review location-disclosure rules before publishing any records or attaching examples to public issues. Use synthetic examples when asking for help.

## Standards and design references

The field names and general recommendations are informed by the [Darwin Core terms](https://dwc.tdwg.org/terms/), the [GBIF data quality recommendations](https://techdocs.gbif.org/en/data-publishing/data-quality-recommendations), and the [Darwin Core term list](https://dwc.tdwg.org/list/). The checks are intentionally narrower than those standards and are described in the test suite.

## Development

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest
```

Contributions should include a synthetic fixture or unit test for each new rule. See [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md), [validation rule reference](docs/validation-rules.md), [AGENTS.md](AGENTS.md), and [PUBLISHING.md](PUBLISHING.md).

## Roadmap

- [x] CSV/TSV validation for occurrence and camera-trap event profiles
- [x] Text, JSON, and HTML reports
- [x] CI tests across supported Python versions
- [ ] Darwin Core Archive (`meta.xml` + core/extension CSV) support
- [ ] Optional taxonomy cross-checking against a user-selected authority
- [ ] Optional spatial checks against user-supplied, locally stored survey boundaries
- [ ] Configurable rule packs for national wildlife census workflows

Roadmap items are proposals, not current capabilities.

## License

MIT. See [LICENSE](LICENSE).
