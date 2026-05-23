# AIIC Stack Test Chat

Reusable full-stack baseline for the AIIC Project Challenge. This prototype is a generic ChatGPT-style app for validating the stack before the official topic is released.

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
LITELLM_MODEL=openrouter/openai/gpt-4o-mini
SECRET_KEY=replace_with_a_random_secret_key
```

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

## Docker Compose

```bash
cp .env.example .env
docker compose config
docker compose up -d --build
curl -f http://127.0.0.1:8000/health
```

The backend stores SQLite data in the `backend_data` Docker volume.

## Nginx

Use `infra/nginx/aiic-project.conf` as the server config. It routes:

- `/` to `http://127.0.0.1:3000`
- `/api/*` to `http://127.0.0.1:8000/api/*`
- `/health` to `http://127.0.0.1:8000/health`

After installing or changing the site:

```bash
sudo nginx -t
sudo systemctl reload nginx
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

## Future Work

- Adapt the product flow to the official challenge topic.
- Add topic-specific prompts and evaluation tests.
- Add a short demo script and final deployment notes.
