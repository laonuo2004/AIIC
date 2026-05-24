# ResearchMocker Tasks

## Product Direction

ResearchMocker is an AI project-deep-dive and reviewer-style mock interviewer for CS/AI undergraduate students preparing for research-oriented interviews: graduate recommendation interviews, research internship interviews, lab admission interviews, and project-experience deep dives.

Chinese positioning:

```text
面向 CS/AI 本科生保研科研面试的项目深挖与审稿人式追问 AI 面试官。
```

Value proposition:

```text
Not a friendly chatbot, but a realistic research interview pressure test that catches vague answers, asks follow-up questions, and gives actionable feedback.
```

The product should not feel like a generic chat window. The core loop is:

1. User logs in or uses a test account.
2. User enters a project card: self-introduction, project/research experience, target direction, weak points, personal contribution, key methods, experiments/results, and failure cases when available.
3. System starts a mock interview.
4. AI interviewer asks one targeted project-deep-dive or reviewer-style follow-up question at a time.
5. User answers.
6. System gives structured feedback: strengths, weaknesses, score, teacher perspective, rhythm/length feedback, and actionable advice.
7. System asks an adaptive follow-up question.
8. User finishes and receives a final review report with objective pass-risk judgment and a training plan.

## User Research Findings

Recent lightweight questionnaire feedback from several CS/AI undergraduates preparing for recommendation/research interviews changed the product focus.

Key findings:

- Students are most worried about teachers continuously digging into project details:
  - why this design was chosen
  - whether alternatives were tried
  - whether experiments really prove the claim
  - what was personally done by the candidate
  - implementation details and failure cases
- Students do not only fear not knowing the answer. They fear giving vague, generic, over-polished, or non-evidence-backed answers that cannot survive follow-up questions.
- Directly using ChatGPT is often too friendly, too generic, and too dependent on the user's prompting ability.
- Students want feedback that says exactly what is weak, what evidence is missing, why a real teacher would follow up, how to rewrite the answer, and what to practice next.
- Real interviews require rhythm control: concise 1-2 minute answers are usually better than long scattered responses.
- Additional response #4 emphasized that project questioning can feel like a rebuttal session, especially around research logic, method design, module necessity, and reviewer-like challenges.
- Users want support beyond one-off Q&A: question practice, hidden-detail follow-up practice, interviewer-perspective expression feedback, and lightweight long-term personalization.
- Objective feedback matters: the product should be able to say likely pass, borderline, or high risk instead of over-comforting the user.
- Method-comparison questions and project storytelling clarity are part of interview success, not optional polish.

Product implication:

- Narrow from a generic AI mock interviewer to a project-deep-dive research interviewer.
- Prioritize pressure testing project claims, adaptive follow-up, and actionable feedback.
- Add reviewer-style challenges where they help expose weak method design, experiment proof, related-method comparison, and personal contribution.
- Treat long-term personalization as valuable, but implement only low-cost memory first: saved project card, weakness notes, session history, and previous feedback summary.
- Treat voice/video as optional demo expansion, not the reliable MVP path.

## Current Baseline To Reuse

Already available:

- FastAPI backend.
- Next.js + TypeScript frontend.
- SQLite persistence.
- HttpOnly cookie auth.
- Streaming chat through LiteLLM/OpenRouter.
- Text, image, and PDF attachment support.
- Interview creation can bind uploaded attachments.
- Text attachments are injected into prompts; image attachments and rendered PDF pages are sent as multimodal image inputs.
- JSON repair and user-friendly fallback handling for LLM output.
- Theme support and settings page.
- Docker Compose and Nginx deployment.
- Backend pytest coverage and frontend checks.
- Public deployment at `http://115.190.120.206/`.

The baseline must be adapted, not recreated.

## P0: Must Finish

- Reposition all user-facing copy from generic chat to ResearchMocker.
- Replace the provider configuration product flow with a backend-managed OpenRouter setup.
- Keep normal users away from API keys, provider names, and raw model IDs.
- Add project card input:
  - self-introduction
  - project/research experience
  - target direction
  - weak points
  - personal contribution
  - key methods/design choices
  - experiments/results
  - failure cases or limitations
  - interview type or scenario
