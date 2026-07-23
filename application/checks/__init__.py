"""Ingress checks layer: deterministic pre-model checks."""

from .checker import IngressChecker
from .contracts import CheckDecision

__all__ = ["CheckDecision", "IngressChecker"]
