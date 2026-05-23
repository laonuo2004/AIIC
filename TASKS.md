# AIIC Stack Test Tasks

## Scope

This is a generic stack-test chat prototype created before the official AIIC topic is released. It validates the intended FastAPI, Next.js, SQLite, LiteLLM, Docker Compose, and Nginx workflow without locking the final challenge product into a topic-specific structure.

## MVP

- Basic username/password registration and login.
- HttpOnly cookie session authentication.
- SQLite-backed users, sessions, conversations, and messages.
- Authenticated streaming chat endpoint through LiteLLM.
- Next.js chat UI with conversation history and loading/error states.
- Docker Compose services for backend and frontend.
- Nginx config that routes `/api/*` and `/health` to backend and `/` to frontend.
- Pytest coverage for health, auth, mocked chat streaming, provider failure, and persistence.

## Risks

- Real chat requires a valid `OPENROUTER_API_KEY` or another LiteLLM-supported provider key in `.env`.
- The prototype is intentionally generic and should be adapted after the official topic is released.
- SQLite is sufficient for the challenge baseline but is not intended for high-concurrency production traffic.

## Verification Checklist

- `cd backend && uv run pytest`
- `cd backend && uv run ruff check .`
- `cd frontend && pnpm lint`
- `cd frontend && pnpm build`
- `docker compose config`
- `curl -f http://127.0.0.1/health` after services are running
