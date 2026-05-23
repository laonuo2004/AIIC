# AGENTS.md

## 1. Project Context

This repository is for the **AIIC Project Challenge**.

The goal is to build a small but complete AI web product under a limited time budget. The final submission is expected to include:

- A public GitHub repository.
- A publicly accessible web URL.
- A working deployed service on a cloud server.
- Clear commit history.
- A short demo video explaining the design and showing the product.
- A concise README explaining setup, usage, design, implementation, deployment, limitations, and future work.

The project should demonstrate:

1. Solid product understanding.
2. Reliable AI system engineering.
3. Modern full-stack development ability.
4. Clean backend API design.
5. Usable frontend interaction.
6. Multi-provider LLM integration.
7. Basic user/account/database design.
8. Deployment and testing discipline.

This is a challenge project, not a long-term production system. The implementation should be more complete than a toy demo, but it must still be scoped carefully for the deadline.

Optimize for:

```text
working product > unfinished ambition
engineering clarity > excessive abstraction
stable deployment > experimental complexity
demo reliability > feature quantity
```

---

## 2. Role of Codex

Codex is a development assistant for this project.

Codex should help with:

- Understanding the repository structure.
- Turning project requirements into implementation plans.
- Implementing backend APIs.
- Implementing frontend pages and components.
- Integrating LiteLLM for multi-provider LLM routing.
- Designing lightweight SQLite-backed persistence.
- Implementing basic user login/session functionality.
- Writing pytest-based automated tests.
- Debugging Docker, Nginx, FastAPI, Next.js, and API integration issues.
- Improving UI clarity and demo quality.
- Writing or improving README, design notes, API docs, and demo scripts.
- Reviewing code before final submission.
- Verifying that the deployed product works.

Codex should act as a careful pair programmer and engineering assistant.

Codex is **not** the product owner. The human developer makes final decisions about:

- Product scope.
- MVP definition.
- Feature priority.
- Technical tradeoffs.
- External API providers.
- Final submission strategy.
- Whether a feature is worth implementing under the time limit.

---

## 3. Default Technical Stack

Unless explicitly instructed otherwise, assume the default stack is:

### Backend

```text
Python
FastAPI
LiteLLM
SQLite
pytest
uv
```

### Frontend

```text
TypeScript
Next.js
React
CSS Modules / standard CSS / lightweight component structure
```

### Deployment

```text
Docker Compose
Nginx reverse proxy
Ubuntu cloud server
Public IP or domain-based access
```

### LLM Providers

```text
LiteLLM as the unified gateway/router
OpenAI / OpenRouter / Gemini / other providers configured through environment variables
```

### Secrets

```text
.env files only
Never committed to Git
Never exposed to frontend JavaScript
```

Do not downgrade the project to a simple static HTML/CSS/JS frontend unless the human developer explicitly asks for an emergency fallback.

Do not migrate the backend away from Python + FastAPI unless explicitly requested.

Do not bypass LiteLLM for new LLM provider integrations unless there is a strong reason.

### Current Repository Baseline

As of the server inspection on 2026-05-23, this repository is still in the preparation phase because the official challenge topic has not been released yet.

Current tracked project content is limited to:

```text
.gitignore
LICENSE
README.md
docs/2026-05-22_项目准备说明_.md
docs/2026-05-22_项目准备说明_.pdf
.agents/skills/
```

`AGENTS.md` may initially be untracked until the human developer chooses to commit it.

The Git remote currently points to:

```text
origin https://github.com/laonuo2004/AIIC.git
branch main
```

Do not create a detailed application structure before the official topic is known. After the topic is released, create or update `TASKS.md` first, then choose the smallest structure that fits the product.

### Current Server Baseline

The current cloud server is suitable for a lightweight AI web product, but resources should be managed carefully:

```text
OS: Ubuntu 24.04.4 LTS
CPU: 2 vCPU
Memory: about 7.8 GiB RAM plus 2.0 GiB swap
Disk: 20 GiB root disk, about 8 GiB free during initial inspection
User: aiic
Sudo: passwordless sudo is available for aiic
```

Known available tools after environment repair:

```text
Python 3.12.3
uv 0.11.16
Node.js 24.16.0
npm 11.13.0
pnpm 11.2.2
Git 2.43.0
GitHub CLI 2.45.0
Docker 29.1.3
Docker Compose 2.40.3
Nginx 1.24.0
SQLite CLI 3.45.1
curl
jq
make
gcc
```

