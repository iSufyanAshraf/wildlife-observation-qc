# Contributing

Thanks for helping improve Wildlife Observation QC.

## Before opening an issue

- Search existing issues to avoid duplicates.
- Use synthetic examples only. Do not post endangered-species coordinates, confidential survey locations, personal information, or unpublished field records.
- State the tool version, Python version, profile, and command used.

## Development setup

```bash
python -m venv .venv
# Activate the environment, then:
python -m pip install -e ".[dev]"
ruff check .
pytest
```

## Pull requests

1. Keep validation deterministic and local-first.
2. Do not add automatic data edits unless a separate, explicit opt-in workflow is designed and reviewed.
3. Add a unit test for every new rule and a synthetic CSV fixture when useful.
4. Document the severity, limitation, and suggested action for each new finding.
5. Do not add network calls, telemetry, or external services to the validation path.
6. Run `ruff check .` and `pytest` before submitting.

## Scope

The project focuses on pre-flight quality checks for wildlife observations and camera-trap effort metadata. It is not a taxonomy resolver, legal compliance engine, wildlife intelligence system, or replacement for a GIS platform.
