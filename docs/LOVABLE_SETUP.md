# Complete the Lovable requirement

**Current status:** React/Vite frontend is implemented. No Lovable project has been created or published from this session. Source code is not proof of a Lovable-hosted deployment.

1. Put this project in a repository you control after reviewing `.gitignore`. Do not upload `.env`, `runtime/`, database files, model caches, or tokens.
2. Open your own Lovable account and use the available GitHub/import workflow for the frontend, or have Lovable reproduce the included React UI from `frontend/src/` using the prompt below. Account/import capabilities may differ; verify the current UI.
3. Deploy FastAPI to a Python/Docker host with PostgreSQL and Qdrant. A published HTTPS frontend cannot use the server on your computer at `localhost:8000`.
4. Set frontend `VITE_API_URL` to that backend's HTTPS origin. Never put provider keys, database URLs or JWT signing secrets in Vite variables: they are public browser values.
5. Add the exact frontend HTTPS origin to backend `CORS_ORIGINS` and restart the backend. Do not open CORS to every origin.
6. Use a valid session token for the test deployment, then integrate a real identity provider for production.
7. Verify the ten demo actions with actual backend calls. Capture the real frontend URL and its browser Network panel. No simulated responses count as integration evidence.

## Prompt to paste into Lovable

Build the SupportFlow frontend for the attached existing FastAPI backend. Use the included React/Vite frontend as the reference implementation and preserve the API contracts. Use a calm sage-green workspace with sidebar navigation, conversation list, source cards, expandable tool logs, escalation ticket badges, document ingestion and per-user monitoring. All business and agent logic must remain on FastAPI. Read VITE_API_URL for the backend URL. Keep bearer session tokens in memory only. Do not request CloudBox passwords or OTPs.

Implement POST /chat, POST /threads, GET /threads, GET /threads/{thread_id}, GET/POST /documents, POST /feedback and GET /monitoring. Display loading, empty, unauthorized, no-evidence, and service-error states. Render backend citations with title, version, trust level and excerpt; render errors without inventing a successful action. Do not create Supabase functions or client-side agents as replacements for this backend. Preserve response_id for feedback and thread_id for conversation continuity. The exact OpenAPI schema is in docs/openapi.json.

## Acceptance evidence to collect

- Screenshot of the actual Lovable project and published UI.
- Network request showing a successful `/chat` call to the configured backend.
- A source card, tool log, escalation ticket ID and denied cross-account lookup.
- Thread switching and a user switch showing no old-user messages.
- Keep tokens, keys and authorization headers hidden in screenshots and video.
