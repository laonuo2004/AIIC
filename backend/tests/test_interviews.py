def _register_and_login(client, username="lin"):
    client.post("/api/auth/register", json={"username": username, "password": "good-password"})
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "good-password"},
    )
    assert response.status_code == 200


def _profile_payload():
    return {
        "self_introduction": "I am a CS undergraduate working on retrieval augmented generation.",
        "project_experience": "Built an evaluation harness for RAG hallucination analysis.",
        "target_direction": "AI systems research internship",
        "weak_points": "Explaining my exact contribution and evaluation metrics.",
    }


def test_interview_api_requires_auth(client):
    response = client.post("/api/interviews", json=_profile_payload())

    assert response.status_code == 401


def test_create_interview_generates_first_question_and_persists(client, monkeypatch):
    _register_and_login(client)

    def fake_first_question(profile):
        assert "retrieval augmented generation" in profile["self_introduction"]
        return {
            "question": (
                "Walk me through your RAG evaluation harness and your personal contribution."
            ),
            "model_used": "openrouter/qwen/qwen3.6-plus",
            "raw_text": None,
        }

    monkeypatch.setattr("app.api.interviews.generate_first_question", fake_first_question)

    response = client.post("/api/interviews", json=_profile_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "active"
    assert body["current_question"] == (
        "Walk me through your RAG evaluation harness and your personal contribution."
    )
    assert body["turns"][0]["turn_index"] == 1
    assert body["turns"][0]["answer"] is None

    listed = client.get("/api/interviews")
    assert listed.status_code == 200
    assert listed.json()["interviews"][0]["id"] == body["id"]


def test_submit_answer_returns_feedback_and_follow_up(client, monkeypatch):
    _register_and_login(client)
    monkeypatch.setattr(
        "app.api.interviews.generate_first_question",
        lambda profile: {
            "question": "What was your research question?",
            "model_used": "openrouter/qwen/qwen3.6-plus",
            "raw_text": None,
        },
    )
    monkeypatch.setattr(
        "app.api.interviews.evaluate_answer_and_follow_up",
        lambda *, profile, question, answer, previous_turns: {
            "feedback": {
                "strengths": ["Clear project framing"],
                "weaknesses": ["Metrics are still underspecified"],
                "score": 7,
                "advice": "Name the benchmark and compare against a baseline.",
            },
            "follow_up_question": "Which metric best captured hallucination reduction?",
            "model_used": "openrouter/qwen/qwen3.6-flash",
            "raw_text": None,
        },
    )
    interview_id = client.post("/api/interviews", json=_profile_payload()).json()["id"]

    response = client.post(
        f"/api/interviews/{interview_id}/answers",
        json={"answer": "I designed the dataset and measured citation precision."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["turns"][0]["feedback"]["score"] == 7
    assert body["turns"][1]["question"] == "Which metric best captured hallucination reduction?"
    assert body["current_question"] == "Which metric best captured hallucination reduction?"


def test_finish_interview_generates_report_and_marks_finished(client, monkeypatch):
    _register_and_login(client)
    monkeypatch.setattr(
        "app.api.interviews.generate_first_question",
        lambda profile: {
            "question": "What was your research question?",
            "model_used": "openrouter/qwen/qwen3.6-plus",
            "raw_text": None,
        },
    )
    monkeypatch.setattr(
        "app.api.interviews.generate_final_report",
        lambda *, profile, turns: {
            "report": {
                "overall_score": 8,
                "summary": "Strong research framing with room to quantify impact.",
                "weaknesses": ["Evaluation metrics need sharper baselines"],
                "next_steps": ["Prepare a one-minute project contribution answer"],
            },
            "model_used": "openrouter/qwen/qwen3.6-plus",
            "raw_text": None,
        },
    )
    interview_id = client.post("/api/interviews", json=_profile_payload()).json()["id"]

    response = client.post(f"/api/interviews/{interview_id}/finish")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "finished"
    assert body["final_report"]["overall_score"] == 8
    assert body["finished_at"] is not None


def test_interview_ownership_is_enforced(client, monkeypatch):
    _register_and_login(client, username="owner")
    monkeypatch.setattr(
        "app.api.interviews.generate_first_question",
        lambda profile: {
            "question": "What was your research question?",
            "model_used": "openrouter/qwen/qwen3.6-plus",
            "raw_text": None,
        },
    )
    interview_id = client.post("/api/interviews", json=_profile_payload()).json()["id"]
    client.post("/api/auth/logout")
    _register_and_login(client, username="other")

    response = client.get(f"/api/interviews/{interview_id}")

    assert response.status_code == 404
