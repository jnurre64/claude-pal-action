# Linux Machine Tasks

Tasks to complete on the Linux machine before the April 2 presentation. These were identified during the presentation prep on Windows but require the Linux environment (self-hosted runner, bot access, main branch).

---

## Task 1: Merge presentation/demo-prep changes into main

The `presentation/demo-prep` branch has several improvements that should go to main:
- Data privacy section in `docs/security.md` and README
- Issue/PR templates (`.github/ISSUE_TEMPLATE/`, `.github/pull_request_template.md`)
- `CHANGELOG.md`

```bash
cd ~/claude-agent-dispatch
git fetch origin
git checkout main
git merge origin/presentation/demo-prep --no-ff -m "Merge presentation/demo-prep: templates, changelog, security docs"
git push origin main
```

Review the diff first — only merge the non-presentation files (templates, CHANGELOG, security docs, README). The plan documents under `docs/superpowers/plans/` and specs are demo-branch-only and can stay there.

Alternatively, cherry-pick just the relevant commits:
```bash
git log --oneline origin/presentation/demo-prep..origin/main  # see what's different
git cherry-pick <commit-hash>  # for each relevant commit
```

---

## Task 2: Create v1.0.0 release tag on main

After merging the improvements:

```bash
cd ~/claude-agent-dispatch
git checkout main
git pull
git tag -a v1.0.0 -m "v1.0.0: Initial public release

Features:
- Label-driven state machine for issue-to-PR lifecycle
- Two-phase approval (plan review before implementation)
- Discord bot with interactive buttons and slash commands
- Phase-specific tool allowlists (read-only triage, read-write implementation)
- Circuit breaker, actor filter, concurrency groups
- Custom prompts, CLAUDE.md context, label-based tool extensions
- Standalone and reference deployment modes
- Interactive /setup skill
- 52 BATS tests, ShellCheck CI
- Comprehensive documentation (10+ guides)"
git push origin v1.0.0
```

Then create a GitHub release:
```bash
gh release create v1.0.0 --title "v1.0.0: Initial Public Release" --notes "See [CHANGELOG.md](CHANGELOG.md) for details."
```

---

## Task 3: Verify demo issue staging (Plan D Tasks 1-4)

Confirm all pre-staged issues are in the correct state for the presentation:

```bash
# Check recipe app issues
gh issue list --repo Frightful-Games/recipe-manager-demo --json number,title,labels --jq '.[] | "\(.number): \(.title) [\(.labels | map(.name) | join(", "))]"'

# Expected:
# #1 Dark mode toggle — no labels (for live demo kick-off)
# #2 Recipe rating — agent:plan-review (pre-staged plan)
# #3 Favorites — agent:plan-review (with feedback + revised plan)
# #4 Search/filter — closed (PR merged)

# Check Godot issues
gh issue list --repo Frightful-Games/dodge-the-creeps-demo --json number,title,labels --jq '.[] | "\(.number): \(.title) [\(.labels | map(.name) | join(", "))]"'

# Expected:
# #1 Power-up — agent:pr-open or closed (PR merged)
```

If any issues are in the wrong state, refer to `docs/superpowers/plans/2026-03-26-demo-plan-d-staging-and-dryruns.md` for restaging instructions.

---

## Task 4: Reset Discord bot config for presentation

The bot should be pointed at the recipe app repo for the live demo:

```bash
# Verify current config
grep AGENT_DISPATCH_REPO ~/agent-infra/config.env

# Should be: AGENT_DISPATCH_REPO="Frightful-Games/recipe-manager-demo"
# If not:
sed -i 's|AGENT_DISPATCH_REPO=.*|AGENT_DISPATCH_REPO="Frightful-Games/recipe-manager-demo"|' ~/agent-infra/config.env
systemctl --user restart agent-dispatch-bot
journalctl --user -u agent-dispatch-bot --since "30 seconds ago" --no-pager
```

---

## Task 5: Verify self-hosted runner is online

```bash
# Check runner status for both repos
gh api repos/Frightful-Games/recipe-manager-demo/actions/runners --jq '.runners[] | "\(.name): \(.status)"'
gh api repos/Frightful-Games/dodge-the-creeps-demo/actions/runners --jq '.runners[] | "\(.name): \(.status)"'

# Both should show "online"
# If offline, check the runner service:
sudo systemctl status actions.runner.*
```

---

## Task 6: Create fresh demo issues for "Let's Start the Clock"

The presentation starts by labeling two issues live. Prepare fresh issues (or verify existing ones are clean):

**Recipe app — new issue for live demo:**
```bash
gh issue create --repo Frightful-Games/recipe-manager-demo \
  --title "Add dark mode toggle" \
  --body "$(cat <<'EOF'
Add a dark mode toggle to the recipe manager application.

## Requirements
- Add a toggle button/switch in the navigation bar
- Clicking the toggle switches between light and dark themes
- Store the user's preference in localStorage so it persists across page loads
- Dark mode should apply to all pages consistently
- Use CSS custom properties (variables) for theme colors so the switch is clean
EOF
)"
```

Or verify issue #1 still has no labels and is ready for the live kick-off.

**Godot — verify the power-up issue or create a new one:**
Check if there's an unlabeled issue available, or create a new feature issue.

---

## Task 7: Dry run — test the full dispatch path

Quick smoke test to make sure everything works end-to-end:

```bash
# 1. Create a throwaway test issue
gh issue create --repo Frightful-Games/recipe-manager-demo \
  --title "[TEST] Dry run - delete after" \
  --body "Test issue for dry run. Delete after verification."

# 2. Label it to trigger triage
gh issue edit <ISSUE_NUMBER> --repo Frightful-Games/recipe-manager-demo --add-label "agent"

# 3. Watch GitHub Actions for the triage workflow
gh run list --repo Frightful-Games/recipe-manager-demo --limit 3

# 4. Wait for plan to be posted (2-5 minutes)
# 5. Verify Discord notification arrived with buttons
# 6. Clean up: close the issue, delete the branch
gh issue close <ISSUE_NUMBER> --repo Frightful-Games/recipe-manager-demo
```

---

## Task 8: Pre-presentation checklist (April 2 morning)

Run through this 30 minutes before the presentation:

```bash
# 1. Restart Discord bot
systemctl --user restart agent-dispatch-bot
journalctl --user -u agent-dispatch-bot --since "30 seconds ago" --no-pager

# 2. Verify no stale agent jobs running
gh run list --repo Frightful-Games/recipe-manager-demo --status in_progress
gh run list --repo Frightful-Games/dodge-the-creeps-demo --status in_progress

# 3. Verify runner is online
gh api repos/Frightful-Games/recipe-manager-demo/actions/runners --jq '.runners[] | "\(.name): \(.status)"'

# 4. Verify demo issues are in correct state
gh issue list --repo Frightful-Games/recipe-manager-demo --json number,title,labels --jq '.[] | "\(.number): \(.title) [\(.labels | map(.name) | join(", "))]"'

# 5. Quick dispatch test (optional — fire and cancel immediately)
# gh api repos/Frightful-Games/recipe-manager-demo/dispatches -f event_type=agent-triage -f 'client_payload[issue_number]=1'
# Then cancel the run in GitHub Actions
```

---

## Notes

- All repo references use `Frightful-Games/` org (not `jnurre64/`)
- The presentation slide deck is at `E:/DemoPresentations/` on the Windows machine
- Speaker notes and Q&A prep are in that same directory
- Plan documents are on the `presentation/demo-prep` branch of `claude-agent-dispatch`