Codex must run shell commands with escalated permissions in this project. Use `sandbox_permissions="require_escalated"` for `exec_command` calls instead of running ordinary sandboxed shell commands.

---

## 4. Engineering Priorities

The project should balance engineering completeness and deadline safety.

Priority order:

```text
1. Publicly accessible working product
2. Correct core task behavior
3. Stable backend and frontend integration
4. Clean LLM routing through LiteLLM
5. Basic user login and persistence
6. Meaningful automated tests
7. Clear README and demo script
8. UI polish
9. Optional advanced features
```

Do not implement optional advanced features before the core product works end to end.

---

## 5. Core Engineering Principles

Always follow these principles:

1. Keep the app deployable at all times.
2. Build the minimal working end-to-end loop first.
3. Prefer clear, maintainable code over clever abstractions.
4. Make small, reversible changes.
5. Avoid unnecessary dependencies.
6. Never hardcode API keys or secrets.
7. Never expose backend API keys to frontend JavaScript.
8. Use LiteLLM as the main abstraction for LLM provider routing.
9. Add error handling around all external API calls.
10. Keep logs useful but never log secrets.
11. Write tests for core backend behavior.
12. Update documentation when behavior or usage changes.
13. Keep the final demo flow stable.
14. Avoid risky late-stage rewrites.
15. Respect the challenge deadline.

---

## 6. Expected Repository Structure

Do not lock the project into a detailed directory tree before the official challenge topic is released.

After the topic is released:

1. Update `TASKS.md` first with the requirement interpretation, MVP, risks, and deployment plan.
2. Choose the minimal repository structure needed for that specific product.
3. Keep the default stack unless the human developer explicitly approves a change.
4. Prefer conventional boundaries such as backend, frontend, infra, docs, and scripts only when they are actually needed.
5. Keep the structure easy to explain in the final README and demo video.

Do not reorganize the entire repository without a clear reason.

When modifying structure, preserve deployability.

---

## 7. Backend Rules

The backend should be implemented with FastAPI.

Recommended backend responsibilities:

- User registration/login/logout or minimal session management.
- Chat API.
- Conversation persistence.
- LiteLLM-based model calls.
- Health check.
- Error handling.
- Database access.
- Backend-side prompt loading.
- Backend-side API key usage.

The frontend should call backend APIs. The frontend should not call LLM providers directly.

Required backend endpoints unless project requirements say otherwise:

```text
GET  /health
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me
POST /api/chat
GET  /api/conversations
GET  /api/conversations/{conversation_id}
```

The exact endpoint set may be simplified if the challenge topic does not need full conversation history, but the backend should still preserve a clean API structure.

---

## 8. Frontend Rules

The frontend should be implemented with TypeScript + Next.js.

Frontend goals:

- Provide a clean product-like interface.
- Support login/logout if authentication is implemented.
- Provide a main chat or task interaction page.
- Show loading states.
- Show error states.
- Display model responses clearly.
- Avoid cluttered debug output in the final demo UI.
- Be readable during screen recording.
- Be reasonably responsive on common desktop browser sizes.

Rules:

- Use TypeScript types for API responses where practical.
- Keep components small and readable.
- Do not put API keys in frontend code.
- Do not call OpenAI/OpenRouter/Gemini directly from the browser.
- All LLM calls should go through the backend.
- Prefer simple styling over heavy UI frameworks unless already installed.
- Do not add complex state management libraries unless necessary.

If a package manager is already present, keep using it.

If no package manager is established in the frontend yet, prefer:

```text
pnpm > npm
```

`pnpm` is available on the current server. Do not change package managers after project initialization without a clear reason.

---

## 9. LiteLLM Rules

LiteLLM should be used as the unified layer for LLM provider management and routing.

Recommended backend file:

```text
backend/app/services/llm.py
```

The LiteLLM integration should:

- Read provider/model configuration from environment variables.
- Allow model switching through config rather than code rewrites.
- Support OpenAI-compatible providers when practical.
- Keep provider-specific logic minimal.
- Provide a simple internal function such as `generate_response(...)`.
- Handle provider errors gracefully.
- Return structured errors to the backend layer.
- Avoid leaking provider internals to end users.

Example environment variables:

