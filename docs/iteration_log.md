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

### Narrow To Project-Deep-Dive Pressure Test

Decision:

- Narrow the product from a generic AI mock interviewer to a project-deep-dive interviewer for CS/AI research interviews.
- Previous positioning at this stage: "面向 CS/AI 本科生保研科研面试的项目深挖型 AI 面试官。"

Reason:

- Lightweight questionnaire feedback showed students are most worried about teachers continuously digging into project details.
- The highest-value pain is not simply "I do not know the answer"; it is "my answer sounds smooth but has no evidence, ownership, or technical depth under follow-up."
- Direct ChatGPT practice is often too friendly, too generic, and too dependent on the student's prompting ability.

Product consequences:

- Add project card input as the main entry point.
- Prioritize adaptive project follow-up questions.
- Add teacher-perspective explanation to feedback.
- Add answer rhythm/length feedback for concise 1-2 minute responses.
- Treat standard/sharp interview style as a high-value, low-cost feature.
- Keep face-to-face mode optional until the text MVP is reliable.

### Add Reviewer-Style Pressure And Objective Pass-Risk

Decision:

- Refine positioning to: "面向 CS/AI 本科生保研科研面试的项目深挖与审稿人式追问 AI 面试官。"
- Add reviewer-style/rebuttal-style questioning as a high-value mode, without broadening beyond project deep dives.
- Add objective pass-risk judgment to the final report: likely pass, borderline, or high risk.
- Treat long-term personalization as important, but only implement low-cost memory during the MVP.

Reason:

- A fourth anonymized research response described project-detail questioning as potentially becoming like a rebuttal session.
- The user specifically wanted method-design challenges, related-method comparisons, personal-contribution clarification, and project story clarity feedback.
- The user also highlighted that plain ChatGPT lacks long-term personalized context and tends to require re-pasting the same profile/project material.
- Objective feedback matters more than comfort: the product should be allowed to say current performance may not pass if the answer is weak.

Product consequences:

- Keep P0 focused on project card, project deep-dive, adaptive follow-up, structured feedback, final report, and deployment.
- Strengthen P0.5 with reviewer-style questions, pass-risk final report, method-comparison follow-ups, personal contribution clarification, project story clarity, and saved project profile if low-cost.
- Move full long-term memory, semantic parsing, large question banks, advanced analytics, voice, and video to future work.

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

- Use `openrouter/qwen/qwen3.6-plus` for first questions, follow-up generation, per-answer feedback, and final reports.

Reason:

- The prompt-first MVP depends on stronger reviewer-style judgment inside the existing feedback/report fields.
- One interview model reduces demo variability while the product is still narrow and time-boxed.

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
- Full semantic resume/PDF parsing as a required MVP path.

## Scope Cuts

Cut from MVP:

- Full voice/video interview as required path.
- Broad job interview categories.
- Complex algorithm practice.
- Large question bank.
- User-configured API keys.
- OAuth/email verification.
- Mandatory semantic resume/PDF parsing.
- Advanced analytics dashboard.
- Multi-user admin system.
- Complicated multi-agent architecture.

Reason:

- The product must be reliable and demoable under a tight deadline.
- User research points to project-depth feedback as the clearest need, so broad feature coverage would dilute the product.

## Implementation Log

Add entries below as changes are made.

### 2026-05-24: v0.3 Release Notes

Highlights:

- Shipped the text interview MVP with project-card driven interviews.
- Added adaptive follow-up questions with reviewer-style pressure.
- Added structured per-answer feedback and final report outputs.
- Persisted interview sessions, turns, and attachments.
- Added backend tests for interview flows and reliability fixes for LLM outputs.

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

### 2026-05-24: Attachments And Demo Reliability Pass

Change:

- Added interview attachment binding for uploaded project materials.
- Injected text attachments into interview prompts as XML/CDATA context.
- Sent image attachments to OpenRouter-compatible multimodal model calls as `image_url` inputs.
- Added PDF upload support for interview context: extract page text when available and render pages as image inputs, with a default 12-page limit.
- Added JSON repair/fallback behavior for interview LLM outputs.
- Switched feedback/follow-up generation to the fast interview model.
- Improved profile validation so "short profile + uploaded files" is a valid demo path.
- Improved frontend error display for FastAPI validation errors.
- Refined QA feedback layout and history navigation.
- Updated Docker build mirrors and removed the Python `pytesseract` dependency in favor of system `tesseract` CLI where OCR is needed.
- Expanded server disk capacity from about 20G to 40G.

Reason:

- Supporting files make the project-deep-dive workflow much more realistic: students can provide reports, notes, diagrams, and experiment figures without typing everything live.
- The demo needs a fast and reliable path from profile/files to first question, feedback, follow-up, and final report.
- Build and disk reliability matter because late deployment work is high risk.

Verification:

- `cd backend && uv run pytest`: 28 passed
- `cd backend && uv run ruff check .`
- `cd frontend && pnpm lint`
- `cd frontend && pnpm build`
- `docker compose config --quiet --no-env-resolution`
- `docker compose up -d --build`
- `curl -f http://127.0.0.1:8000/health`
- `curl -f http://127.0.0.1:3000`
- `curl -f http://115.190.120.206/health`
- Local API smoke: short profile plus attachments created an interview with `200 OK`.
- Human public demo check: developer reported no blocking issue after manual testing.

Known risk:

- No automated browser screenshot regression for the QA feedback layout yet.
- No separately recorded full public run log for upload PDF/image -> multi-turn interview -> final report.

### Entry Template

```text
Date/time:
Change:
Reason:
Files:
Verification:
Known risk:
```
