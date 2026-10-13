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
from app.config import settings



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
        query = query.strip()
        if not query:
            raise ValueError("Pertanyaan atau topik diskusi tidak boleh kosong.")

        selected_providers = selected_providers or ["chatgpt", "claude", "gemini"]
        linked_document_ids = linked_document_ids or []
        if max_rounds > settings.max_debate_rounds:
            raise ValueError(
                f"Jumlah putaran debat ({max_rounds}) melebihi batas maksimal {settings.max_debate_rounds} putaran."
            )
        if max_rounds < 1:
            raise ValueError("Jumlah putaran debat minimal 1 putaran.")
        bounded_max_rounds = max_rounds


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
            max_rounds=bounded_max_rounds,
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

        run = db.query(DiscussionRun).filter_by(id=resp.run_id).first()
        if not run:
            raise ValueError("Sesi diskusi terkait tidak ditemukan.")
        if run.status == "stopped":
            raise ValueError("Sesi diskusi sedang dihentikan (stopped). Silakan lanjutkan (resume) sesi terlebih dahulu sebelum menambahkan respons.")
        if run.status == "completed":
            raise ValueError("Sesi diskusi telah selesai dan tidak dapat diubah lagi.")

        clean_content = content.strip()
        if not clean_content and status == "completed":
            raise ValueError("Konten respons manual tidak boleh kosong jika ditandai selesai.")

        resp.content = clean_content
        resp.status = status
        if model_id:
            resp.model_id = model_id

        # Estimate tokens roughly (~4 chars/token) for transparency
        est_tokens = len(clean_content.split()) * 2
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
        cls._update_run_status(db, run)
        return resp

    @classmethod
    def _update_run_status(cls, db: Session, run: DiscussionRun):
        if run.status in ("stopped", "completed"):
            return

        responses = db.query(ModelResponse).filter_by(run_id=run.id, stage=run.current_stage).all()
        debater_responses = [r for r in responses if r.provider != "moderator"]
        all_done = debater_responses and all(r.status in ("completed", "failed") for r in debater_responses)

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
    def resume_discussion(cls, db: Session, run_id: str) -> DiscussionRun:
        run = db.query(DiscussionRun).filter_by(id=run_id).first()
        if not run:
            raise ValueError("Sesi diskusi tidak ditemukan.")
        if run.status != "stopped":
            raise ValueError(f"Hanya sesi dengan status 'stopped' yang dapat dilanjutkan (status saat ini: '{run.status}').")
        if run.current_stage == "completed":
            raise ValueError("Sesi diskusi telah selesai secara permanen dan tidak dapat dilanjutkan.")
        run.status = "awaiting_input"
        db.commit()
        db.refresh(run)
        return run

    @classmethod
    async def advance_debate_stage(cls, db: Session, run_id: str) -> DiscussionRun:
        run = db.query(DiscussionRun).filter_by(id=run_id).first()
        if not run:
            raise ValueError("Sesi diskusi tidak ditemukan.")
        if run.mode != "debate":
            raise ValueError("Hanya sesi debat yang memiliki alur tahapan multi-stage.")

        if run.status != "awaiting_input":
            raise ValueError(f"Hanya sesi dengan status 'awaiting_input' yang dapat dimajukan (status saat ini: '{run.status}').")

        current_stage = run.current_stage

        if current_stage == "initial_analysis":
            # Check that at least one response is completed
            initial_responses = db.query(ModelResponse).filter_by(
                run_id=run.id, stage="initial_analysis", status="completed"
            ).all()
            if not initial_responses:
                raise ValueError(
                    "Belum ada respons analisis awal yang selesai. Harap masukkan setidaknya satu respons sebelum melanjutkan ke kritik silang."
                )

            # Transition to Cross-Critique
            run.current_stage = "cross_critique"
            active_round = db.query(DiscussionRound).filter_by(
                run_id=run.id, round_number=run.current_round
            ).first()
            if active_round:
                active_round.stage = "cross_critique"

            resp_data = [{"provider": r.provider, "content": r.content} for r in initial_responses]

            # Generate cross critiques for each provider (prevent duplicate rows)
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

                existing = db.query(ModelResponse).filter_by(
                    run_id=run.id,
                    round_id=active_round.id if active_round else None,
                    provider=r.provider,
                    stage="cross_critique"
                ).first()

                if existing:
                    existing.prompt_used = critique_prompt
                else:
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
            critique_responses = db.query(ModelResponse).filter_by(
                run_id=run.id, stage="cross_critique", status="completed"
            ).all()
            if not critique_responses:
                raise ValueError(
                    "Belum ada respons kritik silang yang selesai. Harap selesaikan setidaknya satu kritik sebelum melanjutkan ke sanggahan."
                )

            # Transition to Rebuttal
            run.current_stage = "rebuttal"
            active_round = db.query(DiscussionRound).filter_by(
                run_id=run.id, round_number=run.current_round
            ).first()
            if active_round:
                active_round.stage = "rebuttal"

            # Gather initial and critiques
            initial_responses = db.query(ModelResponse).filter_by(
                run_id=run.id, stage="initial_analysis", status="completed"
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

                existing = db.query(ModelResponse).filter_by(
                    run_id=run.id,
                    round_id=active_round.id if active_round else None,
                    provider=r.provider,
                    stage="rebuttal"
                ).first()

                if existing:
                    existing.prompt_used = rebuttal_prompt
                else:
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
            rebuttal_responses = db.query(ModelResponse).filter_by(
                run_id=run.id, stage="rebuttal", status="completed"
            ).all()
            if not rebuttal_responses:
                raise ValueError(
                    "Belum ada respons sanggahan yang selesai. Harap selesaikan sanggahan sebelum melanjutkan ke tahap berikutnya."
                )

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
                if active_round:
                    active_round.stage = "final_synthesis"

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

                # Store or update synthesis placeholder
                existing_synth = db.query(ModelResponse).filter_by(
                    run_id=run.id,
                    stage="final_synthesis",
                    provider="moderator"
                ).first()

                if existing_synth:
                    existing_synth.prompt_used = synthesis_prompt
                else:
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

        elif current_stage in ("final_synthesis", "completed"):
            raise ValueError("Sesi debat telah mencapai tahap sintesis akhir dan tidak dapat dimajukan lagi.")

        db.refresh(run)
        return run

    @classmethod
    def submit_synthesis(
        cls,
        db: Session,
        run_id: str,
        raw_synthesis: str,
        moderator_provider: str = "human_moderator",
        allow_partial: bool = False,
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
        if run.status == "completed":
            raise ValueError("Sesi diskusi telah selesai sebelumnya.")

        # Prerequisite check: must have at least 1 completed debater response
        completed_responses_count = db.query(ModelResponse).filter(
            ModelResponse.run_id == run.id,
            ModelResponse.status == "completed",
            ModelResponse.provider != "moderator"
        ).count()
        if completed_responses_count == 0:
            raise ValueError("Tidak dapat membuat sintesis: belum ada respons peserta dewan yang diselesaikan dalam diskusi ini.")

        if run.mode == "debate":
            if run.current_stage != "final_synthesis" and not allow_partial:
                raise ValueError("Tahap debat belum mencapai final_synthesis. Harap selesaikan tahapan debat atau aktifkan opsi sintesis parsial.")
            if run.status == "stopped" and not allow_partial:
                raise ValueError("Sesi diskusi sedang dihentikan (stopped). Lanjutkan (resume) sesi terlebih dahulu atau aktifkan opsi sintesis parsial.")

        # Create or update Synthesis
        synth = db.query(Synthesis).filter_by(run_id=run.id).first()
        if not synth:
            synth = Synthesis(
                run_id=run.id,
                moderator_provider=moderator_provider,
                mode="manual_partial" if allow_partial else "manual",
                raw_synthesis=raw_synthesis.strip()
            )
            db.add(synth)
        else:
            synth.raw_synthesis = raw_synthesis.strip()
            synth.moderator_provider = moderator_provider
            synth.mode = "manual_partial" if allow_partial else "manual"

        # Auto-extract or fill structured sections if provided
        synth.problem_summary = problem_summary or cls._extract_section(raw_synthesis, "Ringkasan Masalah")
        synth.consensus_points = consensus_points or cls._extract_section(raw_synthesis, "Kesepakatan Antarmodel")
        synth.disagreements = disagreements or cls._extract_section(raw_synthesis, "Perbedaan Pendapat")
        synth.unresolved_critiques = unresolved_critiques or cls._extract_section(raw_synthesis, "Kritik yang Belum Terselesaikan")
        synth.evidence_backed_claims = evidence_backed_claims or cls._extract_section(raw_synthesis, "Bukti yang Mendukung Kesimpulan")
        synth.recommendations = recommendations or cls._extract_section(raw_synthesis, "Rekomendasi")
        synth.uncertainties_and_verifications = uncertainties_and_verifications or cls._extract_section(raw_synthesis, "Ketidakpastian & Kebutuhan Verifikasi")
        synth.references_cited = references_cited or cls._extract_section(raw_synthesis, "Referensi Sumber")

        # Mark model response for synthesis completed if existing
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
        if run.status == "completed":
            raise ValueError("Sesi diskusi telah selesai dan tidak dapat dihentikan.")
        run.status = "stopped"
        db.commit()
        db.refresh(run)
        return run

    @classmethod
    def generate_markdown_report(cls, db: Session, run_id: str) -> str:
        run = db.query(DiscussionRun).filter_by(id=run_id).first()
        if not run:
            raise ValueError("Sesi diskusi tidak ditemukan.")

        status_label = run.status.upper()
        if run.status == "stopped":
            status_label = "STOPPED (Dihentikan Lebih Awal - Laporan Parsial)"
        elif run.status == "awaiting_input":
            status_label = "AWAITING_INPUT (Menunggu Respons Peserta/Moderator)"
        elif run.status == "completed":
            status_label = "COMPLETED (Diskusi Selesai Penuh)"

        lines = [
            f"# Laporan Hasil AI Council — {run.mode.upper()}",
            f"**Tanggal Pembuatan:** {run.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Status Sesi:** {status_label}",
            f"**Tahap Terakhir:** {run.current_stage} (Putaran {run.current_round} dari {run.max_rounds})",
            f"**Topik / Pertanyaan Penelitian:**\n> {run.query}\n",
            "---",
            "## 1. Respons Peserta AI Dewan"
        ]

        # Only list actual participant debater models (exclude moderator)
        all_responses = db.query(ModelResponse).filter_by(run_id=run.id).all()
        debater_responses = [r for r in all_responses if r.provider != "moderator"]

        completed_debaters = [r for r in debater_responses if r.status == "completed"]
        if not completed_debaters and not any(r.status == "failed" for r in debater_responses):
            lines.append("\n*Catatan: Belum ada respons peserta dewan yang diselesaikan sebelum laporan ini dibuat.*")
        else:
            stage_order = ["initial_analysis", "cross_critique", "rebuttal"]
            stage_names = {
                "initial_analysis": "Tahap 1: Analisis Awal (Initial Analysis)",
                "cross_critique": "Tahap 2: Kritik Silang Antarmodel (Cross-Critique)",
                "rebuttal": "Tahap 3: Sanggahan & Pembelaan (Rebuttal)"
            }
            for st in stage_order:
                st_responses = [r for r in debater_responses if r.stage == st]
                if not st_responses:
                    continue
                lines.append(f"\n### {stage_names.get(st, st.upper())}")
                for r in st_responses:
                    lines.append(f"\n#### Peserta: {r.provider.upper()} (Model: {r.model_id or 'manual'} | Mode: {r.integration_mode})")
                    if r.status == "completed":
                        lines.append(r.content)
                    elif r.status == "failed":
                        lines.append(f"*Gagal: {r.error_message}*")
                    else:
                        lines.append("*(Status: Menunggu respons / belum diisi)*")

        lines.append("\n---")
        lines.append("## 2. Sintesis Moderator AI Council\n")

        syntheses = db.query(Synthesis).filter_by(run_id=run.id).all()
        if syntheses:
            for s in syntheses:
                prefix = ""
                if s.mode == "manual_partial" or run.status == "stopped":
                    prefix = "*(Catatan: Sintesis Parsial / Early Conclusion)*\n\n"
                lines.append(f"{prefix}{s.raw_synthesis}")
        else:
            if run.status == "stopped":
                lines.append("*Sintesis belum dibuat karena sesi ini dihentikan lebih awal oleh pengguna (Laporan Parsial).*")
            elif run.current_stage != "completed":
                lines.append("*Sintesis belum dibuat (Sesi masih dalam proses diskusi).*")
            else:
                lines.append("*Tidak ada sintesis yang tercatat.*")

        references = db.query(SourceReference).filter_by(run_id=run.id).all()
        if references:
            lines.append("\n---")
            lines.append("## 3. Sumber & Kutipan Dokumen yang Diverifikasi\n")
            for ref in references:
                doc_title = ref.document.title if ref.document else "Dokumen Referensi"
                lines.append(f"- **{doc_title}** (Halaman {ref.page_number}): *\"{ref.quote}\"*")

        return "\n".join(lines)

