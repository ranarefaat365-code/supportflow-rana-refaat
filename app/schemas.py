from typing import Literal, Any
from pydantic import BaseModel, Field, ConfigDict


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Principal(Strict):
    user_id: str
    account_id: str
    verified: bool = False
    role: Literal["user", "admin"] = "user"


class Filters(Strict):
    product: str | None = None
    version: str | None = None
    source_type: str | None = None
    trust_level: Literal["official", "internal", "untrusted"] | None = "official"


class Citation(Strict):
    doc_id: str
    title: str
    product: str
    version: str
    source_type: str
    trust_level: str
    chunk_id: str
    content: str
    score: float
    source_path: str


class ToolError(Strict):
    code: str
    message: str
    retryable: bool = False


class ToolEvent(Strict):
    name: str
    ok: bool
    data: Any = None
    error: ToolError | None = None
    latency_ms: float = 0


class ChatRequest(Strict):
    message: str = Field(min_length=1, max_length=4000)
    thread_id: str | None = None
    filters: Filters = Field(default_factory=Filters)
    # Never trusted; present for compatibility with the assignment contract.
    user_id: str | None = None


class ChatResponse(Strict):
    thread_id: str
    response_id: str
    answer: str
    citations: list[Citation]
    tool_events: list[ToolEvent]
    needs_escalation: bool
    ticket_id: str | None = None
    route: str
    trace_id: str
    request_id: str
    latency_ms: float
    trajectory: list[str]


class ThreadCreate(Strict):
    title: str = Field(default="New conversation", max_length=100)


class MessageView(Strict):
    id: str
    role: str
    content: str
    payload: dict = Field(default_factory=dict)


class ThreadView(Strict):
    thread_id: str
    title: str
    messages: list[MessageView] = Field(default_factory=list)


class DocumentCreate(Strict):
    markdown: str = Field(min_length=20, max_length=60000)


class DocumentInfo(Strict):
    doc_id: str
    title: str
    product: str
    version: str
    source_type: str
    trust_level: str
    source_path: str


class FeedbackRequest(Strict):
    response_id: str
    helpful: bool


class TicketRequest(Strict):
    thread_id: str
    summary: str = Field(min_length=3, max_length=1500)
    category: Literal["security", "privacy", "billing", "technical"] = "technical"


class EvalRequest(Strict):
    suite: Literal["structural"] = "structural"


class StatusResponse(Strict):
    status: str
    dependencies: dict[str, str]


class Ack(Strict):
    ok: bool
    id: str | None = None


class EvalResponse(Strict):
    status: str
    report: dict


class MonitoringResponse(Strict):
    requests: int
    mean_latency_ms: float
    escalation_rate: float
    error_rate: float
    recent: list[dict]
