"""Speckit integration — attach structured decomposition to task workspace."""

from __future__ import annotations

import json
from typing import Any

from ._infra import get_db, tasks_dir, now_iso, cancel_alarms_by_filter
from .crud import get_task
from .scheduler import schedule_task_wakeup


def attach_speckit_plan(task_id: str, speckit: dict[str, Any]) -> dict[str, Any]:
    detail = get_task(task_id)
    if not detail:
        return {"ok": False, "reason": f"任务 {task_id} 不存在"}

    task = detail["task"]
    ws = tasks_dir() / task_id
    speckit_dir = ws / "speckit"
    speckit_dir.mkdir(parents=True, exist_ok=True)

    task_list = speckit.get("task_list") if isinstance(speckit.get("task_list"), dict) else {}
    task_nodes = task_list.get("tasks") if isinstance(task_list.get("tasks"), list) else []
    paths = speckit.get("paths") if isinstance(speckit.get("paths"), dict) else {}
    files = speckit.get("files") if isinstance(speckit.get("files"), dict) else {}
    manifest = {
        "schema": speckit.get("schema") or "digital_employee.speckit.v1",
        "task_id": task_id,
        "task_title": task.get("title"),
        "created_at": now_iso(),
        "decision": speckit.get("decision") or {},
        "paths": paths,
        "contract": speckit.get("contract") or {},
        "capability_gap": speckit.get("capability_gap") or {},
        "task_list": task_list,
    }

    (speckit_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    for filename in ("spec.md", "plan.md", "tasks.md", "tasks.json"):
        content = files.get(filename)
        if content is None:
            content = json.dumps({"tasks": task_nodes}, ensure_ascii=False, indent=2) if filename == "tasks.json" else ""
        (speckit_dir / filename).write_text(str(content), encoding="utf-8")

    notes_file = ws / "NOTES.md"
    existing_notes = notes_file.read_text(encoding="utf-8") if notes_file.exists() else f"# {task.get('title')}\n\n"
    if "## SpecKit 拆解" not in existing_notes:
        workspace_note = str(speckit.get("workspace_note") or "").strip()
        if not workspace_note:
            workspace_note = (
                "## SpecKit 拆解\n"
                "- 先阅读 `speckit/spec.md` 明确目标和验收标准。\n"
                "- 再按 `speckit/plan.md` 和 `speckit/tasks.md` 执行。\n"
                "- 完成后写入 task_note，并通过 express_to_human 回复结果。"
            )
        notes_file.write_text(
            existing_notes.rstrip()
            + "\n\n"
            + workspace_note.rstrip()
            + "\n",
            encoding="utf-8",
        )

    inserted = _sync_speckit_todo_plans(task_id, task_nodes)
    cancel_alarms_by_filter(kind="task_reminder", payload_filter={"task_id": task_id})
    schedule_task_wakeup(task_id, title=task.get("title"), status=task.get("status") or "planned", force=True)
    return {
        "ok": True,
        "speckit": {
            "artifact_dir": str(speckit_dir),
            "spec_path": str(speckit_dir / "spec.md"),
            "plan_path": str(speckit_dir / "plan.md"),
            "tasks_path": str(speckit_dir / "tasks.md"),
            "tasks_json_path": str(speckit_dir / "tasks.json"),
            "task_node_count": len(task_nodes),
            "task_plan_count": inserted,
        },
    }


def _sync_speckit_todo_plans(task_id: str, task_nodes: list[dict[str, Any]]) -> int:
    if not task_nodes:
        return 0
    now = now_iso()
    inserted = 0
    db = get_db()
    try:
        existing = {
            str(row["content"])
            for row in db.execute("SELECT content FROM todo_plans WHERE task_id=?", (task_id,)).fetchall()
        }
        for index, node in enumerate(task_nodes, start=1):
            node_id = str(node.get("id") or f"S{index:03d}")
            title = str(node.get("title") or node_id)
            capability = str(node.get("required_capability") or "speckit")
            output = str(node.get("output") or "").strip()
            content = f"[SpecKit:{node_id}] {title} · {capability}"
            if output:
                content += f" -> {output}"
            if content in existing:
                continue
            db.execute(
                "INSERT INTO todo_plans (task_id, content, deadline, status, order_num, created_at) "
                "VALUES (?, ?, ?, 'pending', ?, ?)",
                (task_id, content, None, index, now),
            )
            inserted += 1
        db.commit()
    finally:
        db.close()
    return inserted
