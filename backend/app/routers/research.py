from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.all_models import ResearchProject
from app.schemas.all_schemas import (
    ProjectCreate, ProjectUpdate, ProjectOut
)
from app.services.prompt_builder import PromptBuilder

router = APIRouter(prefix="/api/research", tags=["Research"])


@router.get("/projects", response_model=List[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(ResearchProject).order_by(ResearchProject.updated_at.desc()).all()


@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = ResearchProject(
        title=payload.title,
        description=payload.description,
        research_question=payload.research_question,
        notes=payload.notes
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(ResearchProject).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyek penelitian tidak ditemukan.")
    return project


@router.put("/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(ResearchProject).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyek penelitian tidak ditemukan.")

    if payload.title is not None:
        project.title = payload.title
    if payload.description is not None:
        project.description = payload.description
    if payload.research_question is not None:
        project.research_question = payload.research_question
    if payload.notes is not None:
        project.notes = payload.notes

    db.commit()
    db.refresh(project)
    return project


@router.delete("/projects/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(ResearchProject).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyek penelitian tidak ditemukan.")
    db.delete(project)
    db.commit()
    return {"success": True, "message": "Proyek penelitian berhasil dihapus."}


@router.get("/notebooklm-prompt")
def generate_notebooklm_prompt(
    research_question: str,
    notes: Optional[str] = None
):
    prompt = PromptBuilder.build_notebooklm_prompt(
        research_question=research_question,
        project_notes=notes
    )
    return {
        "prompt": prompt,
        "official_url": "https://notebooklm.google.com"
    }
