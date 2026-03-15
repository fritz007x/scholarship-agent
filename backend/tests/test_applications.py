import pytest
from app.models.application import Application


class TestListApplications:
    def test_list_empty(self, client, auth_headers):
        response = client.get("/applications", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["applications"] == []

    def test_list_no_auth(self, client):
        response = client.get("/applications")
        assert response.status_code == 403


class TestCreateApplication:
    def test_create_success(self, client, auth_headers, sample_scholarship):
        response = client.post("/applications", headers=auth_headers, json={
            "scholarship_id": sample_scholarship.id,
            "priority": 1,
            "notes": "My top choice"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["scholarship_id"] == sample_scholarship.id
        assert data["status"] == "saved"
        assert data["priority"] == 1
        assert data["checklist_total"] > 0

    def test_create_generates_checklist(self, client, auth_headers, sample_scholarship):
        response = client.post("/applications", headers=auth_headers, json={
            "scholarship_id": sample_scholarship.id
        })
        data = response.json()
        checklist = data["checklist"]
        types = [item["type"] for item in checklist]
        assert "form" in types
        assert "essay" in types
        assert "document" in types
        assert "recommendation" in types

    def test_create_nonexistent_scholarship(self, client, auth_headers):
        response = client.post("/applications", headers=auth_headers, json={
            "scholarship_id": 999
        })
        assert response.status_code == 404

    def test_create_duplicate(self, client, auth_headers, sample_scholarship):
        client.post("/applications", headers=auth_headers, json={
            "scholarship_id": sample_scholarship.id
        })
        response = client.post("/applications", headers=auth_headers, json={
            "scholarship_id": sample_scholarship.id
        })
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


class TestGetApplication:
    def test_get_existing(self, client, auth_headers, sample_scholarship):
        create_resp = client.post("/applications", headers=auth_headers, json={
            "scholarship_id": sample_scholarship.id
        })
        app_id = create_resp.json()["id"]

        response = client.get(f"/applications/{app_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == app_id

    def test_get_nonexistent(self, client, auth_headers):
        response = client.get("/applications/999", headers=auth_headers)
        assert response.status_code == 404

    def test_get_other_users_application(self, client, db, sample_scholarship, auth_headers):
        from app.models.user import User
        from app.utils.security import get_password_hash, create_access_token

        other_user = User(email="other@example.com", hashed_password=get_password_hash("OtherPass123"))
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        app = Application(user_id=other_user.id, scholarship_id=sample_scholarship.id, status="saved")
        db.add(app)
        db.commit()
        db.refresh(app)

        response = client.get(f"/applications/{app.id}", headers=auth_headers)
        assert response.status_code == 404


class TestUpdateApplication:
    def test_update_status(self, client, auth_headers, sample_scholarship):
        create_resp = client.post("/applications", headers=auth_headers, json={
            "scholarship_id": sample_scholarship.id
        })
        app_id = create_resp.json()["id"]

        response = client.put(f"/applications/{app_id}", headers=auth_headers, json={
            "status": "in_progress"
        })
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"

    def test_update_sets_submitted_at(self, client, auth_headers, sample_scholarship):
        create_resp = client.post("/applications", headers=auth_headers, json={
            "scholarship_id": sample_scholarship.id
        })
        app_id = create_resp.json()["id"]

        response = client.put(f"/applications/{app_id}", headers=auth_headers, json={
            "status": "submitted"
        })
        assert response.status_code == 200
        assert response.json()["submitted_at"] is not None

    def test_update_nonexistent(self, client, auth_headers):
        response = client.put("/applications/999", headers=auth_headers, json={
            "status": "in_progress"
        })
        assert response.status_code == 404


class TestDeleteApplication:
    def test_delete_success(self, client, auth_headers, sample_scholarship):
        create_resp = client.post("/applications", headers=auth_headers, json={
            "scholarship_id": sample_scholarship.id
        })
        app_id = create_resp.json()["id"]

        response = client.delete(f"/applications/{app_id}", headers=auth_headers)
        assert response.status_code == 204

        response = client.get(f"/applications/{app_id}", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_nonexistent(self, client, auth_headers):
        response = client.delete("/applications/999", headers=auth_headers)
        assert response.status_code == 404


class TestChecklistUpdate:
    def test_mark_item_complete(self, client, auth_headers, sample_scholarship):
        create_resp = client.post("/applications", headers=auth_headers, json={
            "scholarship_id": sample_scholarship.id
        })
        data = create_resp.json()
        app_id = data["id"]
        item_id = data["checklist"][0]["id"]

        response = client.put(
            f"/applications/{app_id}/checklist/{item_id}",
            headers=auth_headers,
            json={"completed": True}
        )
        assert response.status_code == 200
        assert response.json()["checklist_completed"] == 1

    def test_mark_item_incomplete(self, client, auth_headers, sample_scholarship):
        create_resp = client.post("/applications", headers=auth_headers, json={
            "scholarship_id": sample_scholarship.id
        })
        data = create_resp.json()
        app_id = data["id"]
        item_id = data["checklist"][0]["id"]

        client.put(
            f"/applications/{app_id}/checklist/{item_id}",
            headers=auth_headers,
            json={"completed": True}
        )
        response = client.put(
            f"/applications/{app_id}/checklist/{item_id}",
            headers=auth_headers,
            json={"completed": False}
        )
        assert response.status_code == 200
        assert response.json()["checklist_completed"] == 0

    def test_nonexistent_item(self, client, auth_headers, sample_scholarship):
        create_resp = client.post("/applications", headers=auth_headers, json={
            "scholarship_id": sample_scholarship.id
        })
        app_id = create_resp.json()["id"]

        response = client.put(
            f"/applications/{app_id}/checklist/fake-id",
            headers=auth_headers,
            json={"completed": True}
        )
        assert response.status_code == 404
