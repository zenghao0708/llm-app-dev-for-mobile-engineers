from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "workflow" / "weekly_report_inputs.json"


@dataclass(frozen=True)
class WorkflowStep:
    name: str
    status: str
    detail: str
    requires_confirmation: bool = False


def run_workflow(input_path: Path, approve: bool = False, output_path: Path | None = None) -> dict:
    """Run a fixed weekly-report workflow with an explicit confirmation gate."""

    payload = load_input(input_path)
    steps: list[WorkflowStep] = []

    # Keep collection and validation deterministic. The model/template step should
    # never receive malformed business data.
    normalized = collect_inputs(payload)
    steps.append(WorkflowStep("collect_inputs", "complete", "Loaded tasks, meetings, commits, risks, and next-week plan."))

    draft = build_draft(normalized)
    steps.append(WorkflowStep("build_draft", "complete", "Generated a structured weekly report draft."))

    validation = validate_workflow(normalized, draft)
    steps.append(WorkflowStep("validate_draft", "complete", "Checked required sections and high-risk reminders."))

    if validation["errors"]:
        return _result("failed", "validation_failed", normalized, draft, validation, steps)

    steps.append(
        WorkflowStep(
            "human_confirmation",
            "waiting" if not approve else "complete",
            "Publishing requires a human confirmation because it sends content outside the drafting flow.",
            requires_confirmation=True,
        )
    )
    if not approve:
        return _result("waiting_confirmation", "approval_required", normalized, draft, validation, steps)

    # Approval and output are deliberately separate. A confirmed workflow can still
    # run as a dry run when no real publishing target is provided.
    published_to = publish_report(draft, output_path)
    is_dry_run = output_path is None
    publish_status = "dry_run" if is_dry_run else "complete"
    publish_detail = "Dry-run completed without writing a file." if is_dry_run else f"Published report to {published_to}."
    steps.append(WorkflowStep("publish_report", publish_status, publish_detail))
    result_status = "dry_run" if is_dry_run else "complete"
    stop_reason = "dry_run" if is_dry_run else "published"
    result = _result(result_status, stop_reason, normalized, draft, validation, steps)
    result["published_to"] = published_to
    return result


def load_input(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"workflow input not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid workflow input JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("workflow input must be a JSON object")
    return payload


def collect_inputs(payload: dict) -> dict:
    """Normalize the workflow payload and reject malformed list items early."""

    user_id = _required_str(payload, "user_id")
    week = _required_str(payload, "week")
    normalized = {"user_id": user_id, "week": week}
    normalized["tasks"] = _required_object_list(payload, "tasks", ("title", "status", "platform", "impact"))
    normalized["meetings"] = _required_object_list(payload, "meetings", ("topic", "decision"))
    normalized["commits"] = _required_object_list(payload, "commits", ("repo", "summary"))
    normalized["risks"] = _required_string_list(payload, "risks")
    normalized["next_week"] = _required_string_list(payload, "next_week")
    return normalized


def build_draft(data: dict) -> str:
    done_tasks = [task for task in data["tasks"] if task.get("status") == "done"]
    in_progress = [task for task in data["tasks"] if task.get("status") != "done"]
    sections = [
        f"# 移动端 AI 周报（{data['week']}）",
        "",
        f"负责人：{data['user_id']}",
        "",
        "## 本周完成",
        *_task_lines(done_tasks),
        "",
        "## 进行中",
        *_task_lines(in_progress),
        "",
        "## 会议结论",
        *[f"- {item.get('topic', '会议')}：{item.get('decision', '无结论')}" for item in data["meetings"]],
        "",
        "## 代码变化",
        *[f"- {item.get('repo', 'repo')}：{item.get('summary', '无摘要')}" for item in data["commits"]],
        "",
        "## 风险与阻塞",
        *[f"- {risk}" for risk in data["risks"]],
        "",
        "## 下周计划",
        *[f"- {item}" for item in data["next_week"]],
    ]
    return "\n".join(sections).strip() + "\n"


def validate_workflow(data: dict, draft: str) -> dict:
    """Validate both rendered draft shape and the structured data behind it."""

    required_sections = ["## 本周完成", "## 进行中", "## 会议结论", "## 代码变化", "## 风险与阻塞", "## 下周计划"]
    missing = [section for section in required_sections if section not in draft]
    errors = list(missing)
    warnings = []
    for index, task in enumerate(data["tasks"]):
        for field in ("title", "status", "platform", "impact"):
            if not task[field].strip():
                errors.append(f"tasks[{index}].{field} must not be empty")
    if not any(risk.strip() for risk in data["risks"]):
        errors.append("risks must include at least one non-empty item")
    if "## 风险与阻塞" in draft and "无" in _section_text(draft, "## 风险与阻塞"):
        warnings.append("risk section is present but may not describe concrete blockers")
    return {"ok": not errors, "errors": errors, "warnings": warnings}


def validate_draft(draft: str) -> dict:
    """Validate draft shape when only the rendered text is available."""

    required_sections = ["## 本周完成", "## 进行中", "## 会议结论", "## 代码变化", "## 风险与阻塞", "## 下周计划"]
    missing = [section for section in required_sections if section not in draft]
    return {"ok": not missing, "errors": missing, "warnings": []}


def publish_report(draft: str, output_path: Path | None) -> str:
    if output_path is None:
        return "dry-run"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(draft, encoding="utf-8")
    return str(output_path)


def _task_lines(tasks: list[dict]) -> list[str]:
    if not tasks:
        return ["- 无"]
    return [
        f"- [{task.get('platform', 'Unknown')}] {task.get('title', '未命名任务')}：{task.get('impact', '无影响说明')}"
        for task in tasks
    ]


def _result(status: str, stop_reason: str, data: dict, draft: str, validation: dict, steps: list[WorkflowStep]) -> dict:
    return {
        "status": status,
        "stop_reason": stop_reason,
        "week": data["week"],
        "user_id": data["user_id"],
        "draft": draft,
        "validation": validation,
        "steps": [step.__dict__ for step in steps],
    }


def _required_str(payload: dict, field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"field {field!r} must be a non-empty string")
    return value.strip()


def _required_object_list(payload: dict, field: str, required_fields: tuple[str, ...]) -> list[dict]:
    value = payload.get(field)
    if not isinstance(value, list) or not value:
        raise ValueError(f"field {field!r} must be a non-empty list")
    normalized = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"{field}[{index}] must be an object")
        normalized_item = {}
        for required_field in required_fields:
            normalized_item[required_field] = _required_str(item, required_field)
        normalized.append(normalized_item)
    return normalized


def _required_string_list(payload: dict, field: str) -> list[str]:
    value = payload.get(field)
    if not isinstance(value, list) or not value:
        raise ValueError(f"field {field!r} must be a non-empty list")
    normalized = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field}[{index}] must be a non-empty string")
        normalized.append(item.strip())
    return normalized


def _section_text(draft: str, heading: str) -> str:
    lines = draft.splitlines()
    try:
        start = lines.index(heading) + 1
    except ValueError:
        return ""
    body = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        body.append(line)
    return "\n".join(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a fixed weekly-report workflow with a confirmation gate.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--approve", action="store_true", help="Approve the publish step.")
    parser.add_argument("--out", type=Path, help="Write the approved report to this path.")
    args = parser.parse_args()

    try:
        result = run_workflow(args.input, approve=args.approve, output_path=args.out)
    except (FileNotFoundError, ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
