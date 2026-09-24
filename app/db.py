import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Text, JSON, Boolean, Float, select
from sqlalchemy.orm import DeclarativeBase, mapped_column, Session
from .config import ROOT
from .security import ScopeError, sanitize


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id = mapped_column(String, primary_key=True)
    account_id = mapped_column(String, nullable=False)
    verified = mapped_column(Boolean, default=False)
    role = mapped_column(String, default="user")


class Account(Base):
    __tablename__ = "accounts"
    id = mapped_column(String, primary_key=True)
    data = mapped_column(JSON)


class Order(Base):
    __tablename__ = "orders"
    id = mapped_column(String, primary_key=True)
    account_id = mapped_column(String, index=True)
    data = mapped_column(JSON)


class Thread(Base):
    __tablename__ = "threads"
    id = mapped_column(String, primary_key=True)
    user_id = mapped_column(String, index=True)
    title = mapped_column(String)


class Message(Base):
    __tablename__ = "messages"
    id = mapped_column(String, primary_key=True)
    thread_id = mapped_column(String, index=True)
    user_id = mapped_column(String, index=True)
    role = mapped_column(String)
    content = mapped_column(Text)
    payload = mapped_column(JSON, default=dict)
    created_at = mapped_column(String)


class Ticket(Base):
    __tablename__ = "tickets"
    id = mapped_column(String, primary_key=True)
    user_id = mapped_column(String, index=True)
    account_id = mapped_column(String)
    thread_id = mapped_column(String)
    request_id = mapped_column(String, unique=True)
    data = mapped_column(JSON)


class Document(Base):
    __tablename__ = "documents"
    id = mapped_column(String, primary_key=True)
    metadata_json = mapped_column(JSON)
    body = mapped_column(Text)


class Feedback(Base):
    __tablename__ = "feedback"
    id = mapped_column(String, primary_key=True)
    user_id = mapped_column(String)
    response_id = mapped_column(String)
    helpful = mapped_column(Boolean)


class RequestRecord(Base):
    __tablename__ = "requests"
    id = mapped_column(String, primary_key=True)
    user_id = mapped_column(String, index=True)
    trace_id = mapped_column(String)
    latency = mapped_column(Float)
    escalation = mapped_column(Boolean)
    error = mapped_column(Boolean)
    route = mapped_column(String)
    created_at = mapped_column(String)


def uid():
    return str(uuid.uuid4())


