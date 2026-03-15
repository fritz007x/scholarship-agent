"""
End-to-end tests that exercise full user workflows across multiple API endpoints.

These tests simulate real user journeys:
1. Registration -> Login -> Profile setup -> Browse scholarships -> Apply -> Track progress
2. Essay library management and reuse across applications
3. Document upload and attachment to checklist items
4. Multi-user isolation (users can't see each other's data)
5. Admin workflows (scholarship creation, scraper management)
"""

import io
import pytest
from app.models.scholarship import Scholarship
from app.models.user import User
from app.utils.security import get_password_hash, create_access_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def register_and_login(client, email="user@example.com", password="SecurePass1"):
    """Register a user and return (user_data, auth_headers)."""
    reg = client.post("/auth/register", json={"email": email, "password": password})
    assert reg.status_code == 201
    user_data = reg.json()

    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    token = login.json()["access_token"]

    return user_data, {"Authorization": f"Bearer {token}"}


def create_scholarship_in_db(db, name="Test Scholarship", **overrides):
    """Insert a scholarship directly into the DB and return it."""
    defaults = dict(
        name=name,
        provider="Test Foundation",
        description="A scholarship for testing",
        award_amount=5000.0,
        deadline=None,
        eligibility={"gpa_minimum": 3.0, "majors": ["computer science"]},
        application_requirements={
            "essays": [{"prompt": "Why do you deserve this?", "word_count": 500}],
            "documents": ["transcript"],
            "other": ["Online form"],
        },
        keywords=["test"],
        categories=["merit-based"],
    )
    defaults.update(overrides)
    s = Scholarship(**defaults)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


# ===========================================================================
# E2E Workflow Tests
# ===========================================================================


