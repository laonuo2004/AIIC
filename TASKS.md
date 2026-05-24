# ResearchMocker Tasks

## Product Direction

ResearchMocker is an AI mock interviewer for CS/AI undergraduate students preparing for research-oriented interviews: graduate recommendation interviews, research internship interviews, lab admission interviews, and project-experience deep dives.

The product should not feel like a generic chat window. The core loop is:

1. User logs in or uses a test account.
2. User enters self-introduction, project/research experience, target direction, and weak points.
3. System starts a mock interview.
4. AI interviewer asks one targeted question at a time.
5. User answers.
6. System gives structured feedback: strengths, weaknesses, score, and actionable advice.
7. System asks an adaptive follow-up question.
8. User finishes and receives a final review report.

## Current Baseline To Reuse

Already available:

- FastAPI backend.
- Next.js + TypeScript frontend.
- SQLite persistence.
- HttpOnly cookie auth.
- Streaming chat through LiteLLM/OpenRouter.
- Text/image attachment support.
- Theme support and settings page.
- Docker Compose and Nginx deployment.
- Backend pytest coverage and frontend checks.
- Public deployment at `http://115.190.120.206/`.

The baseline must be adapted, not recreated.

## P0: Must Finish For MVP

- Reposition all user-facing copy from generic chat to ResearchMocker.
- Replace the provider configuration product flow with a backend-managed OpenRouter setup.
- Keep normal users away from API keys, provider names, and raw model IDs.
- Add candidate profile input:
  - self-introduction
  - project/research experience
  - target direction
  - weak points
  - interview type or scenario
- Build the text interview workflow:
  - start interview
  - show one question at a time
  - submit answer
  - receive structured feedback
  - receive adaptive follow-up question
  - finish interview
  - show final report
- Add backend interview APIs or adapt existing chat APIs cleanly.
- Add prompt files for:
  - interviewer persona
  - candidate profile analysis
  - follow-up question generation
  - answer feedback
  - final report
- Implement backend model routing:
  - `openrouter/qwen/qwen3.6-plus` for profile analysis and final report
  - `openrouter/qwen/qwen3.6-flash` for frequent interview turns and single-answer feedback
- Persist interview records in SQLite or clearly display them during the session if time is tight.
- Add pytest coverage for the interview API with mocked LLM calls.
- Keep deployment working through Docker Compose and Nginx.
- Update README, Product Memo notes, iteration log, and demo script.
- Prepare a test account if login remains required.

## P1: Important But Can Be Simplified

- Saved interview history list and detail view.
- Better final report sections:
  - overall score
  - technical depth
  - project ownership
  - research thinking
  - communication clarity
  - weakest answers
  - next practice plan
- Reuse attachments for optional project notes, screenshots, or short video/image context.
- Add a reserved Face-to-Face Interview page between Text Interview and Settings.
- On the face-to-face page, provide the product shell for:
  - interviewer image upload
  - reference audio upload
  - generated ready/listening video previews
  - microphone-based interview start state
- Build a backend adapter spike for Volcengine only if P0 is stable.
- Document provider risks and fallback behavior.

## P2: Optional Only After MVP Is Stable

- Full Volcengine end-to-end real-time speech interaction.
- Voice cloning from uploaded interviewer reference audio.
- OmniHuman 1.5 fast-mode video generation from interviewer image.
- Seamless switching among ready, listening, and speaking video states.
- Exportable final report.
- More interview templates for different labs or research areas.
- Lightweight analytics for common weaknesses across sessions.

## Cut: Deliberately Not Doing Now

- Voice/video as the only working product path.
- Broad big-tech algorithm interview platform.
- Large question bank.
- PDF parsing as a required feature.
- OAuth or email verification.
- Multi-provider settings page for normal users.
- User-entered provider API keys.
- Complex dashboard.
- PostgreSQL, Redis, Celery, Kubernetes, or local large model inference.
- Heavy animation or visual polish that delays the core demo.

## Time-Aware Plan

### First 1 Hour

- Finalize product positioning and document scope.
- Update this task board.
- Decide demo flow and fallback.
- Identify the smallest code path from current chat baseline to interview MVP.