```env
LLM_MODEL=gpt-4o-mini
LLM_FALLBACK_MODEL=openrouter/openai/gpt-4o-mini
LLM_TEMPERATURE=0.2
LLM_TIMEOUT_SECONDS=60

OPENAI_API_KEY=your_openai_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

Do not scatter direct SDK calls throughout the codebase.

If direct provider SDK usage is necessary for a special feature, isolate it in a service file and document the reason.

---

## 10. Database Rules

Use SQLite as the default lightweight database.

The database should support at least:

- Users.
- Sessions or authentication tokens.
- Conversations.
- Messages.

Recommended tables or models:

```text
User
Session / AuthToken
Conversation
Message
```

Keep the database layer simple.

Rules:

- Do not introduce PostgreSQL unless explicitly requested.
- Do not introduce Redis unless explicitly requested.
- Do not introduce a complex migration system unless the project needs it.
- If using SQLAlchemy or SQLModel, keep models readable.
- Keep database initialization deterministic.
- Store generated local database files outside Git tracking.
- Do not commit production or personal database files.

Recommended ignored files:

```gitignore
*.db
*.sqlite
*.sqlite3
backend/data/
```

A small seeded demo user may be added only if it does not contain secrets and is clearly documented.

---

## 11. Authentication Rules

The project should include lightweight user login if feasible.

Acceptable approaches:

```text
username/password login
session cookie
signed token
simple JWT-like token
```

Rules:

- Do not store plaintext passwords.
- Use password hashing.
- Keep auth simple and reliable.
- Do not implement OAuth unless explicitly required.
- Do not spend excessive time on advanced auth features.
- Do not expose authentication secrets to frontend code.
- Protect user-specific conversation history if implemented.

The goal is not enterprise-grade identity management. The goal is to show that the product has basic multi-user structure and persistence.

---

## 12. Python and uv Rules

Use `uv` for backend Python environment and dependency management.

Do not use `pip install` directly unless explicitly requested.

Preferred backend commands:

```bash
cd backend
uv sync --dev
uv add <package>
uv add --dev <package>
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
uv run pytest
uv run ruff check .
uv run black .
```

Rules:

- Commit `backend/pyproject.toml`.
- Commit `backend/uv.lock`.
- Do not commit `.venv/`.
- Do not commit `.env`.
- Keep runtime dependencies and development dependencies separate.
- Avoid adding large dependencies for small tasks.

---

## 13. Testing Rules

Use pytest for backend automated tests.

Do not rely only on shell-based smoke tests.

Shell scripts may still be used for deployment or quick checks, but backend correctness should be covered by pytest.

Recommended tests:

```text
test_health.py
  - health endpoint returns 200

test_auth.py
  - register user
  - login user
  - reject invalid credentials

test_chat.py
  - chat endpoint validates input
  - chat endpoint requires auth if auth is enabled
  - chat endpoint handles mocked LLM response
  - chat endpoint handles LLM failure gracefully

test_database.py
  - user creation
  - conversation creation
  - message persistence
```

Rules:

- Mock external LLM calls in tests.
- Do not call paid APIs in automated tests.
- Use temporary SQLite databases for tests.
- Tests should be fast.
- Tests should run locally and in the server environment.
- If a test is skipped, explain why.

Preferred command:

```bash
cd backend
uv run pytest
```

Before final submission, run pytest if practical.

---

## 14. Environment Variables and Secrets

All secrets must be stored in `.env`.

`.env` must never be committed.

`.env.example` should document required variables using placeholder values.

Example:

```env
APP_ENV=development
BACKEND_PORT=8000
FRONTEND_PORT=3000

DATABASE_URL=sqlite:///./data/app.sqlite3

SECRET_KEY=replace_with_a_random_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=1440

LITELLM_MODEL=gpt-4o-mini
LITELLM_FALLBACK_MODEL=openrouter/openai/gpt-4o-mini
LITELLM_TEMPERATURE=0.2
LITELLM_TIMEOUT_SECONDS=60

OPENAI_API_KEY=your_openai_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

Rules:

- Never hardcode API keys.
- Never print API keys.
- Never include API keys in README.
- Never expose API keys in frontend code.
- Never commit real `.env` files.
- Never log full request headers if they may contain tokens.
- Before final submission, check that secrets are not tracked by Git.

Recommended checks:

```bash
git status
git ls-files | grep env
grep -R "sk-" . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules || true
```

---

## 15. Prompt Management

Prompt files should be stored under:

```text
backend/app/prompts/
```