def now():
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, url):
        if url.startswith("sqlite:///"):
            Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            url,
            pool_pre_ping=True,
            connect_args={"check_same_thread": False, "timeout": 15}
            if url.startswith("sqlite")
            else {"connect_timeout": 5},
        )
        Base.metadata.create_all(self.engine)

    def seed(self):
        with Session(self.engine) as s:
            for i, data in enumerate(json.loads((ROOT / "data/accounts.json").read_text()), 1):
                if not s.get(Account, data["account_id"]):
                    s.add(Account(id=data["account_id"], data=data))
                if not s.get(User, f"user_{i}"):
                    s.add(User(id=f"user_{i}", account_id=data["account_id"], verified=data["verified"], role="user"))
            if not s.get(User, "admin"):
                s.add(User(id="admin", account_id="acc_1001", verified=True, role="admin"))
            for data in json.loads((ROOT / "data/orders.json").read_text()):
                if not s.get(Order, data["order_id"]):
                    s.add(Order(id=data["order_id"], account_id=data["account_id"], data=data))
            s.commit()

    def user(self, user_id):
        with Session(self.engine) as s:
            x = s.get(User, user_id)
            return dict(user_id=x.id, account_id=x.account_id, verified=x.verified, role=x.role) if x else None

    def new_thread(self, p, title="New conversation"):
        tid = uid()
        with Session(self.engine) as s:
            s.add(Thread(id=tid, user_id=p.user_id, title=sanitize(title)))
            s.commit()
        return {"thread_id": tid, "title": sanitize(title), "messages": []}

    def thread(self, p, tid):
        with Session(self.engine) as s:
            x = s.scalar(select(Thread).where(Thread.id == tid, Thread.user_id == p.user_id))
            if not x:
                raise ScopeError("Thread unavailable")
            messages = s.scalars(
                select(Message)
                .where(Message.thread_id == tid, Message.user_id == p.user_id)
                .order_by(Message.created_at)
            ).all()
            return dict(
                thread_id=x.id,
                title=x.title,
                messages=[dict(id=m.id, role=m.role, content=m.content, payload=m.payload) for m in messages],
            )

    def threads(self, p):
        with Session(self.engine) as s:
            return [
                dict(thread_id=t.id, title=t.title, messages=[])
                for t in s.scalars(select(Thread).where(Thread.user_id == p.user_id))
            ]

    def save_message(self, p, tid, role, content, payload=None, mid=None):
        self.thread(p, tid)
        with Session(self.engine) as s:
            s.add(
                Message(
                    id=mid or uid(),
                    thread_id=tid,
                    user_id=p.user_id,
                    role=role,
                    content=sanitize(content),
                    payload=payload or {},
                    created_at=now(),
                )
            )
            s.commit()

    def account(self, p):
        with Session(self.engine) as s:
            x = s.get(Account, p.account_id)
            return x.data if x else None

    def order(self, p, oid):
        with Session(self.engine) as s:
            # The ownership constraint is in the query, never in frontend or model.
            x = s.scalar(select(Order).where(Order.id == oid, Order.account_id == p.account_id))
            if not x:
                raise ScopeError("Order unavailable in this account")
            return x.data

    def ticket(self, p, tid, summary, category, request_id):
        self.thread(p, tid)
        with Session(self.engine) as s:
            existing = s.scalar(select(Ticket).where(Ticket.request_id == request_id, Ticket.user_id == p.user_id))
            if existing:
                return existing.data
            account = self.account(p)
            data = dict(
                ticket_id="SUP-" + uuid.uuid4().hex[:12].upper(),
                user_id=p.user_id,
                account_id=p.account_id,
                workspace_id=account["workspace_id"],
                summary=sanitize(summary),
                category=category,
                status="escalated",
                timestamp=now(),
                product_area="CloudBox",
                steps_tried="Not yet provided",
                error_message="Not yet provided",
                related_ticket_ids=[],
            )
            s.add(
                Ticket(
                    id=data["ticket_id"],
                    user_id=p.user_id,
                    account_id=p.account_id,
                    thread_id=tid,
                    request_id=request_id,
                    data=data,
                )
            )
            s.commit()
            return data

    def documents(self):
        with Session(self.engine) as s:
            return [(d.metadata_json, d.body) for d in s.scalars(select(Document))]

    def put_document(self, meta, body):
        with Session(self.engine) as s:
            s.merge(Document(id=meta["doc_id"] + "@" + meta["version"], metadata_json=meta, body=body))
            s.commit()

    def feedback(self, p, response_id, helpful):
        with Session(self.engine) as s:
            m = s.scalar(
                select(Message).where(
                    Message.id == response_id, Message.user_id == p.user_id, Message.role == "assistant"
                )
            )
            if not m:
                raise ScopeError("Response unavailable")
            fid = uid()
            s.add(Feedback(id=fid, user_id=p.user_id, response_id=response_id, helpful=helpful))
            s.commit()
            return fid, m.payload.get("trace_id")

    def record(self, p, response):
        with Session(self.engine) as s:
            s.add(
                RequestRecord(
                    id=response["request_id"],
                    user_id=p.user_id,
                    trace_id=response["trace_id"],
                    latency=response["latency_ms"],
                    escalation=response["needs_escalation"],
                    error=any(not e["ok"] for e in response["tool_events"]),
                    route=response["route"],
                    created_at=now(),
                )
            )
            s.commit()

    def monitoring(self, p):
        with Session(self.engine) as s:
            rows = s.scalars(
                select(RequestRecord)
                .where(RequestRecord.user_id == p.user_id)
                .order_by(RequestRecord.created_at.desc())
                .limit(100)
            ).all()
            n = len(rows)
            return dict(
                requests=n,
                mean_latency_ms=sum(x.latency for x in rows) / max(n, 1),
                escalation_rate=sum(x.escalation for x in rows) / max(n, 1),
                error_rate=sum(x.error for x in rows) / max(n, 1),
                recent=[
                    dict(
                        request_id=x.id,
                        trace_id=x.trace_id,
                        latency_ms=x.latency,
                        route=x.route,
                        error=x.error,
                        created_at=x.created_at,
                    )
                    for x in rows
                ],
            )
