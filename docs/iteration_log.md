# Iteration Log

Use this file to record decisions, scope cuts, user findings, and implementation changes.

## 2026-05-24: Product Direction Update

Official product direction:

- Build an AI mock interviewer.
- Focus on a narrow and deep product rather than a broad platform.
- Required deliverables include public URL, public repository, demo video, product memo, and stable deployment.

Chosen product:

- ResearchMocker, a mock interviewer for CS/AI research-oriented interviews.
- Primary scenario: project/research experience deep dive for graduate recommendation, research internship, or lab admission interviews.

Why this scope:

- Students often know their project but explain it vaguely.
- Interview value comes from follow-up pressure and concrete feedback.
- A focused text interview loop is more reliable than a broad feature set under time pressure.

## Baseline Before Direction Change

Available engineering foundation:

- FastAPI backend.
- Next.js frontend.
- SQLite persistence.
- HttpOnly cookie auth.
- Streaming LLM calls through LiteLLM/OpenRouter.
- Attachments.
- Docker Compose and Nginx deployment.
- Backend tests and frontend checks.

Problem with baseline:

- It looked like a generic chat workspace.
- It exposed provider/model configuration that normal users should not need.
- It did not enforce an interview workflow.

## Decisions

### Hide Provider Complexity

Decision:

- Use a project-level OpenRouter key in backend configuration.
- Do not ask normal users to enter API keys.
- Do not expose raw provider/model IDs in the main product flow.

Reason:

- This is a product for interview practice, not a developer console.
- Provider setup distracts from the core user value.

### Backend Model Routing

Decision:

- Use `openrouter/qwen/qwen3.6-plus` for deep analysis and final reports.
- Use `openrouter/qwen/qwen3.6-flash` for fast interview turns and per-answer feedback.

Reason:

- Deep analysis benefits from stronger reasoning.
- Multi-turn practice needs speed and responsiveness.

### Face-to-Face Interview As Optional Differentiator

Decision:

- Reserve a page for real-time face-to-face interview simulation.
- Use Volcengine real-time speech and OmniHuman only after text MVP is stable.

Reason:

- This could be the demo highlight.
- It also carries API, latency, quota, and integration risk.
- Text interview must remain the reliable fallback.

## Reference Project Review

Reference:

- `AI-Interviewer`

Useful ideas:

- Candidate material can drive personalized questions.
- Structured outputs help render predictable UI.
- A mock interview product needs a clear preparation/start/interview flow.

Not adopted directly:

- Vite frontend stack.
- Direct OpenAI SDK calls scattered in the app.
- Webcam/technical interview features that are not core to ResearchMocker.
- Resume PDF parsing as a required MVP path.

## Scope Cuts

Cut from MVP:

- Full voice/video interview as required path.
- Broad job interview categories.
- Complex algorithm practice.
- Large question bank.
- User-configured API keys.
- OAuth/email verification.
- Mandatory PDF parsing.

Reason:

- The product must be reliable and demoable under a tight deadline.

## Implementation Log

Add entries below as changes are made.

### 2026-05-24: Text Interview MVP Implemented

Change:

- Added persisted interview sessions and turns.
- Added `/api/interviews` create/list/detail/answer/finish endpoints.
- Added prompt-backed LiteLLM routing with deep and fast interview model settings.
- Replaced the generic chat-first UI with Text Interview, Face-to-Face Interview, and Settings.
- Added backend pytest coverage for interview auth, persistence, feedback/follow-up, final report, and ownership.

Reason:

- Make the product demonstrate a structured mock interview workflow rather than a generic chatbot.

Verification:

- `cd backend && uv run pytest tests/test_interviews.py`

Known risk:

- Public deployment still needs a real OpenRouter smoke test with server-side credentials.

### Entry Template

```text
Date/time:
Change:
Reason:
Files:
Verification:
Known risk:
```
