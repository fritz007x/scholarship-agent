import os
import uuid
import shutil
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, UploadFile
from typing import List, Optional, Set

from app.models.document import Document
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.config import get_settings

settings = get_settings()

# Allowed file types for upload
ALLOWED_EXTENSIONS: Set[str] = {
    '.pdf', '.doc', '.docx', '.txt', '.rtf',
    '.png', '.jpg', '.jpeg', '.gif',
    '.xls', '.xlsx', '.csv'
}

ALLOWED_MIME_TYPES: Set[str] = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
    'application/rtf',
    'image/png', 'image/jpeg', 'image/gif',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/csv'
}


class DocumentService:
    def __init__(self, db: Session):
        self.db = db

    def get_document(self, document_id: int, user_id: int) -> Optional[Document]:
        return self.db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == user_id
        ).first()

    def get_all_documents(
        self,
        user_id: int,
        document_type: Optional[str] = None
    ) -> List[Document]:
        query = self.db.query(Document).filter(Document.user_id == user_id)

        if document_type:
            query = query.filter(Document.document_type == document_type)

        return query.order_by(Document.updated_at.desc()).all()

    def _get_user_upload_dir(self, user_id: int) -> str:
        user_dir = os.path.join(settings.upload_dir, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        return user_dir

    def _generate_unique_filename(self, original_filename: str) -> str:
        ext = os.path.splitext(original_filename)[1]
        return f"{uuid.uuid4()}{ext}"

    async def create_document(
        self,
        user_id: int,
        file: UploadFile,
        document_data: DocumentCreate
    ) -> Document:
        # Validate file extension
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type '{ext}' not allowed. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        # Validate MIME type
        if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"MIME type '{file.content_type}' not allowed"
            )

        # Validate file size
        max_size = settings.max_upload_size_mb * 1024 * 1024
        content = await file.read()
        if len(content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum of {settings.max_upload_size_mb}MB"
            )

        # Generate unique filename and save
        user_dir = self._get_user_upload_dir(user_id)
        unique_filename = self._generate_unique_filename(file.filename)
        file_path = os.path.join(user_dir, unique_filename)
        relative_path = os.path.join(str(user_id), unique_filename)

        with open(file_path, "wb") as f:
            f.write(content)

        document = Document(
            user_id=user_id,
            filename=unique_filename,
            original_filename=file.filename,
            file_path=relative_path,
            file_size=len(content),
            mime_type=file.content_type,
            document_type=document_data.document_type,
            title=document_data.title or file.filename,
            description=document_data.description,
            tags=document_data.tags or [],
            used_in_applications=[]
        )

        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def update_document(self, document_id: int, user_id: int, update_data: DocumentUpdate) -> Document:
        document = self.get_document(document_id, user_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        update_dict = update_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            setattr(document, field, value)

        self.db.commit()
        self.db.refresh(document)
        return document

    def delete_document(self, document_id: int, user_id: int) -> bool:
        document = self.get_document(document_id, user_id)

        if not document:
            return False

        # Delete file from disk
        file_path = os.path.join(settings.upload_dir, document.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)

        self.db.delete(document)
        self.db.commit()
        return True

    def get_file_path(self, document_id: int, user_id: int) -> Optional[str]:
        document = self.get_document(document_id, user_id)
        if not document:
            return None
        return os.path.join(settings.upload_dir, document.file_path)

    def add_usage(self, document_id: int, user_id: int, application_id: int) -> Document:
        """Track that a document was used in an application."""
        document = self.get_document(document_id, user_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        used_in = document.used_in_applications or []
        if application_id not in used_in:
            used_in.append(application_id)
            document.used_in_applications = used_in
            self.db.commit()
            self.db.refresh(document)

        return document
