# Instructions for coding agents

- Preserve the local-first design: input data must not be uploaded, transmitted, or sent to telemetry services.
- Never include real wildlife observation records, precise sensitive coordinates, patrol details, credentials, or personal information in tests, docs, commits, or generated reports.
- Use synthetic fixtures and safe placeholder coordinates only.
- Keep the validator deterministic, dependency-light, and read-only with respect to source files.
- Do not silently repair data, infer a species identity, or make ecological conclusions.
- Every new rule must define its severity, message, remediation suggestion, and a regression test.
- Be conservative when interpreting standards. Document project-specific checks separately from normative requirements.
- Run `ruff check .` and `pytest` before proposing changes.
