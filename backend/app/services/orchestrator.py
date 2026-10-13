import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app import database
from app.models.all_models import (
    Conversation,
    DiscussionRun,
    DiscussionRound,
    ModelResponse,
    Critique,
    Synthesis,
    SourceReference,
    Document,
    Message,
    ProviderConfiguration,
    UsageRecord
)
from app.services.prompt_builder import PromptBuilder
from app.services.document_service import DocumentService
from app.services.provider_manager import provider_manager
from app.config import settings


class Orchestrator:
    # Active automated debate background tasks
    _active_debate_tasks: Dict[str, asyncio.Task] = {}

    @classmethod
    def get_db_session(cls) -> Session:
        """Returns a database session for background or concurrent execution."""
        return database.SessionLocal()

    @classmethod
    def parse_participant(cls, item: str, db: Session) -> Dict[str, Any]:
        """
        Parses provider and model from item string.
        Examples:
        - "openrouter:deepseek/deepseek-r1:free" -> provider="openrouter", model_id="deepseek/deepseek-r1:free"
        - "ollama:llama3.2" -> provider="ollama", model_id="llama3.2"
        - "chatgpt" -> provider="chatgpt", model_id="gpt-4o"
        """
        raw = item.strip()
        if ":" in raw and not raw.startswith("http"):
            parts = raw.split(":", 1)
            provider = parts[0].strip()
            model_id = parts[1].strip()
        else:
            provider = raw
            provider_cfg = db.query(ProviderConfiguration).filter_by(id=provider).first()
            model_id = provider_cfg.selected_model if provider_cfg else provider

        provider_cfg = db.query(ProviderConfiguration).filter_by(id=provider).first()
        is_api = bool(
            (provider_cfg and provider_cfg.default_mode == "api") or
            provider_manager.is_api_configured(provider) or
            provider in ("openrouter", "ollama")
        )

        display_name = model_id.split("/")[-1] if "/" in model_id else model_id
        return {
            "provider": provider,
            "model_id": model_id,
            "display_name": display_name,
            "is_api": is_api,
            "raw": raw
        }

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
        conversation_title: Optional[str] = None,
        auto_run: bool = True,
        zero_cost_mode: bool = True,
        moderator_model: Optional[str] = None
    ) -> DiscussionRun:
        query = query.strip()
        if not query:
            raise ValueError("Pertanyaan atau topik diskusi tidak boleh kosong.")

        selected_providers = selected_providers or [
            "openrouter:deepseek/deepseek-r1:free",
            "openrouter:meta-llama/llama-3.3-70b-instruct:free",
            "openrouter:qwen/qwen-2.5-72b-instruct:free"
        ]
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

        # Check if all providers are manual
        all_manual = True
        for raw_item in selected_providers:
            part = cls.parse_participant(raw_item, db)
            if part["is_api"]:
                all_manual = False
                break

        initial_status = "in_progress" if (auto_run and mode == "debate" and not all_manual) else "awaiting_input"

        run = DiscussionRun(
            conversation_id=conv.id,
            mode=mode,
            status=initial_status,
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

        # 5. Initialize responses for each selected provider / model
        api_tasks = []
        for raw_item in selected_providers:
            part = cls.parse_participant(raw_item, db)
            pid = part["provider"]
            model_id = part["model_id"]
            is_api = part["is_api"]
            p_label = f"{pid} ({part['display_name']})"

            if mode == "debate":
                prompt = PromptBuilder.build_initial_debate_prompt(
                    query=query,
                    provider=p_label,
                    round_number=1,
                    document_chunks=doc_chunks
                )
            else:
                prompt = PromptBuilder.build_parallel_prompt(
                    query=query,
                    provider=p_label,
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

        # 6. Execution routing
        if mode == "debate" and auto_run and not all_manual:
            try:
                loop = asyncio.get_running_loop()
                task = loop.create_task(
                    cls.run_automated_debate(
                        run.id,
                        zero_cost_mode=zero_cost_mode,
                        moderator_model=moderator_model
                    )
                )
                cls._active_debate_tasks[run.id] = task
            except RuntimeError:
                pass
        elif mode == "parallel" and api_tasks:
            await cls._execute_api_tasks_concurrent(run.id, api_tasks, zero_cost_mode=zero_cost_mode)
            db.refresh(run)
            cls._update_run_status(db, run)
        else:
            cls._update_run_status(db, run)

        db.refresh(run)
        return run

    @classmethod
    async def _execute_api_tasks_concurrent(
        cls,
        run_id: str,
        tasks: List[Tuple[str, str, str, str]],
        zero_cost_mode: bool = True
    ):
        """
        Executes API completions concurrently with individual error containment.
        Failure of one model does not disrupt others.
        """
        async def run_single(resp_id: str, pid: str, model_id: str, prompt: str):
            adapter = provider_manager.get_adapter(pid, model=model_id, zero_cost_mode=zero_cost_mode)
            if not adapter:
                with cls.get_db_session() as db:
                    resp = db.query(ModelResponse).filter_by(id=resp_id).first()
                    if resp:
                        resp.status = "failed"
                        resp.error_message = f"Adapter API untuk provider '{pid}' tidak ditemukan."
                        db.commit()
                return

            with cls.get_db_session() as db:
                resp = db.query(ModelResponse).filter_by(id=resp_id).first()
                if resp:
                    resp.status = "in_progress"
                    db.commit()

            try:
                result = await adapter.complete(prompt=prompt)
                with cls.get_db_session() as db:
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
                                action=resp.stage,
                                prompt_tokens=result.prompt_tokens,
                                completion_tokens=result.completion_tokens,
                                total_tokens=result.total_tokens,
                                estimated_cost_usd=result.estimated_cost_usd,
                                is_actual_cost=result.is_actual_cost,
                                run_id=run_id
                            ))
                        db.commit()
            except Exception as e:
                with cls.get_db_session() as db:
                    resp = db.query(ModelResponse).filter_by(id=resp_id).first()
                    if resp:
                        resp.status = "failed"
                        resp.error_message = f"Panggilan API gagal: {str(e)}"
                        db.commit()

        sem = asyncio.Semaphore(5)
        async def sem_task(t):
            async with sem:
                await run_single(*t)

        await asyncio.gather(*(sem_task(t) for t in tasks), return_exceptions=True)

    @classmethod
    async def _execute_api_tasks(cls, db: Session, tasks: list, run_id: str):
        """Maintained for test and caller compatibility."""
        await cls._execute_api_tasks_concurrent(run_id, tasks)

    @classmethod
    async def run_automated_debate(
        cls,
        run_id: str,
        zero_cost_mode: bool = True,
        moderator_model: Optional[str] = None
    ):
        """
        Main autonomous debate orchestrator loop.
        Executes:
        STAGE 1 (Initial Analysis) -> STAGE 2 (Cross-Critique) -> STAGE 3 (Rebuttal) -> STAGE 4 (Final Synthesis)
        without requiring manual stage advancement clicks.
        """
        current_task = asyncio.current_task()
        if current_task:
            cls._active_debate_tasks[run_id] = current_task

        try:
            while True:
                with cls.get_db_session() as db:
                    run = db.query(DiscussionRun).filter_by(id=run_id).first()
                    if not run or run.status in ("stopped", "completed", "failed"):
                        break

                    current_stage = run.current_stage

                    pending_responses = db.query(ModelResponse).filter_by(
                        run_id=run.id,
                        stage=current_stage,
                        status="pending"
                    ).all()

                    tasks_to_run = []
                    has_manual_pending = False
                    for r in pending_responses:
                        if r.integration_mode == "api":
                            tasks_to_run.append((r.id, r.provider, r.model_id or r.provider, r.prompt_used))
                        else:
                            has_manual_pending = True

                if tasks_to_run:
                    with cls.get_db_session() as db:
                        run = db.query(DiscussionRun).filter_by(id=run_id).first()
                        if run and run.status != "stopped":
                            run.status = "in_progress"
                            db.commit()

                    await cls._execute_api_tasks_concurrent(
                        run_id=run_id,
                        tasks=tasks_to_run,
                        zero_cost_mode=zero_cost_mode
                    )

                if has_manual_pending:
                    with cls.get_db_session() as db:
                        run = db.query(DiscussionRun).filter_by(id=run_id).first()
                        if run and run.status != "stopped":
                            run.status = "awaiting_input"
                            db.commit()
                    break

                with cls.get_db_session() as db:
                    run = db.query(DiscussionRun).filter_by(id=run_id).first()
                    if not run or run.status == "stopped":
                        break

                    completed_count = db.query(ModelResponse).filter_by(
                        run_id=run.id,
                        stage=current_stage,
                        status="completed"
                    ).count()
                    total_count = db.query(ModelResponse).filter_by(
                        run_id=run.id,
                        stage=current_stage
                    ).count()

                    if total_count > 0 and completed_count == 0:
                        run.status = "failed"
                        db.commit()
                        break

                if current_stage == "final_synthesis":
                    break
                else:
                    try:
                        with cls.get_db_session() as db:
                            run = await cls.advance_debate_stage(db, run_id)
                            if run.current_stage == "final_synthesis":
                                break
                    except Exception:
                        break

                await asyncio.sleep(0.1)

            # Final Synthesis
            with cls.get_db_session() as db:
                run = db.query(DiscussionRun).filter_by(id=run_id).first()
                if run and run.current_stage == "final_synthesis" and run.status not in ("completed", "stopped", "failed"):
                    synth_resp = db.query(ModelResponse).filter_by(
                        run_id=run.id,
                        stage="final_synthesis",
                        provider="moderator"
                    ).first()
                    if synth_resp and synth_resp.status != "completed":
                        await cls._execute_automated_synthesis(
                            run_id=run_id,
                            moderator_model=moderator_model,
                            zero_cost_mode=zero_cost_mode
                        )

        except asyncio.CancelledError:
            with cls.get_db_session() as db:
                run = db.query(DiscussionRun).filter_by(id=run_id).first()
                if run and run.status != "completed":
                    run.status = "stopped"
                    db.commit()
        except Exception:
            with cls.get_db_session() as db:
                run = db.query(DiscussionRun).filter_by(id=run_id).first()
                if run and run.status != "completed":
                    run.status = "failed"
                    db.commit()
        finally:
            cls._active_debate_tasks.pop(run_id, None)

    @classmethod
    async def _execute_automated_synthesis(
        cls,
        run_id: str,
        moderator_model: Optional[str] = None,
        zero_cost_mode: bool = True
    ):
        """
        Executes final synthesis automatically using a verified free moderator model.
        """
        with cls.get_db_session() as db:
            run = db.query(DiscussionRun).filter_by(id=run_id).first()
            if not run or run.status in ("completed", "stopped"):
                return
            synth_resp = db.query(ModelResponse).filter_by(
                run_id=run.id,
                stage="final_synthesis",
                provider="moderator"
            ).first()
            if not synth_resp:
                return

            prompt = synth_resp.prompt_used

            adapter = None
            mod_provider = "moderator"
            mod_model_id = moderator_model or "google/gemini-2.0-flash-exp:free"

            if moderator_model:
                adapter = provider_manager.get_adapter(moderator_model, zero_cost_mode=zero_cost_mode)

            if not adapter:
                or_key = provider_manager.get_secret("openrouter")
                if or_key:
                    adapter = provider_manager.get_adapter("openrouter", model=mod_model_id, zero_cost_mode=zero_cost_mode)
                    mod_provider = "openrouter"

            if not adapter:
                gem_key = provider_manager.get_secret("gemini")
                if gem_key:
                    adapter = provider_manager.get_adapter("gemini", model="gemini-1.5-flash", zero_cost_mode=zero_cost_mode)
                    mod_provider = "gemini"
                    mod_model_id = "gemini-1.5-flash"

            if not adapter:
                adapter = provider_manager.get_adapter("ollama", model="llama3.2")
                if adapter:
                    mod_provider = "ollama"
                    mod_model_id = "llama3.2"

            if not adapter:
                successful_res = db.query(ModelResponse).filter_by(
                    run_id=run.id,
                    status="completed"
                ).first()
                if successful_res and successful_res.provider != "moderator":
                    adapter = provider_manager.get_adapter(
                        successful_res.provider,
                        model=successful_res.model_id,
                        zero_cost_mode=zero_cost_mode
                    )
                    mod_provider = successful_res.provider
                    mod_model_id = successful_res.model_id

            if not adapter:
                synth_resp.status = "failed"
                synth_resp.error_message = "Tidak ada provider API yang tersedia untuk membuat sintesis otomatis."
                db.commit()
                return

            synth_resp.status = "in_progress"
            synth_resp.model_id = mod_model_id
            db.commit()

        system_prompt = (
            "Anda adalah AI Council Moderator yang netral, teliti, dan objektif. "
            "Tugas Anda merangkum perdebatan antar-model, memetakan kesepakatan (consensus), "
            "titik perbedaan pendapat (divergence), bukti yang terverifikasi, dan rekomendasi final."
        )

        result = await adapter.complete(prompt=prompt, system_prompt=system_prompt, timeout=90.0)

        with cls.get_db_session() as db:
            run = db.query(DiscussionRun).filter_by(id=run_id).first()
            synth_resp = db.query(ModelResponse).filter_by(
                run_id=run.id,
                stage="final_synthesis",
                provider="moderator"
            ).first()
            if not run or not synth_resp:
                return

            if result.error:
                synth_resp.status = "failed"
                synth_resp.error_message = f"Panggilan moderator otomatis gagal: {result.error}"
                run.status = "awaiting_input"
                db.commit()
            else:
                synth_resp.status = "completed"
                synth_resp.content = result.content
                synth_resp.prompt_tokens = result.prompt_tokens
                synth_resp.completion_tokens = result.completion_tokens
                synth_resp.total_tokens = result.total_tokens

                cls.submit_synthesis(
                    db=db,
                    run_id=run.id,
                    raw_synthesis=result.content,
                    moderator_provider=f"{mod_provider}:{mod_model_id}"
                )

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
        if run.status == "completed" and run.mode != "parallel":
            raise ValueError("Sesi diskusi telah selesai dan tidak dapat diubah lagi.")

        clean_content = content.strip()
        if not clean_content and status == "completed":
            raise ValueError("Konten respons manual tidak boleh kosong jika ditandai selesai.")

        resp.content = clean_content
        resp.status = status
        if model_id:
            resp.model_id = model_id

        est_tokens = len(clean_content.split()) * 2
        resp.completion_tokens = est_tokens
        resp.total_tokens = est_tokens

        # Record manual usage record
        db.add(UsageRecord(
            provider=resp.provider,
            model_id=resp.model_id or "manual",
            mode="manual",
            action=resp.stage,
            prompt_tokens=0,
            completion_tokens=est_tokens,
            total_tokens=est_tokens,
            estimated_cost_usd=0.0,
            is_actual_cost=True,
            run_id=resp.run_id
        ))

        db.commit()
        db.refresh(resp)

        cls._update_run_status(db, run)
        return resp

    @classmethod
    def _update_run_status(cls, db: Session, run: DiscussionRun):
        if run.status in ("stopped", "failed"):
            return

        responses = db.query(ModelResponse).filter_by(run_id=run.id, stage=run.current_stage).all()
        debater_responses = [r for r in responses if r.provider != "moderator"]
        all_done = debater_responses and all(r.status in ("completed", "failed") for r in debater_responses)

        if run.mode == "parallel":
            if all_done:
                run.status = "completed"
            else:
                if run.status != "in_progress":
                    run.status = "awaiting_input"
        elif run.mode == "debate":
            if run.current_stage == "final_synthesis":
                synthesis = db.query(Synthesis).filter_by(run_id=run.id).first()
                if synthesis:
                    run.status = "completed"
                else:
                    if run.status != "in_progress":
                        run.status = "awaiting_input"
            else:
                if run.status != "in_progress":
                    run.status = "awaiting_input"

        db.commit()

    @classmethod
    def stop_discussion(cls, db: Session, run_id: str) -> DiscussionRun:
        run = db.query(DiscussionRun).filter_by(id=run_id).first()
        if not run:
            raise ValueError("Sesi diskusi tidak ditemukan.")
        if run.status == "completed":
            raise ValueError("Sesi diskusi telah selesai dan tidak dapat dihentikan.")

        task = cls._active_debate_tasks.get(run_id)
        if task and not task.done():
            task.cancel()

        run.status = "stopped"
        db.commit()
        db.refresh(run)
        return run

    @classmethod
    def resume_discussion(
        cls,
        db: Session,
        run_id: str,
        auto_run: bool = False,
        zero_cost_mode: bool = True
    ) -> DiscussionRun:
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

        if auto_run and run.mode == "debate":
            try:
                loop = asyncio.get_running_loop()
                task = loop.create_task(
                    cls.run_automated_debate(run.id, zero_cost_mode=zero_cost_mode)
                )
                cls._active_debate_tasks[run.id] = task
                run.status = "in_progress"
                db.commit()
                db.refresh(run)
            except RuntimeError:
                pass

        return run

    @classmethod
    def continue_to_debate(cls, db: Session, run_id: str, auto_run: bool = False) -> DiscussionRun:
        parallel_run = db.query(DiscussionRun).filter_by(id=run_id).first()
        if not parallel_run:
            raise ValueError("Sesi diskusi tidak ditemukan.")
        if parallel_run.mode != "parallel":
            raise ValueError("Fitur 'Lanjutkan ke AI Debate' hanya berlaku untuk sesi mode parallel.")

        bounded_max_rounds = min(max(settings.max_debate_rounds, 1), 3)

        debate_run = DiscussionRun(
            conversation_id=parallel_run.conversation_id,
            mode="debate",
            status="awaiting_input",
            current_stage="initial_analysis",
            current_round=1,
            max_rounds=bounded_max_rounds,
            query=parallel_run.query,
            selected_providers=parallel_run.selected_providers,
            linked_document_ids=parallel_run.linked_document_ids
        )
        db.add(debate_run)
        db.flush()

        # Copy source references
        existing_refs = db.query(SourceReference).filter_by(run_id=parallel_run.id).all()
        for ref in existing_refs:
            db.add(SourceReference(
                run_id=debate_run.id,
                document_id=ref.document_id,
                chunk_id=ref.chunk_id,
                quote=ref.quote,
                page_number=ref.page_number,
                relevance_score=ref.relevance_score,
                is_verified=ref.is_verified,
                source_type=ref.source_type
            ))

        round_1 = DiscussionRound(
            run_id=debate_run.id,
            round_number=1,
            stage="initial_analysis",
            status="in_progress"
        )
        db.add(round_1)
        db.flush()

        doc_chunks = []
        if parallel_run.linked_document_ids:
            doc_chunks = DocumentService.search_relevant_chunks(
                db, query=parallel_run.query, document_ids=parallel_run.linked_document_ids, top_k=5
            )

        parallel_responses = {
            r.provider: r for r in parallel_run.responses if r.provider != "moderator"
        }

        for raw_item in debate_run.selected_providers:
            part = cls.parse_participant(raw_item, db)
            pid = part["provider"]
            model_id = part["model_id"]
            is_api = part["is_api"]
            p_label = f"{pid} ({part['display_name']})"

            prompt = PromptBuilder.build_initial_debate_prompt(
                query=debate_run.query,
                provider=p_label,
                round_number=1,
                document_chunks=doc_chunks
            )

            par_resp = parallel_responses.get(pid)
            if par_resp and par_resp.status == "completed" and par_resp.content.strip():
                resp = ModelResponse(
                    run_id=debate_run.id,
                    round_id=round_1.id,
                    provider=pid,
                    model_id=par_resp.model_id or model_id,
                    stage="initial_analysis",
                    integration_mode=par_resp.integration_mode,
                    prompt_used=prompt,
                    content=par_resp.content,
                    status="completed",
                    completion_tokens=par_resp.completion_tokens,
                    total_tokens=par_resp.total_tokens,
                    estimated_cost_usd=par_resp.estimated_cost_usd
                )
            else:
                resp = ModelResponse(
                    run_id=debate_run.id,
                    round_id=round_1.id,
                    provider=pid,
                    model_id=model_id,
                    stage="initial_analysis",
                    integration_mode="api" if is_api else "manual",
                    prompt_used=prompt,
                    content="",
                    status="pending"
                )
            db.add(resp)

        db.commit()
        db.refresh(debate_run)

        if auto_run:
            try:
                loop = asyncio.get_running_loop()
                task = loop.create_task(cls.run_automated_debate(debate_run.id))
                cls._active_debate_tasks[debate_run.id] = task
                debate_run.status = "in_progress"
                db.commit()
                db.refresh(debate_run)
            except RuntimeError:
                pass

        return debate_run

    @classmethod
    async def advance_debate_stage(cls, db: Session, run_id: str) -> DiscussionRun:
        run = db.query(DiscussionRun).filter_by(id=run_id).first()
        if not run:
            raise ValueError("Sesi diskusi tidak ditemukan.")
        if run.mode != "debate":
            raise ValueError(
                "Mode 'parallel' adalah analisis perbandingan langsung satu tahap dan tidak memiliki alur advance debat. "
                "Gunakan fitur 'Lanjutkan ke AI Debate' untuk memulai debat multi-tahap."
            )

        if run.status not in ("awaiting_input", "in_progress"):
            raise ValueError(f"Hanya sesi dengan status 'awaiting_input' atau 'in_progress' yang dapat dimajukan (status saat ini: '{run.status}').")

        current_stage = run.current_stage

        if current_stage == "initial_analysis":
            initial_responses = db.query(ModelResponse).filter_by(
                run_id=run.id, stage="initial_analysis", status="completed"
            ).all()
            if not initial_responses:
                raise ValueError(
                    "Belum ada respons analisis awal yang selesai. Harap masukkan setidaknya satu respons sebelum melanjutkan ke kritik silang."
                )

            run.current_stage = "cross_critique"
            active_round = db.query(DiscussionRound).filter_by(
                run_id=run.id, round_number=run.current_round
            ).first()
            if active_round:
                active_round.stage = "cross_critique"

            resp_data = [
                {"provider": f"{r.provider} ({r.model_id or 'manual'})", "content": r.content}
                for r in initial_responses
            ]

            for r in initial_responses:
                critique_prompt = PromptBuilder.build_critique_prompt(
                    query=run.query,
                    reviewer_provider=f"{r.provider} ({r.model_id or 'manual'})",
                    all_responses=resp_data,
                    round_number=run.current_round
                )

                provider_cfg = db.query(ProviderConfiguration).filter_by(id=r.provider).first()
                is_api = bool(
                    (provider_cfg and provider_cfg.default_mode == "api") or
                    provider_manager.is_api_configured(r.provider) or
                    r.provider in ("openrouter", "ollama") or
                    r.integration_mode == "api"
                )

                existing = db.query(ModelResponse).filter_by(
                    run_id=run.id,
                    round_id=active_round.id if active_round else None,
                    provider=r.provider,
                    model_id=r.model_id,
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

            run.current_stage = "rebuttal"
            active_round = db.query(DiscussionRound).filter_by(
                run_id=run.id, round_number=run.current_round
            ).first()
            if active_round:
                active_round.stage = "rebuttal"

            initial_responses = db.query(ModelResponse).filter_by(
                run_id=run.id, stage="initial_analysis", status="completed"
            ).all()

            for r in initial_responses:
                critiques_for_me = "\n\n".join([
                    f"[{c.provider} ({c.model_id or 'manual'})]: {c.content}"
                    for c in critique_responses if not (c.provider == r.provider and c.model_id == r.model_id)
                ])

                rebuttal_prompt = PromptBuilder.build_rebuttal_prompt(
                    query=run.query,
                    provider=f"{r.provider} ({r.model_id or 'manual'})",
                    my_initial_response=r.content,
                    critiques_received=critiques_for_me or "Tidak ada kritik spesifik yang diajukan.",
                    round_number=run.current_round
                )

                provider_cfg = db.query(ProviderConfiguration).filter_by(id=r.provider).first()
                is_api = bool(
                    (provider_cfg and provider_cfg.default_mode == "api") or
                    provider_manager.is_api_configured(r.provider) or
                    r.provider in ("openrouter", "ollama") or
                    r.integration_mode == "api"
                )

                existing = db.query(ModelResponse).filter_by(
                    run_id=run.id,
                    round_id=active_round.id if active_round else None,
                    provider=r.provider,
                    model_id=r.model_id,
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
                    all_initial=[{"provider": f"{x.provider} ({x.model_id or 'manual'})", "content": x.content} for x in initial],
                    all_critiques=[{"reviewer_provider": f"{x.provider} ({x.model_id or 'manual'})", "target_provider": "council", "content": x.content} for x in critiques],
                    all_rebuttals=[{"provider": f"{x.provider} ({x.model_id or 'manual'})", "content": x.content} for x in rebuttals],
                    document_chunks=doc_chunks
                )

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
                        integration_mode="api",
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

        clean_synth = raw_synthesis.strip()
        if not clean_synth:
            raise ValueError("Teks sintesis akhir tidak boleh kosong.")

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
                raw_synthesis=clean_synth
            )
            db.add(synth)
        else:
            synth.raw_synthesis = clean_synth
            synth.moderator_provider = moderator_provider
            synth.mode = "manual_partial" if allow_partial else "manual"

        # Auto-extract or fill structured sections if provided
        synth.problem_summary = problem_summary or cls._extract_section(clean_synth, "Ringkasan Masalah")
        synth.consensus_points = consensus_points or cls._extract_section(clean_synth, "Kesepakatan Antarmodel")
        synth.disagreements = disagreements or cls._extract_section(clean_synth, "Perbedaan Pendapat")
        synth.unresolved_critiques = unresolved_critiques or cls._extract_section(clean_synth, "Kritik yang Belum Terselesaikan")
        synth.evidence_backed_claims = evidence_backed_claims or cls._extract_section(clean_synth, "Bukti yang Mendukung Kesimpulan")
        synth.recommendations = recommendations or cls._extract_section(clean_synth, "Rekomendasi")
        synth.uncertainties_and_verifications = uncertainties_and_verifications or cls._extract_section(clean_synth, "Ketidakpastian & Kebutuhan Verifikasi")
        synth.references_cited = references_cited or cls._extract_section(clean_synth, "Referensi Sumber")

        # Mark model response for synthesis completed if existing
        synth_resp = db.query(ModelResponse).filter_by(run_id=run.id, stage="final_synthesis").first()
        if synth_resp:
            synth_resp.status = "completed"
            synth_resp.content = clean_synth

        run.status = "completed"
        run.current_stage = "completed"

        # Also append moderator message to conversation history
        db.add(Message(
            conversation_id=run.conversation_id,
            role="moderator",
            provider=moderator_provider,
            content=clean_synth
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
            if header_keyword.lower() in line.lower() and (line.startswith("#") or any(f"{i}" in line[:3] for i in range(1, 9))):
                capturing = True
                continue
            elif capturing and (line.startswith("#") or any(f"{i}." in line[:4] for i in range(1, 9))):
                break
            elif capturing:
                captured_lines.append(line)

        res = "\n".join(captured_lines).strip()
        return res if res else None

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

        all_responses = db.query(ModelResponse).filter_by(run_id=run.id).all()
        debater_responses = [r for r in all_responses if r.provider != "moderator"]

        completed_debaters = [r for r in debater_responses if r.status == "completed"]
        if not completed_debaters and not any(r.status == "failed" for r in debater_responses):
            lines.append("\n*Catatan: Belum ada respons peserta dewan yang diselesaikan sebelum laporan ini dibuat.*")
        else:
            stage_order = ["parallel_analysis", "initial_analysis", "cross_critique", "rebuttal"]
            stage_names = {
                "parallel_analysis": "Analisis Mandiri Dewan AI (Parallel Analysis)",
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
                doc_title = "Dokumen Referensi"
                if hasattr(ref, "document") and ref.document and getattr(ref.document, "title", None):
                    doc_title = ref.document.title
                elif ref.document_id:
                    doc = db.query(Document).filter_by(id=ref.document_id).first()
                    if doc and doc.title:
                        doc_title = doc.title
                lines.append(f"- **{doc_title}** (Halaman {ref.page_number}): *\"{ref.quote}\"*")

        return "\n".join(lines)
