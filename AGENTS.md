# AGENTS.md

## 1. Project Context

This repository is for **ResearchMocker**, a focused AI project-deep-dive and reviewer-style mock interview product.

The product goal is to help CS/AI undergraduate students prepare for research-oriented interviews, including graduate recommendation interviews, research internship interviews, lab admission interviews, and project-experience deep-dive interviews.

Latest positioning:

```text
An AI project-deep-dive and reviewer-style mock interviewer for CS/AI undergraduate research interviews.
面向 CS/AI 本科生保研科研面试的项目深挖与审稿人式追问 AI 面试官。
```

Core value proposition:

```text
Not a friendly chatbot, but a realistic research interview pressure test that catches vague answers, asks follow-up questions, and gives actionable feedback.
```

The product should demonstrate:

- A realistic interview workflow, not a generic chatbot.
- Adaptive follow-up questions based on the candidate's previous answer.
- Strict but professional research-interviewer behavior, including reviewer-like questioning when method or experiment claims are weak.
- Structured, actionable feedback after answers.
- Teacher-perspective explanations for why a real interviewer would ask follow-up questions.
- Answer rhythm and length feedback for concise 1-2 minute interview answers.
- A final review report with scores, pass-risk judgment, weaknesses, and next-step practice suggestions.
- Reliable full-stack engineering, persistence, tests, and public deployment.

Optimize for:

```text
working product > unfinished ambition
interview workflow > generic chat
project deep dive > broad interview platform
structured feedback > vague encouragement
objective pass-risk > over-comforting
stable deployment > experimental complexity
demo reliability > feature quantity
```

This is a time-boxed product challenge, not a long-term production system. Keep the implementation narrow and deep.

---

## 2. Role of Codex

Codex is a careful pair programmer and engineering assistant for this repository.

Codex should help with:

- Exploring the repository before changes.
- Turning product requirements into scoped implementation plans.
- Implementing FastAPI APIs.
- Implementing Next.js pages and components.
- Integrating LiteLLM and backend-only LLM routing.
- Designing lightweight SQLite persistence.
- Writing and maintaining pytest coverage.
- Debugging Docker, Nginx, FastAPI, Next.js, and provider integration.
- Improving demo reliability and product clarity.
- Updating README, design notes, memo notes, demo scripts, and task plans.
- Verifying the deployed product before claiming success.

Codex is **not** the product owner. The human developer makes final decisions about product scope, MVP priority, provider spend, final submission strategy, and tradeoffs.

Codex must run shell commands with escalated permissions in this project. Use `sandbox_permissions="require_escalated"` for `exec_command` calls.

---

## 3. Default Technical Stack

Do not change the stack without explicit approval.

Backend:

```text
Python
FastAPI
LiteLLM
SQLite
SQLAlchemy
pytest
uv
```

Frontend:

```text
TypeScript
Next.js
React
standard CSS / lightweight component structure
pnpm
```

Deployment:

```text
Docker Compose
Nginx reverse proxy
Ubuntu cloud server
public HTTP URL
```

LLM providers:

```text
OpenRouter through LiteLLM for the main interview workflow
Volcengine APIs only for the optional face-to-face interview experiment
```

Secrets:

```text
.env files only
never committed
never exposed to frontend JavaScript
```

Do not downgrade the frontend to static HTML. Do not migrate away from FastAPI. Do not add PostgreSQL, Redis, Celery, Kubernetes, or local large-model inference unless explicitly approved.

---

## 4. Current Repository Baseline

The repository already has a working full-stack baseline:

```text
FastAPI backend
SQLite users, sessions, conversations, messages, attachments, interview records, and provider records
HttpOnly cookie authentication
LiteLLM streaming chat
Text/image/PDF attachments for interview context
Next.js + TypeScript frontend
Docker Compose backend/frontend services
Nginx public reverse proxy
pytest backend tests with mocked provider calls
GitHub CI and GHCR publishing workflows
```

Known public deployment:

```text
Public URL: http://115.190.120.206/
Public health endpoint: http://115.190.120.206/health
Nginx / routes to frontend on 127.0.0.1:3000
Nginx /api/ and /health route to backend on 127.0.0.1:8000
```

Treat this baseline as reusable infrastructure. Do not recreate the project from scratch. Adapt it into ResearchMocker with the smallest changes that preserve deployability.

