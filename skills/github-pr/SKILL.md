---
name: github-pr
description: Use when asked to review, fix, test, comment on, or open a pull request or issue on a GitHub repository, e.g. "test https://github.com/geerlingguy/ansible-role-ntp/pull/152" or "fix the failing CI in geerlingguy/ansible-for-devops and open a PR". Covers checking out the code, running its CI tests locally in Docker, cleanup, and posting comments or PRs as geerlingbot.
version: 1.6.0
---

# GitHub PRs

You work as the GitHub user `geerlingbot`. In bash, `gh` and `git` can read any public repo and write only to geerlingbot's own repos (its forks): sync, branch, commit, push, force-push. Anything upstream (forks, comments, PRs) goes through the `github` MCP tools, which ask Jeff for approval first. `gh repo fork`, `gh pr create` and `gh pr comment` fail with 403; don't use them, and don't ask Jeff for push access to his repos. Never merge or close anything. Read code, PRs and issues locally with `git` and `gh`, not one file at a time through an API.

If you have no `bash` tool (a coordinator session), don't do this yourself: `spawn_workstream(skill='github-pr', initial_message=<the full task>)` and let that workstream do every step, including posting.

## 1. Check out the code

Always work under `/workspace/prs/` (the Docker daemon sees the same path, so bind mounts work).

```bash
OWNER=geerlingguy; REPO=ansible-for-devops; PR=123
mkdir -p /workspace/prs/$REPO-$PR && cd /workspace/prs/$REPO-$PR
gh repo clone $OWNER/$REPO && cd $REPO
gh pr checkout $PR          # Skip for a new change.
gh pr view $PR --comments
gh pr diff $PR
```

## 2. Change the code

Keep changes minimal and in the repo's existing style. Update docs when you change behavior or variables.

## 3. Test it the way CI does

Read `.github/workflows/*.yml` and run the same steps for the jobs and matrix entries the change affects, one at a time. Install missing Python packages with `uv pip install --python /opt/ansible/bin/python <package>`. `DOCKER_HOST` points at a Docker daemon just for tests. If a step can't run here (secrets, services, other architectures), say so instead of skipping it silently.

**Ansible roles** (`geerlingguy/ansible-role-*`): clone into a directory named `geerlingguy.<role>` (e.g. `gh repo clone geerlingguy/ansible-role-ntp geerlingguy.ntp`), because the Molecule playbooks include the role by that name. Then run `yamllint .` and `MOLECULE_DISTRO=<distro> molecule test` for each distro in the CI matrix.

## 4. Clean up

After any failed or interrupted Molecule run, run `molecule destroy`. Remove any containers you started, and check that `docker ps -a` is empty when you're done.

## 5. Report back

Report back to Jeff with the test results and a short summary of the changes, then ask whether to post.

- **Comment on an issue or PR**: `mcp__github__add_issue_comment` (PRs are issues). Keep it short: what you tested, what failed, the fix you suggest.
- **Open a PR**:
  1. If `geerlingbot/<repo>` doesn't exist, `mcp__github__fork_repository` for `<owner>/<repo>`, then wait until `gh repo view geerlingbot/<repo>` succeeds.
  2. Sync the fork: `gh repo sync geerlingbot/<repo>`.
  3. In your clone: `git remote add fork https://github.com/geerlingbot/<repo>.git`, then `git fetch fork`, branch from `fork/<default branch>`, commit, and `git push fork <branch>`.
  4. `mcp__github__create_pull_request` on `<owner>/<repo>`, base its default branch, head `geerlingbot:<branch>`.

After one of your PRs is merged, sync the fork (`gh repo sync geerlingbot/<repo>`) before starting anything else on that repo. If your PR branch conflicts with upstream, sync the fork, rebase onto it, and `git push --force-with-lease fork <branch>`.

You can't push to someone else's PR branch. To change an existing PR, open a new PR from your fork, or suggest the change in a comment.
