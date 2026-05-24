# Product Memo Notes

These notes are source material for a 1-2 page product memo.

## 1. Target Users And Core Pain Points

Target users:

- CS/AI undergraduate students preparing for graduate recommendation interviews.
- Students applying for research internships or lab admission interviews.
- Students who have project/research experience but lack realistic interview practice.

Latest positioning:

```text
面向 CS/AI 本科生保研科研面试的项目深挖与审稿人式追问 AI 面试官。
```

English equivalent:

```text
An AI project-deep-dive and reviewer-style mock interviewer for CS/AI undergraduate research interviews.
```

Core pain points:

- They cannot easily find experienced seniors or professionals for repeated mock interviews.
- They often receive broad advice rather than specific, actionable feedback.
- They struggle to explain project ownership, technical decisions, research motivation, and measurable impact.
- They are not used to follow-up pressure when an interviewer challenges vague statements.
- They worry that over-polished but unsupported answers will collapse when teachers ask for details.
- They need help controlling answer length and rhythm for concise 1-2 minute oral responses.
- They want an interviewer who can challenge research logic and method design like a strict examiner or reviewer.
- They want objective feedback, including whether current performance is likely to pass, borderline, or high risk.
- They want the product to remember profile, goals, projects, weaknesses, and previous practice rather than behaving like a stateless one-off chat.

Anonymized user research summary:

- Participants: several CS/AI undergraduate students preparing for graduate recommendation, research internship, or lab/research interviews.
- Data format: quick questionnaire feedback, summarized anonymously.
- Repeated pattern: students are not only afraid of "not knowing"; they are afraid of giving vague, generic, or evidence-free project answers that cannot survive follow-up questions.
- Common pressure points:
  - why this project design was chosen
  - whether other methods were tried
  - whether experiments really prove the claim
  - which part was personally done by the candidate
  - implementation details and failure cases
  - how to answer concisely without sounding scattered
- Product implication: narrow the product from a generic AI interviewer to a project-deep-dive pressure test that catches weak claims and gives concrete rewrite/practice advice.

User Research Response #4:

- Background: CS/AI undergraduate preparing for graduate recommendation or research interviews.
- Main anxiety: very fine-grained project questioning, especially research logic and method design. The user described this as potentially becoming like a rebuttal session where an examiner continuously challenges why a module is designed in a certain way.
- Needed support:
  - question practice for unknown graduate recommendation interview question types
  - project follow-up practice that catches hidden details missed by normal mock interviews
  - expression feedback from an interviewer perspective, because listening to one's own recording is not enough
- Plain ChatGPT limitation:
  - every new session requires re-pasting prompt, resume, and project descriptions
  - it does not remember profile, target scenario, strengths, weaknesses, and previous practice history
  - the user wants a long-term interview coach that gradually understands their needs
- Desired post-interview feedback:
  - overall evaluation first
  - explicit likely pass / borderline / high risk judgment
  - objective language instead of over-comforting
  - language and expression issues
  - next practice focus
  - concrete training plan
- Desired interviewer simulation:
  - graduate recommendation examiner
  - reviewer-like perspective
  - detailed and logical project challenges
  - comparison with related methods
  - clarification of personal contribution
  - judgment of whether the project story is clear and convincing
- Product implication:
  - add reviewer-style/rebuttal-style pressure as a P0.5 mode
  - add objective pass-risk evaluation to the final report
  - include method-comparison and personal-contribution follow-ups
  - treat project storytelling clarity as a first-class feedback dimension
  - keep long-term personalization lightweight in the MVP through saved project card, weakness notes, session history, and previous feedback summary

## 2. Product Design

Core function:

ResearchMocker runs a structured mock interview for research/project deep dives. It should feel closer to a strict but professional teacher-led project defense or reviewer-style rebuttal than a friendly chatbot.

Main loop:

```text
project card -> project deep-dive -> reviewer-style follow-up -> structured feedback -> final training plan
```

Deliberately included:

- Project card/candidate profile input.
- One-question-at-a-time interview flow.
- Adaptive follow-up questions.
- Per-answer feedback.
- Teacher-perspective explanation: why a real interviewer would ask this.
- Answer rhythm and length feedback.
- Standard/sharp interview style.
- Reviewer-style/rebuttal-style follow-up for method design, experimental proof, related-method comparison, and personal contribution.
- Objective final report with pass-risk judgment.
- Lightweight personalization when persistence is available.
- Final report.
- Login and saved interview persistence.

Deliberately omitted or minimized:

- Broad algorithm interview training.
- Complex question bank.
- PDF parsing as a required feature.
- OAuth and email verification.
- Multi-provider API-key configuration for users.
- Full voice/video interview as the required path.
- Big-tech coding judge.
- Large manually curated question bank.
- Advanced analytics dashboard.
- Full long-term memory system as a required MVP feature.
- Semantic resume/project parsing.

Reason:

The narrow project/research interview loop is more valuable and more demoable than a broad but shallow interview platform. User research showed that project-detail pressure, reviewer-style challenges, objective pass-risk feedback, and actionable answer repair are the clearest pain points.

## 3. Iteration Record

Initial baseline:

- Full-stack chat product shell with auth, persistence, attachments, model routing, Docker/Nginx deployment, and tests.

Problem found:

- A generic chat interface is not enough for a mock interviewer product.
- User-facing provider configuration is too technical for the target user.

Direction change:

- Reposition product as ResearchMocker.
- Hide provider complexity from users.
- Add project-deep-dive interview workflow, structured feedback, and final report.
- Add teacher-perspective and rhythm feedback as high-value product signals.
- Reserve face-to-face mode as an optional differentiator.

Latest research-driven scope change:

- Previous framing: AI mock interviewer for research-oriented interviews.
- Updated framing: project-deep-dive and reviewer-style mock interviewer for CS/AI research interviews.
- Reason: questionnaire feedback showed project-detail follow-up is the sharpest and most concrete pain.
- Consequence: prioritize project card, adaptive pressure, evidence checking, method-comparison follow-up, project story clarity, answer rewrite advice, objective pass-risk, and final training plan over broad interview coverage.

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
- Add stronger user memory: target school/type, project summaries, known weaknesses, practice history, and previous feedback summaries.
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