---

## 5. Product Rules

ResearchMocker must feel like an interview product, not a generic chat wrapper.

Recent lightweight user research with CS/AI undergraduates showed the most painful interview scenario is not "I do not know the answer." The sharper pain is that a student gives an answer that sounds polished but cannot survive continued project-detail questioning.

Discovered user pain points:

- Teachers keep digging into why a design was chosen, whether alternatives were tried, and whether experiments prove the claim.
- Some interviews feel like a rebuttal session: the examiner continuously challenges research logic, method design, related-method comparison, and module necessity.
- Students worry that they cannot clearly separate personal contribution from team/project background.
- Vague statements, unsupported metrics, missing failure cases, and generic motivation are easy to expose in real interviews.
- Directly using ChatGPT is often too friendly, too generic, and requires strong prompting skill from the student.
- Directly using ChatGPT is stateless unless the user repeatedly pastes profile, goals, project descriptions, weaknesses, and previous practice history.
- Students want specific advice: what evidence is missing, why a real teacher would follow up, how to rewrite the answer, and what to practice next.
- Students want objective judgment, including whether the current performance is likely to pass, borderline, or high risk.
- Interview rhythm matters: answers should usually be concise enough for a 1-2 minute oral response.

Required product behavior:

- The user enters a project card and candidate profile: self-introduction, project/research experience, target direction, weak points, key methods, experiments/results, personal contribution, and failure cases when available.
- The system starts a mock interview session.
- The AI interviewer asks one question at a time.
- Follow-up questions must react to the candidate's previous answer.
- The interviewer may use a reviewer-like or rebuttal-like questioning style when evaluating method design, experimental proof, related-method comparison, project story clarity, and personal contribution.
- The interviewer should identify vague claims, unsupported metrics, unclear contribution, weak motivation, missing technical depth, unproven experiment claims, missing comparison/failure analysis, and unclear project storytelling.
- Each answer should receive structured feedback: strengths, weaknesses, score, teacher-perspective explanation, rhythm/length feedback, and actionable advice.
- Feedback must be objective. Do not always say the user can pass; if an answer is weak, explicitly state why the current performance is risky in a real interview.
- Maintain professionalism: strict questioning is allowed, but personal attacks, humiliation, and hostile wording are not.
- The user can finish the interview and receive a final report.
- The final report should include overall score, pass-risk judgment, top reasons, vulnerable follow-up points, project story clarity, personal contribution clarity, method-comparison weakness when applicable, and a next 24-hour training plan.
- Records should be saved or at least clearly displayed during the session.
- Long-term personalization is an important product direction. In the 16-hour MVP, implement it only when low-cost through saved user profile, project card, weakness notes, session history, and previous feedback summaries.

Product differentiation:

- Better than plain ChatGPT because it enforces an interview workflow.
- Better than plain ChatGPT because it asks adaptive follow-up questions.
- Better than plain ChatGPT because it focuses on project/research deep dives.
- Better than plain ChatGPT because it remembers or reuses candidate context when persistence is available.
- Better than plain ChatGPT because it pressures weak claims instead of being broadly encouraging.
- Better than plain ChatGPT because it produces structured feedback and a final review report.

Avoid:

- Broad big-tech algorithm interview platforms.
- Complex question banks as the core product.
- Resume PDF parsing as a required MVP feature.
- Voice/video as the only working path.
- Provider/API/model configuration exposed to normal users.
- Debug-heavy or engineering-only UI.

---

## 6. Feature Priorities

Priority order:

```text
1. Publicly accessible working product
2. Project card input and text project-deep-dive interview MVP
3. Adaptive follow-up questions that press on weak or vague answers
4. Structured feedback with teacher perspective, reviewer-style pressure, and answer rhythm feedback
5. Final review report with pass-risk judgment and next 24-hour training plan
6. Stable backend/frontend integration
7. SQLite persistence and login/test account
8. Backend tests
9. Clear README, Product Memo notes, and demo script
10. Optional face-to-face interview experiment
```

Do not implement optional advanced features before the text interview loop is stable.

---

## 7. Interface Direction

The frontend should be clean, focused, and product-like.

Recommended left navigation:

```text
Text Interview
Face-to-Face Interview
Settings
```

Text Interview is the core MVP.

