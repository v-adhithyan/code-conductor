"""CodeConductor command line interface."""

import os
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from codeconductor import __version__
from codeconductor.actions import post_pr_comment, pr_review, render_review, triage
from codeconductor.engine import load_workflow, run_workflow
from codeconductor.provider import OpenAIProvider

app = typer.Typer(help="Run local-first AI engineering workflows.", no_args_is_help=True)
workflow_app = typer.Typer(help="List and run YAML workflows.", no_args_is_help=True)
app.add_typer(workflow_app, name="workflow")
console = Console()


def project_root() -> Path:
    return Path.cwd()


def workflows_dir() -> Path:
    source_workflows = Path(__file__).resolve().parents[2] / "workflows"
    if source_workflows.exists():
        return source_workflows
    return Path(__file__).resolve().parent / "workflows"


def invoke(workflow_name: str, values: dict[str, object], root: Path | None = None) -> dict:
    root = root or project_root()
    load_dotenv(root / ".env")
    local_workflow = root / ".codeconductor" / "workflows" / f"{workflow_name}.yaml"
    workflow = load_workflow(local_workflow if local_workflow.exists() else workflows_dir() / f"{workflow_name}.yaml")
    provider = OpenAIProvider()
    registry = {
        "codeconductor.triage": lambda args: triage(args, provider),
        "codeconductor.pr_review": lambda args: pr_review(args, provider),
    }
    # Values override the workflow's illustrative defaults.
    workflow.steps[0].with_.update(values)
    return run_workflow(workflow, registry)


@app.command()
def version() -> None:
    """Print the installed version."""
    console.print(f"CodeConductor {__version__}")


@app.command()
def init(path: Path = typer.Argument(Path("."), help="Repository to initialize")) -> None:
    """Add CodeConductor workflow examples to a repository, including an empty one."""
    path = path.expanduser().resolve()
    if not path.exists():
        path.mkdir(parents=True)
    codeconductor_dir = path / ".codeconductor"
    codeconductor_dir.mkdir(exist_ok=True)
    examples_dir = codeconductor_dir / "workflows"
    examples_dir.mkdir(exist_ok=True)
    for workflow in workflows_dir().glob("*.yaml"):
        destination = examples_dir / workflow.name
        if not destination.exists():
            destination.write_text(workflow.read_text(encoding="utf-8"), encoding="utf-8")
    env_example = path / ".env.example"
    if not env_example.exists():
        env_example.write_text("OPENAI_API_KEY=\n# Optional model override\nCODECONDUCTOR_MODEL=gpt-4o-mini\n", encoding="utf-8")
    console.print(f"Initialized CodeConductor in [bold]{path}[/bold]")
    console.print("Copy .env.example to .env and add your OpenAI API key.")


@app.command()
def doctor() -> None:
    """Check local requirements for CodeConductor workflows."""
    load_dotenv(project_root() / ".env")
    console.print(f"Python: {os.sys.version.split()[0]}")
    console.print(f"OpenAI API key: {'configured' if os.getenv('OPENAI_API_KEY') else 'missing'}")
    console.print(f"GitHub CLI: {'available' if os.system('command -v gh >/dev/null 2>&1') == 0 else 'missing'}")


@app.command()
def triage_issue(
    title: str = typer.Option(..., prompt=True, help="Issue title"),
    body: str = typer.Option(..., prompt=True, help="Issue description"),
    output: Optional[Path] = typer.Option(None, help="Write Markdown to a file"),
) -> None:
    """Check whether an issue has enough detail to implement."""
    try:
        result = invoke("issue-triage", {"title": title, "body": body})["triage"]
    except Exception as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print(Panel.fit(result["summary"], title=result["status"].replace("_", " ")))
    if result["questions"]:
        for index, question in enumerate(result["questions"], 1):
            console.print(f"{index}. {question}")
    if output:
        output.write_text(f"# {result['status']}\n\n{result['summary']}\n" + "\n".join(f"- {q}" for q in result["questions"]), encoding="utf-8")
        console.print(f"Saved to {output}")


@app.command()
def review_pr(
    pr: str = typer.Argument(..., help="GitHub pull request number"),
    repo: Path = typer.Option(Path("."), help="Local checkout of the repository"),
    post_comment: bool = typer.Option(False, "--post-comment", help="Post the report to GitHub after confirmation"),
    output: Optional[Path] = typer.Option(None, help="Write Markdown report to a file"),
) -> None:
    """Review a GitHub pull request and show a local report."""
    repo = repo.expanduser().resolve()
    try:
        result = invoke("pr-review", {"pr": pr, "repo": str(repo)}, root=repo)["review"]
    except Exception as exc:
        raise typer.BadParameter(str(exc)) from exc
    report = render_review(result)
    console.print(report)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
        console.print(f"Saved report to {output}")
    if post_comment and typer.confirm(f"Post this review to {result['url']}?", default=False):
        post_pr_comment(repo, pr, report)
        console.print("Posted review comment.")


@workflow_app.command("list")
def workflow_list() -> None:
    """List built-in and repository-local workflows."""
    candidates = {path.name: path for path in workflows_dir().glob("*.yaml")}
    local = project_root() / ".codeconductor" / "workflows"
    if local.exists():
        candidates.update({path.name: path for path in local.glob("*.yaml")})
    for path in sorted(candidates.values(), key=lambda item: item.name):
        try:
            workflow = load_workflow(path)
            console.print(f"[bold]{workflow.name}[/bold]  {workflow.description}")
        except Exception as exc:
            console.print(f"[red]{path.name}: invalid workflow ({exc})[/red]")


@workflow_app.command("run")
def workflow_run(
    name: str = typer.Argument(..., help="Workflow name, such as issue-triage"),
    inputs: list[str] = typer.Option([], "--input", help="Set an action input as key=value; repeat as needed"),
    output: Optional[Path] = typer.Option(None, help="Write a Markdown report to a file"),
) -> None:
    """Run a YAML workflow with supplied action inputs."""
    values: dict[str, str] = {}
    for item in inputs:
        if "=" not in item:
            raise typer.BadParameter(f"Expected key=value for --input, got {item!r}")
        key, value = item.split("=", 1)
        values[key.strip()] = value
    root = project_root()
    custom_workflow = root / ".codeconductor" / "workflows" / f"{name}.yaml"
    packaged_workflow = workflows_dir() / f"{name}.yaml"
    path = custom_workflow if custom_workflow.exists() else packaged_workflow
    try:
        load_dotenv(root / ".env")
        workflow = load_workflow(path)
        if not workflow.steps:
            raise ValueError("Workflow has no steps")
        workflow.steps[0].with_.update(values)
        provider = OpenAIProvider()
        result = run_workflow(workflow, {
            "codeconductor.triage": lambda args: triage(args, provider),
            "codeconductor.pr_review": lambda args: pr_review(args, provider),
        })
    except Exception as exc:
        raise typer.BadParameter(str(exc)) from exc
    rendered = "\n".join(f"## {step}\n\n{data}" for step, data in result.items())
    console.print(rendered)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
        console.print(f"Saved report to {output}")


if __name__ == "__main__":
    app()
