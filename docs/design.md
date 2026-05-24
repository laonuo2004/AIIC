# AIIC Chat Studio Design Notes

## Product Interpretation

AIIC Chat Studio is a compact AI web product that demonstrates the expected challenge engineering loop: authenticated users, provider configuration, model routing, persistence, attachments, streaming responses, deployment, and tests. It intentionally stays smaller than a production assistant platform so the demo remains reliable under the challenge time budget.

## Target Users

The primary user is a reviewer or developer evaluating whether the project can support a real AI product workflow. The app should make the important engineering choices visible without exposing secrets or debug noise.

## Product Flow

1. A user registers or logs in.
2. The user configures their OpenRouter API key.
3. The app verifies the key by syncing models from OpenRouter.
4. The user enables available models and selects one for chat.
5. The user chats with optional text/image attachments.
6. The backend streams the answer and persists the conversation.
7. The user can return later, reopen the thread, and continue.

## Interface Direction

The UI should feel like a focused studio rather than a generic demo:

- Black/white/gray base palette with a fixed purple accent.
- Left app rail for Chat, OpenRouter, and Settings.
- Collapsible conversation sidebar.
- Main chat surface with Markdown-rendered messages.
- Composer with attachment controls, empty disabled state, and `Ctrl+Enter` send.
- Theme modes: `system`, `light`, and `dark`, saved in `localStorage`.

## Backend Design

FastAPI remains the boundary for all product operations. The browser never calls OpenRouter or other LLM providers directly.

Core backend responsibilities:

- Auth and session management.
- SQLite persistence.
- OpenRouter key encryption and model sync.
- User model preferences.
- Attachment upload/download with ownership checks.
- Chat request validation and streaming.
- LiteLLM provider routing.

OpenRouter model ids returned by the model API are stored as provider ids such as `qwen/...`; LiteLLM calls normalize them to `openrouter/{id}`.

## Secret Handling

OpenRouter keys saved by users are encrypted using key material derived from `SECRET_KEY`. API responses only expose `configured` and a short `key_hint`. Real `.env` files and API keys must never be committed.

If `SECRET_KEY` changes in production, saved provider keys should be considered unrecoverable and users must re-enter them.

## Attachments

Attachments are stored under `UPLOAD_DIR`, defaulting to `./data/uploads`, and are served only through authenticated API endpoints.

Text attachments use UTF-8 content and are injected as context. Image attachments are converted to base64 data URLs and sent as `image_url` content for models that support multimodal input.

Limits:

- 5MB per file.
- 4 attachments per message.
- Text: `.txt`, `.md`, `.json`, `.csv`, `.log`.
- Images: PNG, JPEG, WebP, GIF.

## Proxy And Deployment

The app reads standard proxy variables (`HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`) plus optional `OPENROUTER_HTTP_PROXY`. It does not install or operate Clash. If the deployment server needs `clash-for-linux`, that belongs in server operations documentation and should remain outside the application code.

The public deployment remains:

- App: http://115.190.120.206/
- Health: http://115.190.120.206/health
- Nginx `/` to frontend.
- Nginx `/api/` and `/health` to backend.

## Tradeoffs

- SQLite is sufficient for a small challenge deployment and keeps operations simple.
- User-level OpenRouter configuration avoids committing or exposing shared provider keys.
- LiteLLM keeps the app provider-agnostic enough for later OpenAI/Gemini expansion.
- Attachments are intentionally limited to text and common image formats to preserve demo reliability.
- HTTPS, OAuth, billing, team accounts, and large-file processing are out of scope for the first Chat Studio version.
