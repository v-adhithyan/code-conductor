#!/usr/bin/env python3
"""Check PR authorization and opt-in label before exposing review context to Codex."""

import json
import os
import subprocess


def gh(*args: str) -> str:
    return subprocess.check_output(["gh", *args], text=True).strip()


def main() -> None:
    pr_number = str(int(os.environ["PR_NUMBER"]))
    repository = os.environ["GITHUB_REPOSITORY"]
    actor = os.environ["GITHUB_ACTOR"]
    allowed = {name.strip() for name in os.environ.get("AI_ALLOWED_USERS", "").split(",") if name.strip()}
    pr = json.loads(gh("api", f"repos/{repository}/pulls/{pr_number}"))
    labels = {label["name"] for label in pr.get("labels", [])}
    same_repository = (pr.get("head", {}).get("repo") or {}).get("full_name") == repository
    authorized = actor in allowed
    opted_in = "ai-address-review" in labels
    ready = authorized and opted_in and same_repository
    if not authorized:
        print("The triggering user is not in AI_ALLOWED_USERS.")
    elif not opted_in:
        print("Add the ai-address-review label to opt this PR into AI review follow-up.")
    elif not same_repository:
        print("AI review follow-up currently supports branches in this repository, not fork branches.")
    else:
        print("Pull request is authorized and opted in.")
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        print(f"ready={str(ready).lower()}", file=output)
        if ready:
            print(f"branch={pr['head']['ref']}", file=output)


if __name__ == "__main__":
    main()
