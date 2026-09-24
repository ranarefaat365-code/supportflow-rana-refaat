import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from .config import Settings
from .service import Service
from .schemas import (
    ChatRequest,
    ChatResponse,
    ThreadCreate,
    ThreadView,
    DocumentCreate,
    DocumentInfo,
    FeedbackRequest,
    TicketRequest,
    ToolEvent,
    Principal,
    StatusResponse,
    Ack,
    EvalRequest,
    EvalResponse,
    MonitoringResponse,
)
from .security import authenticate, ScopeError
from .tools import TicketArgs


def create_app(settings=None):
    config = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        app.state.service = Service(config)
        yield
        app.state.service.close()

    app = FastAPI(title="SupportFlow API", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins.split(","),
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["X-Request-ID"],
    )
    bearer = HTTPBearer(auto_error=False)

    def svc(request: Request):
        return request.app.state.service

    def principal(credentials: HTTPAuthorizationCredentials = Depends(bearer), service=Depends(svc)):
        if not credentials:
            raise HTTPException(401, detail={"code": "UNAUTHENTICATED", "message": "Sign in to continue."})
        return authenticate(credentials.credentials, config, service.db)

    def admin(p: Principal = Depends(principal)):
        if p.role != "admin":
            raise HTTPException(403, detail={"code": "ADMIN_REQUIRED", "message": "Administrator access required."})
        return p

    @app.middleware("http")
    async def request_id(request, call_next):
        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(ScopeError)
    async def scope_error(request, exc):
        return JSONResponse(
            status_code=403,
            content={
                "error": {"code": "SCOPE_DENIED", "message": "Resource unavailable in this session."},
                "request_id": request.state.request_id,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # FastAPI defaults can echo secret-bearing invalid input. Return only locations/types.
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "INVALID_REQUEST",
                    "fields": [{"location": list(e["loc"]), "type": e["type"]} for e in exc.errors()],
                },
                "request_id": request.state.request_id,
            },
        )

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        return JSONResponse(
            status_code=503,
            content={
                "error": {"code": "DEPENDENCY_UNAVAILABLE", "message": "The request could not be completed safely."},
                "request_id": request.state.request_id,
            },
        )

    @app.get("/health", response_model=StatusResponse)
    def health(service=Depends(svc)):
        dependencies = {}
        try:
            with service.db.engine.connect() as c:
                c.execute(text("SELECT 1"))
            dependencies["database"] = "ok"
        except Exception:
            dependencies["database"] = "unavailable"
        try:
            service.rag.client.get_collections()
            dependencies["qdrant"] = "ok"
        except Exception:
            dependencies["qdrant"] = "unavailable"
        dependencies["langfuse"] = "configured_unverified" if service.telemetry.client else "not_configured"
        dependencies["model"] = config.model_mode
        return {
            "status": "ok" if dependencies["database"] == dependencies["qdrant"] == "ok" else "degraded",
            "dependencies": dependencies,
        }

    @app.post("/chat", response_model=ChatResponse)
    def chat(body: ChatRequest, request: Request, p=Depends(principal), service=Depends(svc)):
        return service.chat(p, body, request.state.request_id)

    @app.post("/threads", response_model=ThreadView)
    def new_thread(body: ThreadCreate, p=Depends(principal), service=Depends(svc)):
        return service.db.new_thread(p, body.title)

    @app.get("/threads", response_model=list[ThreadView])
    def threads(p=Depends(principal), service=Depends(svc)):
        return service.db.threads(p)

    @app.get("/threads/{thread_id}", response_model=ThreadView)
    def thread(thread_id: str, p=Depends(principal), service=Depends(svc)):
        return service.db.thread(p, thread_id)

    @app.post("/documents", response_model=DocumentInfo)
    def ingest(body: DocumentCreate, p=Depends(admin), service=Depends(svc)):
        try:
            return service.rag.ingest(body.markdown, "admin-upload")
        except ValueError:
            raise HTTPException(
                422,
                detail={
                    "code": "INVALID_DOCUMENT",
                    "message": "Check YAML metadata, section size and sensitive content.",
                },
            ) from None

    @app.get("/documents", response_model=list[DocumentInfo])
    def documents(p=Depends(principal), service=Depends(svc)):
        return [m for m, _ in service.db.documents()]

    @app.post("/feedback", response_model=Ack)
    def feedback(body: FeedbackRequest, p=Depends(principal), service=Depends(svc)):
        fid, trace_id = service.db.feedback(p, body.response_id, body.helpful)
        service.telemetry.feedback(trace_id, body.helpful)
        return {"ok": True, "id": fid}

    @app.post("/tickets", response_model=ToolEvent)
    def tickets(body: TicketRequest, request: Request, p=Depends(principal), service=Depends(svc)):
        return service.tools.call(
            "create_ticket", TicketArgs(**body.model_dump(), request_id=request.state.request_id), p
        )

    @app.post("/evals/run", response_model=EvalResponse)
    def evals(body: EvalRequest, p=Depends(admin)):
        if not config.enable_evals:
            raise HTTPException(403, detail={"code": "EVALS_DISABLED"})
        # A subprocess blocks outbound sockets before importing the evaluator.
        import subprocess
        import sys
        import json
        from pathlib import Path

        output = Path("runtime/evaluations") / str(uuid.uuid4())
        process = subprocess.run(
            [sys.executable, "-m", "scripts.offline_eval", str(output)], capture_output=True, timeout=90
        )
        report_path = output / "eval_results.json"
        if not report_path.exists():
            raise HTTPException(503, detail={"code": "EVALUATION_FAILED"})
        return {
            "status": "completed" if process.returncode == 0 else "completed_with_failures",
            "report": json.loads(report_path.read_text()),
        }

    @app.get("/monitoring", response_model=MonitoringResponse)
    def monitoring(p=Depends(principal), service=Depends(svc)):
        return service.db.monitoring(p)

    return app


app = create_app()