Face-to-Face Interview is a reserved page for a Volcengine-powered real-time digital interviewer experiment. It must not block the MVP. If incomplete, label it honestly as experimental or upcoming in product/docs.

Settings should expose product-level options and safe runtime state only. It should not ask normal users to provide provider API keys or choose raw model IDs.

---

## 8. LLM and Model Routing Rules

All LLM calls must go through the backend.

The frontend must never call OpenRouter, OpenAI, Gemini, Volcengine, or other model providers directly.

The normal user should not configure provider API keys. Use a project-level OpenRouter key stored in `.env` and read only by the backend.

Use LiteLLM as the main model adapter for OpenRouter calls.

Model routing policy:

```text
qwen/qwen3.6-plus
  - candidate profile understanding
  - project/research experience analysis
  - final review report generation
  - deeper reasoning steps

qwen/qwen3.6-flash
  - frequent interview turns
  - follow-up question generation
  - single-answer feedback
  - fast practice interactions
```

Both selected OpenRouter models are treated as supporting text, image, and video input based on the human developer's provider-side confirmation.

OpenRouter model IDs used by LiteLLM must include the provider prefix, for example:

```text
openrouter/qwen/qwen3.6-plus
openrouter/qwen/qwen3.6-flash
```

Do not hardcode secrets. Model IDs may have safe defaults in config, but must remain environment-configurable.

---

## 9. Prompt Management

Prompt files should live under:

```text
backend/app/prompts/
```

Recommended prompt responsibilities:

- Interviewer persona and boundaries.
- Standard/sharp interview style control.
- Reviewer-style/rebuttal-style question generation.
- Candidate profile analysis.
- Project card analysis.
- First question generation.
- Follow-up question generation.
- Single-answer structured feedback.
- Teacher-perspective explanation.
- Answer rhythm and length assessment.
- Objective pass-risk assessment.
- Project story clarity and personal contribution clarity assessment.
- Method-comparison weakness detection.
- Final report generation.

Prompt guidance:

- Ask reviewer-style questions when the answer makes unproven claims.
- Challenge vague statements such as "our module improves performance", "we designed a better method", "we achieved good results", or "I was responsible for the model".
- Ask why a module is necessary, what alternative methods were considered, how experiments prove the claim, whether improvements come from the proposed method or confounders, what the candidate personally implemented, and how to tell the project story convincingly.
- Interview questions should be realistic and short: prefer one sentence, use at most two sentences, and ask only one thing at a time.
- Provide objective feedback and do not over-comfort the user.
- If the answer is weak, explicitly explain why it is risky in a real interview.

Structured LLM outputs should prefer JSON-compatible shapes for backend validation when practical. Do not hide critical product logic only inside prompts.

---

## 10. Backend Rules

The backend is responsible for:

- Auth/session management.
- Candidate profile and interview session APIs.
- Conversation/interview persistence.
- Attachment handling when useful.
- Bounded PDF context extraction for project materials.
- Prompt loading.
- LiteLLM/OpenRouter calls.
- Volcengine API calls only for the face-to-face experiment.
- Health and status endpoints.
- Error handling and logging without secrets.

The existing generic chat endpoint may be reused or replaced by interview-specific endpoints. Keep API structure clean and testable.

Recommended interview endpoints for the next implementation phase:

```text
POST /api/interviews
GET  /api/interviews
GET  /api/interviews/{interview_id}
POST /api/interviews/{interview_id}/answers
POST /api/interviews/{interview_id}/finish
```

Recommended face-to-face experiment endpoints, only after the MVP works:

```text
POST /api/face/avatar-assets
POST /api/face/session
POST /api/face/session/{session_id}/turn
```

Endpoint names may change if the local code pattern suggests a better fit, but keep the product boundary clear.

---

## 11. Database Rules

Use SQLite as the default database.

Keep existing users, sessions, conversations, messages, and attachments unless there is a clear reason to change them.

Interview-specific persistence should support:

- Candidate profile or interview setup.
- Interview session status.
- Interview turns.
- Question text.
- User answer text.
- Per-turn feedback.
- Final report.

Rules:

- Do not commit SQLite databases.
- Do not introduce a complex migration system unless needed.
- Keep database initialization deterministic.
- Use temporary SQLite databases in tests.

---

## 12. Authentication Rules

