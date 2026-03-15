import uuid
from typing import List, Dict, Any, Optional
from app.models.scholarship import Scholarship
from app.schemas.application import ChecklistItem


class ChecklistGenerator:
    """Generates application checklists from scholarship requirements."""

    @staticmethod
    def generate_checklist(scholarship: Scholarship) -> List[Dict[str, Any]]:
        checklist = []

        # Always add application form item
        checklist.append({
            "id": str(uuid.uuid4()),
            "type": "form",
            "description": "Complete application form",
            "completed": False,
            "essay_id": None,
            "document_id": None
        })

        app_requirements = scholarship.application_requirements or {}

        # Parse essay requirements
        essays = app_requirements.get("essays", [])
        for i, essay_req in enumerate(essays):
            prompt = essay_req.get("prompt", f"Essay {i + 1}")
            word_count = essay_req.get("word_count")

            description = prompt
            if word_count:
                description = f"{prompt} ({word_count} words)"

            checklist.append({
                "id": str(uuid.uuid4()),
                "type": "essay",
                "description": description,
                "completed": False,
                "essay_id": None,
                "document_id": None
            })

        # Parse document requirements
        documents = app_requirements.get("documents", [])
        document_type_labels = {
            "transcript": "Official transcript",
            "recommendation_letter": "Letter of recommendation",
            "resume": "Resume/CV",
            "financial_document": "Financial documentation",
            "essay": "Written essay document"
        }

        for doc in documents:
            if isinstance(doc, str):
                description = document_type_labels.get(doc, doc.replace("_", " ").title())
            else:
                description = doc.get("name", "Document")

            checklist.append({
                "id": str(uuid.uuid4()),
                "type": "document",
                "description": description,
                "completed": False,
                "essay_id": None,
                "document_id": None
            })

        # Parse recommendation requirements
        recommendations = app_requirements.get("recommendations", 0)
        if isinstance(recommendations, int):
            for i in range(recommendations):
                checklist.append({
                    "id": str(uuid.uuid4()),
                    "type": "recommendation",
                    "description": f"Letter of recommendation #{i + 1}",
                    "completed": False,
                    "essay_id": None,
                    "document_id": None
                })

        # Parse other requirements
        other = app_requirements.get("other", [])
        for item in other:
            if isinstance(item, str):
                checklist.append({
                    "id": str(uuid.uuid4()),
                    "type": "other",
                    "description": item,
                    "completed": False,
                    "essay_id": None,
                    "document_id": None
                })

        return checklist

    @staticmethod
    def mark_item_complete(
        checklist: List[Dict[str, Any]],
        item_id: str,
        completed: bool = True,
        essay_id: Optional[int] = None,
        document_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Mark a checklist item as complete and optionally attach a resource."""
        for item in checklist:
            if item["id"] == item_id:
                item["completed"] = completed
                if essay_id is not None:
                    item["essay_id"] = essay_id
                if document_id is not None:
                    item["document_id"] = document_id
                break
        return checklist

    @staticmethod
    def calculate_progress(checklist: List[Dict[str, Any]]) -> tuple[int, int]:
        """Calculate total and completed items count."""
        total = len(checklist)
        completed = sum(1 for item in checklist if item.get("completed", False))
        return total, completed
