# Contributor Dependency Entrypoint Design

Date: 2026-07-26

Status: Approved approach, pending written-spec review

## Goal

Give new contributors a familiar root-level Python installation command without
creating a second dependency version list.

## Design

- Keep `backend/pyproject.toml` as the single source of truth for runtime and
  development Python dependencies.
- Add a root `requirements.txt` containing only `-e ./backend[dev]`.
- Update the README Windows setup command to use
  `python -m pip install -r requirements.txt`.
- Keep frontend dependencies in `frontend/package.json` and its lock file.
- Do not add dependency managers, workspace tooling, or speculative module
  abstractions.

## Validation

- Install resolution must accept the root requirements file.
- Existing backend tests and lint must pass.
- Frontend type checking and build must pass.