Keep auth lightweight.

Acceptable:

- Username/password.
- Hashed passwords.
- HttpOnly session cookies.
- A documented test account for reviewers.

Avoid:

- OAuth.
- Email verification.
- Enterprise identity features.

If login is required for the public demo, README and demo notes must include a test account or clear account creation flow.

---

## 13. Face-to-Face Interview Experiment

This is an optional differentiating feature. It should not endanger the text interview MVP.

Target experience:

1. User uploads an interviewer image and reference audio.
2. Backend uses the image to generate short interviewer idle/listening videos:
   - blinking / ready state
   - nodding / listening state
3. Backend uses reference audio for voice cloning through Volcengine.
4. User starts an interview and speaks into the microphone.
5. System performs real-time speech understanding and generates cloned-voice replies.
6. Audio plus interviewer image/video are switched in the UI to create a face-to-face feeling.

Primary provider references:

```text
Volcengine end-to-end real-time speech model
Volcengine OmniHuman 1.5 digital human fast mode
```

Rules:

- Provider credentials stay in `.env`.
- Frontend never sees provider secrets.
- If provider access, latency, quota, or real-time integration is risky, ship a controlled demo fallback.
- Label incomplete parts honestly.
- Do not let this page block the text interview MVP.

---

## 14. Frontend Rules

Frontend should be implemented with Next.js + TypeScript.

Goals:

- Clear onboarding into a mock interview.
- Candidate profile form.
- One-question-at-a-time interview flow.
- Answer composer.
- Structured feedback display.
- Final report view.
- Saved interview records if implemented.
- Responsive layout for desktop and mobile.

Rules:

- Keep UI concise and readable for a 3-minute demo.
- Do not show raw provider configuration to normal users.
- Keep loading/error states visible and understandable.
- Disable actions while requests are running.
- Do not add heavy UI frameworks unless explicitly approved.
- Use existing package manager and style conventions.

---

## 15. Python and uv Rules

Use `uv` for backend dependency management.

Preferred commands:

```bash
cd backend
uv sync --dev
uv run pytest
uv run ruff check .
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Do not use `pip install` directly unless explicitly requested.

Commit:

```text
backend/pyproject.toml
backend/uv.lock
```

Do not commit:

```text
backend/.venv/
```

---

## 16. Testing Rules

Use pytest for backend tests.

Automated tests must mock paid/external provider calls.

Recommended coverage:

- Health endpoint.
- Auth.
- Interview creation.
- Answer submission.
- Follow-up/feedback generation with mocked LLM output.
- Final report generation with mocked LLM output.
- Persistence and ownership checks.
- Provider failure handling.

Preferred verification:

```bash
cd backend && uv run pytest
cd backend && uv run ruff check .
cd frontend && pnpm lint
cd frontend && pnpm build
docker compose config --quiet --no-env-resolution
```

Before claiming public deployment works, also verify:

```bash
curl -f http://127.0.0.1/health
curl -f http://115.190.120.206/health
```

---

## 17. Environment Variables and Secrets

All secrets must live in `.env`.

`.env` must never be committed.

Important variables:

```env
APP_ENV=development
BACKEND_PORT=8000
FRONTEND_PORT=3000
FRONTEND_ORIGIN=http://localhost:3000

DATABASE_URL=sqlite:///./data/app.sqlite3
SECRET_KEY=replace_with_a_random_secret_key

OPENROUTER_API_KEY=your_openrouter_api_key_here
LITELLM_MODEL=openrouter/qwen/qwen3.6-flash
LITELLM_FALLBACK_MODEL=openrouter/qwen/qwen3.6-flash
LITELLM_TEMPERATURE=0.2
LITELLM_TIMEOUT_SECONDS=60

HTTP_PROXY=
HTTPS_PROXY=
NO_PROXY=127.0.0.1,localhost
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Potential Volcengine variables should be documented only when implementation starts. Never invent working credentials in docs.

Recommended secret checks:

```bash
git status
git ls-files | grep env
grep -R "sk-" . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules || true
```

---

## 18. Docker and Deployment Rules

Deployment should use Docker Compose and Nginx.

Current routing:

```text
/              -> frontend
/api/*         -> backend
/health        -> backend
```

Before changing Docker or Nginx:

