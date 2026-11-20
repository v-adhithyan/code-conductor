"""Small sequential workflow runner."""

from pathlib import Path
from typing import Any, Callable

import yaml

from codeconductor.models import Workflow

Action = Callable[[dict[str, Any]], dict[str, Any]]


def load_workflow(path: Path) -> Workflow:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    workflow = Workflow.model_validate(raw)
    workflow.validate_step_ids()
    return workflow


def run_workflow(workflow: Workflow, actions: dict[str, Action]) -> dict[str, Any]:
    outputs: dict[str, Any] = {}
    for step in workflow.steps:
        if step.uses not in actions:
            raise ValueError(f"Unknown action `{step.uses}` in step `{step.id}`")
        outputs[step.id] = actions[step.uses](step.with_)
    return outputs
