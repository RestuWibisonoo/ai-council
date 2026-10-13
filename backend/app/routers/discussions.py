from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.all_models import (
    Conversation, DiscussionRun, ModelResponse, Synthesis, Message
)
from app.schemas.all_schemas import (
    DiscussionCreateRequest,
    DiscussionRunOut,
    ModelResponseOut,
    SubmitManualResponseRequest,
    SubmitManualSynthesisRequest,
    ConversationOut,
    ConversationDetailOut
)
from app.services.orchestrator import Orchestrator

router = APIRouter(prefix="/api/discussions", tags=["Discussions"])


@router.post("", response_model=DiscussionRunOut, status_code=status.HTTP_201_CREATED)
async def create_discussion(
    payload: DiscussionCreateRequest,
    db: Session = Depends(get_db)
):
    if not payload.selected_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pilih setidaknya satu provider AI untuk diskusi."
        )

    try:
        run = await Orchestrator.create_discussion_run(
            db=db,
            query=payload.query,
            mode=payload.mode,
            selected_providers=payload.selected_providers,
            max_rounds=payload.max_rounds,
            project_id=payload.project_id,
            linked_document_ids=payload.linked_document_ids,
            conversation_title=payload.conversation_title
        )
        return run
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal memulai diskusi: {str(e)}"
        )


@router.get("/{run_id}", response_model=DiscussionRunOut)
def get_discussion_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(DiscussionRun).filter_by(id=run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesi diskusi tidak ditemukan."
        )
    return run


@router.post("/{run_id}/responses", response_model=ModelResponseOut)
def submit_response(
    run_id: str,
    payload: SubmitManualResponseRequest,
    db: Session = Depends(get_db)
):
    try:
        resp = Orchestrator.submit_manual_response(
            db=db,
            response_id=payload.response_id,
            content=payload.content,
            model_id=payload.model_id,
            status=payload.status
        )
        return resp
    except ValueError as ve:
        status_code = status.HTTP_404_NOT_FOUND if "tidak ditemukan" in str(ve).lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{run_id}/advance", response_model=DiscussionRunOut)
async def advance_debate(run_id: str, db: Session = Depends(get_db)):
    try:
        run = await Orchestrator.advance_debate_stage(db=db, run_id=run_id)
        return run
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{run_id}/continue-to-debate", response_model=DiscussionRunOut, status_code=status.HTTP_201_CREATED)
def continue_to_debate(run_id: str, db: Session = Depends(get_db)):
    try:
        debate_run = Orchestrator.continue_to_debate(db=db, run_id=run_id)
        return debate_run
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{run_id}/synthesis")
def submit_synthesis(
    run_id: str,
    payload: SubmitManualSynthesisRequest,
    db: Session = Depends(get_db)
):
    try:
        synth = Orchestrator.submit_synthesis(
            db=db,
            run_id=run_id,
            raw_synthesis=payload.raw_synthesis,
            moderator_provider=payload.moderator_provider,
            allow_partial=payload.allow_partial,
            problem_summary=payload.problem_summary,
            consensus_points=payload.consensus_points,
            disagreements=payload.disagreements,
            unresolved_critiques=payload.unresolved_critiques,
            evidence_backed_claims=payload.evidence_backed_claims,
            recommendations=payload.recommendations,
            uncertainties_and_verifications=payload.uncertainties_and_verifications,
            references_cited=payload.references_cited
        )
        return {"success": True, "synthesis_id": synth.id}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{run_id}/stop", response_model=DiscussionRunOut)
def stop_discussion(run_id: str, db: Session = Depends(get_db)):
    try:
        run = Orchestrator.stop_discussion(db=db, run_id=run_id)
        return run
    except ValueError as ve:
        status_code = status.HTTP_404_NOT_FOUND if "tidak ditemukan" in str(ve).lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(ve))


@router.post("/{run_id}/resume", response_model=DiscussionRunOut)
def resume_discussion(run_id: str, db: Session = Depends(get_db)):
    try:
        run = Orchestrator.resume_discussion(db=db, run_id=run_id)
        return run
    except ValueError as ve:
        status_code = status.HTTP_404_NOT_FOUND if "tidak ditemukan" in str(ve).lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(ve))



@router.get("/{run_id}/export")
def export_report(
    run_id: str,
    format: Optional[str] = "md",
    db: Session = Depends(get_db)
):
    try:
        report_text = Orchestrator.generate_markdown_report(db=db, run_id=run_id)
        fmt = (format or "md").lower().strip()
        if fmt == "txt":
            media_type = "text/plain; charset=utf-8"
            filename = f"ai_council_report_{run_id[:8]}.txt"
        else:
            media_type = "text/markdown; charset=utf-8"
            filename = f"ai_council_report_{run_id[:8]}.md"

        return PlainTextResponse(
            content=report_text,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-cache"
            }
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))


# Conversation endpoints
conv_router = APIRouter(prefix="/api/conversations", tags=["Conversations"])


@conv_router.get("", response_model=List[ConversationOut])
def list_conversations(project_id: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Conversation)
    if project_id:
        q = q.filter_by(project_id=project_id)
    return q.order_by(Conversation.updated_at.desc()).all()


@conv_router.get("/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter_by(id=conversation_id).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Percakapan tidak ditemukan.")
    return conv


@conv_router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter_by(id=conversation_id).first()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Percakapan tidak ditemukan.")
    db.delete(conv)
    db.commit()
    return {"success": True, "message": "Percakapan berhasil dihapus."}