### Hours 2-5

- Implement backend interview schemas, prompts, model routing, and mocked tests.
- Keep the existing auth/session/database foundation.
- Prefer one clean interview endpoint set over scattered chat hacks.

### Hours 6-9

- Implement frontend text interview flow:
  - profile form
  - interview question panel
  - answer composer
  - structured feedback
  - final report
- Remove or hide provider configuration from normal navigation.

### Hours 10-12

- Persist interview records.
- Polish mobile/desktop layout enough for recording.
- Add demo data and test account if needed.
- Update README and Product Memo notes.

### Hours 13-14

- Run backend tests and frontend checks.
- Deploy with Docker Compose.
- Verify public URL and `/health`.
- Do one real OpenRouter smoke test.

### Hours 15-16

- Record demo video.
- Finalize Product Memo.
- Push final commits.
- Prepare submission email.
- Avoid post-deadline deployments.

## LLM Strategy

Normal users should not see provider details.

Backend routing:

- Deep model: `openrouter/qwen/qwen3.6-plus`
- Fast model: `openrouter/qwen/qwen3.6-flash`

Both selected models are treated as supporting text, image, and video input based on provider-side confirmation.

Use cases:

- Candidate profile and project understanding: deep model.
- First question: deep model if profile is rich, otherwise fast model.
- Follow-up questions: fast model.
- Single-answer feedback: fast model.
- Final report: deep model.

All provider calls must be backend-only through LiteLLM or an isolated adapter.

## Face-to-Face Interview Concept

This is a differentiating extension, not the MVP dependency.

Target flow:

1. User uploads interviewer image and reference audio.
2. Backend generates two short interviewer videos:
   - ready/blinking
   - listening/nodding
3. Backend uses reference audio for voice cloning.
4. User speaks through microphone.
5. Volcengine real-time speech model handles speech-to-speech interaction.
6. UI switches among ready, listening, and speaking states to create a face-to-face interview feeling.

Primary APIs:

- Volcengine end-to-end real-time speech model.
- Volcengine OmniHuman 1.5 digital human fast mode.

Fallback:

- If real-time API integration is too risky, show the reserved page and use the text interview MVP for the final demo.
- If video generation is slow, use pre-generated ready/listening clips.
- If voice cloning is unavailable, use text interview plus documented next step.

## Risks And Fallbacks

- **LLM latency or provider failure**: keep an existing persisted demo session and use mocked tests for reliability.
- **Model output not valid JSON**: add repair/parsing fallback or store raw text with a user-friendly error.
- **Scope creep from face-to-face mode**: do not start full Volcengine integration before text MVP works.
- **Deployment failure**: preserve current Docker/Nginx baseline and rollback to last working image/build.
- **Time pressure**: ship text interview + final report first; reserve face-to-face as design/experimental page.
- **Secrets risk**: verify `.env`, database files, caches, `.venv`, `.next`, and `node_modules` are not tracked.

## Verification Checklist

For documentation-only changes:

- `git diff --check`
- `git status --short`
- `rg -n "[C]hat Studio|[O]penRouter page" README.md TASKS.md docs AGENTS.md`

For implementation changes:

- `cd backend && uv run pytest`
- `cd backend && uv run ruff check .`
- `cd frontend && pnpm lint`
- `cd frontend && pnpm build`
- `docker compose config --quiet --no-env-resolution`
- `docker compose up -d --build`
- `curl -f http://127.0.0.1/health`
- `curl -f http://115.190.120.206/health`

## Demo Checklist

- Open public URL.
- Log in with a test account or register quickly.
- Show the first screen as ResearchMocker, not a generic chat app.
- Enter a candidate profile and project summary.
- Start text interview.
- Show the AI asking a targeted project/research question.
- Answer vaguely once so the product can expose the weakness.
- Show structured feedback and an adaptive follow-up.
- Finish interview and show final report.
- If face-to-face page is ready, show it briefly as the bridge from text practice to realistic interview simulation.
- End with engineering summary: FastAPI, Next.js, SQLite, LiteLLM/OpenRouter, Docker/Nginx, tests.
