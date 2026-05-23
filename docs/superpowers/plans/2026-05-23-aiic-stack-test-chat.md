# AIIC Stack Test Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable full-stack ChatGPT-style baseline for stack and workflow testing before the official AIIC topic is released.

**Architecture:** FastAPI owns auth, SQLite persistence, and LiteLLM streaming. Next.js talks only to the backend with HttpOnly cookie sessions. Docker Compose runs backend and frontend, while Nginx routes `/api/*` and `/health` to the backend and `/` to the frontend.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, SQLite, LiteLLM, pytest, uv, TypeScript, Next.js, React, pnpm, Docker Compose, Nginx.

---

### Task 1: Backend Core

**Files:**
- Create `backend/pyproject.toml`, `backend/app/**`, `backend/tests/**`

- [x] Write failing pytest coverage for health, auth, conversations, and mocked streaming chat.
- [x] Implement configuration, database models, auth helpers, LiteLLM service wrapper, and API routes.
- [x] Verify with `cd backend && uv run pytest`.

### Task 2: Frontend App

**Files:**
- Create `frontend/package.json`, `frontend/app/**`, `frontend/components/**`, `frontend/lib/**`

- [x] Implement login/register screen, authenticated chat shell, conversation sidebar, and streaming SSE handling.
- [x] Verify with `cd frontend && pnpm lint` and `cd frontend && pnpm build`.

### Task 3: Deployment And Docs

**Files:**
- Create `.env.example`, `docker-compose.yml`, `infra/nginx/aiic-project.conf`
- Modify `README.md`, `.gitignore`
- Create `TASKS.md`

- [x] Document local setup, env vars, deployment shape, testing, limitations, and future work.
- [x] Verify with `docker compose config` and secret/tracking checks.
