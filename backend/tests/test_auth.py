def test_register_login_me_logout_flow(client):
    register = client.post(
        "/api/auth/register",
        json={"username": "ada", "password": "correct horse battery staple"},
    )
    assert register.status_code == 201
    assert register.json()["username"] == "ada"
    assert "session" not in register.json()

    login = client.post(
        "/api/auth/login",
        json={"username": "ada", "password": "correct horse battery staple"},
    )
    assert login.status_code == 200
    assert login.json()["username"] == "ada"
    assert "session_token" in login.cookies

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == "ada"

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 204

    logged_out = client.get("/api/auth/me")
    assert logged_out.status_code == 401


def test_login_rejects_invalid_credentials(client):
    client.post("/api/auth/register", json={"username": "grace", "password": "good-password"})

    response = client.post("/api/auth/login", json={"username": "grace", "password": "bad"})

    assert response.status_code == 401
