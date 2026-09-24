# Monitoring and one trace walkthrough

## Included evidence

`artifacts/final/traces/` contains actual local traces from the final structural evaluation. These are local trace records, not Langfuse dashboard exports. The frontend monitoring screen reads owner-scoped request metrics from FastAPI.

## Connect Langfuse

Create a project in your Langfuse account. Put its public key, secret key and base URL into local `.env`. Restart FastAPI. Issue a request such as `Please check order ord_7001 and tell me the amount.` with the verified `user_1` session. Copy the returned trace ID and locate it in the Langfuse project.

Verify one root `supportflow.request` with the same thread ID as session ID. It should contain orchestrator, knowledge, retrieval, embedding, account-tools and critic spans. A status or order request must show its actual tool span. With `MODEL_MODE=llm`, the response path adds a generation span. With extractive mode there is **no generation call**, and the UI/video must not pretend there is one.

Generation spans record provider-returned input/output token counts. Cost is computed only when configured per-million rates are supplied. Unset rates are labelled unconfigured rather than silently asserted free. Local hash embeddings have zero external model cost. Semantic API embeddings use provider usage when available. Monitoring failures are caught and do not crash chat.

Export status in local JSON means “attempted, not confirmed”; only finding the trace in Langfuse establishes successful delivery. Save an actual dashboard screenshot and inspect token/latency fields after adding keys.

## Debugged trace: incomplete current-status answer

The baseline evaluation (`artifacts/baseline/eval_results.json`, case `eval_006`) routed to the status tool correctly but lacked the expected official status-policy citation. Follow its `output.trace_id` in the baseline trace files.

1. `agent.orchestrator`: correct `status_tool` route.
2. `tool.get_service_status`: returns `unknown` because no live provider is configured; this is expected and safe.
3. `retrieval.qdrant`: lexical retrieval and excerpt selection did not retain the expected evidence.
4. `agent.critic_response`: produced a status fallback, but the expected citation check failed.
5. Fix: use the bounded route-specific retrieval query during excerpt selection and rank meaningful query terms with document-frequency weighting, while preserving complete conditional paragraphs.
6. Final evaluation: the same original golden passes its structural expected-source check. This does not establish semantic-judge success or a real current CloudBox incident.

## Suggested alert thresholds — not configured alerts

Start with tool error rate above 10% over 20 requests, p95 latency above 15 seconds, any account-scope regression, or a sudden escalation-rate increase. These are suggested initial thresholds. No automatic alert delivery has been set up in a Langfuse account here; configure and test it before claiming that requirement complete.
