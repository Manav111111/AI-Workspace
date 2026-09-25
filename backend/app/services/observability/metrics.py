import threading
import time
from typing import Any, Dict, List


class OperationalMetricsCollector:
    """Thread-safe bounded-cardinality metrics accumulator for production operations.
    Avoids high-cardinality explosions by bounding dimensions (status, operation type).
    """

    def __init__(self, max_latency_samples: int = 1000):
        self._lock = threading.Lock()
        self._max_samples = max_latency_samples
        self._requests_total = 0
        self._requests_success = 0
        self._requests_error = 0
        self._budget_denials = 0
        self._rate_limit_denials = 0
        self._total_latencies: List[float] = []
        self._retrieval_latencies: List[float] = []
        self._llm_latencies: List[float] = []
        self._tool_latencies: List[float] = []

    def record_request(
        self,
        status: str,
        total_latency_ms: float,
        retrieval_latency_ms: float = 0.0,
        llm_latency_ms: float = 0.0,
        tool_latency_ms: float = 0.0,
    ) -> None:
        with self._lock:
            self._requests_total += 1
            if status.upper() == "SUCCESS":
                self._requests_success += 1
            else:
                self._requests_error += 1

            self._append_sample(self._total_latencies, total_latency_ms)
            if retrieval_latency_ms > 0:
                self._append_sample(self._retrieval_latencies, retrieval_latency_ms)
            if llm_latency_ms > 0:
                self._append_sample(self._llm_latencies, llm_latency_ms)
            if tool_latency_ms > 0:
                self._append_sample(self._tool_latencies, tool_latency_ms)

    def record_budget_denial(self) -> None:
        with self._lock:
            self._budget_denials += 1

    def record_rate_limit_denial(self) -> None:
        with self._lock:
            self._rate_limit_denials += 1

    def _append_sample(self, target_list: List[float], val: float) -> None:
        if len(target_list) >= self._max_samples:
            target_list.pop(0)
        target_list.append(round(val, 2))

    def _calc_stats(self, samples: List[float]) -> Dict[str, float]:
        if not samples:
            return {"avg": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0}
        s = sorted(samples)
        n = len(s)
        avg = round(sum(s) / n, 2)
        p50 = s[int(n * 0.5)]
        p95 = s[min(int(n * 0.95), n - 1)]
        p99 = s[min(int(n * 0.99), n - 1)]
        return {"avg": avg, "p50": p50, "p95": p95, "p99": p99}

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            error_rate = (
                round((self._requests_error / self._requests_total) * 100, 2)
                if self._requests_total > 0
                else 0.0
            )
            return {
                "requests_total": self._requests_total,
                "requests_success": self._requests_success,
                "requests_error": self._requests_error,
                "error_rate_percent": error_rate,
                "budget_denials_total": self._budget_denials,
                "rate_limit_denials_total": self._rate_limit_denials,
                "latencies_ms": {
                    "total": self._calc_stats(self._total_latencies),
                    "retrieval": self._calc_stats(self._retrieval_latencies),
                    "llm": self._calc_stats(self._llm_latencies),
                    "tools": self._calc_stats(self._tool_latencies),
                },
            }


# Global operational metrics instance
metrics_collector = OperationalMetricsCollector()