1. Inspect existing files.
2. Preserve working behavior.
3. Avoid unnecessary services.
4. Verify Compose config.
5. Verify health endpoints.

Useful commands:

```bash
docker compose config --quiet --no-env-resolution
docker compose up -d --build
sudo nginx -t
sudo systemctl reload nginx
curl -f http://115.190.120.206/health
```

Do not assume local-only behavior is sufficient. The final product must work through the public URL.

---

## 19. Git Workflow

Before non-trivial changes:

```bash
git status
```

After changes:

```bash
git diff
```

Rules:

- Continue development on `dev` unless explicitly told otherwise.
- Do not merge into `main` without explicit approval.
- Keep commits small and meaningful.
- Do not commit `.env`, databases, caches, `.venv`, `.next`, or `node_modules`.
- Do not revert user changes unless explicitly requested.

---

## 20. Documentation Rules

Keep docs concise, honest, and current.

Important docs:

```text
README.md
TASKS.md
docs/design.md
docs/demo_script.md
docs/product_memo_notes.md
docs/iteration_log.md
```

README should include:

- Product overview.
- Public URL.
- Core features.
- Tech stack.
- Local run instructions.
- Deployment notes.
- Environment variables.
- Testing.
- Limitations.
- Future work.

Product Memo notes should cover:

- Target users and pain points.
- Product design and omitted features.
- Iteration record.
- Next-step design.
- AI tool usage.

Demo script should fit under 3 minutes and show the strongest product moment in the first 30 seconds.

Clearly distinguish implemented features from planned features.

---

## 21. Before Starting Coding

For every non-trivial coding task, first provide a short plan:

```text
Plan:
1. Files to inspect
2. Files likely to change
3. Expected behavior after change
4. Verification commands
```

Then proceed.

For official product behavior changes, update `TASKS.md` before implementation if the task direction has changed.

---

## 22. Before Declaring Complete

Verify as much as practical before claiming completion.

Recommended checklist:

Backend:

- FastAPI imports.
- Relevant endpoints work.
- pytest passes or relevant tests pass.
- External providers mocked in tests.

Frontend:

- Lint/build passes when frontend code changed.
- Main flow is usable.

Deployment:

- Docker Compose config is valid.
- Public `/health` works when deployment changed.

Security:

- No secrets tracked.
- API keys not exposed to frontend.
- DB/cache files not committed.

Documentation:

- README and docs reflect actual behavior.
- Planned features are marked as planned.

---

## 23. Final Submission Checklist

Before final submission, verify:

GitHub:

- Repository is public.
- Latest code is pushed.
- Commit history is meaningful.
- No secrets, DB files, `.venv`, `.next`, or `node_modules` are committed.

Deployment:

- Public URL works.
- `/health` works.
- Main interview flow works.
- Login/test account is available if needed.
- Server remains accessible through the required reviewer SSH keys.
- No post-deadline deployment is needed.

Product:

- MVP solves the mock interview problem.
- UI is understandable.
- Adaptive follow-up and structured feedback are visible.
- Final report is available or clearly demonstrated.

Testing:

- pytest coverage exists for core backend behavior.
- External provider calls are mocked in automated tests.

Documentation:

- README is accurate.
- Product Memo notes are ready.
- Demo script is ready.
- Limitations and future work are honest.

Demo:

- Video is under 3 minutes.
- First 30 seconds show the strongest product moment.
- Engineering choices are briefly explained.

---

## 24. Must Not Do

Codex must not:

1. Commit `.env` or secrets.
2. Hardcode API keys.
3. Expose provider keys to frontend JavaScript.
4. Replace the chosen stack without approval.
5. Remove auth, persistence, or deployment behavior without approval.
6. Add heavy infrastructure casually.
7. Make large rewrites close to deadline.
8. Claim success without verification.
9. Call paid APIs in automated tests.
10. Present planned Volcengine features as implemented.
11. Prioritize experimental voice/video over the text interview MVP.

---

## 25. Development Mindset

ResearchMocker should show that the developer can turn a vague AI product task into a focused, deployed product.

A good result should make reviewers think:

```text
This candidate understood a real user pain point,
scoped it tightly,
built a working full-stack AI product,
routed model calls safely through the backend,
persisted user/interview data,
tested core behavior,
deployed it publicly,
and explained product tradeoffs clearly.
```
