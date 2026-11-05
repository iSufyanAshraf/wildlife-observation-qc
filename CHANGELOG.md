# Changelog

## Unreleased — Phase 2 GIS validation

- Add optional local GeoJSON Polygon/MultiPolygon boundary checks with WGS84 longitude/latitude semantics.
- Add CLI and dashboard boundary selection, size limits, clear validation errors, and outside-boundary warnings.
- Keep GIS processing local and in memory; Shapely remains an optional dependency.

## 0.3.0 — 2026-11-04

- Reject header-only datasets instead of reporting a pass with zero records.
- Enforce a 100 MB input limit, 100,000 data-row limit, and 250-column limit.
- Require whole-number `individualCount` values and validate calendar-aware compact date intervals.
- Protect dashboard uploads with a per-server CSRF token while retaining loopback peer and local `Host` checks; this supports browsers that rewrite `Origin` metadata.
- Add regression tests for browser-style upload headers, missing or malformed CSRF tokens, empty inputs, malformed intervals, fractional counts, and resource limits.


## 0.2.0 — 2026-11-02

- Added optional Excel `.xlsx` validation with worksheet selection.
- Added a local browser dashboard with in-memory uploads and JSON report export.
- Added upload limits, loopback-only binding, local-origin checks, and archive safeguards.
- Kept CSV/TSV validation and the command-line interface backward compatible.


## 0.1.0 — 2026-11-02

- Initial release of local CSV/TSV checks for wildlife occurrence records.
- Added camera-trap event and effort profile.
- Added text, JSON, and self-contained HTML reporting.
- Added synthetic sample datasets, tests, GitHub Actions CI, and maintainer guidance.

