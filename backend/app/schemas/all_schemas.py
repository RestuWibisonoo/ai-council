from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# --- Provider Schemas ---
class ProviderConfigBase(BaseModel):
    display_name: str
    is_enabled: bool = True
    default_mode: str = "manual"  # "manual" | "api"
    official_url: str
    selected_model: str
    supported_models: List[str] = Field(default_factory=list)
    usage_limit_monthly_usd: float = 20.0


class ProviderConfigOut(ProviderConfigBase):
    id: str
    api_key_configured: bool
    current_month_usage_usd: float
    is_verified: bool
    last_checked_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProviderConfigUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    default_mode: Optional[str] = None
    selected_model: Optional[str] = None
    api_key: Optional[str] = None  # Handled safely by backend, never returned
    usage_limit_monthly_usd: Optional[float] = None


class ProviderTestRequest(BaseModel):
    api_key: Optional[str] = None
    model: Optional[str] = None


class ProviderTestResponse(BaseModel):
    success: bool
    message: str
    status_code: Optional[int] = None
    model_tested: Optional[str] = None


# --- Document Schemas ---
class DocumentChunkOut(BaseModel):
    id: str
    chunk_index: int
    page_number: int
    content: str
    token_count_estimate: int

    model_config = ConfigDict(from_attributes=True)


class DocumentOut(BaseModel):
    id: str
    project_id: Optional[str] = None
    filename: str
    original_name: str
    file_type: str
    file_size_bytes: int
    title: str
    total_pages: int
    total_chunks: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentDetailOut(DocumentOut):
    chunks: List[DocumentChunkOut] = Field(default_factory=list)


class DocumentSearchResult(BaseModel):
    document_id: str
    chunk_id: str
    document_title: str
    page_number: int
    content: str
    relevance_score: float
    is_verified: bool = True


# --- Research Project Schemas ---
class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    research_question: Optional[str] = None
    notes: Optional[str] = None


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    research_question: Optional[str] = None
    notes: Optional[str] = None


class ProjectOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    research_question: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Discussion & Debate Schemas ---
class ModelResponseOut(BaseModel):
    id: str
    run_id: str
    round_id: Optional[str] = None
    provider: str
    model_id: Optional[str] = None
    stage: str
    integration_mode: str
    prompt_used: str
    content: str
    status: str
    error_message: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CritiqueOut(BaseModel):
    id: str
    run_id: str
    round_id: Optional[str] = None
    reviewer_provider: str
    target_provider: str
    content: str
    unsupported_claims: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    hidden_assumptions: List[str] = Field(default_factory=list)
    logical_fallacies: List[str] = Field(default_factory=list)
    risks_limitations: List[str] = Field(default_factory=list)
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SynthesisOut(BaseModel):
    id: str
    run_id: str
    round_id: Optional[str] = None
    moderator_provider: str
    mode: str
    problem_summary: Optional[str] = None
    consensus_points: Optional[str] = None
    disagreements: Optional[str] = None
    unresolved_critiques: Optional[str] = None
    evidence_backed_claims: Optional[str] = None
    recommendations: Optional[str] = None
    uncertainties_and_verifications: Optional[str] = None
    references_cited: Optional[str] = None
    raw_synthesis: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SourceReferenceOut(BaseModel):
    id: str
    run_id: str
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None
    quote: str
    page_number: int
    relevance_score: float
    is_verified: bool
    source_type: str

    model_config = ConfigDict(from_attributes=True)


class DiscussionRoundOut(BaseModel):
    id: str
    run_id: str
    round_number: int
    stage: str
    status: str
    created_at: datetime
    responses: List[ModelResponseOut] = Field(default_factory=list)
    critiques: List[CritiqueOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class DiscussionRunOut(BaseModel):
    id: str
    conversation_id: str
    mode: str
    status: str
    current_stage: str
    current_round: int
    max_rounds: int
    query: str
    selected_providers: List[str] = Field(default_factory=list)
    linked_document_ids: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    responses: List[ModelResponseOut] = Field(default_factory=list)
    critiques: List[CritiqueOut] = Field(default_factory=list)
    syntheses: List[SynthesisOut] = Field(default_factory=list)
    source_references: List[SourceReferenceOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class DiscussionCreateRequest(BaseModel):
    query: str = Field(..., min_length=1)
    mode: str = "parallel"  # "parallel" | "debate" | "research"
    selected_providers: List[str] = Field(default=["chatgpt", "claude", "gemini"])
    max_rounds: int = Field(default=2, ge=1, le=3)
    project_id: Optional[str] = None
    linked_document_ids: List[str] = Field(default_factory=list)
    conversation_title: Optional[str] = None


class SubmitManualResponseRequest(BaseModel):
    response_id: str
    content: str = Field(..., min_length=1)
    model_id: Optional[str] = None
    status: str = "completed"  # "completed" | "failed"


class SubmitManualSynthesisRequest(BaseModel):
    run_id: str
    moderator_provider: str = "human_moderator"
    allow_partial: bool = False
    problem_summary: Optional[str] = None
    consensus_points: Optional[str] = None
    disagreements: Optional[str] = None
    unresolved_critiques: Optional[str] = None
    evidence_backed_claims: Optional[str] = None
    recommendations: Optional[str] = None
    uncertainties_and_verifications: Optional[str] = None
    references_cited: Optional[str] = None
    raw_synthesis: str = Field(..., min_length=1)



class ConversationOut(BaseModel):
    id: str
    project_id: Optional[str] = None
    title: str
    mode: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailOut(ConversationOut):
    runs: List[DiscussionRunOut] = Field(default_factory=list)


# --- Usage Schemas ---
class UsageRecordOut(BaseModel):
    id: str
    provider: str
    model_id: str
    mode: str
    action: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    is_actual_cost: bool
    run_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UsageSummaryOut(BaseModel):
    total_requests: int
    manual_requests: int
    api_requests: int
    total_tokens: int
    estimated_total_cost_usd: float
    by_provider: Dict[str, Dict[str, Any]]
