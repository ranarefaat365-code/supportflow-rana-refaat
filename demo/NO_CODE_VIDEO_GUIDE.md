# SupportFlow video: what to show and what to say (8–9 minutes)

Keep the backend and frontend running. Record the browser and your voice. Open `architecture/SUPPORTFLOW_ARCHITECTURE.svg` in a browser tab and the local UI in another. Hide your token, `.env`, terminal history, and any credentials. Do not claim Lovable hosting, a remote Langfuse dashboard, PostgreSQL deployment, or LLM-judge scores unless you have actually completed and verified them.

**0:00–0:50 — 1. Architecture diagram**  
**Show:** Open the SVG, zoom to fit. Point to the frontend, API, graph, five nodes, data and evaluation.  
**Say:** “Hi, I’m Rana Refaat. This is SupportFlow, a customer support application for a fictional product called CloudBox. The frontend sends requests to FastAPI. Authentication and account isolation are enforced on the backend. LangGraph routes each request through specialized knowledge, troubleshooting, account tools, escalation, and critic nodes. Qdrant stores searchable documentation; the local profile stores account and conversation data in SQLite. The diagram also shows where evaluation and tracing fit in.”

**0:50–1:25 — 2. Interface and authentication**  
**Show:** Your signed-in UI, menu and your name in the header. Never show the token entry or terminal output.  
**Say:** “This is the customer-facing interface. From here I can manage conversations, inspect the knowledge base, view sources and tool activity, and see monitoring summaries. The frontend displays results; account access and decisions happen on the server.”

**1:25–2:20 — 3. Grounded answer**  
**Show:** New conversation. Ask `Compare Standard and Team plans, storage, users and priority support.` Expand citations and tool logs.  
**Say:** “Here the knowledge workflow retrieves a bounded number of relevant passages. The answer shows readable citations with document titles and versions, so I can check where a claim came from. The local demo uses extractive evidence selection; I’m not claiming that a language model generated this answer. Notice that the tool log exposes the retrieval step.”

**2:20–3:05 — 4. Troubleshooting and thread history**  
**Show:** New chat. Ask `My files are duplicated after I worked offline. What should I do?` Then ask a short follow-up in the same thread and show the conversation list.  
**Say:** “This request routes to troubleshooting. The response follows an ordered workflow grounded in the support documentation. It preserves safety warnings around conflict copies. I can continue in the same thread, and the conversation remains available from the sidebar.”

**3:05–3:50 — 5. Account tool**  
**Show:** Ask `Please check order ord_7001 and tell me the amount.` Expand its tool event.  
**Say:** “This request uses an account-scoped tool. The server derives the user from the authenticated session, checks order ownership, and returns the result through the tool event. The response does not guess private account data from documentation.”

**3:50–4:35 — 6. Escalation**  
**Show:** Ask `I think someone accessed my account. What do I do?` Show escalation indicator and ticket ID.  
**Say:** “A possible account compromise takes the escalation route. The system creates a structured ticket and returns its identifier. It avoids asking for a password, a verification code, or payment details, and it does not promise an unverified resolution time.”

**4:35–5:20 — 7. Cross-account isolation**  
**Show:** Ask `Please check order ord_7003 for acc_1003.` Show the refusal and tool event; do not expose another account’s details.  
**Say:** “This is an intentional cross-account access attempt. The backend checks session scope and rejects the lookup. The user cannot expand their permissions by typing a different account ID in the chat.”

**5:20–6:00 — 8. Live status tool**  
**Show:** Ask `Is CloudBox currently experiencing an outage?` Expand status tool event.  
**Say:** “A current outage cannot be established from an old help article. The workflow invokes the service-status tool. In this local profile, an external status provider is not configured, so the response states that current availability cannot be verified.”

**6:00–6:45 — 9. Documents, monitoring and API**  
**Show:** Open Knowledge base, Monitoring, then `http://127.0.0.1:8000/docs` and scroll endpoint names only.  
**Say:** “The knowledge view lists the indexed sources. Monitoring provides local activity and trace identifiers. FastAPI exposes typed endpoints for chat, threads, documents, feedback, evaluations and tickets. Remote Langfuse tracing would require project credentials; these local metrics are not a Langfuse dashboard.”

**6:45–8:05 — 10. Evaluation evidence and limits**  
**Show:** Open `docs/VALIDATION.md`, then `artifacts/eval_results.json` and `artifacts/deepeval_results.json` without showing code. Scroll through a sample trajectory.  
**Say:** “The saved local evaluation ran twenty supplied goldens plus twelve custom edge cases against the compiled graph. The structural checks passed on thirty-two cases and saved outputs and trajectories. These checks cover routing, sources and safety contracts. They do not substitute for a completed semantic LLM-judge evaluation. The documentation also records what still needs verification: hosted Lovable integration, remote Langfuse evidence, the PostgreSQL deployment profile and a production identity provider.”

**8:05–8:45 — Reproducibility and close**  
**Show:** The GitHub repository page after you have uploaded it, open README and the SVG diagram. If not uploaded yet, show the local README instead.  
**Say:** “The repository includes the backend, frontend source and prebuilt local UI, knowledge corpus, test fixtures, saved evaluation evidence, architecture diagram and Windows startup guide. This demo shows the local end-to-end workflow and its current limits. Thank you for watching.”

If any query behaves differently during the recording, describe the actual result on screen rather than reading an expected outcome. Pause during loading and edit out idle time only if your submission rules allow it.
