import time
import httpx
from pydantic import Field
from .schemas import Strict, Filters, Principal, ToolEvent, ToolError
from .security import ScopeError, require_scope, sanitize


class SearchArgs(Strict):
    query: str = Field(max_length=8000)
    filters: Filters = Field(default_factory=Filters)
    limit: int = Field(default=4, ge=1, le=4)


class AccountArgs(Strict):
    account_id: str


class OrderArgs(AccountArgs):
    order_id: str


class StatusArgs(Strict):
    pass


class SummaryArgs(Strict):
    thread_id: str


class TicketArgs(SummaryArgs):
    summary: str
    category: str
    request_id: str


class ToolLayer:
    def __init__(self, db, rag, telemetry, settings):
        self.db = db
        self.rag = rag
        self.telemetry = telemetry
        self.settings = settings

    def call(self, name, args, p: Principal):
        start = time.perf_counter()
        with self.telemetry.span("tool." + name):
            try:
                fn = getattr(self, name)
                data = fn(args, p)
                event = ToolEvent(name=name, ok=True, data=data)
            except ScopeError:
                event = ToolEvent(
                    name=name,
                    ok=False,
                    error=ToolError(
                        code="SCOPE_DENIED", message="This resource is unavailable in your authenticated account."
                    ),
                )
            except PermissionError:
                event = ToolEvent(
                    name=name,
                    ok=False,
                    error=ToolError(
                        code="VERIFICATION_REQUIRED",
                        message="Complete verification through the secure sign-in flow. Do not send a code here.",
                    ),
                )
            except (httpx.TimeoutException, TimeoutError):
                event = ToolEvent(
                    name=name,
                    ok=False,
                    error=ToolError(code="TIMEOUT", message="The service did not respond in time.", retryable=True),
                )
            except Exception:
                event = ToolEvent(
                    name=name,
                    ok=False,
                    error=ToolError(
                        code="TOOL_UNAVAILABLE",
                        message="The requested operation is temporarily unavailable.",
                        retryable=True,
                    ),
                )
        event.latency_ms = round((time.perf_counter() - start) * 1000, 3)
        return event.model_dump()

    def search_knowledge_base(self, args: SearchArgs, p):
        return self.rag.search(args.query, args.filters, args.limit)

    def get_account(self, args: AccountArgs, p):
        require_scope(p, args.account_id)
        if not p.verified:
            raise PermissionError()
        return self.db.account(p)

    def get_order(self, args: OrderArgs, p):
        require_scope(p, args.account_id)
        if not p.verified:
            raise PermissionError()
        return self.db.order(p, args.order_id)

    def get_service_status(self, args: StatusArgs, p):
        if not self.settings.status_url:
            # Never invent a live incident from historical corpus or fixture.
            return {
                "status": "unknown",
                "message": "Live service status is not configured. Current CloudBox availability cannot be verified.",
                "source": "unconfigured",
                "observed_at": None,
            }
        with httpx.Client(timeout=4, follow_redirects=False) as client:
            response = client.get(self.settings.status_url)
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict) or data.get("status") not in {"operational", "degraded", "outage", "unknown"}:
            raise ValueError("Invalid status response")
        return {
            "status": data["status"],
            "message": sanitize(str(data.get("message", "No status message."))[:700]),
            "source": "configured-status-provider",
            "observed_at": data.get("observed_at"),
        }

    def create_ticket(self, args: TicketArgs, p):
        return self.db.ticket(p, args.thread_id, sanitize(args.summary), args.category, args.request_id)

    def get_thread_summary(self, args: SummaryArgs, p):
        messages = self.db.thread(p, args.thread_id)["messages"]
        return {"recent_user_messages": [m["content"] for m in messages if m["role"] == "user"][-3:]}
