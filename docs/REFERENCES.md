# Primary implementation references

The assignment assets remain the requirements source of truth. These official references were checked while implementing the selected APIs:

- LangGraph graph/state/conditional edges: https://docs.langchain.com/oss/python/langgraph/graph-api
- Qdrant payload filtering: https://qdrant.tech/documentation/search/filtering/
- Qdrant query points: https://api.qdrant.tech/api-reference/search/query-points
- DeepEval custom metrics: https://deepeval.com/docs/metrics-custom
- DeepEval end-to-end evaluation: https://deepeval.com/docs/evaluation-end-to-end-single-turn
- Langfuse instrumentation: https://langfuse.com/docs/observability/sdk/instrumentation
- Langfuse Python API: https://python.reference.langfuse.com/langfuse

Pinned Python dependencies are in `requirements.txt`; frontend dependencies and resolutions are in `frontend/package.json` and `frontend/package-lock.json`. Runtime testing is reported separately from documentation review.
