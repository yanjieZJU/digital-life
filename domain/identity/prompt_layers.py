"""Digital-life gateway prompt providers."""

from __future__ import annotations

import os
from typing import Any

from infrastructure.config import get_instance_app_config_path


def _digital_life_prompts_enabled() -> bool:
    raw = os.getenv("DIGITAL_LIFE_PROMPTS_ENABLED", "true").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _load_prompt_overrides() -> dict[str, str]:
    try:
        import yaml

        # 实例配置统一在 config/app.yaml；旧的 data/config.yaml 已废弃
        cfg_path = get_instance_app_config_path()
        if not cfg_path.exists():
            return {}
        with cfg_path.open(encoding="utf-8") as handle:
            cfg = yaml.safe_load(handle) or {}
        overrides = cfg.get("prompts_override", {})
        if isinstance(overrides, dict):
            return {
                str(key): str(value)
                for key, value in overrides.items()
                if value is not None
            }
    except Exception:
        pass
    return {}


def _prompt(name: str, default: str, overrides: dict[str, str]) -> str:
    return (overrides.get(name, default) or "").strip()


def gateway_system_prompt() -> str:
    """Only injects persona as an ephemeral extension.

    The L4 lifecycle prompt is already part of the permanent system prompt. Injecting it again here would
    duplicate the entire lifecycle block.
    """
    if not _digital_life_prompts_enabled():
        return ""
    from domain.memory.context.selectors import load_life_persona

    persona = load_life_persona().strip()
    if not persona:
        return ""
    return "## 数字员工人格\n\n" + persona


def gateway_wake_prompt(*, source: Any) -> str:
    if not _digital_life_prompts_enabled():
        return ""
    try:
        platform_value = getattr(getattr(source, "platform", None), "value", None)
        if platform_value == "local":
            return ""
    except Exception:
        pass

    from domain.lifecycle.event_registry import get_event_type

    overrides = _load_prompt_overrides()
    human_def = get_event_type("message")
    default_human_prompt = human_def.prompt_template if human_def else ""
    prompt = _prompt("message", default_human_prompt, overrides)
    if not prompt:
        return ""
    return "## Digital Life Wake Prompt: message\n\n" + prompt