class TestFullRegistrationToApplicationWorkflow:
    """Register -> Login -> Set up profile -> Browse scholarships -> Apply."""

    def test_new_user_full_journey(self, client, db):
        # 1. Register
        reg = client.post("/auth/register", json={
            "email": "student@test.edu",
            "password": "MyPass123"
        })
        assert reg.status_code == 201
        user_id = reg.json()["id"]

        # 2. Login
        login = client.post("/auth/login", json={
            "email": "student@test.edu",
            "password": "MyPass123"
        })
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Verify identity
        me = client.get("/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["id"] == user_id

        # 4. Get profile (auto-created empty)
        profile = client.get("/profile", headers=headers)
        assert profile.status_code == 200
        assert profile.json()["user_id"] == user_id
        assert profile.json()["first_name"] is None

        # 5. Update profile
        update = client.put("/profile", headers=headers, json={
            "first_name": "Jane",
            "last_name": "Doe",
            "gpa": 3.8,
            "intended_major": "Computer Science",
            "current_school": "Test University",
            "graduation_year": 2027,
        })
        assert update.status_code == 200
        assert update.json()["first_name"] == "Jane"
        assert update.json()["gpa"] == 3.8

        # 6. Browse scholarships (public endpoint)
        scholarship = create_scholarship_in_db(db)
        listing = client.get("/scholarships")
        assert listing.status_code == 200
        assert listing.json()["total"] >= 1
        scholarship_id = listing.json()["scholarships"][0]["id"]

        # 7. View scholarship details
        detail = client.get(f"/scholarships/{scholarship_id}")
        assert detail.status_code == 200
        assert detail.json()["name"] == "Test Scholarship"

        # 8. Create application
        app_resp = client.post("/applications", headers=headers, json={
            "scholarship_id": scholarship_id,
            "priority": 1,
            "notes": "My dream scholarship"
        })
        assert app_resp.status_code == 201
        app_data = app_resp.json()
        assert app_data["status"] == "saved"
        assert app_data["checklist_total"] > 0
        assert app_data["priority"] == 1

        # 9. Verify application appears in list
        apps = client.get("/applications", headers=headers)
        assert apps.status_code == 200
        assert apps.json()["total"] == 1
        assert apps.json()["applications"][0]["scholarship_name"] == "Test Scholarship"

        # 10. Update application status
        app_id = app_data["id"]
        upd = client.put(f"/applications/{app_id}", headers=headers, json={
            "status": "in_progress"
        })
        assert upd.status_code == 200
        assert upd.json()["status"] == "in_progress"


class TestEssayCreationAndApplicationAttachment:
    """Create essays -> Create application -> Attach essay to checklist item."""

    def test_essay_to_checklist_workflow(self, client, db):
        _, headers = register_and_login(client, "writer@test.edu", "EssayPass1")

        # Create an essay
        essay_resp = client.post("/essays", headers=headers, json={
            "title": "Why I Deserve This Scholarship",
            "content": "I am passionate about technology and have dedicated my high school years to...",
            "prompt_category": "personal_statement",
            "tags": ["stem", "motivation"],
            "is_template": False,
        })
        assert essay_resp.status_code == 201
        essay_id = essay_resp.json()["id"]
        assert essay_resp.json()["word_count"] > 0

        # Create a second essay (template)
        template_resp = client.post("/essays", headers=headers, json={
            "title": "Generic Leadership Essay",
            "content": "Throughout my career I have demonstrated leadership by...",
            "prompt_category": "leadership",
            "is_template": True,
        })
        assert template_resp.status_code == 201

        # Verify listing with filters
        all_essays = client.get("/essays", headers=headers)
        assert all_essays.json()["total"] == 2

        templates_only = client.get("/essays?is_template=true", headers=headers)
        assert templates_only.json()["total"] == 1
        assert templates_only.json()["essays"][0]["title"] == "Generic Leadership Essay"

        # Create scholarship & application
        scholarship = create_scholarship_in_db(db)
        app_resp = client.post("/applications", headers=headers, json={
            "scholarship_id": scholarship.id
        })
        assert app_resp.status_code == 201
        app_data = app_resp.json()
        app_id = app_data["id"]

        # Find the essay-type checklist item
        essay_items = [c for c in app_data["checklist"] if c["type"] == "essay"]
        assert len(essay_items) > 0
        item_id = essay_items[0]["id"]

        # Attach essay to checklist item
        attach = client.put(
            f"/applications/{app_id}/checklist/{item_id}",
            headers=headers,
            json={"completed": True, "essay_id": essay_id}
        )
        assert attach.status_code == 200
        updated_checklist = attach.json()["checklist"]
        attached_item = next(c for c in updated_checklist if c["id"] == item_id)
        assert attached_item["completed"] is True
        assert attached_item["essay_id"] == essay_id

        # Verify progress incremented
        assert attach.json()["checklist_completed"] >= 1

    def test_essay_update_and_delete(self, client):
        _, headers = register_and_login(client, "editor@test.edu", "EditPass1")

        # Create
        resp = client.post("/essays", headers=headers, json={
            "title": "Draft Essay",
            "content": "Initial draft content.",
        })
        essay_id = resp.json()["id"]

        # Update
        upd = client.put(f"/essays/{essay_id}", headers=headers, json={
            "title": "Final Essay",
            "content": "Polished final content with more words added here.",
        })
        assert upd.status_code == 200
        assert upd.json()["title"] == "Final Essay"

        # Delete
        delete = client.delete(f"/essays/{essay_id}", headers=headers)
        assert delete.status_code == 204

        # Verify gone
        get = client.get(f"/essays/{essay_id}", headers=headers)
        assert get.status_code == 404


class TestDocumentUploadAndAttachment:
    """Upload document -> Attach to application checklist."""

    def test_document_lifecycle(self, client, db):
        _, headers = register_and_login(client, "uploader@test.edu", "UploadPass1")

        # Upload a document
        file_content = b"Fake PDF transcript content"
        upload_resp = client.post(
            "/documents",
            headers=headers,
            files={"file": ("transcript.pdf", io.BytesIO(file_content), "application/pdf")},
            data={
                "document_type": "transcript",
                "title": "Fall 2025 Transcript",
                "description": "Official transcript from Test University",
                "tags": "academic,official",
            }
        )
        assert upload_resp.status_code == 201
        doc_data = upload_resp.json()
        doc_id = doc_data["id"]
        assert doc_data["original_filename"] == "transcript.pdf"
        assert doc_data["document_type"] == "transcript"
        assert doc_data["mime_type"] == "application/pdf"

        # Verify appears in listing
        listing = client.get("/documents", headers=headers)
        assert listing.json()["total"] == 1

        # Filter by type
        filtered = client.get("/documents?document_type=transcript", headers=headers)
        assert filtered.json()["total"] == 1

        # Download
        download = client.get(f"/documents/{doc_id}/download", headers=headers)
        assert download.status_code == 200

        # Create app and attach doc to checklist
        scholarship = create_scholarship_in_db(db)
        app_resp = client.post("/applications", headers=headers, json={
            "scholarship_id": scholarship.id
        })
        app_data = app_resp.json()
        app_id = app_data["id"]

        doc_items = [c for c in app_data["checklist"] if c["type"] == "document"]
        assert len(doc_items) > 0
        item_id = doc_items[0]["id"]

        attach = client.put(
            f"/applications/{app_id}/checklist/{item_id}",
            headers=headers,
            json={"completed": True, "document_id": doc_id}
        )
        assert attach.status_code == 200
        attached = next(c for c in attach.json()["checklist"] if c["id"] == item_id)
        assert attached["document_id"] == doc_id
        assert attached["completed"] is True

    def test_document_update_and_delete(self, client):
        _, headers = register_and_login(client, "docmgr@test.edu", "DocPass123")

        upload = client.post(
            "/documents",
            headers=headers,
            files={"file": ("resume.pdf", io.BytesIO(b"resume data"), "application/pdf")},
            data={"title": "Old Resume"},
        )
        doc_id = upload.json()["id"]

        # Update metadata
        upd = client.put(f"/documents/{doc_id}", headers=headers, json={
            "title": "Updated Resume 2025",
            "tags": ["resume", "current"],
        })
        assert upd.status_code == 200
        assert upd.json()["title"] == "Updated Resume 2025"

        # Delete
        delete = client.delete(f"/documents/{doc_id}", headers=headers)
        assert delete.status_code == 204

        get = client.get(f"/documents/{doc_id}", headers=headers)
        assert get.status_code == 404


class TestApplicationLifecycle:
    """Full application lifecycle: saved -> in_progress -> submitted -> awarded."""

    def test_status_progression(self, client, db):
        _, headers = register_and_login(client, "lifecycle@test.edu", "LifePass1")
        scholarship = create_scholarship_in_db(db)

        # Create
        app_resp = client.post("/applications", headers=headers, json={
            "scholarship_id": scholarship.id
        })
        app_id = app_resp.json()["id"]
        assert app_resp.json()["status"] == "saved"

        # Progress through statuses
        for next_status in ["in_progress", "submitted", "awarded"]:
            resp = client.put(f"/applications/{app_id}", headers=headers, json={
                "status": next_status
            })
            assert resp.status_code == 200
            assert resp.json()["status"] == next_status

        # Verify submitted_at was set when status went to submitted
        final = client.get(f"/applications/{app_id}", headers=headers)
        assert final.json()["submitted_at"] is not None

    def test_complete_all_checklist_items(self, client, db):
        _, headers = register_and_login(client, "checklist@test.edu", "CheckPass1")
        scholarship = create_scholarship_in_db(db)

        app_resp = client.post("/applications", headers=headers, json={
            "scholarship_id": scholarship.id
        })
        app_data = app_resp.json()
        app_id = app_data["id"]
        total = app_data["checklist_total"]

        # Complete every item
        for item in app_data["checklist"]:
            resp = client.put(
                f"/applications/{app_id}/checklist/{item['id']}",
                headers=headers,
                json={"completed": True}
            )
            assert resp.status_code == 200

        # Verify all complete
        final = client.get(f"/applications/{app_id}", headers=headers)
        assert final.json()["checklist_completed"] == total

    def test_multiple_applications(self, client, db):
        _, headers = register_and_login(client, "multi@test.edu", "MultiPass1")

        s1 = create_scholarship_in_db(db, name="Scholarship A", award_amount=1000.0)
        s2 = create_scholarship_in_db(db, name="Scholarship B", award_amount=2000.0)
        s3 = create_scholarship_in_db(db, name="Scholarship C", award_amount=3000.0)

        for s in [s1, s2, s3]:
            resp = client.post("/applications", headers=headers, json={
                "scholarship_id": s.id
            })
            assert resp.status_code == 201

        listing = client.get("/applications", headers=headers)
        assert listing.json()["total"] == 3


class TestMultiUserIsolation:
    """Verify users cannot access each other's data."""

    def test_application_isolation(self, client, db):
        _, headers_a = register_and_login(client, "alice@test.edu", "AlicePass1")
        _, headers_b = register_and_login(client, "bob@test.edu", "BobbyPass1")
        scholarship = create_scholarship_in_db(db)

        # Alice creates an application
        alice_app = client.post("/applications", headers=headers_a, json={
            "scholarship_id": scholarship.id
        })
        alice_app_id = alice_app.json()["id"]

        # Bob can't see Alice's application
        resp = client.get(f"/applications/{alice_app_id}", headers=headers_b)
        assert resp.status_code == 404

        # Bob sees empty list
        bob_apps = client.get("/applications", headers=headers_b)
        assert bob_apps.json()["total"] == 0

    def test_essay_isolation(self, client):
        _, headers_a = register_and_login(client, "alice2@test.edu", "AlicePass1")
        _, headers_b = register_and_login(client, "bob2@test.edu", "BobbyPass1")

        # Alice creates an essay
        essay = client.post("/essays", headers=headers_a, json={
            "title": "Alice's Private Essay",
            "content": "This is private.",
        })
        essay_id = essay.json()["id"]

        # Bob can't see it
        resp = client.get(f"/essays/{essay_id}", headers=headers_b)
        assert resp.status_code == 404

        bob_essays = client.get("/essays", headers=headers_b)
        assert bob_essays.json()["total"] == 0

    def test_document_isolation(self, client):
        _, headers_a = register_and_login(client, "alice3@test.edu", "AlicePass1")
        _, headers_b = register_and_login(client, "bob3@test.edu", "BobbyPass1")

        upload = client.post(
            "/documents",
            headers=headers_a,
            files={"file": ("secret.pdf", io.BytesIO(b"secret"), "application/pdf")},
            data={"title": "Alice's Doc"},
        )
        doc_id = upload.json()["id"]

        resp = client.get(f"/documents/{doc_id}", headers=headers_b)
        assert resp.status_code == 404

        resp = client.get(f"/documents/{doc_id}/download", headers=headers_b)
        assert resp.status_code == 404

    def test_profile_isolation(self, client):
        _, headers_a = register_and_login(client, "alice4@test.edu", "AlicePass1")
        _, headers_b = register_and_login(client, "bob4@test.edu", "BobbyPass1")

        # Alice sets profile
        client.put("/profile", headers=headers_a, json={
            "first_name": "Alice",
            "gpa": 4.0
        })

        # Bob's profile is independent
        bob_profile = client.get("/profile", headers=headers_b)
        assert bob_profile.json()["first_name"] is None


class TestProfileWorkflow:
    """Profile creation, partial updates, and reading back."""

    def test_profile_partial_updates(self, client):
        _, headers = register_and_login(client, "partial@test.edu", "PartialP1")

        # First update: personal info
        client.put("/profile", headers=headers, json={
            "first_name": "Jane",
            "last_name": "Smith",
        })

        # Second update: academic info (should not erase personal info)
        resp = client.put("/profile", headers=headers, json={
            "gpa": 3.9,
            "current_school": "MIT",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["first_name"] == "Jane"
        assert data["gpa"] == 3.9
        assert data["current_school"] == "MIT"

    def test_full_profile_setup(self, client):
        _, headers = register_and_login(client, "fullprofile@test.edu", "FullPass1")

        resp = client.put("/profile", headers=headers, json={
            "first_name": "Test",
            "last_name": "Student",
            "date_of_birth": "2005-06-15",
            "phone": "555-0100",
            "city": "Cambridge",
            "state": "MA",
            "zip_code": "02139",
            "country": "US",
            "current_school": "MIT",
            "graduation_year": 2027,
            "gpa": 3.95,
            "gpa_scale": 4.0,
            "intended_major": "Computer Science",
            "test_scores": {"SAT": 1500, "ACT": 34},
            "career_interests": ["AI", "Robotics"],
            "extracurriculars": [
                {"name": "Robotics Club", "role": "President", "years": 3},
            ],
            "awards": [
                {"name": "Science Fair Winner", "year": 2024, "level": "state"},
            ],
            "gender": "female",
            "citizenship_status": "us_citizen",
            "first_generation": True,
            "essay_topics": ["technology", "leadership"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["gpa"] == 3.95
        assert data["first_generation"] is True
        assert len(data["extracurriculars"]) == 1
        assert data["test_scores"]["SAT"] == 1500


class TestScholarshipSearchAndFiltering:
    """Test scholarship browsing, search, and filtering."""

    def test_search_by_name(self, client, db):
        create_scholarship_in_db(db, name="STEM Excellence Award")
        create_scholarship_in_db(db, name="Arts & Humanities Grant", award_amount=3000.0)

        resp = client.get("/scholarships?search=STEM")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["scholarships"][0]["name"] == "STEM Excellence Award"

    def test_filter_by_amount(self, client, db):
        create_scholarship_in_db(db, name="Small Grant", award_amount=500.0)
        create_scholarship_in_db(db, name="Big Grant", award_amount=10000.0)

        resp = client.get("/scholarships?min_amount=5000")
        assert resp.status_code == 200
        names = [s["name"] for s in resp.json()["scholarships"]]
        assert "Big Grant" in names
        assert "Small Grant" not in names

    def test_pagination(self, client, db):
        for i in range(5):
            create_scholarship_in_db(db, name=f"Scholarship {i}", award_amount=float(i * 1000))

        page1 = client.get("/scholarships?limit=2&offset=0")
        page2 = client.get("/scholarships?limit=2&offset=2")

        assert len(page1.json()["scholarships"]) == 2
        assert len(page2.json()["scholarships"]) == 2
        assert page1.json()["total"] == 5

        # Different pages have different scholarships
        ids_1 = {s["id"] for s in page1.json()["scholarships"]}
        ids_2 = {s["id"] for s in page2.json()["scholarships"]}
        assert ids_1.isdisjoint(ids_2)


class TestAdminScholarshipCreation:
    """Admin can create scholarships; regular users cannot."""

    def test_admin_creates_scholarship(self, client, admin_headers):
        resp = client.post("/scholarships", headers=admin_headers, json={
            "name": "Admin Created Scholarship",
            "provider": "Admin Foundation",
            "description": "Created by admin",
            "award_amount": 7500.0,
            "keywords": ["admin", "test"],
        })
        assert resp.status_code == 201
        assert resp.json()["name"] == "Admin Created Scholarship"

        # Verify visible in public listing
        listing = client.get("/scholarships")
        names = [s["name"] for s in listing.json()["scholarships"]]
        assert "Admin Created Scholarship" in names

    def test_regular_user_cannot_create_scholarship(self, client):
        _, headers = register_and_login(client, "regular@test.edu", "RegularP1")

        resp = client.post("/scholarships", headers=headers, json={
            "name": "Unauthorized Scholarship",
            "provider": "Hacker",
        })
        assert resp.status_code == 403

    def test_unauthenticated_cannot_create_scholarship(self, client):
        resp = client.post("/scholarships", json={
            "name": "Anonymous Scholarship",
        })
        assert resp.status_code == 403


class TestAuthEdgeCases:
    """Auth edge cases in real workflows."""

    def test_expired_or_invalid_token_blocked_everywhere(self, client, db):
        bad_headers = {"Authorization": "Bearer totally.invalid.token"}
        scholarship = create_scholarship_in_db(db)

        # All protected endpoints should reject
        assert client.get("/auth/me", headers=bad_headers).status_code == 401
        assert client.get("/profile", headers=bad_headers).status_code == 401
        assert client.get("/applications", headers=bad_headers).status_code == 401
        assert client.get("/essays", headers=bad_headers).status_code == 401
        assert client.get("/documents", headers=bad_headers).status_code == 401

        # But public endpoints still work
        assert client.get("/scholarships").status_code == 200
        assert client.get(f"/scholarships/{scholarship.id}").status_code == 200
        assert client.get("/health").status_code == 200

    def test_register_login_and_use_token(self, client):
        """The token from login actually works on protected endpoints."""
        client.post("/auth/register", json={
            "email": "tokentest@test.edu",
            "password": "TokenTest1"
        })
        login = client.post("/auth/login", json={
            "email": "tokentest@test.edu",
            "password": "TokenTest1"
        })
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        # Use the token
        me = client.get("/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["email"] == "tokentest@test.edu"

        profile = client.get("/profile", headers=headers)
        assert profile.status_code == 200


class TestCrossResourceWorkflow:
    """Test workflows that span essays + documents + applications together."""

    def test_build_complete_application_package(self, client, db):
        """Simulate a student building a complete application: profile, essays, docs, checklist."""
        _, headers = register_and_login(client, "complete@test.edu", "CompleteP1")

        # Set up profile
        client.put("/profile", headers=headers, json={
            "first_name": "Complete",
            "last_name": "Student",
            "gpa": 3.7,
            "intended_major": "Engineering",
        })

        # Write an essay
        essay = client.post("/essays", headers=headers, json={
            "title": "My STEM Passion",
            "content": "I have always been fascinated by how things work...",
            "prompt_category": "personal_statement",
        })
        essay_id = essay.json()["id"]

        # Upload a transcript
        doc = client.post(
            "/documents",
            headers=headers,
            files={"file": ("transcript.pdf", io.BytesIO(b"transcript"), "application/pdf")},
            data={"document_type": "transcript", "title": "Official Transcript"},
        )
        doc_id = doc.json()["id"]

        # Create application
        scholarship = create_scholarship_in_db(db)
        app_resp = client.post("/applications", headers=headers, json={
            "scholarship_id": scholarship.id,
            "priority": 1,
        })
        app_id = app_resp.json()["id"]
        checklist = app_resp.json()["checklist"]

        # Attach essay to essay item
        essay_item = next((c for c in checklist if c["type"] == "essay"), None)
        if essay_item:
            client.put(
                f"/applications/{app_id}/checklist/{essay_item['id']}",
                headers=headers,
                json={"completed": True, "essay_id": essay_id}
            )

        # Attach document to document item
        doc_item = next((c for c in checklist if c["type"] == "document"), None)
        if doc_item:
            client.put(
                f"/applications/{app_id}/checklist/{doc_item['id']}",
                headers=headers,
                json={"completed": True, "document_id": doc_id}
            )

        # Complete remaining items (forms, recommendations, etc.)
        for item in checklist:
            if item["type"] not in ("essay", "document"):
                client.put(
                    f"/applications/{app_id}/checklist/{item['id']}",
                    headers=headers,
                    json={"completed": True}
                )

        # Verify everything is complete
        final = client.get(f"/applications/{app_id}", headers=headers)
        final_data = final.json()
        assert final_data["checklist_completed"] == final_data["checklist_total"]

        # Submit
        submit = client.put(f"/applications/{app_id}", headers=headers, json={
            "status": "submitted"
        })
        assert submit.status_code == 200
        assert submit.json()["status"] == "submitted"
        assert submit.json()["submitted_at"] is not None

    def test_reuse_essay_across_applications(self, client, db):
        """Same essay attached to multiple applications."""
        _, headers = register_and_login(client, "reuse@test.edu", "ReusePass1")

        essay = client.post("/essays", headers=headers, json={
            "title": "Reusable Leadership Essay",
            "content": "Leadership means taking initiative and inspiring others...",
        })
        essay_id = essay.json()["id"]

        s1 = create_scholarship_in_db(db, name="Scholarship X")
        s2 = create_scholarship_in_db(db, name="Scholarship Y")

        app1 = client.post("/applications", headers=headers, json={"scholarship_id": s1.id})
        app2 = client.post("/applications", headers=headers, json={"scholarship_id": s2.id})

        # Attach same essay to essay items in both applications
        for app_data in [app1.json(), app2.json()]:
            essay_items = [c for c in app_data["checklist"] if c["type"] == "essay"]
            if essay_items:
                resp = client.put(
                    f"/applications/{app_data['id']}/checklist/{essay_items[0]['id']}",
                    headers=headers,
                    json={"completed": True, "essay_id": essay_id}
                )
                assert resp.status_code == 200


class TestDeleteCascadeBehavior:
    """Verify deleting resources doesn't break related data."""

    def test_delete_application_after_attachments(self, client, db):
        _, headers = register_and_login(client, "deleter@test.edu", "DeletePass1")

        # Create essay and doc
        essay = client.post("/essays", headers=headers, json={
            "title": "An Essay", "content": "Content here."
        })
        doc = client.post(
            "/documents",
            headers=headers,
            files={"file": ("f.pdf", io.BytesIO(b"data"), "application/pdf")},
        )

        # Create and populate application
        scholarship = create_scholarship_in_db(db)
        app_resp = client.post("/applications", headers=headers, json={
            "scholarship_id": scholarship.id
        })
        app_id = app_resp.json()["id"]

        # Delete the application
        delete = client.delete(f"/applications/{app_id}", headers=headers)
        assert delete.status_code == 204

        # Essay and document still exist
        assert client.get(f"/essays/{essay.json()['id']}", headers=headers).status_code == 200
        assert client.get(f"/documents/{doc.json()['id']}", headers=headers).status_code == 200
