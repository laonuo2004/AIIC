# AIIC Stack Test Demo Script

Target length: under 3 minutes.

## Flow

1. Open http://115.190.120.206/.
2. Register a new test account with a non-secret username and password.
3. Log in and confirm the chat interface loads with an empty or existing thread list.
4. Send a short message, for example: `用两句话说明这个原型验证了哪些技术栈。`
5. Point out that the assistant response streams through the FastAPI backend via LiteLLM and OpenRouter.
6. Refresh the page and reopen the thread to show SQLite conversation persistence.
7. Log out, then try to access a conversation path through the UI flow and confirm protected data is not visible without login.

## Talking Points

- The app is a reusable stack-test baseline, not the final topic-specific AIIC product.
- Backend: FastAPI, SQLite, HttpOnly session cookies, LiteLLM streaming, pytest.
- Frontend: Next.js, TypeScript, login/register, conversation sidebar, streaming response UI.
- Deployment: Docker Compose services behind Nginx on an Ubuntu cloud server.
- Model routing is configured by environment variables; the current deployed OpenRouter model is `openrouter/qwen/qwen3.6-flash`.
- Secrets stay in `.env` and are never sent to frontend JavaScript or committed to Git.

## Fallback Line

If the external model provider is slow during recording, show the existing persisted conversation and explain that backend tests mock provider calls while the public deployment has already passed a real OpenRouter smoke test.
