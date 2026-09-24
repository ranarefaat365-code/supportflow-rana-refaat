import time
import threading
from .config import ROOT
from .db import Database, uid
from .rag import Retriever
from .telemetry import Telemetry
from .tools import ToolLayer
from .graph import Workflow
from .security import sanitize, ScopeError
from .schemas import ChatResponse


class Service:
    def __init__(self, settings):
        settings.validate_runtime()
        self.settings = settings
        self.db = Database(settings.database_url)
        self.db.seed()
        self.telemetry = Telemetry(settings)
        self.rag = Retriever(settings, self.db, self.telemetry)
        self.tools = ToolLayer(self.db, self.rag, self.telemetry, settings)
        self.workflow = Workflow(self.tools, self.telemetry, settings)
        self.chat_lock = threading.RLock()  # Single-worker reference deployment; serializes same-thread updates.
        documents = self.db.documents()
        if not documents:
            self.rag.ingest_corpus(ROOT / "rag_materials")
        elif self.rag.client.count(self.rag.collection).count == 0:
            # Rehydrate a missing or newly selected embedding collection from relational document records.
            import yaml

            for meta, body in documents:
                self.rag.ingest(
                    "---\n" + yaml.safe_dump({k: v for k, v in meta.items() if k != "source_path"}) + "---\n\n" + body,
                    meta["source_path"],
                )

    def chat(self, p, request, request_id=None):
        with self.chat_lock:
            if request.user_id and request.user_id != p.user_id:
                raise ScopeError("User mismatch")
            tid = request.thread_id or self.db.new_thread(p)["thread_id"]
            self.db.thread(p, tid)  # Before graph, model, retrieval or other effects.
            message = sanitize(request.message)
            start = time.perf_counter()
            rid = request_id or uid()
            mid = uid()
            with self.telemetry.trace(p.user_id, tid, rid) as trace:
                state = self.workflow.run(
                    dict(
                        user_id=p.user_id,
                        principal=p.model_dump(),
                        thread_id=tid,
                        request=message,
                        request_id=rid,
                        trace_id=trace["trace_id"],
                        filters=request.filters.model_dump(),
                        trajectory=[],
                        tool_events=[],
                    )
                )
                result = ChatResponse(
                    thread_id=tid,
                    response_id=mid,
                    answer=state["final_answer"],
                    citations=state["evidence"],
                    tool_events=state["tool_events"],
                    needs_escalation=state["escalation_state"]["needed"],
                    ticket_id=state["escalation_state"]["ticket_id"],
                    route=state["route"],
                    trace_id=trace["trace_id"],
                    request_id=rid,
                    latency_ms=round((time.perf_counter() - start) * 1000, 2),
                    trajectory=state["trajectory"],
                ).model_dump()
                trace["summary"] = {
                    "route": state["route"],
                    "model_calls": state.get("model_calls", 0),
                    "tool_calls": state.get("tool_calls", 0),
                    "search_calls": state.get("search_calls", 0),
                    "latency_ms": result["latency_ms"],
                }
                self.db.save_message(p, tid, "user", message)
                self.db.save_message(p, tid, "assistant", result["answer"], result, mid=mid)
                self.db.record(p, result)
            return result

    def close(self):
        self.telemetry.close()
        self.rag.close()
        self.db.engine.dispose()
