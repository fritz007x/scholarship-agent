import pytest


class TestGetProfile:
    def test_get_creates_empty_profile(self, client, auth_headers, test_user):
        response = client.get("/profile", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_user.id
        assert data["first_name"] is None

    def test_get_no_auth(self, client):
        response = client.get("/profile")
        assert response.status_code == 403


class TestCreateProfile:
    def test_create_profile(self, client, auth_headers, test_user):
        response = client.post("/profile", headers=auth_headers, json={
            "first_name": "John",
            "last_name": "Doe",
            "gpa": 3.8,
            "current_school": "MIT",
            "intended_major": "Computer Science"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "John"
        assert data["gpa"] == 3.8

    def test_create_duplicate_profile(self, client, auth_headers):
        client.post("/profile", headers=auth_headers, json={"first_name": "John"})
        response = client.post("/profile", headers=auth_headers, json={"first_name": "Jane"})
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


class TestUpdateProfile:
    def test_update_profile(self, client, auth_headers):
        client.post("/profile", headers=auth_headers, json={"first_name": "John"})
        response = client.put("/profile", headers=auth_headers, json={
            "first_name": "Jane",
            "gpa": 3.95,
            "test_scores": {"SAT": 1500, "ACT": 34}
        })
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Jane"
        assert data["gpa"] == 3.95
        assert data["test_scores"]["SAT"] == 1500

    def test_update_creates_if_missing(self, client, auth_headers):
        response = client.put("/profile", headers=auth_headers, json={
            "first_name": "Auto"
        })
        assert response.status_code == 200
        assert response.json()["first_name"] == "Auto"

    def test_partial_update(self, client, auth_headers):
        client.post("/profile", headers=auth_headers, json={
            "first_name": "John",
            "last_name": "Doe"
        })
        response = client.put("/profile", headers=auth_headers, json={
            "gpa": 3.7
        })
        assert response.status_code == 200
        data = response.json()
        assert data["gpa"] == 3.7
        assert data["first_name"] == "John"

    def test_update_with_activities(self, client, auth_headers):
        response = client.put("/profile", headers=auth_headers, json={
            "extracurriculars": [
                {"name": "Robotics Club", "role": "President", "years": 3}
            ],
            "awards": [
                {"name": "Science Fair Winner", "year": 2025, "level": "state"}
            ]
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data["extracurriculars"]) == 1
        assert data["extracurriculars"][0]["name"] == "Robotics Club"
