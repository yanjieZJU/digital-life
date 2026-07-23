"""Path resolution — scope → directory mapping for registered tools/skills.

Pure functions, no IO side effects.
"""

from __future__ import annotations

from pathlib import Path

_VALID_SCOPES = {"personal", "project", "shared"}


def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).resolve().parents[2]


def validate_scope(scope: str) -> None:
    if scope not in _VALID_SCOPES:
        raise ValueError(f"scope must be one of {_VALID_SCOPES}, got '{scope}'")


def resolve_tool_path(
    scope: str,
    name: str,
    *,
    instance_id: str,
    project_id: str = "",
) -> Path:
    """Return the relative path (from project root) where a tool .py should live."""
    validate_scope(scope)
    if scope == "personal":
        return Path(f"apps/{instance_id}/tools/{name}.py")
    if scope == "project":
        if not project_id:
            raise ValueError("project scope requires project_id")
        return Path(f"projects/{project_id}/code/tools/{name}.py")
    # shared
    return Path(f"shared/tools/{name}.py")


def resolve_skill_path(
    scope: str,
    name: str,
    *,
    instance_id: str,
    project_id: str = "",
) -> Path:
    """Return the relative path where a skill SKILL.md should live."""
    validate_scope(scope)
    if scope == "personal":
        return Path(f"apps/{instance_id}/skills/{name}/SKILL.md")
    if scope == "project":
        if not project_id:
            raise ValueError("project scope requires project_id")
        return Path(f"projects/{project_id}/skills/{name}/SKILL.md")
    # shared
    return Path(f"shared/skills/{name}/SKILL.md")


def resolve_manifest_path(scope: str, kind: str, *, instance_id: str, project_id: str = "") -> Path:
    """Return the manifest.json path for a (scope, kind) combo.

    kind: "tools" or "skills".
    """
    validate_scope(scope)
    if scope == "personal":
        base = Path(f"apps/{instance_id}")
    elif scope == "project":
        base = Path(f"projects/{project_id}")
    else:
        base = Path("shared")
    manifest_name = f"{kind}_manifest.json"
    if kind == "tools":
        return base / "tools" / manifest_name
    return base / "skills" / manifest_name
