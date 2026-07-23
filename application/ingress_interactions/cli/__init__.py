"""CLI ingress interactions normalization."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import uuid4

from ..contracts import InteractionMessage


class CliIngress:
    """Convert local CLI invocations into InteractionMessage."""

    def normalize(
        self,
        argv: Sequence[str],
        *,
        cwd: str = "",
        message_id: str | None = None,
    ) -> InteractionMessage:
        return InteractionMessage(
            message_id=message_id or f"in_{uuid4().hex}",
            actor_id=cwd or "local",
            content=" ".join(argv).strip(),
            metadata={"external_channel": "cli", "argv": list(argv)},
        )


__all__ = ["CliIngress"]
