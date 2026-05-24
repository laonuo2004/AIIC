# AIIC Chat Studio Demo Script

Target length: under 3 minutes.

## Flow

1. Open http://115.190.120.206/.
2. Register a new test account or log in with a prepared demo account.
3. Show the Chat Studio layout: left app rail, conversation list, main chat surface, black/white theme, and purple accent.
4. Open the OpenRouter page, save a user API key, and point out that the UI only shows a key hint, not the plaintext key.
5. Sync models from OpenRouter, enable a small set of models, and select one model for chat.
6. Return to Chat, attach a small UTF-8 text file and an image, then send a prompt such as: `请结合附件内容，用三点总结这个输入适合如何改进产品演示。`
7. Point out that the assistant response streams through FastAPI and LiteLLM using the selected OpenRouter model.
8. Refresh the page and reopen the thread to show SQLite conversation persistence.
9. Open Settings and show safe runtime/deployment state: environment, database type, upload limits, proxy status, and default model.
10. Log out and confirm protected conversations/attachments are not visible without authentication.

## Talking Points

- AIIC Chat Studio is a lightweight AI product shell built from the original full-stack baseline.
- Backend: FastAPI, SQLite, HttpOnly session cookies, encrypted user OpenRouter keys, model sync, protected uploads, LiteLLM streaming, pytest.
- Frontend: Next.js, TypeScript, Chat/OpenRouter/Settings navigation, theme modes, Markdown rendering, attachments, and streaming response UI.
- Deployment: Docker Compose services behind Nginx on an Ubuntu cloud server.
- Model routing is user-configurable through OpenRouter and normalized through LiteLLM.
- Secrets stay in `.env` or encrypted database records and are never sent to frontend JavaScript as plaintext.
- Proxy setup, including `clash-for-linux`, is server operations work outside the application.

## Fallback Line

If the external model provider is slow during recording, show an existing persisted conversation and explain that automated tests mock provider calls while the public deployment can be smoke-tested with a real OpenRouter key before submission.
