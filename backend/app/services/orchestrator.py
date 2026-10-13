import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.all_models import (
    Conversation,
    DiscussionRun,
    DiscussionRound,
    ModelResponse,
    Critique,
    Synthesis,
    SourceReference,
    Message,
    ProviderConfiguration,
    UsageRecord
)
from app.services.prompt_builder import PromptBuilder
from app.services.document_service import DocumentService
from app.services.provider_manager import provider_manager


class Orchestrator:
    @classmethod
    async def create_discussion_run(
        cls,
        db: Session,
        query: str,
        mode: str = "parallel",
        selected_providers: Optional[List[str]] = None,
        max_rounds: int = 2,
        project_id: Optional[str] = None,
        linked_document_ids: Optional[List[str]] = None,
        conversation_title: Optional[str] = None
    ) -> DiscussionRun:
        selected_providers = selected_providers or ["chatgpt", "claude", "gemini"]
        linked_document_ids = linked_document_ids or []

        # 1. Create or link Conversation
        title = conversation_title or (query[:50] + ("..." if len(query) > 50 else ""))
        conv = Conversation(
            project_id=project_id,
            title=title,
            mode=mode
        )
        db.add(conv)
        db.flush()

        # Add initial user message
        db.add(Message(
            conversation_id=conv.id,
            role="user",
            content=query
        ))

        # 2. Retrieve document chunks if linked
        doc_chunks = []
        if linked_document_ids:
            doc_chunks = DocumentService.search_relevant_chunks(
                db, query=query, document_ids=linked_document_ids, top_k=5
            )

        # 3. Create DiscussionRun
        stage = "initial_analysis" if mode == "debate" else "parallel_analysis"
        run = DiscussionRun(
            conversation_id=conv.id,
            mode=mode,
            status="awaiting_input",
            current_stage=stage,
            current_round=1,
            max_rounds=max_rounds,
            query=query,
            selected_providers=selected_providers,
            linked_document_ids=linked_document_ids
        )
        db.add(run)
        db.flush()

        # Save source references
        for item in doc_chunks:
            ref = SourceReference(
                run_id=run.id,
                document_id=item["document_id"],
                chunk_id=item["chunk_id"],
                quote=item["content"][:300] + ("..." if len(item["content"]) > 300 else ""),
                page_number=item["page_number"],
                relevance_score=item["relevance_score"],
                is_verified=True,
                source_type="document"
            )
            db.add(ref)

        # 4. Create Round 1
        round_1 = DiscussionRound(
            run_id=run.id,
            round_number=1,
            stage=stage,
            status="in_progress"
        )
        db.add(round_1)
        db.flush()

        # 5. Initialize responses for each selected provider
        api_tasks = []
        for pid in selected_providers:
            provider_cfg = db.query(ProviderConfiguration).filter_by(id=pid).first()
            model_id = provider_cfg.selected_model if provider_cfg else pid
            is_api = bool(provider_cfg and provider_cfg.default_mode == "api" and provider_manager.is_api_configured(pid))

            if mode == "debate":
                prompt = PromptBuilder.build_initial_debate_prompt(
                    query=query,
                    provider=pid,
                    round_number=1,
                    document_chunks=doc_chunks
                )
            else:
                prompt = PromptBuilder.build_parallel_prompt(
                    query=query,
                    provider=pid,
                    document_chunks=doc_chunks
                )

            resp = ModelResponse(
                run_id=run.id,
                round_id=round_1.id,
                provider=pid,
                model_id=model_id,
                stage=stage,
                integration_mode="api" if is_api else "manual",
                prompt_used=prompt,
                content="",
                status="pending"
            )
            db.add(resp)
            db.flush()

            if is_api:
                api_tasks.append((resp.id, pid, model_id, prompt))

        db.commit()
        db.refresh(run)

        # Run API tasks in background or synchronously if any
        if api_tasks:
            await cls._execute_api_tasks(db, api_tasks, run.id)

        # Refresh state
        db.refresh(run)
        cls._update_run_status(db, run)
        return run

    @classmethod
    async def _execute_api_tasks(cls, db: Session, tasks: list, run_id: str):
        for resp_id, pid, model_id, prompt in tasks:
            adapter = provider_manager.get_adapter(pid, model=model_id)
            if adapter:
                try:
                    result = await adapter.complete(prompt=prompt)
                    resp = db.query(ModelResponse).filter_by(id=resp_id).first()
                    if resp:
                        if result.error:
                            resp.status = "failed"
                            resp.error_message = result.error
                        else:
                            resp.status = "completed"
                            resp.content = result.content
                            resp.prompt_tokens = result.prompt_tokens
                            resp.completion_tokens = result.completion_tokens
                            resp.total_tokens = result.total_tokens
                            resp.estimated_cost_usd = result.estimated_cost_usd

                            # Record usage
                            db.add(UsageRecord(
                                provider=pid,
                                model_id=model_id,
                                mode="api",
                                action="initial_analysis",
                                prompt_tokens=result.prompt_tokens,
                                completion_tokens=result.completion_tokens,
                                total_tokens=result.total_tokens,
                                estimated_cost_usd=result.estimated_cost_usd,
                                is_actual_cost=False,
                                run_id=run_id
                            ))
                        db.commit()
                except Exception as e:
                    resp = db.query(ModelResponse).filter_by(id=resp_id).first()
                    if resp:
                        resp.status = "failed"
                        resp.error_message = f"Panggilan API gagal: {str(e)}"
                        db.commit()

    @classmethod
    def submit_manual_response(
        cls,
        db: Session,
        response_id: str,
        content: str,
        model_id: Optional[str] = None,
        status: str = "completed"
    ) -> ModelResponse:
        resp = db.query(ModelResponse).filter_by(id=response_id).first()
        if not resp:
            raise ValueError("Respons tidak ditemukan.")

        resp.content = content.strip()
        resp.status = status
        if model_id:
            resp.model_id = model_id

        # Estimate tokens roughly (~4 chars/token) for transparency
        est_tokens = len(content.split()) * 2
        resp.completion_tokens = est_tokens
        resp.total_tokens = est_tokens

        # Record manual usage
        db.add(UsageRecord(
            provider=resp.provider,
            model_id=resp.model_id or "manual",
            mode="manual",
            action=resp.stage,
            prompt_tokens=len(resp.prompt_used.split()) * 2,
            completion_tokens=est_tokens,
            total_tokens=est_tokens,
            estimated_cost_usd=0.0,
            is_actual_cost=False,
            run_id=resp.run_id
        ))

        db.commit()
        db.refresh(resp)

        # Update run status
        run = db.query(DiscussionRun).filter_by(id=resp.run_id).first()
        if run:
            cls._update_run_status(db, run)

        return resp

    @classmethod
    def _update_run_status(cls, db: Session, run: DiscussionRun):
        responses = db.query(ModelResponse).filter_by(run_id=run.id, stage=run.current_stage).all()
        all_done = responses and all(r.status in ("completed", "failed") for r in responses)

        if run.mode == "parallel":
            if all_done:
                run.status = "completed"
            else:
                run.status = "awaiting_input"
        elif run.mode == "debate":
            if run.current_stage == "final_synthesis":
                synthesis = db.query(Synthesis).filter_by(run_id=run.id).first()
                if synthesis:
                    run.status = "completed"
                else:
                    run.status = "awaiting_input"
            else:
                run.status = "awaiting_input"

        db.commit()

    @classmethod
    async def advance_debate_stage(cls, db: Session, run_id: str) -> DiscussionRun:
        run = db.query(DiscussionRun).filter_by(id=run_id).first()
        if not run:
            raise ValueError("Sesi diskusi tidak ditemukan.")
        if run.mode != "debate":
            raise ValueError("Hanya sesi debat yang memiliki alur tahapan multi-stage.")

        current_stage = run.current_stage

        if current_stage == "initial_analysis":
            # Transition to Cross-Critique
            run.current_stage = "cross_critique"
            active_round = db.query(DiscussionRound).filter_by(
                run_id=run.id, round_number=run.current_round
            ).first()

            # Gather initial responses
            initial_responses = db.query(ModelResponse).filter_by(
                run_id=run.id, stage="initial_analysis", status="completed"
            ).all()

            resp_data = [{"provider": r.provider, "content": r.content} for r in initial_responses]

            # Generate cross critiques for each provider
            for r in initial_responses:
                critique_prompt = PromptBuilder.build_critique_prompt(
                    query=run.query,
                    reviewer_provider=r.provider,
                    all_responses=resp_data,
                    round_number=run.current_round
                )

                # Check if reviewer has API
                provider_cfg = db.query(ProviderConfiguration).filter_by(id=r.provider).first()
                is_api = bool(provider_cfg and provider_cfg.default_mode == "api" and provider_manager.is_api_configured(r.provider))

                critique_resp = ModelResponse(
                    run_id=run.id,
                    round_id=active_round.id if active_round else None,
                    provider=r.provider,
                    model_id=r.model_id,
                    stage="cross_critique",
                    integration_mode="api" if is_api else "manual",
                    prompt_used=critique_prompt,
                    content="",
                    status="pending"
                )
                db.add(critique_resp)

            db.commit()

        elif current_stage == "cross_critique":
            # Transition to Rebuttal
            run.current_stage = "rebuttal"
            active_round = db.query(DiscussionRound).filter_by(
                run_id=run.id, round_number=run.current_round
            ).first()

            # Gather initial and critiques
            initial_responses = db.query(ModelResponse).filter_by(
                run_id=run.id, stage="initial_analysis", status="completed"
            ).all()
            critique_responses = db.query(ModelResponse).filter_by(
                run_id=run.id, stage="cross_critique", status="completed"
            ).all()

            for r in initial_responses:
                # Combine critiques aimed at this provider
                critiques_for_me = "\n\n".join([
                    f"[{c.provider}]: {c.content}"
                    for c in critique_responses if c.provider != r.provider
                ])

                rebuttal_prompt = PromptBuilder.build_rebuttal_prompt(
                    query=run.query,
                    provider=r.provider,
                    my_initial_response=r.content,
                    critiques_received=critiques_for_me or "Tidak ada kritik spesifik yang diajukan.",
                    round_number=run.current_round
                )

                provider_cfg = db.query(ProviderConfiguration).filter_by(id=r.provider).first()
                is_api = bool(provider_cfg and provider_cfg.default_mode == "api" and provider_manager.is_api_configured(r.provider))

                reb_resp = ModelResponse(
                    run_id=run.id,
                    round_id=active_round.id if active_round else None,
                    provider=r.provider,
                    model_id=r.model_id,
                    stage="rebuttal",
                    integration_mode="api" if is_api else "manual",
                    prompt_used=rebuttal_prompt,
                    content="",
                    status="pending"
                )
                db.add(reb_resp)

            db.commit()

        elif current_stage == "rebuttal":
            # Check if multi-round remains or go to final synthesis
            if run.current_round < run.max_rounds:
                run.current_round += 1
                run.current_stage = "cross_critique"
                new_round = DiscussionRound(
                    run_id=run.id,
                    round_number=run.current_round,
                    stage="cross_critique",
                    status="in_progress"
                )
                db.add(new_round)
                db.commit()
            else:
                # Go to Final Synthesis
                run.current_stage = "final_synthesis"
                active_round = db.query(DiscussionRound).filter_by(
                    run_id=run.id, round_number=run.current_round
                ).first()

                initial = db.query(ModelResponse).filter_by(run_id=run.id, stage="initial_analysis", status="completed").all()
                critiques = db.query(ModelResponse).filter_by(run_id=run.id, stage="cross_critique", status="completed").all()
                rebuttals = db.query(ModelResponse).filter_by(run_id=run.id, stage="rebuttal", status="completed").all()

                doc_chunks = []
                if run.linked_document_ids:
                    doc_chunks = DocumentService.search_relevant_chunks(
                        db, query=run.query, document_ids=run.linked_document_ids, top_k=5
                    )

                synthesis_prompt = PromptBuilder.build_synthesis_prompt(
                    query=run.query,
                    all_initial=[{"provider": x.provider, "content": x.content} for x in initial],
                    all_critiques=[{"reviewer_provider": x.provider, "target_provider": "council", "content": x.content} for x in critiques],
                    all_rebuttals=[{"provider": x.provider, "content": x.content} for x in rebuttals],
                    document_chunks=doc_chunks
                )

                # Create synthesis placeholder response
                synth_resp = ModelResponse(
                    run_id=run.id,
                    round_id=active_round.id if active_round else None,
                    provider="moderator",
                    model_id="council_moderator",
                    stage="final_synthesis",
                    integration_mode="manual",
                    prompt_used=synthesis_prompt,
                    content="",
                    status="pending"
                )
                db.add(synth_resp)
                db.commit()

        db.refresh(run)
        return run

    @classmethod
    def submit_synthesis(
        cls,
        db: Session,
        run_id: str,
        raw_synthesis: str,
        moderator_provider: str = "human_moderator",
        problem_summary: Optional[str] = None,
        consensus_points: Optional[str] = None,
        disagreements: Optional[str] = None,
        unresolved_critiques: Optional[str] = None,
        evidence_backed_claims: Optional[str] = None,
        recommendations: Optional[str] = None,
        uncertainties_and_verifications: Optional[str] = None,
        references_cited: Optional[str] = None
    ) -> Synthesis:
        run = db.query(DiscussionRun).filter_by(id=run_id).first()
        if not run:
            raise ValueError("Sesi diskusi tidak ditemukan.")

        # Create or update Synthesis
        synth = db.query(Synthesis).filter_by(run_id=run.id).first()
        if not synth:
            synth = Synthesis(
                run_id=run.id,
                moderator_provider=moderator_provider,
                raw_synthesis=raw_synthesis.strip()
            )
            db.add(synth)
        else:
            synth.raw_synthesis = raw_synthesis.strip()
            synth.moderator_provider = moderator_provider

        # Auto-extract or fill structured sections if provided
        synth.problem_summary = problem_summary or cls._extract_section(raw_synthesis, "Ringkasan Masalah")
        synth.consensus_points = consensus_points or cls._extract_section(raw_synthesis, "Kesepakatan Antarmodel")
        synth.disagreements = disagreements or cls._extract_section(raw_synthesis, "Perbedaan Pendapat")
        synth.unresolved_critiques = unresolved_critiques or cls._extract_section(raw_synthesis, "Kritik yang Belum Terselesaikan")
        synth.evidence_backed_claims = evidence_backed_claims or cls._extract_section(raw_synthesis, "Bukti yang Mendukung Kesimpulan")
        synth.recommendations = recommendations or cls._extract_section(raw_synthesis, "Rekomendasi")
        synth.uncertainties_and_verifications = uncertainties_and_verifications or cls._extract_section(raw_synthesis, "Ketidakpastian & Kebutuhan Verifikasi")
        synth.references_cited = references_cited or cls._extract_section(raw_synthesis, "Referensi Sumber")

        # Mark model response for synthesis completed
        synth_resp = db.query(ModelResponse).filter_by(run_id=run.id, stage="final_synthesis").first()
        if synth_resp:
            synth_resp.status = "completed"
            synth_resp.content = raw_synthesis

        run.status = "completed"
        run.current_stage = "completed"

        # Also append moderator message to conversation history
        db.add(Message(
            conversation_id=run.conversation_id,
            role="moderator",
            provider=moderator_provider,
            content=raw_synthesis
        ))

        db.commit()
        db.refresh(synth)
        return synth

    @staticmethod
    def _extract_section(text: str, header_keyword: str) -> Optional[str]:
        """Helper to extract structured section from text if header matches."""
        lines = text.split("\n")
        capturing = False
        captured_lines = []
        for line in lines:
            if header_keyword.lower() in line.lower() and (line.startswith("#") or line.startswith("1") or line.startswith("2") or line.startswith("3") or line.startswith("4") or line.startswith("5") or line.startswith("6") or line.startswith("7") or line.startswith("8")):
                capturing = True
                continue
            elif capturing and (line.startswith("#") or any(f"{i}." in line[:4] for i in range(1, 9))):
                break
            elif capturing:
                captured_lines.append(line)

        res = "\n".join(captured_lines).strip()
        return res if res else None

    @classmethod
    def stop_discussion(cls, db: Session, run_id: str) -> DiscussionRun:
        run = db.query(DiscussionRun).filter_by(id=run_id).first()
        if not run:
            raise ValueError("Sesi diskusi tidak ditemukan.")
        run.status = "stopped"
        db.commit()
        db.refresh(run)
        return run

    @classmethod
    def generate_markdown_report(cls, db: Session, run_id: str) -> str:
        run = db.query(DiscussionRun).filter_by(id=run_id).first()
        if not run:
            raise ValueError("Sesi diskusi tidak ditemukan.")

        lines = [
            f"# Laporan Hasil AI Council — {run.mode.upper()}",
            f"**Tanggal:** {run.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Status:** {run.status}",
            f"**Topik / Pertanyaan:**\n> {run.query}\n",
            "---",
            "## 1. Respons Peserta AI Dewan"
        ]

        responses = db.query(ModelResponse).filter_by(run_id=run.id).all()
        for r in responses:
            lines.append(f"\n### {r.provider.upper()} ({r.stage} - Mode: {r.integration_mode})")
            if r.status == "completed":
                lines.append(r.content)
            elif r.status == "failed":
                lines.append(f"*Gagal: {r.error_message}*")
            else:
                lines.append("*Status: Menunggu respons pengguna / API*")

        syntheses = db.query(Synthesis).filter_by(run_id=run.id).all()
        if syntheses:
            lines.append("\n---")
            lines.append("## 2. Sintesis Akhir Moderator AI Council\n")
            for s in syntheses:
                lines.append(s.raw_synthesis)

        references = db.query(SourceReference).filter_by(run_id=run.id).all()
        if references:
            lines.append("\n---")
            lines.append("## 3. Sumber & Kutipan Dokumen yang Diverifikasi\n")
            for ref in references:
                lines.append(f"- **Halaman {ref.page_number}**: \"{ref.quote}\"")

        return "\n".join(lines)
