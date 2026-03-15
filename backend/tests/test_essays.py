import pytest


class TestCreateEssay:
    def test_create_success(self, client, auth_headers):
        response = client.post("/essays", headers=auth_headers, json={
            "title": "My Leadership Journey",
            "content": "I have always been a leader in my community.",
            "prompt_category": "leadership",
            "tags": ["personal", "leadership"]
        })
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "My Leadership Journey"
        assert data["word_count"] == 9
        assert data["tags"] == ["personal", "leadership"]
        assert data["used_in_applications"] == []

    def test_create_empty_content(self, client, auth_headers):
        response = client.post("/essays", headers=auth_headers, json={
            "title": "Draft Essay"
        })
        assert response.status_code == 201
        assert response.json()["word_count"] == 0

    def test_create_no_auth(self, client):
        response = client.post("/essays", json={"title": "Test"})
        assert response.status_code == 403


class TestListEssays:
    def test_list_empty(self, client, auth_headers):
        response = client.get("/essays", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_list_with_essays(self, client, auth_headers):
        client.post("/essays", headers=auth_headers, json={"title": "Essay 1"})
        client.post("/essays", headers=auth_headers, json={"title": "Essay 2"})

        response = client.get("/essays", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["total"] == 2

    def test_filter_by_category(self, client, auth_headers):
        client.post("/essays", headers=auth_headers, json={
            "title": "Essay A", "prompt_category": "leadership"
        })
        client.post("/essays", headers=auth_headers, json={
            "title": "Essay B", "prompt_category": "community_service"
        })

        response = client.get("/essays", headers=auth_headers, params={
            "prompt_category": "leadership"
        })
        assert response.json()["total"] == 1
        assert response.json()["essays"][0]["title"] == "Essay A"

    def test_filter_by_template(self, client, auth_headers):
        client.post("/essays", headers=auth_headers, json={
            "title": "Template", "is_template": True
        })
        client.post("/essays", headers=auth_headers, json={
            "title": "Regular", "is_template": False
        })

        response = client.get("/essays", headers=auth_headers, params={
            "is_template": True
        })
        assert response.json()["total"] == 1


class TestGetEssay:
    def test_get_existing(self, client, auth_headers):
        create_resp = client.post("/essays", headers=auth_headers, json={
            "title": "My Essay"
        })
        essay_id = create_resp.json()["id"]

        response = client.get(f"/essays/{essay_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["title"] == "My Essay"

    def test_get_nonexistent(self, client, auth_headers):
        response = client.get("/essays/999", headers=auth_headers)
        assert response.status_code == 404


class TestUpdateEssay:
    def test_update_content(self, client, auth_headers):
        create_resp = client.post("/essays", headers=auth_headers, json={
            "title": "Draft",
            "content": "Initial content"
        })
        essay_id = create_resp.json()["id"]

        response = client.put(f"/essays/{essay_id}", headers=auth_headers, json={
            "content": "Updated content with more words here"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Updated content with more words here"
        assert data["word_count"] == 6

    def test_update_nonexistent(self, client, auth_headers):
        response = client.put("/essays/999", headers=auth_headers, json={
            "title": "New Title"
        })
        assert response.status_code == 404


class TestDeleteEssay:
    def test_delete_success(self, client, auth_headers):
        create_resp = client.post("/essays", headers=auth_headers, json={
            "title": "To Delete"
        })
        essay_id = create_resp.json()["id"]

        response = client.delete(f"/essays/{essay_id}", headers=auth_headers)
        assert response.status_code == 204

    def test_delete_nonexistent(self, client, auth_headers):
        response = client.delete("/essays/999", headers=auth_headers)
        assert response.status_code == 404
