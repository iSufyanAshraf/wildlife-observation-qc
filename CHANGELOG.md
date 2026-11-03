# Changelog

## Unreleased — Phase 1 hardening

- Reject header-only datasets instead of reporting a pass with zero records.
- Enforce a 100 MB input limit, 100,000 data-row limit, and 250-column limit.
- Require whole-number `individualCount` values and validate calendar-aware compact date intervals.
- Restore same-origin checks for browser uploads while allowing non-browser local clients that omit `Origin` unless marked cross-site.
- Add regression tests for empty inputs, malformed intervals, fractional counts, resource limits, and cross-origin upload attempts.


## 0.2.0 — 2026-11-02

- Added optional Excel `.xlsx` validation with worksheet selection.
- Added a local browser dashboard with in-memory uploads and JSON report export.
- Added upload limits, loopback-only binding, local-origin checks, and archive safeguards.
- Kept CSV/TSV validation and the command-line interface backward compatible.

## 0.2.0 — 2026-11-02

- Added optional Excel `.xlsx` validation with worksheet selection.
- Added a local browser dashboard with in-memory uploads and JSON report export.
- Added size limits, loopback-only binding, and security headers for the dashboard.
- Kept CSV/TSV validation and the command-line interface backward compatible.

## 0.1.0 — 2026-11-02

- Initial release of local CSV/TSV checks for wildlife occurrence records.
- Added camera-trap event and effort profile.
- Added text, JSON, and self-contained HTML reporting.
- Added synthetic sample datasets, tests, GitHub Actions CI, and maintainer guidance.
