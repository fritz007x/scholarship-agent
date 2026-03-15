import pytest
from app.models.scholarship import Scholarship


class TestListScholarships:
    def test_list_no_auth_required(self, client):
        response = client.get("/scholarships")
        assert response.status_code == 200
        data = response.json()
        assert "scholarships" in data
        assert "total" in data

    def test_list_with_results(self, client, sample_scholarship):
        response = client.get("/scholarships")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["scholarships"][0]["name"] == "STEM Excellence Award"

    def test_search_by_name(self, client, sample_scholarship):
        response = client.get("/scholarships", params={"search": "STEM"})
        assert response.status_code == 200
        assert response.json()["total"] == 1

    def test_search_no_match(self, client, sample_scholarship):
        response = client.get("/scholarships", params={"search": "nonexistent"})
        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_filter_min_amount(self, client, sample_scholarship):
        response = client.get("/scholarships", params={"min_amount": 10000})
        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_filter_max_amount(self, client, sample_scholarship):
        response = client.get("/scholarships", params={"max_amount": 10000})
        assert response.status_code == 200
        assert response.json()["total"] == 1

    def test_pagination(self, client, db):
        for i in range(5):
            db.add(Scholarship(name=f"Scholarship {i}", provider="Test"))
        db.commit()

        response = client.get("/scholarships", params={"limit": 2, "offset": 0})
        assert response.status_code == 200
        data = response.json()
        assert len(data["scholarships"]) == 2
        assert data["total"] == 5


class TestGetScholarship:
    def test_get_existing(self, client, sample_scholarship):
        response = client.get(f"/scholarships/{sample_scholarship.id}")
        assert response.status_code == 200
        assert response.json()["name"] == "STEM Excellence Award"

    def test_get_nonexistent(self, client):
        response = client.get("/scholarships/999")
        assert response.status_code == 404


class TestCreateScholarship:
    def test_create_as_admin(self, client, admin_headers):
        response = client.post("/scholarships", headers=admin_headers, json={
            "name": "New Scholarship",
            "provider": "Foundation",
            "award_amount": 2500
        })
        assert response.status_code == 201
        assert response.json()["name"] == "New Scholarship"

    def test_create_as_regular_user(self, client, auth_headers):
        response = client.post("/scholarships", headers=auth_headers, json={
            "name": "New Scholarship"
        })
        assert response.status_code == 403

    def test_create_no_auth(self, client):
        response = client.post("/scholarships", json={"name": "New Scholarship"})
        assert response.status_code == 403
