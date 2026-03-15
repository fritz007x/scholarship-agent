import pytest
from unittest.mock import MagicMock
from app.services.checklist import ChecklistGenerator


class TestGenerateChecklist:
    def _make_scholarship(self, requirements=None):
        scholarship = MagicMock()
        scholarship.application_requirements = requirements or {}
        return scholarship

    def test_always_includes_form(self):
        scholarship = self._make_scholarship()
        checklist = ChecklistGenerator.generate_checklist(scholarship)
        assert len(checklist) == 1
        assert checklist[0]["type"] == "form"
        assert checklist[0]["completed"] is False

    def test_parses_essays(self):
        scholarship = self._make_scholarship({
            "essays": [
                {"prompt": "Why STEM?", "word_count": 500},
                {"prompt": "Leadership experience"}
            ]
        })
        checklist = ChecklistGenerator.generate_checklist(scholarship)
        essay_items = [i for i in checklist if i["type"] == "essay"]
        assert len(essay_items) == 2
        assert "500 words" in essay_items[0]["description"]

    def test_parses_documents(self):
        scholarship = self._make_scholarship({
            "documents": ["transcript", "recommendation_letter"]
        })
        checklist = ChecklistGenerator.generate_checklist(scholarship)
        doc_items = [i for i in checklist if i["type"] == "document"]
        assert len(doc_items) == 2
        assert "Official transcript" in doc_items[0]["description"]

    def test_parses_recommendations(self):
        scholarship = self._make_scholarship({"recommendations": 3})
        checklist = ChecklistGenerator.generate_checklist(scholarship)
        rec_items = [i for i in checklist if i["type"] == "recommendation"]
        assert len(rec_items) == 3

    def test_parses_other_requirements(self):
        scholarship = self._make_scholarship({
            "other": ["Interview", "Portfolio submission"]
        })
        checklist = ChecklistGenerator.generate_checklist(scholarship)
        other_items = [i for i in checklist if i["type"] == "other"]
        assert len(other_items) == 2

    def test_full_requirements(self):
        scholarship = self._make_scholarship({
            "essays": [{"prompt": "Essay 1"}],
            "documents": ["transcript"],
            "recommendations": 1,
            "other": ["Interview"]
        })
        checklist = ChecklistGenerator.generate_checklist(scholarship)
        # 1 form + 1 essay + 1 document + 1 recommendation + 1 other = 5
        assert len(checklist) == 5


class TestCalculateProgress:
    def test_empty_checklist(self):
        total, completed = ChecklistGenerator.calculate_progress([])
        assert total == 0
        assert completed == 0

    def test_none_completed(self):
        checklist = [
            {"id": "1", "completed": False},
            {"id": "2", "completed": False},
        ]
        total, completed = ChecklistGenerator.calculate_progress(checklist)
        assert total == 2
        assert completed == 0

    def test_some_completed(self):
        checklist = [
            {"id": "1", "completed": True},
            {"id": "2", "completed": False},
            {"id": "3", "completed": True},
        ]
        total, completed = ChecklistGenerator.calculate_progress(checklist)
        assert total == 3
        assert completed == 2

    def test_all_completed(self):
        checklist = [
            {"id": "1", "completed": True},
            {"id": "2", "completed": True},
        ]
        total, completed = ChecklistGenerator.calculate_progress(checklist)
        assert total == 2
        assert completed == 2


class TestMarkItemComplete:
    def test_mark_complete(self):
        checklist = [{"id": "abc", "completed": False, "essay_id": None, "document_id": None}]
        result = ChecklistGenerator.mark_item_complete(checklist, "abc", completed=True)
        assert result[0]["completed"] is True

    def test_mark_with_essay(self):
        checklist = [{"id": "abc", "completed": False, "essay_id": None, "document_id": None}]
        result = ChecklistGenerator.mark_item_complete(checklist, "abc", completed=True, essay_id=42)
        assert result[0]["essay_id"] == 42

    def test_mark_nonexistent_item(self):
        checklist = [{"id": "abc", "completed": False, "essay_id": None, "document_id": None}]
        result = ChecklistGenerator.mark_item_complete(checklist, "xyz", completed=True)
        assert result[0]["completed"] is False
