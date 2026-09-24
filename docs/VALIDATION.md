# Validation evidence and completion status

## Executed checks

- **24 API/security/reliability tests passed** using FastAPI TestClient, real SQLAlchemy storage, actual Qdrant local collections and the compiled graph. Exact JUnit output: `artifacts/pytest-results.xml`.
- **32/32 structural DeepEval cases passed**: 20 original goldens plus 12 custom edge cases. Exact outputs, checks and trajectories: `artifacts/eval_results.json` and `artifacts/deepeval_results.json`.
- Original `evals/goldens.json` was copied without changing the supplied expected answers or source IDs.
- Ruff static checks and formatting passed.
- React/Vite production build succeeded.
- Browser smoke test: authenticated session, live `/chat`, source cards, document list and monitoring rendered against the real local backend. Four actual screenshots are included in `artifacts/screenshots/`.
- Local restart test confirms thread history and Qdrant vectors persist.

These results are scoped to the local default profile: deterministic/extractive mode, lexical hash embeddings, SQLite relational database and Qdrant local persistence. They do not claim semantic-model accuracy or production isolation under every conceivable input.

## Twelve required scenarios

| Brief scenario | Evidence | Status |
|---|---|---|
| 1. Product answer, at least two citations | `test_product_two_citations`; browser answer screenshot | Local pass |
| 2. Sync issue via troubleshooting subagent | `test_sync_subagents`; golden `eval_003` | Local pass |
| 3. Current outage calls status tool | `test_status_uses_tool`; goldens `eval_006`, `eval_018` | Local pass; real status provider not configured |
| 4. Account takeover creates ticket | `test_takeover_ticket`; golden `eval_005` | Local pass |
| 5. Reject mismatched order/account | `test_cross_account_orders_and_claims`; edge cases 02/08 | Local pass |
| 6. Safe unknown answer | `test_unknown_one_question`; edge 01 | Local pass |
| 7. Tool timeout without graph/API crash | `test_timeout_does_not_crash`; edge 04 | Local fault-injection pass |
| 8. Continue same thread | `test_multiturn_thread_and_switch_users`; edge 05 | Local pass |
| 9. Switch users without data exposure | Owner-scope thread/order/feedback/ticket tests | Tested paths pass; not a universal security proof |
| 10. Complete DeepEval dataset and saved report | 32 executed cases with custom structural metric | Structural complete; semantic judge metrics pending |
| 11. Open real Langfuse trace with retrieval/tools/model | Local trace nesting test and export implementation | Remote Langfuse evidence pending |
| 12. Restart and retain documents/threads | `test_persistence_across_restart` | SQLite/Qdrant local pass; PostgreSQL deployment pending |

## Seven submission components

| Deliverable | Included | Remaining |
|---|---|---|
| Repository | Backend/frontend source, requirements, lockfile, tests, README, env template, schema, fixtures | Push to your repository after review |
| Lovable frontend | Tested React/Vite implementation | Import/build and deploy inside your Lovable account; verify hosted backend connection |
| RAG implementation | Ingestion, filters, source metadata, persistent Qdrant, official version precedence | Validate optional semantic provider; include your ingestion proof from deployment |
| Evaluation evidence | DeepEval code, original/custom cases, actual structural results and trajectories | Run semantic LLM judge; inspect real failures |
| Monitoring evidence | Actual local traces, UI monitoring screenshots, Langfuse exporter and debug explanation | Configure your project, verify remote trace, capture dashboard and model-usage evidence |
| Demo video | Detailed English script and verification checklist | Record the actual 7–10 minute walkthrough |
| Technical documentation | Architecture, security, API schema, setup and honest limitations | Update deployed URLs and actual provider/service validation results |

## Failure analysis

The first saved baseline passed 25/32 structural checks. Missing expected citations affected status, private-tool governance, duplicate billing, password recovery and offline-folder questions. A conflicting-version case also selected irrelevant version-history text containing the old retention number.

Changes addressed bounded evidence selection rather than hard-coding golden answers:

- Lowered lexical retrieval threshold to recover relevant small-corpus sources.
- Used the route-specific retrieval query when selecting excerpts.
- Weighted rare terms more than generic terms and preserved evidence diversity.
- Filtered weak extra paragraphs while keeping complete conditions and workflows.
- Retrieved internal account governance separately and labelled it internal; official product evidence remains explicitly identified.
- Applied latest-official-version precedence per document lineage.

Final structural results are 32/32. The expected answer-point strings are retained in reports for human review, but are not silently counted as semantically verified. Use the provided LLM-judge metrics for faithfulness, answer relevancy, contextual precision and contextual recall; their execution is pending.

## Thresholds

Structural contract metric: 1.0. Optional semantic metrics: faithfulness 0.90; answer relevancy, contextual precision and contextual recall 0.80. These are initial benchmarks, not empirically calibrated production thresholds. Account isolation and secret-handling tests are mandatory regardless of average scores.

## Environment limitation and telemetry handling

An optional ONNX-based embedding experiment triggered automatic approval rejection over possible external Microsoft telemetry. The optional embedding package and ONNX runtime were removed rather than bypassing the restriction. The final evaluator uses an outbound-socket-denied subprocess, and the final run completed locally. No semantic ONNX model success is claimed. API-based semantic embedding code is supplied as an explicit credentialed option, not executed here.

No secrets, local databases, runtime vector artifacts, provider keys, or browser session tokens are included in the deliverable. Synthetic test strings in the evaluation dataset are deliberately fictional safety probes.