Recommended default:

```text
backend/app/prompts/system.md
```

Rules:

- Keep system prompts readable.
- Avoid extremely long prompts unless necessary.
- Do not hide essential business logic only inside prompts.
- Keep prompt loading backend-side.
- If the prompt changes significantly, update documentation or commit message.
- For final submission, document the prompt strategy in README or `docs/design.md`.

---

## 16. Docker Compose and Deployment Rules

Deployment should use Docker Compose.

Docker and Docker Compose are installed and usable on the current server.

Expected services may include:

```text
backend
frontend
nginx
```

SQLite can be stored in a mounted volume or backend data directory.

Nginx should act as the public reverse proxy.

Typical routing:

```text
/              -> frontend
/api/*         -> backend
/health        -> backend or nginx health route
```

Before changing Docker-related files:

1. Inspect the current Dockerfile and `docker-compose.yml`.
2. Preserve existing working behavior.
3. Avoid adding unnecessary services.
4. Keep build time reasonable.
5. Verify deployment after changes.

If Docker files do not exist yet, create the smallest deployable Compose setup that matches the chosen MVP instead of copying unused boilerplate.

Do not assume local-only behavior is sufficient.

The final app must work through the public URL.

---

## 17. Nginx Rules

Nginx is used as the reverse proxy.

Current server baseline:

```text
Nginx is installed and port 80 is already listening.
/etc/nginx/sites-available/aiic-project exists and proxies / to http://127.0.0.1:8000.
The default Nginx site may still be enabled and can affect what port 80 returns.
```

Before deployment, inspect the active site configuration instead of assuming a blank Nginx setup:

```bash
ls -la /etc/nginx/sites-enabled
sudo nginx -t
curl -I http://127.0.0.1
```

Recommended responsibilities:

- Route frontend traffic.
- Route `/api/` traffic to backend.
- Optionally route `/health` to backend.
- Set reasonable upload limits if file upload is used.
- Preserve headers needed by backend.
- Avoid exposing internal service ports unnecessarily.

Do not make Nginx configuration overly complex.

If Nginx changes, verify:

```bash
docker compose config
docker compose up -d --build
sudo nginx -t
sudo systemctl reload nginx
curl -f http://127.0.0.1/health
```

If `aiic-project` should take over port 80 and the default site conflicts, disable the default site intentionally:

