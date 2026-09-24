# SupportFlow demo — 7–10 minutes

**Recording target:** about 8½ minutes, including live actions. Read naturally, leave time for responses, and use your own wording. This script is a recording aid, not a claim that a video was recorded here. Hide keys, session tokens and authorization headers. Use fictional customer records only.

**Before recording:** complete the Lovable and Langfuse setup, execute the model-enabled path if you plan to demonstrate a generation span, run evaluations, and verify PostgreSQL/Qdrant persistence. If a gate is incomplete, disclose it rather than reading a completed claim.

## 0:00–0:45 — Problem and architecture

On screen: frontend and architecture diagram.

“Hi, I’m Rana. This is SupportFlow, a customer support application for a fictional storage platform called CloudBox.

The objective is to give customers useful answers while preserving three boundaries: every product claim needs evidence, private records stay within the authenticated account, and sensitive issues go through a controlled escalation process.

The frontend communicates with a FastAPI backend. The backend runs a compiled LangGraph workflow, retrieves documentation from Qdrant, and stores application records in a relational database. The local test profile uses SQLite; the Docker profile is configured for PostgreSQL.”

If you have verified the deployed PostgreSQL profile, replace the last sentence with your actual deployed configuration.

## 0:45–1:35 — Grounded answer and readable citations

Ask: `Compare Standard and Team plans, storage, users and priority support.`

“Let me start with a product question. The knowledge subagent retrieves a small set of relevant sources, rather than sending the entire knowledge base to a model.

The response includes the plan comparison and source cards. Here we can inspect the document title, version, trust level, and the actual excerpt. This makes the answer auditable.

The default response mode is extractive: it uses complete pieces of evidence. Optional model mode selects evidence through a bounded API request, and the critic rejects text that is not present in the retrieved material.”

Open both citations and the tool log. Do not claim this request used a model if extractive mode is active.

## 1:35–2:20 — Troubleshooting and multi-agent flow

New chat. Ask: `My files are duplicated after I worked offline. What should I do?`

“This request takes the troubleshooting route. The orchestrator identifies the issue type, the knowledge subagent retrieves the relevant procedure, and the troubleshooting subagent selects the applicable workflow.

The response preserves the warning about comparing conflict copies before deleting anything. The critic then checks the evidence and citations before returning the final answer.

The agents here are specialized LangGraph nodes with distinct responsibilities. Authorization remains deterministic; it is never delegated to a language model.”

Show the returned trajectory or local trace.

## 2:20–3:10 — Controlled account access

As `user_1`, ask: `Please check order ord_7001 and tell me the amount.`

“Now I’m using an authenticated fictional account. The account-tools subagent can read this order because it belongs to the current account and verification has already been established by the server.

The amount comes from the order tool, not from a document or model guess. The tool activity shows whether the operation succeeded.

The important design choice is that the account identity comes from the validated session and a server-side user record. A customer cannot change their scope by writing a different account ID in a message.”

## 3:10–3:50 — Safe escalation

Ask: `I think someone accessed my account. What do I do?`

“This is a suspected security incident, so the escalation subagent creates a structured ticket. We receive a ticket ID that is stored in the database.

The workflow does not ask for a password or one-time code, and it does not promise a resolution time. If ticket creation fails, the response reports the failure instead of inventing a successful escalation.”

Open the ticket tool event, hiding unnecessary fictional personal details.

## 3:50–4:35 — Cross-account denial and user isolation

Ask: `Please check order ord_7003 for acc_1003.`

“This order belongs to a different account. The tool refuses the operation before exposing the record.

The same boundary applies to thread history, feedback, and tickets. In the test suite, switching users cannot reveal a previous user’s messages. The frontend also clears the old session state when the user signs out.”

Show the structured `SCOPE_DENIED` result. Optionally sign in as another fixture user with the token hidden and show their separate conversation list.

## 4:35–5:30 — Current status and a real Langfuse trace

Ask: `Is CloudBox currently experiencing an outage?`

“For a current outage question, the system must call the service-status tool. Historical incident documents cannot establish current availability. If a live provider is not configured, the answer explicitly says the current status is unknown.”

If Langfuse has been configured and verified, open the actual trace:

“This trace corresponds to one request, and the thread ID groups related requests into a session. We can follow the orchestrator, retrieval, embedding operation, tool call, and final response. This lets us locate whether a failure came from routing, evidence retrieval, or an external tool.”

If model mode was enabled, show its generation span and actual token counts. If it was not enabled, say: “This request used extractive mode, so it has no generation call.”

If Langfuse remains unavailable, show the local trace and explicitly say that the required remote monitoring evidence is still incomplete. This is honest but does not satisfy that submission gate.

## 5:30–6:35 — DeepEval and one real failure

Show the original dataset and `artifacts/eval_results.json`. Show `artifacts/baseline/eval_results.json` as the historical failure, then the final report.

“The evaluation runner invokes the same compiled graph as the API. It includes the twenty supplied golden cases and twelve additional edge cases.

The saved reports contain the answer, citations, route, tool events and trajectory. The custom DeepEval metric checks structural contracts such as route selection, escalation, expected sources and execution bounds.

Here is a real baseline failure: the current-status route called the correct tool, but the expected policy citation was missing. I used the retrieval and response spans to locate the problem. After changing excerpt selection and relevance weighting, the same case passes its structural checks.

These results do not claim that a semantic LLM judge has verified every answer. Faithfulness, relevance and retrieval-quality judge metrics are separate, explicitly configured runs.”

Run the offline suite on screen if time allows. If you completed a judge run, show its actual report and discuss its real results instead of assuming a pass.

## 6:35–7:20 — FastAPI docs and persistence

Open `/docs`, authenticate without showing the token, and execute `POST /chat` with a harmless product question.

“The API exposes typed request and response schemas. Every chat response returns the answer, citations, tool events, escalation state and thread ID, along with request and trace identifiers.

The backend also provides thread management, document ingestion, feedback, protected evaluation execution and ticket creation. Invalid input and tool failures return structured errors.”

If you have verified a service restart, show the same thread after the restart and say exactly which storage profile was tested.

## 7:20–8:30 — Repository and reproducible setup

Show the folder structure and README.

“The repository separates API handling, orchestration, retrieval, tools, persistence and monitoring. The README provides setup instructions, environment variables, fixture identities and verification commands.

Secrets and database files are excluded. The source corpus and evaluation fixtures contain fictional data only.

The current implementation demonstrates the end-to-end workflow and its tested security boundaries. Before production, I would replace the development identity flow, calibrate semantic retrieval, expand adversarial and multilingual evaluation, and verify deployment, monitoring delivery and operational controls.”

Finish by showing the actual repository and frontend URLs only after you have created them.