- Build the text interview workflow:
  - start interview
  - show one project-based question at a time
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
  - `openrouter/qwen/qwen3.6-plus` for first questions, follow-ups, feedback, and final report
- Persist interview records in SQLite or clearly display them during the session if time is tight.
- Keep deployment working through Docker Compose and Nginx.
- Prepare a test account if login remains required.
- Public deployment must work at the demo URL.

Acceptance criteria:

- A reviewer can open the public URL and start a project-deep-dive mock interview.
- The first AI question references the submitted project card rather than asking a generic interview question.
- The user can upload supporting project material, including text, image, or PDF files, and bind it to an interview.
- After one answer, the UI shows structured feedback and an adaptive follow-up.
- The user can finish the interview and see a final review report.
- The final report includes an objective pass-risk judgment: likely pass, borderline, or high risk.
- Provider keys are not requested from the normal user and are not exposed to frontend JavaScript.
- `/health` works publicly after deployment.

Current completion snapshot:

- Text interview MVP, interview persistence, attachment binding, structured feedback, adaptive follow-up, and final report flow are implemented.
- Frontend validation accepts short manual profile text when uploaded files provide the main project context.
- Backend schema validation is aligned with that behavior to avoid false `422` errors.
- QA feedback layout has been manually checked by the developer after UI fixes.
- Docker build mirrors and server disk capacity have been adjusted for reliable rebuilds.
- Current low-risk improvement direction: preserve the existing feedback/report schema while making prompts, UI labels, and demo copy emphasize project anti-follow-up training, missing evidence, personal contribution clarity, rewrite direction, vulnerable follow-up points, and a 24-hour practice plan.

## P0.5: High-Value And Low-Cost

- Add standard/sharp interview style:
  - standard: realistic but balanced
  - sharp: more direct pressure on vague claims and unsupported evidence
- Add reviewer-style/rebuttal-style questioning mode:
  - challenge method design and research logic
  - ask why a module is necessary
  - compare with related or alternative methods
  - question whether experiments prove the claim
  - clarify the candidate's personal contribution
  - keep each question realistic: one sentence preferred, at most two sentences, one thing at a time
- Add teacher-perspective explanation in feedback:
  - why a real teacher would ask this
  - what the answer makes the teacher doubt
  - which evidence would reduce that doubt
- Add project story clarity feedback:
  - whether the project motivation, method, result, and contribution form a convincing story
  - which exact expression is weak
  - which answer does not fit the project design
  - what should be expanded or explained more clearly
- Add objective pass-risk evaluation in the final report:
  - likely pass
  - borderline
  - high risk
  - top 3 reasons for the judgment
  - most vulnerable follow-up points
  - next 24-hour training plan
- Add answer rhythm/length feedback:
  - too short
  - too long
  - scattered
  - suitable for a concise 1-2 minute oral answer
- Add a preset demo sample:
  - CS/AI undergraduate candidate
  - concrete project card
  - target research direction
  - known weak point
- Add robust LLM output handling:
  - JSON parsing
  - fallback when a field is missing
  - user-friendly message when model output cannot be parsed
- Save project profile if existing persistence makes it low-cost.
- Add or update pytest coverage for interview API behavior with mocked LLM calls.
- Update README, Product Memo notes, iteration log, and demo script.

Current P0.5 completion snapshot:

- Reviewer-style short-question prompt constraints are documented and tested.
- LLM JSON repair/fallback behavior is implemented for interview outputs.
- PDF page-limit fallback returns a clear product error.
- Preset/manual demo flow now supports "see uploaded files + short profile" as a valid input path.

## P1: If Time Allows

- Simple login/test account flow.
- Saved interview history list and detail view.
- SQLite persistence polish for interview sessions and turns.
- Basic pytest coverage for auth, ownership, interview creation, answer submission, and final report.
- README polish.
- Product Memo notes ready for final writing.
- User profile memory:
  - target school or target interview type
  - project summaries
  - known weaknesses
  - practice history
  - previous feedback summary
- Question bank or practice coverage map for common graduate recommendation interview question types.
- Lightweight progress tracking across sessions.
- Better final report sections:
  - overall score
  - pass-risk judgment
  - top 3 reasons for the judgment
  - technical depth
  - project ownership
  - research thinking
  - communication clarity
  - project story clarity
  - personal contribution clarity
  - method-comparison weakness if applicable
  - weakest answers
  - next 24-hour training plan
