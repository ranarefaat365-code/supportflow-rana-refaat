# Security boundaries

1. The browser sends a bearer session token. The server validates algorithm, signature, issuer, audience and expiration.
2. The token subject resolves to a user record. Account ID, verified status and role come from that server-side record, not request JSON.
3. The server checks thread ownership before any graph execution. A claimed `user_id` mismatch is immediately rejected.
4. Requested `acc_*` identifiers cannot override scope. Every mismatched identifier in a message causes a denied account operation. Order lookups include `account_id == principal.account_id` in SQL.
5. Unverified sessions are refused private account/order data. Secure verification occurs outside the chat. There is no OTP-in-chat flow.
6. Ticket tools recheck thread ownership and bind user/account/workspace on the server.
7. Normal users cannot ingest official documents or start protected evaluations. Evaluation execution is disabled by default even for admins.
8. Conservative disclosure detection discards the entire secret-bearing message before memory, tools and trace creation. Validation errors do not echo submitted values. The UI never stores session tokens persistently.
9. Monitoring receives IDs, structural metadata, counts, timing and optional model usage. It does not receive raw user messages, account records, or full model inputs/outputs.
10. No refunds or destructive account actions are implemented. A billing escalation creates a ticket, never an authorization to pay or an exact resolution promise.

## Limits, stated plainly

Regex suppression is not comprehensive DLP: arbitrary unlabelled credentials and unusual encodings cannot all be reliably recognized. English rule-based routing does not establish universal resistance to arbitrary phrasing. No test suite can prove “zero exposure under any condition”; the provided suite demonstrates particular tested paths and owner-scoped query design.

The development token CLI can mint any fixture identity because it runs in the trusted server environment. It must not be exposed to users or uploaded with `.env`. Use a real identity provider and secure verification state in production.

The reference deployment needs rate limiting, request-body limits at the reverse proxy, secure transport, retention policy, backup/restore tests, secret scanning and dependency security maintenance before internet use. Qdrant metadata search is for the fictional shared knowledge corpus; private user data is stored in relational owner-scoped records, not globally searchable vectors.

Optional remote generation, embeddings and LLM-judge evaluation send selected fictional project text to the configured provider. Enable these modes only after choosing your provider and configuring your credentials locally.