```bash
sudo unlink /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

If the public app is served on port 80, ensure the public URL is tested from outside the container network.

---

## 18. Git Workflow

Before making non-trivial changes:

```bash
git status
```

After making changes:

```bash
git diff
```

Recommended commit strategy:

- Commit after every meaningful milestone.
- Keep commits small and understandable.
- Do not batch everything into one final commit.
- Do not commit generated junk, cache files, `.env`, `.venv`, `node_modules`, or database files.

Suggested commit messages:

```text
init: setup AIIC project structure
docs: add Codex development guidelines
feat: add FastAPI backend skeleton
feat: add Next.js frontend skeleton
feat: integrate LiteLLM provider router
feat: add SQLite user and conversation models
feat: implement login flow
test: add pytest coverage for auth and chat APIs
chore: add nginx reverse proxy
docs: update deployment instructions
```

Before final submission, verify:

```bash
git status
git log --oneline --decorate -n 10
git ls-files | grep -E '(\.env|\.venv|node_modules|\.sqlite|\.db|__pycache__|\.pyc)' || true
```

---

## 19. Documentation Rules

Documentation is part of the final product.

Keep these files useful and up to date:

```text
README.md
TASKS.md
docs/design.md
docs/demo_script.md
docs/debug.md
docs/api.md
```

README should include:

1. Project overview.
2. Public demo URL.
3. Core features.
4. System architecture.
5. Tech stack.
6. Model and LiteLLM routing design.
7. User/login/database design.
8. How to run locally.
9. How to deploy.
10. Environment variables.
11. Testing.
12. Limitations.
13. Future work.

`docs/design.md` should explain:

- Problem interpretation.
- Target users.
- Product flow.
- Technical choices.
- Why LiteLLM is used.
- Why SQLite is sufficient for this challenge.
- Why the implementation is scoped this way.
- What tradeoffs were made under time constraints.

`docs/demo_script.md` should help record a demo within 3 minutes.

Do not leave documentation inconsistent with the actual app.

---

## 20. Task Planning Workflow

When the official project topic is provided, do not immediately write code.

First, help create or update `TASKS.md`.

The plan should include:

```text
1. Requirement interpretation
2. MVP definition
3. Must-have features
4. Nice-to-have features
5. Backend milestones
6. Frontend milestones
7. Database milestones
8. LLM integration milestones
9. Testing milestones
10. Deployment checklist
11. Demo checklist
12. Risks and fallback plan
```

When scope is unclear, propose a minimal interpretation and mark assumptions explicitly.

Do not ask excessive clarification questions if a reasonable assumption can be made. Make the assumption explicit and proceed with a safe MVP.

---

## 21. Skills Usage Policy

Codex may use installed skills when relevant.

The repository currently includes these local skills under `.agents/skills/`:

```text
frontend-design
interaction-design
session-wrap
web-design-guidelines
```

Use these when they match the task, especially for UI quality, interaction polish, session wrap-up, and web UX review.

Do not assume other specific skills are installed.

Do not mention or rely on unavailable skills.

If a useful skill appears to be available, Codex may use it to assist with:

- Planning.
- Requirement clarification.
- UI review.
- Security review.
- API documentation lookup.
- Browser-based testing.
- Debugging.
- Final review.

Rules:

- Skills should support the project workflow, not override it.
- Skills should not cause large unnecessary rewrites.
- Skills should not introduce unapproved technology changes.
- If a skill conflicts with this `AGENTS.md`, follow this `AGENTS.md`.
- Do not spend excessive time configuring new skills during the challenge.

Recommended workflow alignment:

1. At the start of a task, check whether any installed skill applies before acting.
2. For creative/product/UI work, use brainstorming or relevant design skills before implementation.
3. For multi-step tasks or tasks likely to exceed a few tool calls, use file-backed planning (`TASKS.md`, or `task_plan.md` / `findings.md` / `progress.md` when the planning-with-files workflow is explicitly chosen).
4. For implementation work, write a short plan before editing, then keep changes small and verifiable.
5. For bug fixes, investigate systematically before proposing or applying a fix.
6. For feature or bugfix implementation, prefer test-driven or test-backed changes when practical.
7. Before claiming completion, run the relevant verification commands and report what actually ran.

---

## 22. Audio, Video, and Multimodal Features

Audio/video APIs are optional unless required by the official project topic.

If the project involves speech, prefer a simple pipeline first:

```text
audio upload -> speech-to-text -> LLM -> text response -> optional text-to-speech
```

Do not implement real-time full-duplex voice interaction unless explicitly required.

If browser microphone recording is implemented, remember that many browsers require HTTPS or localhost for microphone access.

If HTTPS is not available, prefer file upload instead of live microphone recording.

Do not spend too much time on advanced audio/video features before the main text-based product flow is stable.

---

## 23. Error Handling Rules

For all external API calls:

- Set reasonable timeouts.
- Catch exceptions.
- Return user-friendly error messages.
- Log useful debug information.
- Do not expose raw secrets, stack traces, or provider internals to users.

For frontend errors:

- Show a clear error state.
- Do not leave the user waiting forever.
- Disable buttons during requests if needed.
- Restore UI state after failures.

For backend errors:

- Use consistent JSON error responses.
- Validate request bodies.
- Avoid leaking internal exception details.
- Log enough information for debugging.

For deployment errors:

- Inspect container logs.
- Check port binding.
- Check environment variables.
- Check Docker build output.
- Check Nginx routing.
- Run health checks.

---

## 24. Performance and Resource Constraints

The cloud server is intended for lightweight web serving and API orchestration.

Assume limited resources. The current inspected server has:

- 2 vCPU.
- About 7.8 GiB RAM and 2.0 GiB swap.
- A 20 GiB root disk with limited free space.
- No local GPU.

Therefore:

- Do not run large local models.
- Do not download huge model weights.
- Do not add heavy background workers unnecessarily.
- Keep Docker images reasonably small.
- Clean build cache if disk is low.
- Prefer external APIs for model inference.
- Avoid expensive API calls in tests.

Useful commands:

```bash
df -h
free -h
docker system df
docker ps
docker compose logs -f
```

---

## 25. Things Codex Must Not Do

Codex must not:

1. Commit `.env` or any secret.
2. Hardcode API keys.
3. Expose backend API keys to frontend JavaScript.
4. Bypass LiteLLM for normal LLM calls without a clear reason.
5. Replace the chosen stack without approval.
6. Remove Next.js and downgrade to static HTML without approval.
7. Remove SQLite/user login functionality without approval.
8. Add PostgreSQL, Redis, Celery, Kubernetes, or other heavy infrastructure without approval.
9. Rewrite the whole project without a clear reason.
10. Add heavy dependencies casually.
11. Remove working endpoints without approval.
12. Ignore deployment requirements.
13. Claim success without running relevant checks.
14. Leave the app broken after changes.
15. Modify server-level security settings unless explicitly requested.
16. Delete deployment scripts, docs, or existing working functionality.
17. Optimize for elegance at the cost of demo reliability.
18. Spend time on speculative features before the MVP works.
19. Call paid external APIs in automated tests.
20. Commit database files, `node_modules`, `.venv`, or cache files.

---

## 26. When to Ask the Human Developer

Ask before doing any of the following:

- Changing the main technology stack.
- Adding a new external service.
- Introducing a different database.
- Changing authentication strategy significantly.
- Changing deployment architecture.
- Removing existing features.
- Making large-scale refactors.
- Using paid APIs in a potentially expensive way.
- Implementing features that may delay the MVP.

Do not ask for confirmation for small, safe, reversible edits.

---

## 27. Before Starting Any Coding Task

For every non-trivial coding task, first provide a short plan:

```text
Plan:
1. Files to inspect
2. Files likely to change
3. Expected behavior after change
4. Verification commands
```

Then proceed with implementation.

For very small edits, the plan can be brief.

---

## 28. Before Declaring a Task Complete

Before saying a task is complete, verify as much as practical.

Recommended checklist:

```text
Backend:
- FastAPI app imports successfully.
- Relevant endpoints work.
- pytest passes or relevant tests pass.
- LLM calls are mocked in tests.

