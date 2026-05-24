# AIIC Chat Studio Tasks

## Scope

Convert the generic stack-test chat baseline into a lightweight AIIC Chat Studio product while preserving the deployable FastAPI, Next.js, SQLite, LiteLLM, Docker Compose, and Nginx architecture.

The official challenge topic has not been released yet, so Chat Studio should remain a reusable product shell: strong enough to demo full-stack AI engineering, but still easy to adapt once topic-specific requirements arrive.

## Product Direction

- Black/white Chat Studio interface with a fixed purple accent.
- Left app rail for Chat, OpenRouter, and Settings.
- Collapsible conversation sidebar; mobile should default to a compact layout.
- Authenticated chat with SQLite-backed conversation persistence.
- User-level OpenRouter API key configuration encrypted from `SECRET_KEY`.
- OpenRouter model sync from `GET https://openrouter.ai/api/v1/models`.
- Enabled model list and selected model preference per user.
- Streaming chat through LiteLLM.
- Text/image attachment upload and protected retrieval.
- Settings page with safe runtime/deployment state only.

## MVP

- Username/password registration and login.
- HttpOnly cookie session authentication.
- SQLite-backed users, sessions, conversations, messages, provider credentials, model preferences, cached models, and attachments.
- Authenticated provider endpoints:
  - `GET /api/providers/openrouter/config`
  - `PUT /api/providers/openrouter/key`
  - `DELETE /api/providers/openrouter/key`
  - `GET /api/providers/openrouter/models?refresh=false`
  - `PATCH /api/providers/openrouter/models`
- Authenticated attachment endpoints:
  - `POST /api/attachments`
  - `GET /api/attachments/{id}`
- Chat endpoint accepting `message`, `conversation_id`, `model_id`, and `attachment_ids`.
- Next.js Chat Studio UI for chat, OpenRouter setup, model preferences, settings, theme selection, Markdown rendering, and composer interactions.
- Docker Compose services for backend and frontend.
- Nginx config that routes `/api/*` and `/health` to backend and `/` to frontend.
- Pytest coverage for health, auth, provider config/models, attachments, mocked chat streaming, provider failure, and persistence.

## Backend Milestones

- Keep FastAPI API structure deployable.
- Encrypt saved OpenRouter API keys and return only key hints.
- Cache synced OpenRouter models with useful display metadata.
- Validate chat preconditions: user key configured, selected model enabled, attachments owned by current user.
- Inject UTF-8 text attachments into LLM context.
- Inject image attachments as data URL `image_url` message content.
- Keep SSE events compatible with the existing `meta`, `delta`, `error`, and `done` flow.
- Read `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`, and optional `OPENROUTER_HTTP_PROXY` from the environment.

## Frontend Milestones

- Rename narrative to AIIC Chat Studio.
- Implement three-zone information architecture: app rail, optional conversation sidebar, main page surface.
- Add OpenRouter settings page for key save/delete, sync, enabled models, and selected model.
- Add Settings page for safe state such as app env, database type, upload limits, proxy enabled status, and default model.
- Add `system`, `light`, and `dark` theme modes saved in `localStorage`.
- Add modern composer with bottom-right send button, disabled empty state, and `Ctrl+Enter` send behavior.
- Render assistant/user messages with Markdown and GFM support.
- Show attachment chips/previews in composer and conversation history.
- Preserve readable loading and error states.

## Upload Rules

- Single file limit: 5MB.
- Per-message attachment limit: 4.
- Accepted text extensions: `.txt`, `.md`, `.json`, `.csv`, `.log`.
- Accepted image MIME types: `image/png`, `image/jpeg`, `image/webp`, `image/gif`.
- Uploaded files are protected by ownership checks and are not served from a public static directory.

## Deployment Notes

- Public URL: http://115.190.120.206/
- Health URL: http://115.190.120.206/health
- The app does not install or manage Clash. If a proxy is needed, `clash-for-linux` is a server operations concern outside the app.
- `httpx[socks]` is available for SOCKS proxy URLs where supported.
- Keep `.env` untracked and never expose API keys to frontend JavaScript.

## Risks

- Real chat requires a valid user OpenRouter API key and an enabled model.
- OpenRouter model availability may vary by account, region, or provider policy.
- Image input only works on models that support vision/multimodal input.
- Changing `SECRET_KEY` invalidates the ability to decrypt previously saved provider keys.
- SQLite is sufficient for the challenge demo but not intended for high-concurrency production traffic.
- The public deployment currently uses HTTP, not HTTPS.

## Verification Checklist

- `cd backend && uv run pytest`
- `cd backend && uv run ruff check .`
- `cd frontend && pnpm lint`
- `cd frontend && pnpm build`
- `docker compose config --quiet --no-env-resolution`
- `docker compose up -d --build`
- `curl -f http://127.0.0.1/health`
- `curl -f http://115.190.120.206/health`

## Demo Checklist

- Register or log in.
- Switch theme and show Chat Studio layout.
- Save OpenRouter key and confirm only the key hint is shown.
- Sync models and select an enabled model.
- Upload one text attachment and one image attachment.
- Send a streamed chat message.
- Refresh and reopen the conversation to show persistence.
- Log out and confirm protected data is unavailable without authentication.
