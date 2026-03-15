import pytest
import io


def make_upload_file(filename="test.pdf", content=b"fake pdf content", content_type="application/pdf"):
    return {"file": (filename, io.BytesIO(content), content_type)}


class TestUploadDocument:
    def test_upload_pdf(self, client, auth_headers):
        response = client.post(
            "/documents",
            headers=auth_headers,
            files=make_upload_file(),
            data={"document_type": "transcript", "title": "My Transcript"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["original_filename"] == "test.pdf"
        assert data["document_type"] == "transcript"
        assert data["title"] == "My Transcript"

    def test_upload_with_tags(self, client, auth_headers):
        response = client.post(
            "/documents",
            headers=auth_headers,
            files=make_upload_file(),
            data={"tags": "academic, official"}
        )
        assert response.status_code == 201
        assert response.json()["tags"] == ["academic", "official"]

    def test_upload_disallowed_extension(self, client, auth_headers):
        response = client.post(
            "/documents",
            headers=auth_headers,
            files=make_upload_file(filename="malware.exe", content_type="application/octet-stream"),
        )
        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"]

    def test_upload_no_auth(self, client):
        response = client.post("/documents", files=make_upload_file())
        assert response.status_code == 403


class TestListDocuments:
    def test_list_empty(self, client, auth_headers):
        response = client.get("/documents", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_list_with_filter(self, client, auth_headers):
        client.post(
            "/documents",
            headers=auth_headers,
            files=make_upload_file(filename="transcript.pdf"),
            data={"document_type": "transcript"}
        )
        client.post(
            "/documents",
            headers=auth_headers,
            files=make_upload_file(filename="resume.pdf"),
            data={"document_type": "resume"}
        )

        response = client.get("/documents", headers=auth_headers, params={
            "document_type": "transcript"
        })
        assert response.json()["total"] == 1


class TestGetDocument:
    def test_get_existing(self, client, auth_headers):
        upload_resp = client.post(
            "/documents",
            headers=auth_headers,
            files=make_upload_file(),
            data={"title": "My Doc"}
        )
        doc_id = upload_resp.json()["id"]

        response = client.get(f"/documents/{doc_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["title"] == "My Doc"

    def test_get_nonexistent(self, client, auth_headers):
        response = client.get("/documents/999", headers=auth_headers)
        assert response.status_code == 404


class TestUpdateDocument:
    def test_update_metadata(self, client, auth_headers):
        upload_resp = client.post(
            "/documents",
            headers=auth_headers,
            files=make_upload_file(),
        )
        doc_id = upload_resp.json()["id"]

        response = client.put(f"/documents/{doc_id}", headers=auth_headers, json={
            "title": "Updated Title",
            "description": "Updated description"
        })
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"


class TestDeleteDocument:
    def test_delete_success(self, client, auth_headers):
        upload_resp = client.post(
            "/documents",
            headers=auth_headers,
            files=make_upload_file(),
        )
        doc_id = upload_resp.json()["id"]

        response = client.delete(f"/documents/{doc_id}", headers=auth_headers)
        assert response.status_code == 204

    def test_delete_nonexistent(self, client, auth_headers):
        response = client.delete("/documents/999", headers=auth_headers)
        assert response.status_code == 404
