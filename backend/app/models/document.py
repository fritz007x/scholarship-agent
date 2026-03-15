from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # File Information
    filename = Column(String, nullable=False)  # Generated unique filename
    original_filename = Column(String, nullable=False)  # User's original filename
    file_path = Column(String, nullable=False)  # Relative path in uploads directory
    file_size = Column(Integer)  # Bytes
    mime_type = Column(String)

    # Categorization
    document_type = Column(String)  # transcript, recommendation_letter, resume, financial_document, essay, other
    title = Column(String)  # User-friendly title
    description = Column(String)
    tags = Column(JSON, default=list)

    # Versioning
    version = Column(Integer, default=1)
    parent_document_id = Column(Integer, ForeignKey("documents.id"))

    # Usage tracking
    used_in_applications = Column(JSON, default=list)  # [application_id, ...]

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="documents")
    parent_document = relationship("Document", remote_side=[id])
