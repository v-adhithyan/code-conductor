"""Workflow format models and validation."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkflowStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    uses: str
    with_: dict[str, Any] = Field(default_factory=dict, alias="with")


class Workflow(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    version: int = Field(ge=1)
    description: str
    steps: list[WorkflowStep] = Field(min_length=1)

    def validate_step_ids(self) -> None:
        ids = [step.id for step in self.steps]
        if len(ids) != len(set(ids)):
            raise ValueError("Workflow step IDs must be unique")
