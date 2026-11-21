#!/usr/bin/env python3
"""Authorize issue implementation only after triage clears requirements."""

import json
import os
import subprocess


def gh(*args: str) -> str:
    return subprocess.check_output(["gh", *args], text=True).strip()


def main() -> None:
    issue_number = str(int(os.environ["ISSUE_NUMBER"]))
    trigger_actor = os.environ.get("AI_TRIGGER_ACTOR", "")
    allowed = {name.strip() for name in os.environ.get("AI_ALLOWED_USERS", "").split(",") if name.strip()}
    issue = json.loads(gh("issue", "view", issue_number, "--json", "author,labels,comments"))
    labels = {label["name"] for label in issue["labels"]}
    comments = [comment["body"] for comment in issue["comments"]]
    authorized = trigger_actor in allowed
    requirements_clear = any("<!-- ai-requirements-clear -->" in body for body in comments)
    ready = (
        authorized
        and "ai-ready-to-implement" in labels
        and "ai-awaiting-clarification" not in labels
        and requirements_clear
    )
    if not authorized:
        print("The triggering user is not in AI_ALLOWED_USERS.")
    elif not ready:
        print("Requirements are not cleared or the issue is no longer ready; skipping implementation.")
    else:
        print("Issue is authorized and requirements are clear.")
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        print(f"ready={str(ready).lower()}", file=output)


if __name__ == "__main__":
    main()
