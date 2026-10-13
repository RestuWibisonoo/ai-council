import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class ResearchProject(Base):
    __tablename__ = "research_projects"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    research_question = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    conversations = relationship("Conversation", back_populates="project", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("research_projects.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    mode = Column(String(50), default="parallel")  # "parallel", "debate", "research"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("ResearchProject", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    runs = relationship("DiscussionRun", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False)  # "user", "assistant", "system", "moderator"
    provider = Column(String(50), nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class DiscussionRun(Base):
    __tablename__ = "discussion_runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    mode = Column(String(50), default="parallel")  # "parallel", "debate", "research"
    status = Column(String(50), default="pending")  # "pending", "in_progress", "awaiting_input", "completed", "failed", "stopped"
    current_stage = Column(String(50), default="initial_analysis")  # "initial_analysis", "cross_critique", "rebuttal", "final_synthesis", "completed"
    current_round = Column(Integer, default=1)
    max_rounds = Column(Integer, default=2)
    query = Column(Text, nullable=False)
    selected_providers = Column(JSON, default=list)  # ["chatgpt", "claude", "gemini", "notebooklm"]
    linked_document_ids = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="runs")
    rounds = relationship("DiscussionRound", back_populates="run", cascade="all, delete-orphan")
    responses = relationship("ModelResponse", back_populates="run", cascade="all, delete-orphan")
    critiques = relationship("Critique", back_populates="run", cascade="all, delete-orphan")
    syntheses = relationship("Synthesis", back_populates="run", cascade="all, delete-orphan")
    source_references = relationship("SourceReference", back_populates="run", cascade="all, delete-orphan")


class DiscussionRound(Base):
    __tablename__ = "discussion_rounds"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("discussion_runs.id", ondelete="CASCADE"), nullable=False)
    round_number = Column(Integer, default=1)
    stage = Column(String(50), nullable=False)  # "initial_analysis", "cross_critique", "rebuttal", "final_synthesis"
    status = Column(String(50), default="in_progress")  # "in_progress", "completed"
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("DiscussionRun", back_populates="rounds")
    responses = relationship("ModelResponse", back_populates="round", cascade="all, delete-orphan")
    critiques = relationship("Critique", back_populates="round", cascade="all, delete-orphan")


class ModelResponse(Base):
    __tablename__ = "model_responses"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("discussion_runs.id", ondelete="CASCADE"), nullable=False)
    round_id = Column(String, ForeignKey("discussion_rounds.id", ondelete="SET NULL"), nullable=True)
    provider = Column(String(50), nullable=False)  # "chatgpt", "claude", "gemini", "notebooklm"
    model_id = Column(String(100), nullable=True)
    stage = Column(String(50), default="initial_analysis")
    integration_mode = Column(String(50), default="manual")  # "manual", "api"
    prompt_used = Column(Text, nullable=False)
    content = Column(Text, default="")
    status = Column(String(50), default="pending")  # "pending", "completed", "failed"
    error_message = Column(Text, nullable=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("DiscussionRun", back_populates="responses")
    round = relationship("DiscussionRound", back_populates="responses")


class Critique(Base):
    __tablename__ = "critiques"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("discussion_runs.id", ondelete="CASCADE"), nullable=False)
    round_id = Column(String, ForeignKey("discussion_rounds.id", ondelete="SET NULL"), nullable=True)
    reviewer_provider = Column(String(50), nullable=False)
    target_provider = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    unsupported_claims = Column(JSON, default=list)
    contradictions = Column(JSON, default=list)
    hidden_assumptions = Column(JSON, default=list)
    logical_fallacies = Column(JSON, default=list)
    risks_limitations = Column(JSON, default=list)
    status = Column(String(50), default="completed")
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("DiscussionRun", back_populates="critiques")
    round = relationship("DiscussionRound", back_populates="critiques")


class Synthesis(Base):
    __tablename__ = "syntheses"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("discussion_runs.id", ondelete="CASCADE"), nullable=False)
    round_id = Column(String, ForeignKey("discussion_rounds.id", ondelete="SET NULL"), nullable=True)
    moderator_provider = Column(String(50), default="council_moderator")
    mode = Column(String(50), default="manual")
    problem_summary = Column(Text, nullable=True)
    consensus_points = Column(Text, nullable=True)
    disagreements = Column(Text, nullable=True)
    unresolved_critiques = Column(Text, nullable=True)
    evidence_backed_claims = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)
    uncertainties_and_verifications = Column(Text, nullable=True)
    references_cited = Column(Text, nullable=True)
    raw_synthesis = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("DiscussionRun", back_populates="syntheses")


class ProviderConfiguration(Base):
    __tablename__ = "provider_configurations"

    id = Column(String(50), primary_key=True)  # "chatgpt", "claude", "gemini", "notebooklm"
    display_name = Column(String(100), nullable=False)
    is_enabled = Column(Boolean, default=True)
    default_mode = Column(String(50), default="manual")  # "manual", "api"
    official_url = Column(String(255), nullable=False)
    api_key_configured = Column(Boolean, default=False)
    selected_model = Column(String(100), nullable=False)
    supported_models = Column(JSON, default=list)
    usage_limit_monthly_usd = Column(Float, default=20.0)
    current_month_usage_usd = Column(Float, default=0.0)
    is_verified = Column(Boolean, default=True)
    last_checked_at = Column(DateTime, nullable=True)


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("research_projects.id", ondelete="SET NULL"), nullable=True)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)  # "pdf", "txt", "md"
    file_size_bytes = Column(Integer, default=0)
    title = Column(String(255), nullable=False)
    total_pages = Column(Integer, default=1)
    total_chunks = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("ResearchProject", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, default=1)
    content = Column(Text, nullable=False)
    token_count_estimate = Column(Integer, default=0)

    document = relationship("Document", back_populates="chunks")


class SourceReference(Base):
    __tablename__ = "source_references"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("discussion_runs.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(String, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    chunk_id = Column(String, ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True)
    quote = Column(Text, nullable=False)
    page_number = Column(Integer, default=1)
    relevance_score = Column(Float, default=1.0)
    is_verified = Column(Boolean, default=True)  # True = authentic verified excerpt
    source_type = Column(String(50), default="document")  # "document", "notebooklm"

    run = relationship("DiscussionRun", back_populates="source_references")
    document = relationship("Document")
    chunk = relationship("DocumentChunk")


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id = Column(String, primary_key=True, default=generate_uuid)
    provider = Column(String(50), nullable=False)
    model_id = Column(String(100), default="manual-input")
    mode = Column(String(50), default="manual")  # "manual", "api"
    action = Column(String(50), default="discussion")
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    is_actual_cost = Column(Boolean, default=False)
    run_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
