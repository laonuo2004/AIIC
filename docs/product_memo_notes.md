# Product Memo Notes

These notes are source material for a 1-2 page product memo.

## 1. Target Users And Core Pain Points

Target users:

- CS/AI undergraduate students preparing for graduate recommendation interviews.
- Students applying for research internships or lab admission interviews.
- Students who have project/research experience but lack realistic interview practice.

Core pain points:

- They cannot easily find experienced seniors or professionals for repeated mock interviews.
- They often receive broad advice rather than specific, actionable feedback.
- They struggle to explain project ownership, technical decisions, research motivation, and measurable impact.
- They are not used to follow-up pressure when an interviewer challenges vague statements.

User research to record:

- Interviewed users:
  - Name or anonymized identifier:
  - Background:
  - Interview target:
  - Key quote:
  - Pain point:
- Observed repeated pattern:
- Product implication:

## 2. Product Design

Core function:

ResearchMocker runs a structured mock interview for research/project deep dives.

Main loop:

```text
profile -> targeted question -> answer -> structured feedback -> adaptive follow-up -> final report
```

Deliberately included:

- Candidate profile input.
- One-question-at-a-time interview flow.
- Adaptive follow-up questions.
- Per-answer feedback.
- Final report.
- Login/persistence when practical.

Deliberately omitted or minimized:

- Broad algorithm interview training.
- Complex question bank.
- PDF parsing as a required feature.
- OAuth and email verification.
- Multi-provider API-key configuration for users.
- Full voice/video interview as the required path.

Reason:

The narrow project/research interview loop is more valuable and more demoable than a broad but shallow interview platform.

## 3. Iteration Record

Initial baseline:

- Full-stack chat product shell with auth, persistence, attachments, model routing, Docker/Nginx deployment, and tests.

Problem found:

- A generic chat interface is not enough for a mock interviewer product.
- User-facing provider configuration is too technical for the target user.

Direction change:

- Reposition product as ResearchMocker.
- Hide provider complexity from users.
- Add interview workflow, structured feedback, and final report.
- Reserve face-to-face mode as an optional differentiator.

Reference project:

- `AI-Interviewer` was reviewed as a useful reference for resume/profile-based question generation and interview product framing.
- The implementation should not copy its technical stack or unfinished webcam flow.

Important decisions:

- Use backend-managed OpenRouter Key.
- Route models automatically:
  - Plus for deep analysis/report.
  - Flash for fast interview turns.
- Treat face-to-face mode as an experiment unless P0 is stable.

## 4. Next-Step Design

If given one more week:

- Complete full face-to-face interview mode using Volcengine real-time speech and OmniHuman.
- Add richer interview templates by target lab/research area.
- Add report export.
- Add longitudinal practice history.
- Improve scoring rubric with more calibrated dimensions.
- Add sample interview datasets and anonymized examples.
- Add HTTPS/domain deployment.

## 5. AI Tool Usage

AI tools used:

- Codex for repository exploration, planning, code/documentation edits, and verification.
- ChatGPT or other web AI tools for requirement summarization and product positioning.
- LLM APIs through OpenRouter for product runtime.

How AI was used:

- Requirement interpretation.
- Product scoping.
- UI/flow ideation.
- Backend/frontend implementation support.
- Test and deployment debugging.
- README, memo, and demo script drafting.

Important note:

All AI-generated work should be reviewed and adapted by the developer. Provider secrets and private data must not be pasted into AI tools or committed to Git.
