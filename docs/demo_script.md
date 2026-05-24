# ResearchMocker Demo Script

Target length: under 3 minutes.

## Opening: First 30 Seconds

Show the strongest product moment immediately.

1. Open `http://115.190.120.206/`.
2. Log in with a prepared test account or register quickly.
3. Start from a pre-filled project card:
   - CS/AI undergraduate.
   - One concrete research or project experience.
   - Target direction.
   - Personal contribution.
   - Experiment/result claim.
   - Weak point, such as "I struggle to explain my project contribution clearly."
4. Start the mock interview.
5. Show the interviewer asking a project-specific deep-dive or reviewer-style question, not a generic question.
6. Give a deliberately vague answer, for example "we improved performance a lot by changing the model."
7. Show structured feedback that points out missing evidence, unclear ownership, weak technical depth, and poor answer rhythm.
8. Show the teacher-perspective explanation: why a real teacher would keep asking about this claim.
9. Show the reviewer-style adaptive follow-up that presses method design, experiment proof, or personal contribution.

Suggested narration:

```text
ResearchMocker is an AI project-deep-dive and reviewer-style mock interviewer for research-oriented CS interviews. It is not a friendly chatbot. It pressure-tests vague project answers, explains why a real teacher or reviewer would follow up, and turns the answer into concrete improvement steps.
```

## Main Flow

1. Show the candidate profile fields:
   - self-introduction
   - project/research experience
   - target direction
   - personal contribution
   - key method or design choice
   - experiment/result claim
   - failure case or limitation
   - weak points
2. Start a text interview.
3. Let the AI ask one targeted question.
4. Answer with a short response.
5. Show per-answer feedback:
   - strengths
   - weaknesses
   - teacher perspective
   - rhythm/length feedback
   - project story clarity
   - personal contribution clarity
   - score
   - actionable advice
6. Show a rewrite suggestion or concrete evidence the answer should include.
7. Show the follow-up question reacting to the previous answer.
8. Finish the interview.
9. Show the final report:
   - overall assessment
   - pass-risk judgment: likely pass, borderline, or high risk
   - top 3 reasons for the judgment
   - technical depth
   - project ownership
   - research thinking
   - communication clarity
   - vulnerable follow-up points
   - next practice plan

## Optional Face-to-Face Segment

Only include this segment if the page is implemented enough to show honestly.

1. Open the Face-to-Face Interview page.
2. Show interviewer image upload and reference audio upload.
3. Explain the intended pipeline:
   - image to ready/listening digital human clips
   - reference audio to voice clone
   - microphone input to real-time speech model
   - generated response audio/video for a face-to-face feeling
4. If real API integration is working, show the ready/listening/speaking state switch.
5. If not working, state clearly that this is the next-step design and return to the text MVP.

Suggested narration:

```text
The text flow is the reliable MVP. The face-to-face mode is the next layer: it tries to reduce the gap between ChatGPT-style text practice and the pressure of a real interview.
```

## Engineering Talking Points

Keep this short:

- Backend: FastAPI, SQLite, HttpOnly sessions, pytest.
- Frontend: Next.js, TypeScript, responsive interview UI.
- LLM: backend-only routing through LiteLLM and OpenRouter.
- Models: Plus for deep analysis and final reports, Flash for fast interview turns.
- Deployment: Docker Compose behind Nginx on a public server.
- Safety: secrets stay in `.env`; provider calls are mocked in automated tests.

## Fallback Plan

If the live provider is slow:

- Use a saved demo interview record.
- Show the final report from an earlier run.
- Use the preset project card so the product value is visible without typing live.
- Explain that automated tests mock providers, while the public deployment can be smoke-tested manually.

If face-to-face mode is incomplete:

- Do not fake it as complete.
- Show the reserved page or design note briefly.
- Spend most of the demo on the working text interview loop.

## Closing

End with:

```text
The narrow goal is to help students practice the hardest part of research interviews: defending their own project experience under follow-up questions, then turning vague answers into concrete improvement steps.
```
