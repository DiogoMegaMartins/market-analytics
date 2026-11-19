from __future__ import annotations

import json
import logging
import threading
from collections import defaultdict
from collections.abc import Mapping
from time import perf_counter
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class MetricsRegistry:
    """Small process-local Prometheus registry for the modular-monolith MVP.

    Metrics are intentionally low-cardinality. For multi-worker or multi-replica
    deployments, use one worker per scrape target or replace this registry with
    a shared Prometheus/OpenTelemetry exporter.
    """

    BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self._histograms: dict[
            tuple[str, tuple[tuple[str, str], ...]], dict[str, object]
        ] = {}

    @staticmethod
    def _key(name: str, labels: Mapping[str, str] | None) -> tuple[str, tuple[tuple[str, str], ...]]:
        return name, tuple(sorted((str(k), str(v)) for k, v in (labels or {}).items()))

    def increment(self, name: str, labels: Mapping[str, str] | None = None, amount: float = 1) -> None:
        with self._lock:
            self._counters[self._key(name, labels)] += amount

    def observe(self, name: str, value: float, labels: Mapping[str, str] | None = None) -> None:
        observation = max(0.0, value)
        with self._lock:
            key = self._key(name, labels)
            state = self._histograms.setdefault(
                key, {"count": 0, "sum": 0.0, "buckets": [0] * len(self.BUCKETS)}
            )
            state["count"] = int(state["count"]) + 1
            state["sum"] = float(state["sum"]) + observation
            buckets = state["buckets"]
            for index, bound in enumerate(self.BUCKETS):
                if observation <= bound:
                    buckets[index] += 1

    @staticmethod
    def _labels(
        labels: tuple[tuple[str, str], ...],
        extra: tuple[str, str] | None = None,
    ) -> str:
        values = list(labels)
        if extra:
            values.append(extra)
        if not values:
            return ""

        def escape(value: str) -> str:
            return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')

        return "{" + ",".join(f'{key}="{escape(value)}"' for key, value in values) + "}"

    def render(self, *, pool: Mapping[str, float] | None = None) -> str:
        lines: list[str] = []
        with self._lock:
            counters = list(self._counters.items())
            histograms = [
                (key, {"count": value["count"], "sum": value["sum"], "buckets": value["buckets"][:]})
                for key, value in self._histograms.items()
            ]
        counter_names = sorted({name for (name, _labels), _value in counters})
        for name in counter_names:
            if name == "market_analytics_http_requests_total":
                lines.append("# HELP market_analytics_http_requests_total Total HTTP requests.")
            lines.append(f"# TYPE {name} counter")
        for (name, labels), value in sorted(counters):
            lines.append(f"{name}{self._labels(labels)} {value:g}")
        for (name, labels), state in sorted(histograms):
            lines.append(f"# TYPE {name} histogram")
            for bound, count in zip(self.BUCKETS, state["buckets"], strict=True):
                lines.append(f'{name}_bucket{self._labels(labels, ("le", str(bound)))} {count}')
            lines.append(f'{name}_bucket{self._labels(labels, ("le", "+Inf"))} {state["count"]}')
            lines.append(f"{name}_sum{self._labels(labels)} {state['sum']:.9f}")
            lines.append(f"{name}_count{self._labels(labels)} {state['count']}")
        for key, value in sorted((pool or {}).items()):
            lines.append(f'market_analytics_db_pool_{key} {value:g}')
        return "\n".join(lines) + "\n"


metrics = MetricsRegistry()
http_logger = logging.getLogger("market_analytics.http")


class RequestMetricsMiddleware:
    """ASGI middleware for low-cardinality metrics and request correlation."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        started = perf_counter()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            elapsed = perf_counter() - started
            route = scope.get("route")
            route_label = getattr(route, "path", "unmatched")
            labels = {"method": scope.get("method", "UNKNOWN"), "route": route_label, "status": str(status_code)}
            metrics.increment("market_analytics_http_requests_total", labels)
            metrics.observe("market_analytics_http_request_duration_seconds", elapsed, {
                "method": scope.get("method", "UNKNOWN"), "route": route_label,
            })
            # Log only route templates and metadata; never query strings, headers or bodies.
            http_logger.info(json.dumps({
                "event": "http_request",
                "request_id": request_id,
                "method": scope.get("method", "UNKNOWN"),
                "route": route_label,
                "status_code": status_code,
                "duration_seconds": round(elapsed, 6),
            }, separators=(",", ":")))


def database_pool_metrics() -> dict[str, float]:
    try:
        from app.platform.database.session import get_engine

        pool = get_engine().pool
    except (ImportError, ModuleNotFoundError):
        return {}
    snapshot: dict[str, float] = {}
    for key, getter in (
        ("size", "size"),
        ("checked_out", "checkedout"),
        ("overflow", "overflow"),
        ("checked_in", "checkedin"),
    ):
        method = getattr(pool, getter, None)
        if callable(method):
            try:
                snapshot[key] = float(method())
            except (NotImplementedError, TypeError):
                continue
    return snapshot
