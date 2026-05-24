# AIIC Chat Studio

[![CI](https://github.com/laonuo2004/AIIC/actions/workflows/ci.yml/badge.svg?branch=dev)](https://github.com/laonuo2004/AIIC/actions/workflows/ci.yml)

AIIC Chat Studio is a lightweight AI web product for the AIIC Project Challenge. It evolves the original stack-test chat baseline into a small product studio: authenticated conversations, user-level OpenRouter configuration, model selection, text/image attachments, and a clean black/white interface with a purple accent.

Public demo: http://115.190.120.206/

Health check: http://115.190.120.206/health

## Features

- FastAPI backend with health, auth, conversation, provider, attachment, and streaming chat APIs.
- User registration/login with HttpOnly session cookies and hashed passwords.
- SQLite persistence for users, sessions, conversations, messages, provider credentials, model preferences, model cache, and attachments.
- User-level OpenRouter API key storage encrypted from `SECRET_KEY`; API responses only expose a key hint, never the plaintext key.
- OpenRouter model sync from `GET https://openrouter.ai/api/v1/models`, with enabled/selected model preferences per user.
- Streaming chat through LiteLLM, using OpenRouter model ids normalized to `openrouter/{model_id}` at call time.
- Text and image attachments added to LLM context: UTF-8 text files as context text and images as base64 data URL `image_url` content.
- Next.js + TypeScript frontend with Chat Studio layout, left app rail, collapsible conversations, OpenRouter configuration page, settings page, modern composer, Markdown rendering, attachments, and theme selection.
- Docker Compose services for backend and frontend behind an Nginx reverse proxy.

## Tech Stack

- Backend: Python 3.12, FastAPI, SQLAlchemy, SQLite, LiteLLM, cryptography, httpx with SOCKS support, pytest, uv.
- Frontend: TypeScript, Next.js, React, pnpm, standard CSS.
- Deployment: Docker Compose and Nginx reverse proxy on Ubuntu.
- LLM routing: LiteLLM with OpenRouter as the current user-configurable provider.

## Environment

Create `.env` from `.env.example` and replace placeholder secrets.

Required baseline values:

```env
APP_ENV=development
DATABASE_URL=sqlite:///./data/app.sqlite3
SECRET_KEY=replace_with_a_random_secret_key
LITELLM_MODEL=openrouter/qwen/qwen3.6-flash
LITELLM_FALLBACK_MODEL=openrouter/qwen/qwen3.6-flash
```

Chat Studio requires each logged-in user to save their own OpenRouter key in the app before chatting. Saved keys are encrypted using `SECRET_KEY`; changing `SECRET_KEY` in production means previously saved keys must be entered again.

Never commit `.env` or real API keys.

## Uploads

Attachment uploads are protected API resources, not public static files.

- Upload endpoint: `POST /api/attachments`
- Download/view endpoint: `GET /api/attachments/{id}`
- Storage directory: `UPLOAD_DIR`, default `./data/uploads`
- Single-file limit: `MAX_UPLOAD_BYTES`, default `5242880` bytes, 5MB
- Per-message limit: `MAX_ATTACHMENTS_PER_MESSAGE`, default `4`
- Text extensions: `.txt`, `.md`, `.json`, `.csv`, `.log`
- Image MIME types: `image/png`, `image/jpeg`, `image/webp`, `image/gif`

Text attachments must be UTF-8 encoded. Image attachments are passed to compatible models using OpenRouter/LiteLLM multimodal message content.

## Proxy Notes

The app does not install or manage Clash. If the server needs a proxy, install and operate `clash-for-linux` or another proxy tool as server operations outside this app.

The backend reads standard proxy environment variables used by HTTP clients:

```env
HTTP_PROXY=
HTTPS_PROXY=
NO_PROXY=127.0.0.1,localhost
```

For OpenRouter-specific traffic, set:

```env
OPENROUTER_HTTP_PROXY=
```

The backend includes `httpx[socks]`, so SOCKS proxy URLs such as `socks5://127.0.0.1:7890` can be used where supported by the client path.

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

## API Summary

- `GET /health`
- `GET /api/status`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `POST /api/chat/stream`
- `GET /api/conversations`
- `GET /api/conversations/{conversation_id}`
- `GET /api/providers/openrouter/config`
- `PUT /api/providers/openrouter/key`
- `DELETE /api/providers/openrouter/key`
- `GET /api/providers/openrouter/models?refresh=false`
- `PATCH /api/providers/openrouter/models`
- `POST /api/attachments`
- `GET /api/attachments/{id}`

`POST /api/chat/stream` accepts `message`, `conversation_id`, `model_id`, and `attachment_ids`. The SSE stream keeps the existing `meta`, `delta`, `error`, and `done` event pattern; `meta` may include the actual model used.

## Testing

Backend tests mock LLM/provider calls and must not call paid APIs.

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

The GitHub CI workflow runs backend and frontend checks on pushes and pull requests for `dev` and `main`. It also validates the Compose file with:

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

The backend stores SQLite data in the `backend_data` Docker volume. Uploaded files should stay outside Git tracking.

The Compose file binds backend and frontend ports to `127.0.0.1` so Nginx is the public entrypoint. For public deployment, set:

```env
APP_ENV=production
FRONTEND_ORIGIN=http://115.190.120.206
NEXT_PUBLIC_API_BASE_URL=
```

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

## CI, Releases, and Images

Daily development happens on `dev`. Before merging into `main`, open a pull request and wait for the `backend`, `frontend`, and `compose` CI jobs to pass.

GitHub Container Registry image publishing is configured for release tags, published GitHub Releases, and manual workflow runs:

- `ghcr.io/laonuo2004/aiic-backend`
- `ghcr.io/laonuo2004/aiic-frontend`

Published images receive the release tag, a short commit SHA tag, and `latest` for official releases. The current server deployment can continue using local `docker compose up -d --build`; GHCR images are provided as release artifacts and do not trigger automatic production deployment.

## Limitations

- The public deployment currently uses HTTP, not HTTPS.
- Auth is intentionally lightweight for the challenge scope.
- SQLite is chosen for demo reliability and simple deployment, not high-concurrency production traffic.
- Chat quality and multimodal support depend on the user's OpenRouter key, selected model, and provider availability.
- If a selected model does not support image input, the provider may reject image attachment requests.

## Future Work

- Adapt prompts and product flow to the official AIIC challenge topic when released.
- Add richer model capability filtering and clearer vision-model warnings.
- Expand browser smoke tests for theme, provider setup, attachment upload, and persistence.
- Add HTTPS/domain deployment before a final public submission if time permits.
