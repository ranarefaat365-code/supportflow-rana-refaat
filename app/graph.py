import re
import math
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from .schemas import Principal, Filters
from .tools import SearchArgs, AccountArgs, OrderArgs, StatusArgs, SummaryArgs, TicketArgs
from .model import EvidenceModel
from .rag import normalize


class State(TypedDict, total=False):
    user_id: str
    principal: dict
    thread_id: str
    request_id: str
    request: str
    route: str
    query: str
    retrieval_query: str
    filters: dict
    retrieved_context: list
    evidence: list
    tool_events: list
    escalation_state: dict
    final_answer: str
    trace_id: str
    trajectory: list
    excerpts: list
    diagnostics: list
    model_calls: int
    tool_calls: int
    search_calls: int
    errors: list


FALLBACK = "I do not have enough official evidence to answer that safely. Which CloudBox feature or issue would you like help with?"


class Workflow:
    def __init__(self, tools, telemetry, settings):
        self.tools = tools
        self.telemetry = telemetry
        self.settings = settings
        self.model = EvidenceModel(settings, telemetry)
        g = StateGraph(State)
        for name, fn in [
            ("orchestrator", self.orchestrator),
            ("knowledge", self.knowledge),
            ("troubleshooting", self.troubleshooting),
            ("account_tools", self.account_tools),
            ("escalation", self.escalation),
            ("critic_response", self.critic_response),
        ]:
            g.add_node(name, self.instrument(name, fn))
        g.add_edge(START, "orchestrator")
        g.add_edge("orchestrator", "knowledge")
        g.add_conditional_edges(
            "knowledge",
            lambda s: {
                "knowledge": "critic_response",
                "troubleshooting": "troubleshooting",
                "account_tool": "account_tools",
                "status_tool": "account_tools",
                "escalation": "escalation",
            }[s["route"]],
        )
        g.add_edge("troubleshooting", "critic_response")
        g.add_conditional_edges(
            "account_tools", lambda s: "escalation" if s["escalation_state"]["needed"] else "critic_response"
        )
        g.add_edge("escalation", "critic_response")
        g.add_edge("critic_response", END)
        self.compiled = g.compile()

    def instrument(self, name, fn):
        def run(s):
            with self.telemetry.span("agent." + name):
                s["trajectory"] = [*s.get("trajectory", []), name]
                return fn(s)

        return run

    def call(self, s, name, args):
        if s.get("tool_calls", 0) >= 8:
            raise RuntimeError("Tool budget exhausted")
        s["tool_calls"] = s.get("tool_calls", 0) + 1
        event = self.tools.call(name, args, Principal(**s["principal"]))
        s["tool_events"] = [*s.get("tool_events", []), event]
        return event

    def orchestrator(self, s):
        history = self.call(s, "get_thread_summary", SummaryArgs(thread_id=s["thread_id"]))
        q = s["request"].lower()
        prior = history["data"]["recent_user_messages"] if history["ok"] else []
        # Only scoped, sanitized USER turns are used to resolve a short follow-up.
        contextual = bool(re.search(r"\b(it|that|those|them|what about|and the|still|did not help|didn.t help)\b", q))
        query = (" ".join(prior[-2:]) + " " + s["request"]) if contextual and prior else s["request"]
        route = "knowledge"
        if re.search(
            r"sensitive disclosure|someone accessed|takeover|hacked|exposed credential|data (?:loss|export|deletion)|privacy|delete my account|password|refund|charged twice|duplicate charge|payment dispute|legal request|did not help|didn.t help|still (?:blocked|not syncing)",
            q,
        ):
            route = "escalation"
        elif re.search(
            r"outage|status page|currently.*(?:down|experiencing)|service.*(?:down|status)|many.*(?:users|members).*affected",
            q,
        ):
            route = "status_tool"
        elif re.search(r"\bord(?:er)?[_ ]|\bacc_\d+|my account (?:details|plan|information)|check my account", q):
            route = "account_tool"
        elif re.search(
            r"not sync|sync (?:problem|issue)|duplicat.*offline|files are duplicated|conflict cop|syncing", q
        ):
            route = "troubleshooting"
        s.update(
            route=route,
            query=query,
            evidence=[],
            retrieved_context=[],
            escalation_state={"needed": route == "escalation", "ticket_id": None},
            model_calls=0,
            search_calls=0,
        )
        return s

    def knowledge(self, s):
        query = s["query"]
        if s["route"] == "escalation":
            if re.search(r"refund|charg|invoice|payment", query.lower()):
                query += " billing refund policy escalation"
            elif re.search(r"export|privacy|delet", query.lower()):
                query += " privacy export security escalation"
            elif re.search(r"accessed|takeover|password|hacked|credential|sensitive", query.lower()):
                query += " security account takeover escalation"
            else:
                query += " support escalation policy"
        elif s["route"] == "account_tool":
            query += " account verification private details"
        elif s["route"] == "status_tool":
            query += " current service status"
        elif s["route"] == "troubleshooting":
            query += " desktop sync troubleshooting duplicate conflict"
        s["retrieval_query"] = query
        event = self.call(s, "search_knowledge_base", SearchArgs(query=query, filters=Filters(**s.get("filters", {}))))
        s["search_calls"] += 1
        chunks = event["data"] if event["ok"] else []
        if s["route"] == "account_tool" or (s["route"] == "escalation" and "password" in s["request"].lower()):
            policy = self.call(
                s,
                "search_knowledge_base",
                SearchArgs(
                    query="account order verification support agent playbook",
                    filters=Filters(product="SupportFlow", trust_level="internal", source_type="agent_instruction"),
                    limit=1,
                ),
            )
            s["search_calls"] += 1
            if policy["ok"]:
                chunks += policy["data"]
        s["retrieved_context"] = chunks
        s["evidence"] = chunks
        return s

    def troubleshooting(self, s):
        # Extract the applicable atomic workflow, preserving its condition and order.
        duplicate = bool(re.search(r"duplicat|conflict", s["request"].lower()))
        diagnostics = []
        for chunk in s["evidence"]:
            if chunk["source_type"] != "troubleshooting":
                continue
            if duplicate:
                paragraphs = re.split(r"\n\s*\n", chunk["content"])
                diagnostics.extend((p, chunk) for p in paragraphs if "duplicate files appear" in p)
            else:
                match = re.search(r"If files are not syncing.*?(?=\n\nIf|\Z)", chunk["content"], re.S)
                if match:
                    diagnostics.append((match.group(0).strip(), chunk))
        s["diagnostics"] = diagnostics
        return s

    def account_tools(self, s):
        p = Principal(**s["principal"])
        if s["route"] == "status_tool":
            event = self.call(s, "get_service_status", StatusArgs())
            if (
                event["ok"]
                and event["data"]["status"] in {"degraded", "outage"}
                and re.search(r"many|workspace.*affected|multiple users", s["request"].lower())
            ):
                s["escalation_state"]["needed"] = True
        else:
            accounts = re.findall(r"\bacc_\d+\b", s["request"])
            orders = re.findall(r"\bord_\d+\b", s["request"])
            # Reject ALL mismatched identifiers, even when an owned identifier also appears.
            account = next((a for a in accounts if a != p.account_id), p.account_id)
            if len(set(orders)) > 1:
                s["errors"] = ["Please request one order at a time."]
            elif orders:
                self.call(s, "get_order", OrderArgs(account_id=account, order_id=orders[0]))
            else:
                self.call(s, "get_account", AccountArgs(account_id=account))
        return s

    def escalation(self, s):
        q = s["request"].lower()
        category = (
            "billing"
            if re.search(r"refund|charg|invoice|payment", q)
            else "privacy"
            if re.search(r"export|delet|privacy", q)
            else "security"
            if re.search(r"password|accessed|takeover|hacked|credential|sensitive", q)
            else "technical"
        )
        event = self.call(
            s,
            "create_ticket",
            TicketArgs(thread_id=s["thread_id"], summary=s["request"], category=category, request_id=s["request_id"]),
        )
        if event["ok"]:
            s["escalation_state"]["ticket_id"] = event["data"]["ticket_id"]
        return s

    def select_excerpts(self, s):
        terms = set(re.findall(r"[a-z0-9]+", normalize(s.get("retrieval_query", s["query"])))) - {
            "the",
            "a",
            "an",
            "i",
            "my",
            "is",
            "it",
            "to",
            "and",
            "of",
            "for",
            "do",
            "does",
            "which",
            "what",
            "can",
            "how",
            "with",
            "me",
            "in",
            "you",
            "cloudbox",
            "please",
            "tell",
            "need",
            "about",
            "whether",
            "short",
            "answer",
            "would",
            "like",
        }
        candidates = []
        for chunk in s["evidence"]:
            # Group contiguous list steps with introductory condition.
            body = re.sub(r"^#{1,3} .*\n*", "", chunk["content"]).strip()
            paras = re.split(r"\n\s*\n", body)
            for i, para in enumerate(paras):
                if re.match(r"\d+\. ", para) and i:
                    para = paras[i - 1] + "\n\n" + para
                if "one-time verification code" in para:
                    continue
                overlap = len(terms & set(re.findall(r"[a-z0-9]+", normalize(para))))
                if overlap:
                    candidates.append((overlap, para, chunk))
        # Downweight generic terms present in many paragraphs; rare terms such as SSO matter more.
        candidate_terms = [set(re.findall(r"[a-z0-9]+", normalize(x[1]))) for x in candidates]
        weights = {
            term: math.log(1 + len(candidates) / (1 + sum(term in words for words in candidate_terms)))
            for term in terms
        }
        candidates = [
            (sum(weights[t] for t in terms & words), item[1], item[2])
            for item, words in zip(candidates, candidate_terms)
        ]
        candidates.sort(key=lambda x: x[0], reverse=True)
        all_candidates = list(candidates)
        if candidates:
            candidates = [x for x in candidates if x[0] >= candidates[0][0] * 0.4]
        selected = []
        seen = set()
        # At most two excerpts per document, up to four total.
        # First select one relevant excerpt from each source, then fill remaining slots.
        diverse = []
        source_seen = set()
        for item in all_candidates:
            if item[2]["doc_id"] not in source_seen:
                diverse.append(item)
                source_seen.add(item[2]["doc_id"])
        ordered = diverse[:2] + candidates
        for _, para, chunk in ordered:
            key = chunk["doc_id"]
            if para in seen or sum(x[1]["doc_id"] == key for x in selected) >= 2:
                continue
            selected.append((para, chunk))
            seen.add(para)
            if len(selected) == 4:
                break
        if self.settings.model_mode == "llm" and selected:
            s["model_calls"] = 1
            try:
                paragraphs = [x[1] for x in candidates[:10]]
                chosen = self.model.select(s["request"], paragraphs)
                if chosen is not None:
                    selected = [(text, next(c for _, p, c in candidates if p == text)) for text in chosen]
            except Exception:
                s["errors"] = [*s.get("errors", []), "Model unavailable; used evidence-only extractive fallback."]
        return selected

    def critic_response(self, s):
        selected = self.select_excerpts(s)
        if s.get("diagnostics"):
            selected = (
                s["diagnostics"] + [(text, c) for text, c in selected if c["source_type"] != "troubleshooting"][:2]
            )
        # Only exact excerpts can survive this critic. No generated factual claim is trusted.
        selected = [(text, c) for text, c in selected if text in c["content"] and c["trust_level"] == "official"]
        policy_chunks = [
            c for c in s["evidence"] if c["source_type"] == "agent_instruction" and c["trust_level"] == "internal"
        ]
        cited = []
        lines = []
        for text, c in selected:
            if c["chunk_id"] not in [x["chunk_id"] for x in cited]:
                cited.append(c)
            lines.append(text + f"\n[{c['title']} · {c['doc_id']} v{c['version']}]")
        for c in policy_chunks:
            cited.append(c)
            lines.append(
                f"Account operations follow the internal tool-access policy. [{c['title']} · {c['doc_id']} v{c['version']} · internal]"
            )
        s["excerpts"] = [x[0] for x in selected]
        pre = []
        if s.get("errors"):
            pre.extend(s["errors"])
        for e in s["tool_events"]:
            if e["name"] in {"get_order", "get_account", "get_service_status"}:
                if not e["ok"]:
                    pre.append(e["error"]["message"])
                elif e["name"] == "get_order":
                    d = e["data"]
                    pre.append(
                        f"Verified order {d['order_id']}: {d['amount_usd']} USD; status: {d['status']}. [Authenticated order tool]"
                    )
                elif e["name"] == "get_account":
                    d = e["data"]
                    pre.append(
                        f"Your authenticated account {d['account_id']} is on the {d['plan']} plan. [Authenticated account tool]"
                    )
                else:
                    pre.append(e["data"]["message"] + " [Service status tool]")
        if s["escalation_state"]["needed"]:
            tid = s["escalation_state"]["ticket_id"]
            pre.append(
                f"Escalated. Ticket {tid} was created."
                if tid
                else "Escalation is required, but ticket creation failed. Please contact support through the official channel."
            )
            pre.append(
                "Do not share passwords, one-time codes, or full card numbers in chat. No refund or resolution time is promised."
            )
        if not selected and not pre:
            answer = FALLBACK
        else:
            answer = "\n\n".join(pre + lines)
        s["final_answer"] = answer
        s["evidence"] = cited
        return s

    def run(self, state):
        return self.compiled.invoke(state, config={"recursion_limit": 8})