- Add browser-level screenshot regression for interview feedback layout.
- Add an exportable final report.
- Keep a reserved Face-to-Face Interview page between Text Interview and Settings.
- On the face-to-face page, provide the product shell for:
  - interviewer image upload
  - reference audio upload
  - generated ready/listening video previews
  - microphone-based interview start state
- Build a backend adapter spike for Volcengine only if P0 is stable.
- Document provider risks and fallback behavior.

Current face-to-face experiment snapshot:

- Backend face APIs are implemented for authenticated asset upload, public provider-readable media tokens, voice clone preparation, optional OmniHuman video job submission, session creation, and a browser-to-backend realtime WebSocket contract.
- Frontend Face-to-Face page now supports interviewer image/reference audio setup, voice/video preparation states, push-to-talk microphone streaming, provider status display, transcript/assistant text panes, cloned response audio playback, and ready/listening/speaking/error visual states.
- Volcengine realtime video is not represented as true streaming video. The implemented realtime path is speech/audio; OmniHuman remains async best-effort visual enhancement.
- Provider credentials remain backend-only `.env` values. Normal users do not configure raw model IDs or API keys.
- Public HTTP microphone access may be browser-limited outside localhost; HTTPS or controlled browser permissions may be needed for a full public smoke session.

## P2: Explicitly Not For Today Unless Everything Else Is Done

- Full production Volcengine end-to-end real-time speech binary bridge.
- Fully verified voice cloning from uploaded interviewer reference audio against a real provider account.
- Fully verified OmniHuman 1.5 fast-mode video generation from interviewer image.
- Seamless switching among provider-generated ready, listening, and speaking video states.
- Real-time voice interview validated on the public deployment.
- Video interview.
- Full long-term memory system.
- Semantic resume/project parsing.
- Semantic resume/project parsing.
- Big-tech coding judge.
- Large manually curated question bank.
- Multi-user admin system.
- Advanced analytics dashboard.
- Complicated multi-agent architecture.
- Exportable final report.
- More interview templates for different labs or research areas.
- Lightweight analytics for common weaknesses across sessions.

## Cut: Deliberately Not Doing Now

- Voice/video as the only working product path.
- Broad big-tech algorithm interview platform.
- Large question bank.
- Full resume/PDF semantic parsing as a required feature.
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
- Identify the smallest code path from current baseline to project-deep-dive interview MVP.

### Hours 2-5

- Implement backend interview schemas, prompts, model routing, and mocked tests.
- Keep the existing auth/session/database foundation.
- Prefer one clean interview endpoint set over scattered chat hacks.
- Make model outputs renderable as structured feedback and final reports.
- Include pass-risk and vulnerable follow-up points in the final report schema if low-cost.

### Hours 6-9

- Implement frontend text interview flow:
  - project card/profile form
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
- Add preset project card for demo reliability.

### Hours 13-14

- Run backend tests and frontend checks.
- Deploy with Docker Compose.
- Verify public URL and `/health`.
- Do one real OpenRouter smoke test.
- Verify the first question, feedback, follow-up, and final report are product-specific.
- Verify upload PDF/image -> start interview -> answer -> feedback -> finish report on the public URL before recording.

### Hours 15-16

- Record demo video.
- Finalize Product Memo.
- Push final commits.
- Prepare submission email.
- Avoid post-deadline deployments.

## Demo-Oriented Checklist

- Use a preset project card instead of typing long background live.
- Show a project-specific question in the first 30 seconds.
- Give one deliberately vague answer so the product can expose missing evidence.
- Show teacher-perspective feedback: why a real interviewer would follow up.
- Show reviewer-style pressure: why the method design or experiment claim may not convince an examiner.
- Show rhythm/length feedback.
- Show objective pass-risk or "borderline/high risk" language in the final report if the answer is weak.
- Show an adaptive follow-up question that presses the weak point.
- Finish with a final report and next practice plan.
- Mention the stack briefly only after the product loop is clear.

## Product Memo Checklist

