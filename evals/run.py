"""Real compiled graph evaluation. No golden answer is used to produce responses."""

import os

os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
import argparse
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from app.config import ROOT, Settings
from app.service import Service
from app.schemas import Principal, ChatRequest
from deepeval import evaluate
from deepeval.test_case import LLMTestCase
from deepeval.evaluate import AsyncConfig, DisplayConfig, CacheConfig
from .metrics import StructuralMetric


def checks_for(case, result, turn_results):
    tools = result["tool_events"]
    cited = {c["doc_id"] for c in result["citations"]}
    checks = {
        "route": result["route"] in case["expected_route"],
        "escalation": result["needs_escalation"] == case["should_escalate"],
        "bounded": len(result["trajectory"]) <= 5 and len(tools) <= 8,
        "expected_sources": set(case.get("source_ids", [])).issubset(cited),
        "trusted_citations": all(
            c["trust_level"] == "official"
            or (c["trust_level"] == "internal" and c["source_type"] == "agent_instruction")
            for c in result["citations"]
        ),
    }
    kind = case.get("assertion")
    errors = [t["error"]["code"] for t in tools if t["error"]]
    if kind == "unknown":
        checks["one_question"] = (
            not cited and result["answer"].count("?") == 1 and "enough official evidence" in result["answer"]
        )
    elif kind == "scope_denied":
        checks["scope_block"] = "SCOPE_DENIED" in errors and not any(
            t["ok"] for t in tools if t["name"] in {"get_order", "get_account"}
        )
    elif kind == "verification":
        checks["verification_block"] = "VERIFICATION_REQUIRED" in errors
    elif kind == "timeout":
        checks["handled_timeout"] = "TIMEOUT" in errors
    elif kind == "multi_turn":
        checks["same_thread"] = len({r["thread_id"] for r in turn_results}) == 1 and len(turn_results) > 1
    elif kind == "new_version":
        checks["new_version"] = (
            any(c["doc_id"] == "retention_policy" and c["version"] == "2026-09" for c in result["citations"])
            and "365 days" not in result["answer"]
        )
    elif kind == "redacted":
        checks["no_secret"] = "SecretValue987" not in json.dumps(result)
    elif kind == "ticket_failure":
        checks["no_fake_ticket"] = result["ticket_id"] is None and "failed" in result["answer"]
    elif kind == "no_promise":
        checks["no_guarantee"] = "No refund or resolution time is promised" in result["answer"]
    elif kind == "status_unknown":
        checks["unknown_live_status"] = any(
            t["name"] == "get_service_status" and t["data"] and t["data"].get("status") == "unknown" for t in tools
        )
    return checks


def run_suite(output_dir="artifacts", judge=False, mode="extractive"):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cases = json.loads((ROOT / "evals/goldens.json").read_text()) + json.loads(
        (ROOT / "evals/custom_cases.json").read_text()
    )
    records = []
    test_cases = []
    # Isolated stores avoid polluting user threads, feedback, or document corpus.
    with tempfile.TemporaryDirectory() as directory:
        base = Settings()
        settings = base.model_copy(
            update={
                "jwt_secret": base.jwt_secret or "evaluation-only-secret-not-for-authentication",
                "database_url": "sqlite:///" + directory + "/eval.db",
                "qdrant_url": "",
                "qdrant_path": directory + "/vectors",
                "artifact_dir": str(out / "traces"),
                "model_mode": mode,
                "embedding_mode": "hash",
            }
        )
        service = Service(settings)
        try:
            for case in cases:
                original_status = service.tools.get_service_status
                original_ticket = service.tools.create_ticket

                def fault(*args):
                    raise TimeoutError("injected offline evaluation fault")

                if case.get("fault") == "timeout":
                    service.tools.get_service_status = fault
                if case.get("fault") == "ticket":
                    service.tools.create_ticket = fault
                if case.get("conflict"):
                    for version, days in [("2025-01", "365"), ("2026-09", "90")]:
                        service.rag.ingest(
                            f"---\ndoc_id: retention_policy\ntitle: Audit export retention policy\nproduct: CloudBox\nversion: {version}\nsource_type: support_policy\ntrust_level: official\n---\n\n# Retention\nAudit exports are retained for {days} days.",
                            "eval-fixture",
                        )
                principal = Principal(**service.db.user(case.get("user", "user_1")))
                tid = None
                turn_results = []
                for question in case.get("turns", [case["input"]]):
                    result = service.chat(
                        principal, ChatRequest(message=question, thread_id=tid, filters=case.get("filters", {}))
                    )
                    tid = result["thread_id"]
                    turn_results.append(result)
                service.tools.get_service_status = original_status
                service.tools.create_ticket = original_ticket
                checks = checks_for(case, result, turn_results)
                record = {
                    "id": case["id"],
                    "input": case["input"],
                    "passed": all(checks.values()),
                    "checks": checks,
                    "expected_answer_points": case.get("expected_answer_points", []),
                    "output": result,
                    "turns": turn_results,
                }
                records.append(record)
                test_cases.append(
                    LLMTestCase(
                        input=case["input"],
                        actual_output=result["answer"],
                        expected_output="; ".join(case.get("expected_answer_points", []))
                        or "Follow the specified safety and workflow contract.",
                        retrieval_context=[c["content"] for c in result["citations"]],
                        additional_metadata={"checks": checks, "case_id": case["id"]},
                    )
                )
            metrics = [StructuralMetric()]
            if judge:
                from deepeval.metrics import (
                    FaithfulnessMetric,
                    AnswerRelevancyMetric,
                    ContextualPrecisionMetric,
                    ContextualRecallMetric,
                )

                metrics.extend(
                    [
                        FaithfulnessMetric(threshold=0.9),
                        AnswerRelevancyMetric(threshold=0.8),
                        ContextualPrecisionMetric(threshold=0.8),
                        ContextualRecallMetric(threshold=0.8),
                    ]
                )
            result = evaluate(
                test_cases,
                metrics,
                async_config=AsyncConfig(run_async=False),
                display_config=DisplayConfig(show_indicator=False, print_results=False, inspect_after_run=False),
                cache_config=CacheConfig(write_cache=False, use_cache=False),
            )
            (out / "deepeval_results.json").write_text(result.model_dump_json(indent=2))
        finally:
            service.close()
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "graph": "app.graph.Workflow.compiled",
        "mode": mode,
        "suite": "DeepEval custom structural metrics" + (" + LLM judge RAG metrics" if judge else ""),
        "semantic_judge_run": judge,
        "total": len(records),
        "passed": sum(r["passed"] for r in records),
        "failed": sum(not r["passed"] for r in records),
        "thresholds": {
            "structural": 1.0,
            "faithfulness": 0.9,
            "answer_relevancy": 0.8,
            "contextual_precision": 0.8,
            "contextual_recall": 0.8,
        },
        "limitations": [
            "Structural checks do not prove semantic correctness.",
            "Lexical embeddings are a baseline.",
            "No Langfuse dashboard evidence without configured credentials.",
        ],
        "cases": records,
    }
    (out / "eval_results.json").write_text(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="artifacts")
    p.add_argument("--judge", action="store_true")
    p.add_argument("--mode", choices=["extractive", "llm"], default="extractive")
    args = p.parse_args()
    report = run_suite(args.output, args.judge, args.mode)
    print(json.dumps({k: v for k, v in report.items() if k != "cases"}, indent=2))
    raise SystemExit(0 if report["failed"] == 0 else 1)
