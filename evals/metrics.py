from deepeval.metrics import BaseMetric


class StructuralMetric(BaseMetric):
    """Deterministic contract/trajectory metric; NOT a semantic LLM judge score."""

    threshold = 1.0
    async_mode = False

    def measure(self, test_case, *args, **kwargs):
        checks = test_case.additional_metadata["checks"]
        self.score = sum(bool(x) for x in checks.values()) / max(len(checks), 1)
        self.success = all(checks.values())
        self.reason = "; ".join(f"{k}={v}" for k, v in checks.items())
        self.error = None
        return self.score

    async def a_measure(self, test_case, *args, **kwargs):
        return self.measure(test_case, *args, **kwargs)

    def is_successful(self):
        return self.success

    @property
    def __name__(self):
        return "SupportFlow structural contracts"
