# ResearchMocker

ResearchMocker is an AI project-deep-dive and reviewer-style mock interviewer for CS/AI undergraduate students preparing for research-oriented interviews. It focuses on the hardest part of graduate recommendation, research internship, and lab admission interviews: defending a real project under continuous follow-up questions.

Public demo: http://115.190.120.206/

Health check: http://115.190.120.206/health

## Release

- Version: v0.3 (2026-05-24)
- Release notes: docs/iteration_log.md

## Product Positioning

Many students preparing for graduate recommendation interviews, research internships, or lab admission interviews have project experience but lack realistic practice and actionable feedback. Recent lightweight user research showed that students are especially worried about vague project answers being challenged by teachers or reviewers: why this design was chosen, whether alternatives were tried, whether experiments prove the claim, what part was personally done by the candidate, and whether the project story is convincing.

ResearchMocker aims to close that gap with a narrow workflow:

1. Enter a project card: candidate profile, target direction, project/research experience, personal contribution, evidence, and weak points.
2. Start a mock interview.
3. Answer one project-deep-dive question at a time.
4. Receive structured feedback after each answer, including teacher-perspective explanation and answer rhythm feedback.
5. Continue with adaptive follow-up questions that press on vague or unsupported claims, including reviewer-style method and experiment challenges.
6. Finish with a final review report, objective pass-risk judgment, and next-step practice plan.

The product should be better than plain ChatGPT because it enforces an interview workflow, focuses on project/research depth, exposes unsupported claims, controls interview rhythm, reuses saved context when available, and turns each answer into concrete feedback.

Value proposition:

```text
Not a friendly chatbot, but a realistic research interview pressure test that catches vague answers, asks follow-up questions, and gives actionable feedback.
```

## Current Implementation Status

Implemented:

- FastAPI backend with health, auth, interview, conversation, provider, attachment, and streaming chat APIs.
- User registration/login with HttpOnly session cookies and hashed passwords.
- SQLite persistence for users, sessions, interview sessions, interview turns, conversations, messages, provider records, model cache, and attachments.
- LiteLLM/OpenRouter calls routed through the backend with project-level `.env` credentials.
- Interview-context attachments:
  - text files are injected into prompts as protected XML/CDATA context
  - image files are sent to OpenRouter-compatible multimodal models as `image_url` inputs
  - PDF files are accepted, text is extracted when available, and pages are rendered as image inputs with a page limit
- Next.js + TypeScript frontend with a ResearchMocker text interview workflow, saved interview history, final report view, safe settings page, and experimental face-to-face placeholder.
- Docker Compose backend/frontend services behind Nginx.
- Backend pytest coverage and frontend lint/build checks.

Still planned:

- Real Volcengine face-to-face speech/video integration.
- Exportable final report.
- Stronger long-term personalization across practice sessions.

## Core Features

MVP:

- Text-based mock interview for research/project deep dives.
- Project card setup with self-introduction, project experience, target direction, personal contribution, key methods, experiments/results, failure cases, weak points, and optional supporting files.
- One-question-at-a-time interview flow.
- Adaptive follow-up based on the candidate's previous answer.
- Structured feedback with strengths, weaknesses, score, teacher/reviewer perspective, answer rhythm/length feedback, and actionable advice.
- Final report covering technical depth, project ownership, research thinking, communication clarity, pass-risk judgment, vulnerable follow-up points, and next practice steps.
- Login and saved interview records.

Optional differentiator:

- Face-to-face interview mode using an uploaded interviewer image and audio sample.
- Volcengine real-time speech model for speech interaction.
- Volcengine OmniHuman 1.5 fast mode for ready/listening/speaking digital human video states.

The optional face-to-face mode must not block the text MVP.

## Tech Stack

- Backend: Python 3.12, FastAPI, SQLAlchemy, SQLite, LiteLLM, httpx, pytest, uv.
- Frontend: TypeScript, Next.js, React, pnpm, standard CSS.
- Deployment: Docker Compose and Nginx reverse proxy on Ubuntu.
- LLM routing: OpenRouter through LiteLLM.
- Optional realtime/digital human provider: Volcengine APIs.

## Model Strategy

Normal users should not need to understand providers, API keys, or raw model IDs.

Backend routing:

Current MVP uses `openrouter/qwen/qwen3.6-plus` for first questions, adaptive
follow-ups, single-answer feedback, and final reports. Keeping the interview
workflow on one stronger model makes reviewer-style pressure and pass-risk
judgment more consistent during the demo.

The selected OpenRouter interview model is treated as supporting text, image, and video input based on provider-side confirmation.

## Environment

Create `.env` from `.env.example` and replace placeholder secrets.

Current baseline values:

```env
APP_ENV=development
DATABASE_URL=sqlite:///./data/app.sqlite3
SECRET_KEY=replace_with_a_random_secret_key
LITELLM_MODEL=openrouter/qwen/qwen3.6-flash
LITELLM_FALLBACK_MODEL=openrouter/qwen/qwen3.6-flash
INTERVIEW_DEEP_MODEL=openrouter/qwen/qwen3.6-plus
INTERVIEW_FAST_MODEL=openrouter/qwen/qwen3.6-plus
INTERVIEW_FEEDBACK_MODEL=openrouter/qwen/qwen3.6-plus
OPENROUTER_API_KEY=your_openrouter_api_key_here
UPLOAD_DIR=./data/uploads
MAX_UPLOAD_BYTES=5242880
MAX_ATTACHMENTS_PER_MESSAGE=4
MAX_PDF_PAGES_PER_ATTACHMENT=12
```

Production should use a server-side OpenRouter key. Do not expose provider keys in frontend code or commit them to Git.

