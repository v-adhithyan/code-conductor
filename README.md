# CodeConductor

**Your AI agents. Your tools. One workflow.**

This is a local first, open-source toolkit for reusable engineering workflows. It starts with two actions from a real AI-assisted software development lifecycle: clarify an issue before work begins, and review a pull request. It works in a new repo with no code as well as in an existing checkout.

## Quick start

Requirements: 

Python 3.11+, 
OpenAI API key
github cli with access to the repo you choose. 



```sh
git clone https://github.com/v-adhithyan/code-conductor
cd code-conductor
uv tool install --editable .
cd /path/to/your/repository
code-conductor init
cp .env.example .env
# Add OPENAI_API_KEY to .env
code-conductor doctor
```

The first workflow can run from an empty directory:

```sh
code-conductor triage-issue --title "Add a dark mode" --body "Let users switch the interface to a dark color scheme."
```

Or use the portable YAML workflow interface:

```sh
code-conductor workflow list
code-conductor workflow run issue-triage --input 'title=Add a dark mode' --input 'body=Let users switch the interface to a dark color scheme.'
```

Review a GitHub pull request. The report is displayed locally by default:

```sh
code-conductor review-pr 42 --repo . --output .codeconductor/runs/pr-42.md
```

Posting is a separate, explicit action and asks for confirmation:

```sh
code-conductor review-pr 42 --repo . --post-comment
```

## Workflows

Workflow definitions are readable YAML in `workflows/`. `code-conductor init` copies starter definitions into `.codeconductor/workflows/` in the target repository. The initial schema is intentionally small: workflow name, version, description, and ordered action steps. Unknown fields and duplicate step IDs are rejected.

### Issue requirements triage

Accepts issue text directly, so it can help bootstrap a brand-new project before its first files exist. It returns `clear` or `needs_clarification`, a short summary, and up to five implementation-relevant questions. Issue text is treated as untrusted data.

### Pull request review

Reads the PR diff with GitHub CLI, asks ChatGPT for concrete defects, and produces a Markdown report. Reports stay local unless `--post-comment` is passed and confirmed. Verify findings before acting on them.

## Configuration and privacy

Set `OPENAI_API_KEY` in the environment or in a local `.env` file. `.env` is ignored by Git. `CODECONDUCTOR_MODEL` optionally selects a ChatGPT API model; the default is `gpt-4o-mini`. Workflow inputs and repository diffs are sent to the OpenAI API when an action runs. PR access uses the locally authenticated `gh` CLI.

## Current scope

- Python CLI and a validated, portable YAML workflow format.
- Local execution, with no CodeConductor account or hosted service.
- One ChatGPT adapter and two built-in actions.
- Local output by default; explicit confirmation before posting a PR comment.

The MVP does not merge PRs, push branches, run arbitrary shell steps, or execute code from a repository.

## Sharing and contributing

Workflow files are designed to be copied, forked, and adapted alongside the repository that uses them. Contributions should include a focused action, an example workflow, and clear permission and data-handling notes. Share reports only after removing private repository details.

## Development

```sh
uv sync
uv run code-conductor --help
```

CodeConductor is released under the MIT License.
