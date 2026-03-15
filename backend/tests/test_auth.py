import pytest


class TestRegister:
    def test_register_success(self, client):
        response = client.post("/auth/register", json={
            "email": "new@example.com",
            "password": "NewPass123"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new@example.com"
        assert "id" in data

    def test_register_duplicate_email(self, client, test_user):
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "AnotherPass123"
        })
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_register_weak_password(self, client):
        response = client.post("/auth/register", json={
            "email": "new@example.com",
            "password": "short"
        })
        assert response.status_code == 422

    def test_register_no_uppercase(self, client):
        response = client.post("/auth/register", json={
            "email": "new@example.com",
            "password": "alllowercase1"
        })
        assert response.status_code == 422

    def test_register_no_digit(self, client):
        response = client.post("/auth/register", json={
            "email": "new@example.com",
            "password": "NoDigitsHere"
        })
        assert response.status_code == 422

    def test_register_invalid_email(self, client):
        response = client.post("/auth/register", json={
            "email": "not-an-email",
            "password": "ValidPass123"
        })
        assert response.status_code == 422


class TestLogin:
    def test_login_success(self, client, test_user):
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "TestPass123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "WrongPass123"
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        response = client.post("/auth/login", json={
            "email": "nobody@example.com",
            "password": "SomePass123"
        })
        assert response.status_code == 401


class TestMe:
    def test_get_me(self, client, test_user, auth_headers):
        response = client.get("/auth/me", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"

    def test_get_me_no_auth(self, client):
        response = client.get("/auth/me")
        assert response.status_code == 403

    def test_get_me_invalid_token(self, client):
        response = client.get("/auth/me", headers={"Authorization": "Bearer invalidtoken"})
        assert response.status_code == 401
