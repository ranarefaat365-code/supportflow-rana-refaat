import contextvars
import json
import time
import uuid
from pathlib import Path
from contextlib import contextmanager, ExitStack

CURRENT = contextvars.ContextVar("trace", default=None)
PARENT = contextvars.ContextVar("parent", default=None)


class Telemetry:
    def __init__(self, settings):
        self.path = Path(settings.artifact_dir)
        self.path.mkdir(parents=True, exist_ok=True)
        self.client = None
        if settings.langfuse_public_key and settings.langfuse_secret_key:
            try:
                from langfuse import Langfuse

                self.client = Langfuse(
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                    base_url=settings.langfuse_base_url,
                    timeout=5,
                )
            except Exception:
                self.client = None

    @contextmanager
    def remote_span(self, name, kind="span", **kwargs):
        stack = ExitStack()
        remote = None
        try:
            if self.client:
                try:
                    remote = stack.enter_context(
                        self.client.start_as_current_observation(name=name, as_type=kind, **kwargs)
                    )
                except Exception:
                    trace = CURRENT.get()
                    if trace is not None:
                        trace["monitoring_error"] = "observation_unavailable"
            yield remote
        finally:
            try:
                stack.close()
            except Exception:
                trace = CURRENT.get()
                if trace is not None:
                    trace["monitoring_error"] = "observation_close_failed"

    @contextmanager
    def trace(self, user_id, thread_id, request_id):
        trace = dict(
            trace_id=uuid.uuid4().hex,
            request_id=request_id,
            user_id=user_id,
            session_id=thread_id,
            spans=[],
            export_status="not_configured" if not self.client else "unverified",
        )
        token = CURRENT.set(trace)
        try:
            with self.remote_span("supportflow.request", trace_context={"trace_id": trace["trace_id"]}) as root:
                propagation = ExitStack()
                if root:
                    try:
                        from langfuse import propagate_attributes

                        propagation.enter_context(propagate_attributes(user_id=user_id, session_id=thread_id))
                        trace["trace_id"] = root.trace_id
                        trace["export_status"] = "attempted_not_confirmed"
                    except Exception:
                        trace["monitoring_error"] = "propagation_failed"
                try:
                    yield trace
                finally:
                    try:
                        propagation.close()
                    except Exception:
                        pass
        finally:
            try:
                # No raw requests, answers, tool results or customer PII in traces.
                (self.path / (trace["trace_id"] + ".json")).write_text(json.dumps(trace, indent=2))
            except OSError:
                pass  # Monitoring must not break resolution.
            CURRENT.reset(token)

    @contextmanager
    def span(self, name, kind="span", **metadata):
        trace = CURRENT.get()
        start = time.perf_counter()
        row = dict(
            id=uuid.uuid4().hex[:16], parent_id=PARENT.get(), name=name, kind=kind, metadata=metadata, error=False
        )
        token = PARENT.set(row["id"])
        try:
            with self.remote_span(name, kind, metadata=metadata) as remote:
                yield row
                if remote and kind in {"generation", "embedding"}:
                    try:
                        remote.update(
                            model=row.get("model"), usage_details=row.get("usage"), cost_details=row.get("cost")
                        )
                    except Exception:
                        if trace is not None:
                            trace["monitoring_error"] = "usage_update_failed"
        except Exception:
            row["error"] = True
            raise
        finally:
            row["latency_ms"] = round((time.perf_counter() - start) * 1000, 3)
            if trace is not None:
                trace["spans"].append(row)
            PARENT.reset(token)

    def feedback(self, trace_id, value):
        if self.client and trace_id:
            try:
                self.client.create_score(trace_id=trace_id, name="helpfulness", value=int(value), data_type="BOOLEAN")
            except Exception:
                pass

    def close(self):
        if self.client:
            try:
                self.client.flush()
            except Exception:
                pass