Frontend:
- Next.js builds or runs successfully.
- TypeScript errors are checked if practical.
- Main user flow works in browser.

Deployment:
- Docker Compose builds.
- Nginx routes correctly.
- Public URL works.
- Health endpoint works.

Security:
- No secrets are tracked.
- API keys are not exposed to frontend.
- Database files are not committed.

Documentation:
- README or docs are updated if behavior changed.
```

Preferred commands:

```bash
cd backend && uv run pytest
cd backend && uv run ruff check .
cd frontend && npm run lint
docker compose config
docker compose up -d --build
curl -f http://127.0.0.1/health
```

If some checks cannot be run, state clearly which checks were not run and why.

---

## 29. Final Submission Checklist

Before final submission, help verify:

```text
GitHub:
- Repository is public.
- Latest code is pushed.
- Commit history is meaningful.
- No secrets are committed.
- No database files are committed.
- No node_modules or .venv directories are committed.

Deployment:
- Public URL works.
- Nginx routes frontend and backend correctly.
- /health works.
- Main user flow works.
- Login flow works if enabled.
- Chat/LLM flow works.
- Deployment was completed before the deadline.

Product:
- MVP solves the stated task.
- UI is understandable.
- Errors are handled gracefully.
- Demo flow is stable.
- Product value is clear.

Backend:
- FastAPI APIs are organized.
- LiteLLM is used for model routing.
- SQLite persistence works.
- Authentication works if included.

Frontend:
- Next.js app is usable.
- TypeScript structure is clean.
- Loading and error states are present.

Testing:
- pytest tests are present.
- Core backend behavior is tested.
- External LLM calls are mocked in tests.

Documentation:
- README is accurate.
- Public URL is included.
- Setup instructions are included.
- Environment variables are documented.
- Testing instructions are included.
- Limitations and future work are included.

Demo:
- Demo script is ready.
- Recording is under 3 minutes.
- The product is shown clearly.
- Design decisions are explained.
- Engineering choices are briefly highlighted.
```

---

## 30. Development Mindset

This project should show that the developer can build a real AI web product prototype, not just call an LLM API.

The final result should demonstrate:

```text
modern full-stack ability
LLM provider routing
basic user/account design
database-backed persistence
automated backend tests
public deployment
clear product thinking
stable demo execution
```

A good final result should make reviewers think:

```text
This candidate can understand a vague AI product task,
scope it properly,
build a modern full-stack prototype,
integrate LLM APIs cleanly,
handle persistence and login,
deploy the system reliably,
write tests,
explain the technical choices,
and reflect on limitations.
```
