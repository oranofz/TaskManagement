"""Observability module for distributed tracing and metrics."""
from app.shared.observability.tracing import setup_tracing, get_tracer

__all__ = ["setup_tracing", "get_tracer"]

