# Linux Machine Tasks

Tasks to complete on the Linux machine before the April 2 presentation.

---

## Task 1: Cherry-pick improvements from demo-prep into main

A full merge of `presentation/demo-prep` would carry in demo-specific documents (slide plans, presentation specs). Instead, cherry-pick only the project improvements.

```bash
cd ~/claude-agent-dispatch
git fetch origin
git checkout main
git pull origin main
```

**Cherry-pick these 4 commits (in this order):**

```bash
# 1. Trademark disclaimer in README
git cherry-pick 28f7171

# 2. Notify fix: allow bot backend without webhook URL
git cherry-pick dcc5205

# 3. Triage prompt: ask questions when key details missing
git cherry-pick 233df60

# 4. Data privacy section in security.md + README
git cherry-pick 08b9c82

# 5. Issue/PR templates + CHANGELOG
git cherry-pick 856fb94
```

If any cherry-pick has a conflict (likely on README.md since multiple commits touch it), resolve manually — the changes are small and additive.

```bash
# Verify everything looks right
git log --oneline -6
git diff HEAD~5..HEAD --stat

# Push
git push origin main
```

**What these add to main:**
- Data privacy docs (security.md section + README callout)
- Trademark/non-affiliation disclaimer in README
- Triage prompt improvement (ask questions instead of assuming)
- Notify fix for bot backend
- Issue templates, PR template, CHANGELOG.md

**What stays on demo-prep only:**
- All `docs/superpowers/plans/2026-03-26-*` (demo plans A-D)
- All `docs/superpowers/specs/` (presentation spec)
- `docs/superpowers/plans/2026-03-28-slide-deck-improvements.md`
- `docs/superpowers/plans/2026-03-30-linux-machine-tasks.md`

---

## Task 2: Create v1.0.0 release tag on main

After cherry-picking:

```bash
cd ~/claude-agent-dispatch
git checkout main

# Tag the release
git tag -a v1.0.0 -m "v1.0.0: Initial public release

Features:
- Label-driven state machine for issue-to-PR lifecycle
- Two-phase approval (plan review before implementation)
- Discord bot with interactive buttons and slash commands
- Phase-specific tool allowlists (read-only triage, read-write implement)
- Circuit breaker, actor filter, concurrency groups, timeouts
- Custom prompts per project, CLAUDE.md context, label-based tool extensions
- Standalone and reference deployment modes
- Interactive /setup skill for project configuration
- 52 BATS tests with regression coverage, ShellCheck CI
- Comprehensive documentation (10+ guides)

See CHANGELOG.md for full details."

git push origin v1.0.0
```

Then create the GitHub release:

```bash
gh release create v1.0.0 \
  --repo jnurre64/claude-agent-dispatch \
  --title "v1.0.0: Initial Public Release" \
  --notes "$(cat <<'EOF'
## Claude Agent Dispatch v1.0.0

First public release of the autonomous agent orchestrator for GitHub issues.

### Highlights
- **Label state machine** — `agent` → `triage` → `plan-review` → `plan-approved` → `in-progress` → `pr-open`
- **Two-phase approval** — Human reviews plan before any code is written
- **Discord bot** — Approve plans, give feedback, and monitor progress from Discord
- **Safety guardrails** — Tool allowlists, circuit breaker, actor filter, concurrency groups
- **Two deployment modes** — Standalone (full control) or Reference (auto-updates)
- **Interactive setup** — `/setup` skill walks through configuration in ~5 minutes

### Getting Started
```bash
git clone https://github.com/jnurre64/claude-agent-dispatch.git ~/agent-infra
cd ~/agent-infra && claude
# Type: /setup
```

See [CHANGELOG.md](CHANGELOG.md) for the complete feature list.
See [docs/getting-started.md](docs/getting-started.md) for the full setup guide.
EOF
)"
```

---

## Task 3: Pre-presentation morning checklist (April 2)

Quick verification 30 minutes before:

```bash
# 1. Restart Discord bot
systemctl --user restart agent-dispatch-bot
journalctl --user -u agent-dispatch-bot --since "30 seconds ago" --no-pager

# 2. Verify bot config points at recipe app
grep AGENT_DISPATCH_REPO ~/agent-infra/config.env
# Should be: Frightful-Games/recipe-manager-demo

# 3. Verify no stale jobs running
gh run list --repo Frightful-Games/recipe-manager-demo --status in_progress
gh run list --repo Frightful-Games/dodge-the-creeps-demo --status in_progress

# 4. Verify runner is online
gh api repos/Frightful-Games/recipe-manager-demo/actions/runners --jq '.runners[] | "\(.name): \(.status)"'

# 5. Verify demo issues are ready
gh issue list --repo Frightful-Games/recipe-manager-demo --json number,title,labels --jq '.[] | "\(.number): \(.title) [\(.labels | map(.name) | join(", "))]"'
```

---

## Notes

- All demo repos are under `Frightful-Games/` org
- The presentation slide deck is at `E:/DemoPresentations/` on the Windows machine
- Q&A preparation guide is at `E:/DemoPresentations/qa-preparation.md`
