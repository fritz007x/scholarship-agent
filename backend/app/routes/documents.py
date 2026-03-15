from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import os

from app.database import get_db
from app.schemas.document import DocumentCreate, DocumentUpdate, DocumentResponse, DocumentList
from app.services.document import DocumentService
from app.services.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("", response_model=DocumentList)
def list_documents(
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all documents for the current user."""
    doc_service = DocumentService(db)
    documents = doc_service.get_all_documents(current_user.id, document_type=document_type)
    return DocumentList(documents=documents, total=len(documents))


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # Comma-separated
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a new document."""
    doc_service = DocumentService(db)

    # Parse tags from comma-separated string
    tag_list = []
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    document_data = DocumentCreate(
        document_type=document_type,
        title=title,
        description=description,
        tags=tag_list
    )

    return await doc_service.create_document(current_user.id, file, document_data)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get document metadata."""
    doc_service = DocumentService(db)
    document = doc_service.get_document(document_id, current_user.id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return document


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download a document file."""
    doc_service = DocumentService(db)
    document = doc_service.get_document(document_id, current_user.id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    file_path = doc_service.get_file_path(document_id, current_user.id)

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk"
        )

    return FileResponse(
        path=file_path,
        filename=document.original_filename,
        media_type=document.mime_type
    )


@router.put("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: int,
    update_data: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update document metadata."""
    doc_service = DocumentService(db)
    return doc_service.update_document(document_id, current_user.id, update_data)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document and its file."""
    doc_service = DocumentService(db)
    if not doc_service.delete_document(document_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