- Target users: CS/AI undergraduates preparing for research/recommendation interviews.
- User research: anonymized questionnaire responses from several students.
- Core pain point: project claims fail under continuous teacher follow-up.
- Response #4 insight: some users specifically want reviewer/rebuttal-style pressure and long-term personalization.
- Product design: project card, one-question interview flow, structured feedback, final report.
- Omitted features: voice/video as required path, semantic resume/PDF parsing, coding judge, large question bank, complex dashboard.
- Iteration record: generic chat baseline -> ResearchMocker -> project-deep-dive pressure test.
- Next week plan: face-to-face mode, richer rubrics, exportable reports, interview templates, stronger user memory.
- AI tool usage: Codex, ChatGPT/web AI tools, OpenRouter runtime models.

## Deployment Checklist

- `.env` exists on server and contains server-side OpenRouter credentials.
- Normal UI does not ask reviewers to enter API keys.
- `docker compose config --quiet --no-env-resolution` passes.
- `docker compose up -d --build` succeeds if deployment changes are made.
- `curl -f http://127.0.0.1/health` passes.
- `curl -f http://115.190.120.206/health` passes.
- Public URL loads the frontend.
- Test account or quick registration path is available.
- No deployment is needed after the deadline.

## Final Submission Checklist

- Public product URL works.
- GitHub repository is public.
- Latest code is pushed with meaningful commits.
- README includes overview, run instructions, tech stack, limitations, and demo/test account notes.
- Product Memo is 1-2 pages and reflects user research.
- Demo video is under 3 minutes.
- Server remains accessible for reviewers.
- Required reviewer SSH keys are installed on the server.
- No `.env`, secrets, database files, `.venv`, `.next`, or `node_modules` are committed.

## LLM Strategy

Normal users should not see provider details.

Backend routing:

- Deep model: `openrouter/qwen/qwen3.6-plus`
- Fast model: `openrouter/qwen/qwen3.6-plus`
- Feedback model: `openrouter/qwen/qwen3.6-plus`

The selected interview model is treated as supporting text, image, and video input based on provider-side confirmation.

Use cases:

- Candidate profile and project understanding: plus model.
- First question, follow-up, feedback, and final report: plus model for consistent reviewer-style quality.

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
- **Large PDF context**: keep the 12-page default limit and prefer concise demo materials.
- **Frontend layout regressions**: manually test the feedback cards after CSS changes; add screenshots if time allows.
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

Latest known verification:

- `cd backend && uv run pytest`: 34 passed
- `cd backend && uv run ruff check .`: passed
- `cd frontend && pnpm lint`: passed
- `cd frontend && pnpm build`: passed
- `docker compose config --quiet --no-env-resolution`: passed
- `docker compose up -d --build`: succeeded
- `curl -f http://127.0.0.1:8000/health`: passed
- `curl -f http://127.0.0.1:3000`: passed
- `curl -f http://115.190.120.206/health`: passed
- Local API smoke with short profile plus attachments creating an interview: `200 OK`
- Human public demo check: developer reported no blocking issue after manual testing

Remaining verification gap:

- No automated real-browser screenshot regression for the QA feedback layout.
- No separately recorded full public run log for upload PDF/image -> multi-turn interview -> final report.

## Demo Checklist

- Open public URL.
- Log in with a test account or register quickly.
- Show the first screen as ResearchMocker, not a generic chat app.
- Load or enter a concrete project card.
- Upload supporting project material, preferably one PDF and one image.
- Start text interview.
- Show the AI asking a targeted project-deep-dive question.
- Answer vaguely once so the product can expose missing evidence or unclear ownership.
- Show structured feedback, teacher perspective, rhythm feedback, and an adaptive follow-up.
- Finish interview and show final report.
- If face-to-face page is ready, show it briefly as the bridge from text practice to realistic interview simulation.
- End with engineering summary: FastAPI, Next.js, SQLite, LiteLLM/OpenRouter, Docker/Nginx, tests.
# 2026-05-24 Chinese Prompt Stabilization

- Shifted ResearchMocker prompt behavior toward concise Chinese inputs and outputs for domestic CS/AI interview users and Qwen model stability.
- Simplified demo project-card materials and demo script so the first 30 seconds can show project deep-dive value with shorter prompts and smaller context.
- Kept the existing JSON schema and text interview workflow unchanged.
