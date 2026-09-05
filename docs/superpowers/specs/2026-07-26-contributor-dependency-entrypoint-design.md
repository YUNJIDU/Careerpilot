# Contributor Dependency Entrypoint Design

> 历史记录（2026-09-05 统一标记）：正文保留当时的设计、任务和验收假设，不是当前执行指令。冲突内容已由[当前规则](../../../plan/CURRENT-POLICY.md)替代；按总体规划与新验收核对差距，不重做已完成阶段。

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
