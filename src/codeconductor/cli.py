"""CLI for installing CodeConductor workflow packs into GitHub repositories."""

import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from codeconductor import __version__

app = typer.Typer(
    help="Add reusable GitHub engineering workflows to a repository.", no_args_is_help=True
)
workflow_app = typer.Typer(help="Browse and install workflow packs.", no_args_is_help=True)
app.add_typer(workflow_app, name="workflow")
console = Console()


def packs_dir() -> Path:
    source_packs = Path(__file__).resolve().parents[2] / "packs"
    if source_packs.exists():
        return source_packs
    return Path(__file__).resolve().parent / "packs"


def read_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not manifest.get("name") or not manifest.get("description"):
        raise ValueError(f"Invalid workflow pack manifest: {path}")
    return manifest


def safe_destination(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe workflow pack path: {relative}")
    destination = root
    for part in relative.parts:
        destination = destination / part
        if destination.is_symlink():
            raise ValueError(f"Refusing to write through a symlink: {destination}")
    if destination.exists() and not destination.is_file():
        raise ValueError(f"Destination exists and is not a file: {destination}")
    return destination


def collect_pack_files(pack: Path) -> dict[Path, Path]:
    sources = [packs_dir() / "shared" / "files", pack / "files"]
    files: dict[Path, Path] = {}
    for source_root in sources:
        if not source_root.exists():
            continue
        for source in sorted(source_root.rglob("*")):
            if source.is_symlink():
                raise ValueError(f"Workflow packs cannot contain symlinks: {source}")
            if source.is_file():
                relative = source.relative_to(source_root)
                if relative in files and files[relative].read_bytes() != source.read_bytes():
                    raise ValueError(f"Workflow packs contain conflicting files: {relative}")
                files[relative] = source
    if not files:
        raise ValueError(f"Workflow pack contains no installable files: {pack}")
    return files


@app.command()
def version() -> None:
    """Print the installed version."""
    console.print(f"CodeConductor {__version__}")


@workflow_app.command("list")
def workflow_list() -> None:
    """List workflow packs available to install."""
    for pack in sorted(packs_dir().iterdir(), key=lambda item: item.name):
        manifest_path = pack / "pack.json"
        if not pack.is_dir() or not manifest_path.is_file():
            continue
        try:
            manifest = read_manifest(manifest_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            console.print(f"[red]{pack.name}: invalid pack ({exc})[/red]")
            continue
        console.print(f"[bold]{manifest['name']}[/bold]  {manifest['description']}")


@workflow_app.command("add")
def workflow_add(
    name: str = typer.Argument(..., help="Workflow pack to install"),
    repo: Path = typer.Option(Path("."), "--repo", help="Target repository directory"),
    force: bool = typer.Option(False, "--force", help="Replace conflicting installed files"),
) -> None:
    """Copy a workflow pack into a repository's .github directory."""
    pack = packs_dir() / name
    manifest_path = pack / "pack.json"
    if not manifest_path.is_file():
        available = sorted(
            item.name for item in packs_dir().iterdir() if item.is_dir() and (item / "pack.json").is_file()
        )
        raise typer.BadParameter(f"Unknown workflow pack `{name}`. Available packs: {', '.join(available)}")
    try:
        manifest = read_manifest(manifest_path)
        sources = collect_pack_files(pack)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    root = repo.expanduser().resolve()
    if not root.is_dir():
        raise typer.BadParameter(f"Target repository directory does not exist: {root}")

    plan: list[tuple[Path, Path, str]] = []
    conflicts: list[Path] = []
    unchanged: list[Path] = []
    for relative, source in sources.items():
        try:
            destination = safe_destination(root, relative)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        if destination.is_file():
            if destination.read_bytes() == source.read_bytes():
                unchanged.append(relative)
                continue
            if not force:
                conflicts.append(relative)
                continue
        plan.append((relative, source, "replace" if destination.exists() else "add"))

    if conflicts:
        items = "\n".join(f"  {path}" for path in conflicts)
        raise typer.BadParameter(
            "These files already exist with different contents; no files were changed:\n"
            f"{items}\nRerun with --force to replace them."
        )

    for relative, source, _ in plan:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())

    console.print(f"Installed [bold]{manifest.get('title', name)}[/bold] into {root}")
    for relative, _, action in plan:
        console.print(f"  {action}: {relative}")
    if unchanged:
        console.print(f"Already up to date: {len(unchanged)} file(s)")

    requirements = manifest.get("requirements", {})
    secrets = requirements.get("secrets", [])
    variables = requirements.get("variables", [])
    setup = manifest.get("setup", [])
    if secrets or variables or setup:
        console.print("\n[bold]Finish setup in the GitHub repository:[/bold]")
        for item in secrets:
            console.print(f"  Secret {item['name']}: {item['description']}")
        for item in variables:
            console.print(f"  Variable {item['name']}: {item['description']}")
        for step in setup:
            console.print(f"  {step}")
    console.print("Commit and push these files to enable the GitHub Actions workflows.")


if __name__ == "__main__":
    app()
