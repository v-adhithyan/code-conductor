# CodeConductor

**Install proven engineering workflows in your GitHub repository.**

CodeConductor is a small CLI for adding reusable GitHub Actions workflows to existing or new repositories. GitHub Actions run the workflows; CodeConductor copies the selected files and shows the required setup.

The first packs are adapted from the issue and PR workflows in [Hackerleap](https://github.com/v-adhithyan/crack-interviews): issue requirements triage through a reviewable pull request, and authorized PR comment follow-up.

## Install the CLI

Requirements: Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/v-adhithyan/code-conductor.git
cd code-conductor
uv tool install --editable .
```

## Add workflows to a repository

```sh
cd /path/to/your/repository
code-conductor workflow list
code-conductor workflow add issue-to-pr
code-conductor workflow add pr-review
```

Use `--repo /path/to/repository` to target another existing directory. A new GitHub repository can start as an empty local directory; add the workflow files, make the initial commit, and push them to GitHub. Actions begin after the workflows are on the default branch.

The installer refuses to overwrite files with different contents. Review conflicts and rerun with `--force` only when you want to replace them. Identical files are left in place.

## Workflow packs

### `issue-to-pr`

- Add the `ai-ready` label to an issue.
- ChatGPT checks whether the requirements are clear. If details matter, it asks focused questions on the issue and pauses implementation until someone answers.
- When requirements are clear, the workflow adds `ai-ready-to-implement`. Codex implements the change on a branch and opens a pull request.
- The workflow never merges or deploys.

### `pr-review`

- Add the `ai-address-review` label to a pull request to opt it into review follow-up.
- Authorized human PR comments trigger Codex to address feedback on the same branch.
- The label stays active until a reviewer removes it, so later comments can request another revision.
- Fork branches are not supported by this first pack.

## Project ideas

These are ideas to explore; they are not implemented yet.

- **Jira to GitHub issue triage:** bring Jira tickets into GitHub and run the issue-triage workflow on them.
- **Slack and Microsoft Teams notifications:** send progress updates as each workflow step starts or finishes.
- **Isolated visual QA environments:** connect an AWS account, launch a dedicated test environment for UI changes, and open the project in Docker so visual changes can be previewed safely.

## GitHub setup

After installing a pack, add the listed repository secrets and variables under **Settings → Secrets and variables → Actions**.

If a required setting is missing, the workflow posts a comment on the triggering issue or pull request listing the missing names, then skips AI processing.

Both packs use:

- Secret `OPENAI_API_KEY` for ChatGPT and Codex.
- Secret `AI_GH_TOKEN`, a fine-grained GitHub token with repository contents, issues, and pull requests read/write access. Its workflow events allow the next GitHub Actions stage to run.
- Variable `AI_ALLOWED_USERS`, a comma-separated list of GitHub usernames allowed to trigger the automation.

The `pr-review` pack creates the `ai-address-review` label when a new PR opens. To opt in an older PR, create the same label manually if needed and add it to that PR. Remove the label when you want to stop comment-triggered runs.

## Security and project compatibility

The workflows check the allowlist before sending issue text to OpenAI. Codex receives only the issue or PR context it needs, runs with the `:workspace` permission profile, and does not receive the GitHub write token. Separate workflow steps use `AI_GH_TOKEN` to create branches, comments, and pull requests.

The implementation workflow reads repository instructions such as `AGENTS.md` and the installed `.github/codeconductor/AI_SDLC.md`. It does not assume a particular language, framework, or dependency layout. Project checks run only when the repository documents them and the runner has the required tools.

## Add a workflow pack

Each pack lives in `packs/<name>/` with a `pack.json` manifest and a `files/` tree copied into the target repository. Shared policy files live in `packs/shared/files/`. Add a manifest description, required secrets and variables, setup notes, and the files required by that workflow.

## Development

```sh
uv sync
uv run code-conductor --help
```

CodeConductor is released under the MIT License.
