# ResearchMocker Design Notes

## Product Interpretation

ResearchMocker is a focused AI mock interviewer for CS/AI undergraduate students preparing for research-oriented interviews. The product is intentionally narrow: it helps users practice explaining project and research experience under realistic follow-up pressure.

The goal is not to build a broad interview platform. The goal is to create a complete training loop:

```text
candidate profile -> targeted question -> answer -> structured feedback -> adaptive follow-up -> final report
```

## Target Users

Primary users:

- CS/AI undergraduate students preparing for graduate recommendation interviews.
- Students applying for research internships.
- Students preparing for lab admission or research-oriented postgraduate interviews.

Typical pain points:

- They have project or research experience but cannot explain their contribution clearly.
- They lack experienced seniors or professionals for repeated mock interviews.
- They receive vague advice such as "be clearer" instead of actionable feedback.
- They struggle when interviewers challenge ownership, motivation, metrics, novelty, or technical tradeoffs.

## Product Flow

1. User logs in or uses a test account.
2. User enters self-introduction, project/research experience, target direction, and weak points.
3. System analyzes the profile and starts an interview.
4. AI interviewer asks one targeted question.
5. User answers.
6. System returns structured feedback:
   - strengths
   - weaknesses
   - score
   - actionable advice
7. System asks a follow-up question based on the user's answer.
8. The loop continues for several turns.
9. User finishes and receives a final report.

## Why This Is Not Generic Chat

Plain chat lets the user decide what to ask next. ResearchMocker controls the interview workflow.

Key differences:

- One question at a time.
- Adaptive follow-up questions.
- Explicit evaluation of each answer.
- Project/research deep-dive focus.
- Final report with practice suggestions.
- Stable demo flow for a real target scenario.

## Information Architecture

Recommended left navigation:

```text
Text Interview
Face-to-Face Interview
Settings
```

Text Interview is the MVP and should be fully usable.

Face-to-Face Interview is a reserved experimental page. It can become the visual demo highlight only if the text MVP is already stable.

Settings should show safe product/runtime options. It should not expose provider API keys or raw model IDs to normal users.

## Backend Architecture

FastAPI remains the boundary for all product operations. The browser calls only the backend.

Core backend responsibilities:

- Authentication and sessions.
- Candidate profile and interview session APIs.
- SQLite persistence.
- Prompt loading.
- LiteLLM model calls through OpenRouter.
- Structured response parsing.
- Error handling without leaking provider internals.
- Optional Volcengine integration behind backend endpoints.

Implemented interview API shape:

```text
POST /api/interviews
GET  /api/interviews
GET  /api/interviews/{interview_id}
POST /api/interviews/{interview_id}/answers
POST /api/interviews/{interview_id}/finish
```

The current chat APIs remain for compatibility, but the product-facing workflow is interview-specific.

## Data Model Direction

Reuse the existing user/session foundation.

Interview data should capture:

- Candidate profile.
- Interview type or target direction.
- Interview status.
- Questions.
- User answers.
- Per-turn feedback.
- Final report.
- Timestamps and ownership.

SQLite is sufficient for this challenge-scale deployment and keeps operations simple.

## LLM Routing

Normal users should not choose providers or raw model IDs.

Backend model routing:

- `openrouter/qwen/qwen3.6-plus`
  - candidate profile analysis
  - project/research summary
  - final report
  - deeper reasoning

- `openrouter/qwen/qwen3.6-flash`
  - frequent interview turns
  - answer feedback
  - follow-up question generation
  - fast practice interactions

Both selected models are treated as supporting text, image, and video input based on provider-side confirmation.

## Prompt Design

Prompt files should be split by responsibility:

- Interviewer persona.
- Candidate profile analysis.
- First question generation.
- Follow-up question generation.
- Single-answer feedback.
- Final report generation.

Structured outputs should use JSON-like fields when practical so the backend can render consistent UI sections.

## Face-to-Face Interview Extension

This extension attempts to bridge the gap between text chat and real interview presence.

Target flow:

1. User uploads an interviewer image and reference audio.
2. System generates two short interviewer clips:
   - ready/blinking
   - listening/nodding
3. System uses uploaded audio for voice cloning.
4. User starts a microphone interview.
5. Real-time speech model handles user speech and interviewer response.
6. UI switches among ready, listening, and speaking states.

Provider direction:

- Volcengine end-to-end real-time speech model.
- Volcengine OmniHuman 1.5 digital human fast mode.

Fallback:

- If full integration is not ready, keep the page as a clearly marked experiment.
- If video generation is slow, use pre-generated short clips.
- If real-time voice is risky, demo the text interview MVP and describe this as next-step design.

## Deployment

Current deployment model:

- Docker Compose services for backend and frontend.
- Nginx public reverse proxy.
- `/` routes to frontend.
- `/api/` and `/health` route to backend.
- Public URL: `http://115.190.120.206/`.
- Health URL: `http://115.190.120.206/health`.

Keep deployment simple and stable.

## Tradeoffs

- Text interview is the MVP because it is reliable, fast to test, and demonstrates the core training value.
- Face-to-face mode is a strong demo differentiator, but it is provider-heavy and should not block the core loop.
- SQLite is chosen for challenge reliability, not high-concurrency production use.
- Project-level provider configuration improves user experience by avoiding API-key setup screens.
- Broad interview categories, OAuth, PDF parsing, and complex dashboards are intentionally postponed.
