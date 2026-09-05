# Development Ports Design

> 历史记录（2026-09-05 统一标记）：正文保留当时的设计、任务和验收假设，不是当前执行指令。冲突内容已由[当前规则](../../../plan/CURRENT-POLICY.md)替代；按总体规划与新验收核对差距，不重做已完成阶段。

Date: 2026-07-26

Status: Approved approach, pending written-spec review

## Goal

Avoid common local development port collisions while keeping frontend and
backend services independently runnable on loopback only.

## Design

- React/Vite development server listens on `127.0.0.1:9999`.
- FastAPI/Uvicorn listens on `127.0.0.1:9998`.
- The frontend health client calls `http://127.0.0.1:9998/api/v1/health`.
- Backend CORS allows only `http://127.0.0.1:9999`.
- `.env.example`, tests, package scripts, and README use the same ports.
- No proxy or additional port configuration layer is added.

## Validation

- Backend tests and lint pass.
- Frontend type checking and production build pass.
- A live request to port `9998` returns the health response.
- Vite starts on port `9999` with strict port selection.
