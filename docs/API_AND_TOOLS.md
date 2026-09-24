# API and tool reference

All protected endpoints require `Authorization: Bearer <session token>`. `/health`, `/docs` and `/openapi.json` are public and do not reveal secrets. `docs/openapi.json` is an exported schema from the implemented app.

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| GET | `/health` | Public | Relational/vector dependency status and monitoring configuration state |
| POST | `/chat` | User | Execute real graph with owner-scoped conversation |
| POST | `/threads` | User | Create an owned thread |
| GET | `/threads/{thread_id}` | Owner | Return messages and structured previous responses |
| POST | `/documents` | Admin | Validate and index Markdown with metadata |
| GET | `/documents` | User | List shared corpus metadata |
| POST | `/feedback` | Response owner | Store helpfulness and optionally attach Langfuse score |
| POST | `/evals/run` | Admin + `ENABLE_EVALS=true` | Run isolated outbound-blocked structural suite |
| POST | `/tickets` | Thread owner | Create ticket through typed tool layer |
| GET | `/threads` | User | List only owned threads for frontend switching |
| GET | `/monitoring` | User | Recent metrics for the authenticated user |

Chat payload is stable: `answer`, `citations`, `tool_events`, `needs_escalation`, `ticket_id`, `thread_id`, `response_id`, `route`, `trace_id`, `request_id`, `latency_ms`, `trajectory`. Deterministic shape does not mean random IDs or timings repeat identically.

| Tool | Typed arguments | Successful output | Guard |
|---|---|---|---|
| `search_knowledge_base` | query, filters, limit | Citation/chunk records | Result and search bounds; exact metadata filters |
| `get_account` | account_id | Fixture account record | Session account equality and verified user |
| `get_order` | account_id, order_id | Owned order record | Scope equality, verification and SQL ownership constraint |
| `get_service_status` | empty object | Current provider status or explicit unknown | Fixed server-side URL, timeout, no document-derived incident |
| `create_ticket` | thread_id, summary, category, request_id | Persisted ticket | Thread owner, server-bound account/workspace, sanitized summary |
| `get_thread_summary` | thread_id | Last three sanitized user messages | Current-user thread scope |

Tool envelope: `name`, `ok`, `data`, `error`, `latency_ms`. Error codes include `SCOPE_DENIED`, `VERIFICATION_REQUIRED`, `TIMEOUT`, and `TOOL_UNAVAILABLE`. Provider exception details are not exposed. The HTTP API returns structured 401/403/422/503 errors for authentication, authorization, validation or dependency failure.

Administrator document uploads preserve source metadata. They do not create a public file-serving endpoint; source cards show the complete retrieved source excerpt and repository path. This avoids inventing external URLs for the fictional CloudBox documents.
