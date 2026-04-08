# Design: Workflow Template Detection in `/update` Skill

**Date:** 2026-04-07
**Issue:** #17 — Update skill: detect new workflow templates and offer to install them
**Scope:** Standalone mode only

## Problem

When upstream adds a new workflow template (e.g., `agent-direct-implement.yml` for the `agent:implement` feature), the `/update` skill syncs scripts, prompts, and labels correctly but does not detect the new template. Users must manually discover and create the corresponding workflow file in `.github/workflows/`.

This was encountered during the `agent:implement` rollout to Frightful-Games/Webber (2026-04-05), where `/update` synced 11 files but missed the new workflow template entirely.

## Approach

Add a new step to the update SKILL.md between "Apply Updates" (current Step 5) and "Update Tracking" (current Step 6). This step instructs Claude to scan upstream templates and offer to install any that are missing from the user's repo.

No changes to `setup.sh`, the `.upstream` file format, or any shell scripts. The update skill is already an interactive Claude-guided flow; this adds one more step to those instructions.

## Design

### Detection Logic

1. Glob the upstream clone's `.claude/skills/setup/templates/standalone/` for all `.yml` files.
2. For each template, derive the expected installed filename by stripping the `standalone/` prefix (e.g., `standalone/agent-direct-implement.yml` → `agent-direct-implement.yml`).
3. Check if `.github/workflows/<filename>` exists in the user's repo.
4. Any template without a matching installed workflow is flagged as new.

### Installation Flow (per new template)

1. Show the template name and a brief description (from the workflow's `name:` field and trigger type).
2. Read `AGENT_BOT_USER` from `.agent-dispatch/config.defaults.env` and confirm with the user (e.g., "I'll use `pennyworth-bot` from your config — does that look right?").
3. Apply `{{BOT_USER}}` substitution to the template content.
4. Show the generated workflow to the user.
5. Ask if they want to install it to `.github/workflows/`.
6. If yes, write the file. If no, skip.

### No New Templates

If all upstream templates already have matching workflows, report "No new workflow templates detected" and move on to the next step.

### What This Does NOT Do

- **Modify existing workflows.** Only new (missing) templates are offered. Installed workflows are never touched.
- **Track workflows in `.upstream`.** The `.upstream` file format is unchanged. Detection is based on filesystem comparison, not a manifest.
- **Remove workflows.** If upstream deletes a template, the installed workflow is left in place. There is no reliable way to distinguish "upstream removed this" from "user created this themselves."
- **Propagate env vars from existing workflows.** New templates ship with the standard env block (`GH_TOKEN`, `GITHUB_TOKEN`, `AGENT_CONFIG`). If the user has added custom secrets to other workflows, they handle that themselves after installation.
- **Touch `.env` files.** Config files are owned by the environment and are never modified by the update skill.

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| User renamed a workflow file | Detected as "new" since expected filename is missing. User declines installation. Harmless. |
| `.github/workflows/` directory doesn't exist | Create it before writing (unlikely in standalone, but defensive). |
| `agent-dispatch.yml` (Discord bot dispatch) template | Treated the same as any other template. User declines if they don't use the Discord bot. |
| `AGENT_BOT_USER` not found in config | Ask the user to provide the bot username manually. |
| No upstream templates directory | Skip the step entirely (shouldn't happen, but graceful no-op). |

## Files Changed

| File | Change |
|------|--------|
| `.claude/skills/update/SKILL.md` | Add new step for workflow template detection between current Steps 5 and 6. |

## Testing

- Run `/update` on a standalone installation that is missing a workflow template and verify it is detected and offered for installation.
- Run `/update` on a standalone installation with all workflows present and verify "No new workflow templates" is reported.
- Verify `{{BOT_USER}}` substitution produces correct output matching existing installed workflows.
