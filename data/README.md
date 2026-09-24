# Tool fixture data

These records support local demonstrations of account lookup, order lookup, ticket creation, and ticket status. They are fictional. The learners should expose them through controlled FastAPI tools or a small repository layer.

Required safeguards:

- Never expose records for another account.
- Require an account ID and verification state before returning private details.
- Use the escalation tool for security, privacy, payment disputes, and data loss.
- Return structured errors when an ID is not found.
