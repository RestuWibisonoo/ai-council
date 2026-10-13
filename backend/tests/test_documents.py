import io
import pytest
import fitz  # PyMuPDF


def test_upload_text_and_search(client):
    content = "Microservices architecture membagi aplikasi menjadi beberapa layanan independen yang berkomunikasi melalui API HTTP atau gRPC."
    file_bytes = content.encode("utf-8")

    response = client.post(
        "/api/documents/upload",
        files={"file": ("microservices_guide.txt", io.BytesIO(file_bytes), "text/plain")},
        data={"title": "Panduan Microservices"}
    )
    assert response.status_code == 201
    doc_data = response.json()
    assert doc_data["title"] == "Panduan Microservices"
    assert doc_data["total_chunks"] >= 1

    # Search for relevant chunk
    search_res = client.post(
        "/api/documents/search",
        params={"query": "microservices independen gRPC"}
    )
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results) >= 1
    assert "gRPC" in results[0]["content"]
    assert results[0]["page_number"] == 1


def test_upload_pdf_with_pymupdf(client):
    # Dynamically create a small valid in-memory PDF using PyMuPDF
    pdf_doc = fitz.open()
    page1 = pdf_doc.new_page()
    page1.insert_text((50, 72), "Halaman 1: Konsep Artificial Intelligence dan Reinforcement Learning.")
    page2 = pdf_doc.new_page()
    page2.insert_text((50, 72), "Halaman 2: Evaluasi multi-agen pada game theory dan model diskursus.")
    pdf_bytes = pdf_doc.tobytes()
    pdf_doc.close()

    response = client.post(
        "/api/documents/upload",
        files={"file": ("ai_research_paper.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        data={"title": "AI Research Paper"}
    )
    assert response.status_code == 201
    doc_data = response.json()
    assert doc_data["file_type"] == "pdf"
    assert doc_data["total_pages"] == 2
    assert doc_data["total_chunks"] >= 2

    # Search for page 2 content
    search_res = client.post(
        "/api/documents/search",
        params={"query": "game theory diskursus"}
    )
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results) >= 1
    assert results[0]["page_number"] == 2


def test_upload_empty_file_rejected(client):
    response = client.post(
        "/api/documents/upload",
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        data={"title": "Empty File"}
    )
    assert response.status_code == 400
    assert "kosong" in response.json()["detail"].lower()


def test_upload_corrupt_pdf_rejected(client):
    response = client.post(
        "/api/documents/upload",
        files={"file": ("corrupt.pdf", io.BytesIO(b"not a valid pdf content header"), "application/pdf")},
        data={"title": "Corrupt PDF"}
    )
    assert response.status_code == 400
    assert "file pdf rusak atau tidak dapat dibaca" in response.json()["detail"].lower()


def test_delete_document_and_file_cleanup(client):
    content = "Catatan metodologi riset komparatif."
    res = client.post(
        "/api/documents/upload",
        files={"file": ("metodologi.txt", io.BytesIO(content.encode()), "text/plain")},
        data={"title": "Metodologi"}
    )
    assert res.status_code == 201
    doc_id = res.json()["id"]

    # Delete the document
    del_res = client.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Check search no longer returns it
    search_res = client.post(
        "/api/documents/search",
        params={"query": "metodologi riset komparatif"}
    )
    assert search_res.status_code == 200
    assert len(search_res.json()) == 0