Proxy variables supported by the backend environment:

```env
HTTP_PROXY=
HTTPS_PROXY=
NO_PROXY=127.0.0.1,localhost
OPENROUTER_HTTP_PROXY=
```

Potential Volcengine variables will be documented when that integration begins. Do not add real provider credentials to the repository.

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

For local cross-origin frontend calls:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
FRONTEND_ORIGIN=http://localhost:3000
```

## API Summary

Current APIs:

- `GET /health`
- `GET /api/status`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `POST /api/interviews`
- `GET /api/interviews`
- `GET /api/interviews/{interview_id}`
- `POST /api/interviews/{interview_id}/answers`
- `POST /api/interviews/{interview_id}/finish`
- `POST /api/chat/stream`
- `GET /api/conversations`
- `GET /api/conversations/{conversation_id}`
- `POST /api/attachments`
- `GET /api/attachments/{id}`

The generic chat/provider APIs remain for compatibility, but the product UI uses the interview APIs.

## Uploads

The current backend supports protected attachment uploads. Attachments are not served from a public static directory.

- Upload endpoint: `POST /api/attachments`
- Download/view endpoint: `GET /api/attachments/{id}`
- Storage directory: `UPLOAD_DIR`, default `./data/uploads`
- Single-file limit: `MAX_UPLOAD_BYTES`, default `5242880` bytes, 5MB
- Per-message limit: `MAX_ATTACHMENTS_PER_MESSAGE`, default `4`
- PDF page limit for interview context: `MAX_PDF_PAGES_PER_ATTACHMENT`, default `12`
- Text extensions: `.txt`, `.md`, `.json`, `.csv`, `.log`
- Image MIME types: `image/png`, `image/jpeg`, `image/webp`, `image/gif`
- PDF MIME type: `application/pdf`

For the interview product, attachments are available when creating an interview. They are useful for project notes, papers, reports, screenshots, experiment tables, and other supporting material. Text/PDF content is added to the LLM context, while images and rendered PDF pages are passed as multimodal image inputs.

## Docker Compose

```bash
cp .env.example .env
docker compose config
docker compose up -d --build
curl -f http://127.0.0.1:8000/health
```

The backend stores SQLite data in the `backend_data` Docker volume. Uploaded files should stay outside Git tracking.

The Compose file binds backend and frontend ports to `127.0.0.1` so Nginx is the public entrypoint. For public deployment:

```env
APP_ENV=production
FRONTEND_ORIGIN=http://115.190.120.206
NEXT_PUBLIC_API_BASE_URL=
```

## Nginx

Use the Nginx config under `infra/nginx/` as the current server config. It routes:

- `/` to `http://127.0.0.1:3000`
- `/api/*` to `http://127.0.0.1:8000/api/*`
- `/health` to `http://127.0.0.1:8000/health`

After installing or changing the site:

```bash
sudo nginx -t
sudo systemctl reload nginx
curl -f http://115.190.120.206/health
```

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

Compose validation:

```bash
docker compose config --quiet --no-env-resolution
```

## CI, Releases, and Images

Daily development happens on `dev`. Before merging into `main`, open a pull request and wait for the `backend`, `frontend`, and `compose` CI jobs to pass.

GitHub Container Registry image publishing is configured for release tags, published GitHub Releases, and manual workflow runs. The current server deployment can continue using local `docker compose up -d --build`; registry images are release artifacts and do not trigger automatic production deployment.

## Demo Flow

Target 3-minute demo:

1. Open the public URL.
2. Log in with a test account or register quickly.
3. Enter a candidate profile and project summary.
4. Upload supporting material such as a project PDF/report and an architecture or result image.
5. Start a mock interview.
6. Show the AI asking a targeted project/research question based on the profile and uploaded context.
7. Give a vague answer so the product exposes missing evidence or unclear personal contribution.
8. Show structured feedback, teacher-perspective explanation, rhythm feedback, and an adaptive follow-up question.
9. Finish and show the final review report.
10. Briefly show engineering stack and deployment.

Recommended local demo materials are already in `demo/`:

- `Self-introduction.md`
- `Project or research experience.md`
- `Target direction.md`
- `Weak points.md`
- `1-个人简历.pdf`
- `2-个人自述.pdf`
- `3-成绩证明(含GPA).pdf`
- `4-外语水平证明.pdf`
- `Interviewer.jpg` and `20260518_210026.mp3` for the optional face-to-face experiment

Use the Markdown files to fill the lightweight project card, then attach one or
two small PDFs/images as supporting context. Do not put private credentials or
provider settings into demo inputs.

If the face-to-face page is ready, show it as the bridge from text practice to realistic interview simulation. If it is not ready, do not present it as implemented.

## Limitations

- The current public deployment uses HTTP, not HTTPS.
- Auth is intentionally lightweight.
- SQLite is chosen for demo reliability and simple deployment, not high-concurrency production traffic.
- The existing codebase still contains generic chat/provider baseline pieces that are being adapted into an interview product.
- PDF multimodal context increases request size, so PDF pages are limited for demo reliability.
- The face-to-face interview mode depends on external Volcengine APIs and may remain an experimental extension if time is tight.
- Automated tests must mock external providers; real provider smoke tests should be manual and controlled.

## Future Work

- Add browser-level regression screenshots for the core interview layout.
- Run and document a full public demo regression: upload PDF/image, complete multi-turn interview, and finish the report.
- Add a polished test account/demo dataset.
- Integrate Volcengine real-time speech and OmniHuman 1.5 for face-to-face interview mode.
- Add HTTPS/domain deployment if time allows.
- Expand interview templates by research direction.
