from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.all_models import Document, DocumentChunk
from app.schemas.all_schemas import (
    DocumentOut, DocumentDetailOut, DocumentSearchResult
)
from app.services.document_service import DocumentService
from app.config import settings

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    project_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    try:
        content_bytes = await file.read()
        doc = DocumentService.process_file_upload(
            db=db,
            file_bytes=content_bytes,
            original_filename=file.filename or "uploaded_file.txt",
            project_id=project_id,
            title=title
        )
        return doc
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal memproses dokumen: {str(e)}"
        )


@router.get("", response_model=List[DocumentOut])
def list_documents(project_id: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Document)
    if project_id:
        q = q.filter_by(project_id=project_id)
    return q.order_by(Document.created_at.desc()).all()


@router.get("/{document_id}", response_model=DocumentDetailOut)
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter_by(id=document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dokumen tidak ditemukan.")
    return doc


@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter_by(id=document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dokumen tidak ditemukan.")

    # Remove physical file if exists and verify strict path containment
    try:
        file_path = (settings.upload_dir / doc.filename).resolve()
        if file_path.exists() and file_path.is_relative_to(settings.upload_dir.resolve()):
            file_path.unlink()
    except Exception:
        pass

    db.delete(doc)
    db.commit()
    return {"success": True, "message": "Dokumen berhasil dihapus."}


@router.post("/search", response_model=List[DocumentSearchResult])
def search_documents(
    query: str,
    document_ids: Optional[List[str]] = None,
    top_k: int = 5,
    db: Session = Depends(get_db)
):
    if not query.strip():
        return []
    results = DocumentService.search_relevant_chunks(
        db=db,
        query=query,
        document_ids=document_ids,
        top_k=top_k
    )
    return results
