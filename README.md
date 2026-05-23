# AIIC Stack Test Chat

[![CI](https://github.com/laonuo2004/AIIC/actions/workflows/ci.yml/badge.svg?branch=dev)](https://github.com/laonuo2004/AIIC/actions/workflows/ci.yml)

Reusable full-stack baseline for the AIIC Project Challenge. This prototype is a generic ChatGPT-style app for validating the stack before the official topic is released.

Public demo: http://115.190.120.206/

## Features

- FastAPI backend with `GET /health`, auth APIs, conversation APIs, and streaming chat.
- LiteLLM SDK integration configured for OpenRouter-style models by environment variable.
- SQLite persistence for users, sessions, conversations, and messages.
- HttpOnly cookie session auth with hashed passwords.
- Next.js + TypeScript frontend with login/register, conversation sidebar, streaming assistant output, and error states.
- Docker Compose services for backend and frontend.
- Nginx route template for public deployment.

## Tech Stack

- Backend: Python 3.12, FastAPI, SQLAlchemy, SQLite, LiteLLM, pytest, uv.
- Frontend: TypeScript, Next.js, React, pnpm, standard CSS.
- Deployment: Docker Compose and Nginx reverse proxy.

## Environment

Create `.env` from `.env.example` and replace placeholder secrets.

Required for real model calls:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
LITELLM_MODEL=openrouter/qwen/qwen3.6-flash
LITELLM_FALLBACK_MODEL=openrouter/qwen/qwen3.6-flash
SECRET_KEY=replace_with_a_random_secret_key
```

The current deployed smoke test uses `openrouter/qwen/qwen3.6-flash`. OpenRouter model names must include the LiteLLM provider prefix. The earlier `openrouter/openai/gpt-4o-mini` route returned a region-related 403 from this server, so it is not the default.

Never commit `.env`.

## Local Development

Backend:

```bash
cd backend
uv sync --dev
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
pnpm install
pnpm dev
```

For local cross-origin frontend calls, set:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
FRONTEND_ORIGIN=http://localhost:3000
```

## Testing

Backend tests mock the LLM stream and do not call paid APIs.

```bash
cd backend
uv run pytest
uv run ruff check .
```

Frontend checks:

```bash
cd frontend
pnpm lint
pnpm build
```

The GitHub CI workflow runs the same backend and frontend checks on pushes and pull requests for `dev` and `main`. It also validates the Compose file with:

```bash
docker compose config --quiet --no-env-resolution
```

The `--no-env-resolution` flag keeps CI focused on Compose syntax and service wiring without reading or printing local `.env` values.

## Docker Compose

```bash
cp .env.example .env
docker compose config
docker compose up -d --build
curl -f http://127.0.0.1:8000/health
```

The backend stores SQLite data in the `backend_data` Docker volume.

The Compose file binds backend and frontend ports to `127.0.0.1` so Nginx is the public entrypoint. For public deployment, set:

```env
APP_ENV=production
FRONTEND_ORIGIN=http://115.190.120.206
NEXT_PUBLIC_API_BASE_URL=
```

## CI, Releases, and Images

Daily development happens on `dev`. Before merging into `main`, open a pull request and wait for the `backend`, `frontend`, and `compose` CI jobs to pass.

GitHub Container Registry image publishing is configured for release tags, published GitHub Releases, and manual workflow runs:

- `ghcr.io/laonuo2004/aiic-backend`
- `ghcr.io/laonuo2004/aiic-frontend`

Published images receive the release tag, a short commit SHA tag, and `latest` for official releases. The current server deployment can continue using local `docker compose up -d --build`; GHCR images are provided as release artifacts and do not trigger automatic production deployment.

Release flow:

```bash
git checkout dev
git pull
# update docs or version notes as needed
git tag -a v0.2 -m "v0.2"
git push origin v0.2
```

Then create a GitHub Release from the tag. The repository includes `.github/release.yml` so GitHub auto-generated release notes are grouped into Features, Fixes, Docs, Tests, Chores, Deployment, and Breaking Changes.

## Nginx

Use `infra/nginx/aiic-project.conf` as the server config. It routes:

- `/` to `http://127.0.0.1:3000`
- `/api/*` to `http://127.0.0.1:8000/api/*`
- `/health` to `http://127.0.0.1:8000/health`

After installing or changing the site:

```bash
sudo nginx -t
sudo systemctl reload nginx
curl -f http://115.190.120.206/health
```

## API Summary

- `GET /health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `POST /api/chat/stream`
- `GET /api/conversations`
- `GET /api/conversations/{conversation_id}`

## Limitations

- This is a stack-test prototype, not the final topic-specific product.
- Auth is intentionally lightweight.
- SQLite is chosen for deadline safety and demo simplicity.
- Chat depends on external provider availability and valid environment keys.
- The public deployment currently uses HTTP, not HTTPS.

## Future Work

- Adapt the product flow to the official challenge topic.
- Add topic-specific prompts and evaluation tests.
- Extend docs and demo material after the official topic is released.
