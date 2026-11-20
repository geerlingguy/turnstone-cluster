---
name: ansible-role-pr
description: Use when asked to review, fix, test, comment on, or open a pull request for one of Jeff Geerling's Ansible roles (github.com/geerlingguy/ansible-role-*), e.g. "look at https://github.com/geerlingguy/ansible-role-ntp/pull/152". Covers checking out the PR, linting, Molecule tests in Docker, cleanup, and posting comments or PRs as geerlingbot.
version: 1.0.0
---

# Ansible role PRs

You work as the GitHub user `geerlingbot`. `gh` and `git` in bash can only read from GitHub. Every write (comments, forks, branches, commits, PRs) goes through the `github` MCP tools, which ask Jeff for approval first. Never merge or close anything.

## 1. Check out the code

The directory must be named `geerlingguy.<role>`, because the Molecule playbooks include the role by that name.

```bash
REPO=ansible-role-ntp; ROLE=geerlingguy.ntp; PR=152
mkdir -p /workspace/prs/$REPO-$PR && cd /workspace/prs/$REPO-$PR
gh repo clone geerlingguy/$REPO $ROLE && cd $ROLE
gh pr checkout $PR          # Skip for a new change on master.
gh pr view $PR --comments
gh pr diff $PR
```

Read `.github/workflows/ci.yml` for the lint steps and the `distro` matrix.

## 2. Change the code

Keep changes minimal and in the role's existing style. Update `README.md` when you change variables in `defaults/main.yml`.

## 3. Lint and test

```bash
yamllint .
ansible-lint     # Only if CI runs it.
MOLECULE_DISTRO=rockylinux9 molecule test
```

Run `molecule test` for each distro in the CI matrix, one at a time. `DOCKER_HOST` already points at a Docker daemon just for these tests.

## 4. Clean up

`molecule test` destroys its container when it succeeds. After any failed or interrupted run, run `molecule destroy` before moving on. Check that `docker ps -a` is empty when you're done.

## 5. Report back

Report back to Jeff with the test results for each distro and a short summary of the changes, then ask whether to post.

- **Comment on an issue or PR**: `mcp__github__add_issue_comment` (PRs are issues). Keep it short: what you tested, what failed, the fix you suggest.
- **Open a PR**: `mcp__github__fork_repository` (once per repo, into `geerlingbot`), `mcp__github__create_branch` on the fork, `mcp__github__push_files` with every changed file, then `mcp__github__create_pull_request` against `geerlingguy/<repo>` `master` with head `geerlingbot:<branch>`.

You can't push to someone else's PR branch. To change an existing PR, open a new PR from your fork, or suggest the change in a comment.
