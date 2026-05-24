# ResearchMocker Design Notes

## Product Interpretation

ResearchMocker is a focused AI project-deep-dive and reviewer-style mock interviewer for CS/AI undergraduate students preparing for research-oriented interviews. The product is intentionally narrow: it helps users practice defending project and research experience under realistic teacher-style and reviewer-style follow-up pressure.

The goal is not to build a broad interview platform. The goal is to create a complete training loop:

```text
project card -> project deep-dive -> reviewer-style follow-up -> structured feedback -> final training plan
```

Value proposition:

```text
Not a friendly chatbot, but a realistic research interview pressure test that catches vague answers, asks follow-up questions, and gives actionable feedback.
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
- They are afraid that polished but unsupported answers will fail when teachers ask for project details.
- They need practice keeping answers concise, structured, and suitable for a 1-2 minute oral response.
- They want strict but professional reviewer-like challenges on research logic, method design, experiment proof, and related-method comparison.
- They want objective final feedback that can say likely pass, borderline, or high risk.
- They want a long-term coach that remembers profile, target scenario, project summaries, weaknesses, and practice history.

Recent questionnaire findings:

- Project-detail follow-up is the highest-pressure scenario.
- Teachers often ask why a design was chosen, whether alternatives were tried, whether experiments prove the claim, and what the candidate personally contributed.
- Plain ChatGPT practice is too friendly and too generic unless the user already knows how to prompt it.
- Actionable feedback should explain what evidence is missing, why a real teacher would follow up, and how the answer can be rewritten.
- A fourth anonymized response specifically described project questioning as possibly becoming like a rebuttal session.
- Method-comparison questions and project storytelling clarity should be treated as interview success factors.
- Long-term personalization is valuable, but the MVP should only implement low-cost memory through saved project cards, weakness notes, session history, and previous feedback summaries.

## Product Flow

1. User logs in or uses a test account.
2. User enters a project card:
   - self-introduction
   - target direction
   - project/research background
   - personal contribution
   - key methods/design choices
   - experiments/results
   - failure cases or limitations
   - weak points
3. System analyzes the profile and starts an interview.
4. AI interviewer asks one targeted question.
5. User answers.
6. System returns structured feedback:
   - strengths
   - weaknesses
   - score
   - teacher perspective: why a real teacher would ask this
   - answer rhythm/length assessment
   - project story clarity
   - personal contribution clarity
   - actionable advice
7. System asks a follow-up question based on the user's answer, using reviewer-style pressure when claims are vague or unsupported.
8. The loop continues for several turns.
9. User finishes and receives a final report with objective pass-risk judgment and a next 24-hour training plan.

## Why This Is Not Generic Chat

Plain chat lets the user decide what to ask next. ResearchMocker controls the interview workflow.

Key differences:

- One question at a time.
- Adaptive follow-up questions.
- Explicit evaluation of each answer.
- Project/research deep-dive focus.
- Teacher-style pressure on vague claims, missing evidence, and unclear ownership.
- Reviewer-style pressure on method design, alternative methods, experiment proof, confounders, and project storytelling.
- Objective pass-risk judgment instead of automatic encouragement.
- Lightweight reuse of saved profile/project context when available.
- Answer rhythm and length feedback.
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
- Protected attachment upload and download.
- Attachment-to-interview binding.
- Text/PDF context extraction and multimodal image payload construction.
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

- Project card and candidate profile.
- Bound supporting attachments.
- Interview type or target direction.
- Known weaknesses and target scenario.
- Interview status.
- Questions.
- User answers.
- Per-turn feedback.
- Final report.
- Previous feedback summary when low-cost.
- Timestamps and ownership.

SQLite is sufficient for this challenge-scale deployment and keeps operations simple.

## Attachment Context Design

Supporting files are part of the interview setup, not a separate document-management product.

Implemented behavior:

- Text attachments are wrapped as XML/CDATA-like candidate context before being added to the prompt.
- Image attachments are sent as OpenRouter-compatible multimodal `image_url` content.
- PDF attachments are accepted as protected uploads, text is extracted from pages when available, and pages are rendered as image inputs.
- PDF context is limited by `MAX_PDF_PAGES_PER_ATTACHMENT`, default `12`, to keep demo requests bounded.
- Interview detail responses include bound attachment metadata so the UI can show what evidence the session used.

Design intent:

- Let candidates provide project reports, paper drafts, README notes, screenshots, or result figures without requiring a polished resume parser.
- Keep the product centered on interview pressure and feedback rather than file management.
- Treat full semantic resume/PDF parsing as future work.

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
- Standard/sharp interview style.
- Reviewer-style/rebuttal-style questioning.
- Project card analysis.
- Candidate profile analysis.
- First question generation.
- Follow-up question generation.
- Single-answer feedback.
- Teacher-perspective explanation.
- Answer rhythm and length assessment.
- Objective pass-risk assessment.
- Project story clarity assessment.
- Personal contribution clarity assessment.
- Method-comparison weakness detection.
- Final report generation.

Structured outputs should use JSON-like fields when practical so the backend can render consistent UI sections.

Recommended feedback shape:

```text
strengths
weaknesses
teacher_perspective
missing_evidence
rhythm_feedback
rewrite_suggestion
score
next_question
```

Recommended final report shape:

```text
overall_score
pass_risk: likely_pass | borderline | high_risk
top_3_reasons
most_vulnerable_follow_up_points
project_story_clarity
personal_contribution_clarity
method_comparison_weakness
language_and_expression_issues
next_24_hour_training_plan
```

Interviewer prompt guidance:

- Ask reviewer-style questions when the answer makes unproven claims.
- Challenge vague statements like "our module improves performance", "we designed a better method", "we achieved good results", or "I was responsible for the model".
- Ask why a module is necessary, what alternatives were considered, how experiments prove the claim, whether gains may come from confounders, what the candidate personally implemented, and whether the project story is convincing.
- Keep questions short and realistic for live interviews: one sentence preferred, two sentences maximum, one issue per question.
- Keep the tone strict but professional. The system may say an answer is high risk, but must not insult the user.

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
- Broad interview categories, OAuth, full semantic resume/PDF parsing, and complex dashboards are intentionally postponed.
- Bounded PDF context extraction is implemented for the demo flow.
