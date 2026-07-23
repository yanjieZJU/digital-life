"""Infrastructure HTTP — server, API endpoints, and lifecycle inbound hooks."""

from __future__ import annotations

from .server import run_gateway

__all__ = ["run_gateway"]
