import os
import re
import math
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF
from sqlalchemy.orm import Session
from app.config import settings
from app.models.all_models import Document, DocumentChunk


class DocumentService:
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        # Prevent path traversal and malicious filenames
        base = os.path.basename(filename)
        cleaned = re.sub(r'[^a-zA-Z0-9_.-]', '_', base)
        return cleaned or f"doc_{uuid.uuid4().hex[:8]}"

    @classmethod
    def process_file_upload(
        cls,
        db: Session,
        file_bytes: bytes,
        original_filename: str,
        project_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> Document:
        file_ext = Path(original_filename).suffix.lower()
        if file_ext not in settings.allowed_file_extensions:
            raise ValueError(
                f"Tipe file '{file_ext}' tidak didukung. Harap unggah {', '.join(settings.allowed_file_extensions)}"
            )

        if len(file_bytes) > settings.max_upload_size_bytes:
            max_mb = settings.max_upload_size_bytes / (1024 * 1024)
            raise ValueError(f"Ukuran file melebihi batas maksimal ({max_mb:.0f} MB)")

        doc_id = str(uuid.uuid4())
        safe_name = f"{doc_id}_{cls.sanitize_filename(original_filename)}"
        saved_path = settings.upload_dir / safe_name

        with open(saved_path, "wb") as f:
            f.write(file_bytes)

        display_title = title.strip() if title and title.strip() else Path(original_filename).stem
        file_type = file_ext.replace(".", "")

        # Extract text pages
        pages_content = cls.extract_text_by_pages(saved_path, file_type)
        total_pages = len(pages_content) if pages_content else 1

        doc = Document(
            id=doc_id,
            project_id=project_id,
            filename=safe_name,
            original_name=original_filename,
            file_type=file_type,
            file_size_bytes=len(file_bytes),
            title=display_title,
            total_pages=total_pages,
            total_chunks=0
        )
        db.add(doc)
        db.flush()

        # Chunk pages
        chunks_to_create = []
        chunk_idx = 0
        for page_num, text in pages_content:
            raw_chunks = cls.split_into_chunks(text, max_chunk_chars=800, overlap=100)
            for chunk_text in raw_chunks:
                if not chunk_text.strip():
                    continue
                chunk = DocumentChunk(
                    id=str(uuid.uuid4()),
                    document_id=doc.id,
                    chunk_index=chunk_idx,
                    page_number=page_num,
                    content=chunk_text.strip(),
                    token_count_estimate=len(chunk_text.split())
                )
                chunks_to_create.append(chunk)
                chunk_idx += 1

        db.add_all(chunks_to_create)
        doc.total_chunks = len(chunks_to_create)
        db.commit()
        db.refresh(doc)
        return doc

    @classmethod
    def extract_text_by_pages(cls, file_path: Path, file_type: str) -> List[tuple[int, str]]:
        pages = []
        if file_type == "pdf":
            doc = fitz.open(file_path)
            for page_index in range(len(doc)):
                page = doc[page_index]
                text = page.get_text("text")
                pages.append((page_index + 1, text))
            doc.close()
        else:
            # Plain text or Markdown
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            # If multiple markers exist or just treat as page 1
            pages.append((1, content))
        return pages

    @staticmethod
    def split_into_chunks(text: str, max_chunk_chars: int = 800, overlap: int = 100) -> List[str]:
        cleaned = re.sub(r'\s+', ' ', text).strip()
        if not cleaned:
            return []
        if len(cleaned) <= max_chunk_chars:
            return [cleaned]

        chunks = []
        start = 0
        while start < len(cleaned):
            end = start + max_chunk_chars
            if end >= len(cleaned):
                chunks.append(cleaned[start:])
                break
            # Try splitting at sentence or space
            split_at = cleaned.rfind('. ', start + overlap, end)
            if split_at == -1:
                split_at = cleaned.rfind(' ', start + overlap, end)
            if split_at == -1 or split_at <= start:
                split_at = end

            chunks.append(cleaned[start:split_at].strip())
            start = split_at + 1 if split_at < end else end - overlap

        return chunks

    @classmethod
    def search_relevant_chunks(
        cls,
        db: Session,
        query: str,
        document_ids: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        TF-IDF / keyword retrieval across document chunks.
        """
        query_terms = [re.escape(w.lower()) for w in re.findall(r'\w+', query) if len(w) > 2]
        if not query_terms:
            return []

        q = db.query(DocumentChunk, Document).join(Document, DocumentChunk.document_id == Document.id)
        if document_ids:
            q = q.filter(Document.id.in_(document_ids))

        all_records = q.all()
        scored_results = []

        total_docs = max(len(all_records), 1)

        # Calculate term frequencies
        for chunk, doc in all_records:
            content_lower = chunk.content.lower()
            score = 0.0
            matched_terms = 0

            for term in query_terms:
                count = content_lower.count(term)
                if count > 0:
                    matched_terms += 1
                    # TF component
                    tf = math.log1p(count)
                    score += tf

            if score > 0:
                # Boost if multiple query terms matched
                term_coverage = matched_terms / len(query_terms)
                final_score = score * (1.0 + term_coverage)
                scored_results.append({
                    "document_id": doc.id,
                    "document_title": doc.title,
                    "chunk_id": chunk.id,
                    "page_number": chunk.page_number,
                    "content": chunk.content,
                    "relevance_score": round(final_score, 3),
                    "is_verified": True
                })

        scored_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored_results[:top_k]
