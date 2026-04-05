# Direct Implementation via `agent:implement` Label

## Summary

Add an `agent:implement` label that lets users skip the triage/plan-writing phase when an issue already contains a complete implementation plan. The agent validates the plan against the current codebase, then proceeds directly to implementation in a single run — no human checkpoint between validation and implementation.

## Motivation

When a user brainstorms and writes a detailed plan in a separate Claude session (or manually), the standard `agent` → triage → `agent:plan-approved` flow is redundant. The agent re-explores the codebase and rewrites a plan that already exists. This feature eliminates that overhead while preserving a safety net: a lightweight validation pass ensures the plan references real files, functions, and accessible resources before implementation begins.

### Prior art

Issue [Frightful-Games/Webber#96](https://github.com/Frightful-Games/Webber/issues/96) is the motivating case — a 6-phase implementation plan with a committed spec file, produced through collaborative brainstorming. The full triage phase adds no value here.

## Design

### New Label: `agent:implement`

Added to `labels.txt`:

```
agent:implement|FBCA04|Skip triage — validate and implement a pre-written plan
```

Color `FBCA04` (yellow) matches other "agent is working" states.

### Label State Machine — New Entry Path

```
HUMAN ADDS "agent:implement"
        ↓
    (config check: AGENT_ALLOW_DIRECT_IMPLEMENT)
        ↓
    agent:validating  (new label — agent verifying plan)
        ↓
    ┌───────────────────────────────┐
    ↓                               ↓
agent:needs-info              agent:in-progress
(validation found issues)     (validation passed → implement)
    ↓                               ↓
(human updates issue)         (existing implement flow)
```

This is a new entry point. The existing `agent` → `agent:plan-approved` path is unchanged.

### New Label: `agent:validating`

Added to `labels.txt`:

```
agent:validating|FBCA04|Agent is validating a pre-written plan against the codebase
```

Distinct from `agent:triage` because validation is a different phase with a different prompt — it checks an existing plan rather than exploring and writing one.

### Configuration

A single flag in `defaults.sh`:

```bash
AGENT_ALLOW_DIRECT_IMPLEMENT="${AGENT_ALLOW_DIRECT_IMPLEMENT:-true}"
```

- Default `true`: available on all repos unless explicitly disabled.
- Teams that want to enforce the full triage flow set `AGENT_ALLOW_DIRECT_IMPLEMENT=false`.
- When disabled, `handle_direct_implement()` posts a comment explaining the feature is disabled and sets `agent:failed`.

### Handler: `handle_direct_implement()`

New function in `agent-dispatch.sh`, dispatched by event type `direct_implement`.

**Flow:**

1. **Config gate**: If `AGENT_ALLOW_DIRECT_IMPLEMENT` is not `true`, post comment and set `agent:failed`. Return.
2. **Setup**: `detect_label_tools`, set `agent:validating`, `check_circuit_breaker`, `ensure_repo`, `setup_worktree`.
3. **Fetch context**: Issue title, body, last 20 comments via `gh issue view` (same as `handle_new_issue`).
4. **Data fetch**: Run `extract_debug_data` on comments JSON and issue body. Downloads gists, GitHub attachments to `.agent-data/`. Existing infrastructure handles this.
5. **Export env vars**: `AGENT_ISSUE_TITLE`, `AGENT_ISSUE_BODY`, `AGENT_COMMENTS`, `AGENT_DATA_COMMENT_FILE`, `AGENT_GIST_FILES`, `AGENT_DATA_ERRORS`.
6. **Run validation**: Load `validate.md` prompt, run `claude -p` with `AGENT_ALLOWED_TOOLS_TRIAGE` (read-only).
7. **Parse result**:
   - `{"action": "valid"}` → proceed to step 8.
   - `{"action": "issues_found", "issues": [...]}` → post comment with findings (including instruction to fix and re-label with `agent:implement`), set `agent:needs-info`, send notification, cleanup worktree, return.
   - Parse failure → set `agent:failed`, post diagnostic comment, cleanup worktree, return.
8. **Transition to implementation**: Set `AGENT_PLAN_CONTENT` to the issue body. Call `handle_implement()`. The worktree, env vars, and data files are already set up — `handle_implement()` picks up cleanly.

### Validation Prompt: `prompts/validate.md`

New prompt file. The agent receives the same env vars as triage (`AGENT_ISSUE_TITLE`, `AGENT_ISSUE_BODY`, `AGENT_COMMENTS`) plus data file paths (`AGENT_DATA_COMMENT_FILE`, `AGENT_GIST_FILES`, `AGENT_DATA_ERRORS`).

**Instructions:**

1. Read the CLAUDE.md file for project conventions.
2. Read the issue body and comments to understand the implementation plan.
3. If the issue body references repo-local file paths (e.g., `docs/specs/foo.md`), read those files as additional plan context.
4. **Validate plan correctness:**
   - Verify all file paths mentioned in the plan exist in the repo.
   - Verify functions, classes, enums, and variables referenced in the plan exist (use Grep/Glob).
   - Check that the described code structure matches the current state (e.g., if the plan says "add X to file Y", verify file Y exists and the surrounding context is as described).
5. **Validate data accessibility:**
   - If `$AGENT_DATA_COMMENT_FILE` is set, verify the file exists and is non-empty.
   - If `$AGENT_GIST_FILES` is set, verify each path exists and is non-empty.
   - If `$AGENT_DATA_ERRORS` exists, read it — any failed downloads are issues to report.
   - If the issue body references repo-local spec files, verify they exist and are readable.
6. **Output JSON** (no markdown, no code fences):
   - If all checks pass: `{"action": "valid"}`
   - If any issues found: `{"action": "issues_found", "issues": ["description of issue 1", "description of issue 2"]}`

**Custom override:** `AGENT_PROMPT_VALIDATE` config variable, following the existing `AGENT_PROMPT_*` pattern.

### Modification to `handle_implement()`

One small change to the plan extraction logic. Currently:

```bash
local plan_content
plan_content=$(echo "$issue_json" | jq -r '
    [.comments[] | select(.body | test("<!-- agent-plan -->"))] | last | .body // ""
' 2>/dev/null)

if [ -z "$plan_content" ]; then
    log "Could not find plan comment on issue. Marking as failed."
    set_label "agent:failed"
    # ... error handling ...
    return
fi
```

Becomes:

```bash
local plan_content
if [ -n "${AGENT_PLAN_CONTENT:-}" ]; then
    plan_content="$AGENT_PLAN_CONTENT"
    log "Using pre-loaded plan content (direct implement)"
else
    plan_content=$(echo "$issue_json" | jq -r '
        [.comments[] | select(.body | test("<!-- agent-plan -->"))] | last | .body // ""
    ' 2>/dev/null)

    if [ -z "$plan_content" ]; then
        log "Could not find plan comment on issue. Marking as failed."
        set_label "agent:failed"
        # ... error handling ...
        return
    fi
fi
```

When `AGENT_PLAN_CONTENT` is unset (the `agent:plan-approved` path), the existing extraction runs exactly as before. When pre-set by `handle_direct_implement()`, the extraction is skipped. Zero behavior change for existing flows.

### Workflow: `dispatch-direct-implement.yml`

New reusable workflow, structurally identical to `dispatch-implement.yml`:

- Same inputs: `bot_user`, `issue_number`, `dispatch_script`, `config_path`, `timeout_minutes`, `runner_labels`
- Same secrets: `agent_pat`
- Same concurrency group: `claude-agent-${{ inputs.issue_number || github.event.issue.number }}`
- Same permissions: `contents: write`, `issues: write`, `pull-requests: write`
- Calls: `agent-dispatch.sh direct_implement <repo> <number>`

Consuming repos add a calling workflow that triggers on `issues.labeled` with `agent:implement` and calls this reusable workflow.

### Setup Script Templates

Two new templates for `scripts/setup.sh`:

**Reference mode** (`.claude/skills/setup/templates/caller-direct-implement.yml`):
- Triggers on `issues.labeled` with `agent:implement`
- Actor filter: `github.actor != inputs.bot_user` (prevents bot self-triggering)
- Calls: `jnurre64/claude-agent-dispatch/.github/workflows/dispatch-direct-implement.yml@v1`

**Standalone mode** (`.claude/skills/setup/templates/standalone/agent-direct-implement.yml`):
- Triggers on `issues.labeled` with `agent:implement`
- Actor filter: same
- Runs `agent-dispatch.sh direct_implement` directly

### Re-entry After Validation Failure

When validation fails and sets `agent:needs-info`, the existing `handle_issue_reply` flow would normally re-enter triage — not re-run validation. To handle this correctly:

**Approach**: `handle_direct_implement()` posts a validation failure comment with a `<!-- agent-direct-implement -->` HTML marker. `handle_issue_reply()` is modified to check for this marker in the issue comments. If found, it calls `handle_direct_implement()` instead of `handle_new_issue()`, re-running validation with the updated issue context.

This keeps the reply flow working naturally — the human comments to say they've fixed things, and the agent re-validates rather than starting a full triage.

**Modification to `handle_issue_reply()`**: Add a check before the existing `handle_new_issue` call:

```bash
# Check if this issue entered via direct implement
local has_direct_marker
has_direct_marker=$(echo "$issue_json" | jq -r '
    [.comments[] | select(.body | test("<!-- agent-direct-implement -->"))] | length
' 2>/dev/null || echo "0")

if [ "$has_direct_marker" -gt 0 ]; then
    log "Issue entered via direct implement. Re-running validation..."
    handle_direct_implement
    return
fi
```

### Documentation Updates

| File | Changes |
|------|---------|
| `docs/architecture.md` | Add `agent:implement` and `agent:validating` to the label state machine diagram. Document the new entry path. |
| `docs/configuration.md` | Document `AGENT_ALLOW_DIRECT_IMPLEMENT` flag and `AGENT_PROMPT_VALIDATE` custom prompt override. |
| `docs/customization.md` | Document `AGENT_PROMPT_VALIDATE` override option, following existing `AGENT_PROMPT_*` pattern. |
| `docs/getting-started.md` | Mention `agent:implement` as an alternative flow for pre-planned issues. |
| `README.md` | Update if it references the label state machine or workflow overview. |

## Files to Create

| File | Purpose |
|------|---------|
| `prompts/validate.md` | Validation prompt — verify plan correctness and data accessibility |
| `.github/workflows/dispatch-direct-implement.yml` | Reusable workflow for `agent:implement` trigger |
| `.claude/skills/setup/templates/caller-direct-implement.yml` | Calling workflow template (reference mode) |
| `.claude/skills/setup/templates/standalone/agent-direct-implement.yml` | Calling workflow template (standalone mode) |

## Files to Modify

| File | Changes |
|------|---------|
| `scripts/agent-dispatch.sh` | Add `handle_direct_implement()` handler, add `direct_implement` case to dispatch, add direct-implement marker check to `handle_issue_reply()` |
| `scripts/lib/defaults.sh` | Add `AGENT_ALLOW_DIRECT_IMPLEMENT` and `AGENT_PROMPT_VALIDATE` defaults |
| `labels.txt` | Add `agent:implement` and `agent:validating` labels |
| `docs/architecture.md` | Update state machine, document new flow |
| `docs/configuration.md` | Document new config flag and prompt override |
| `docs/customization.md` | Document validate prompt customization |
| `docs/getting-started.md` | Mention direct implement alternative |
| `README.md` | Update label/workflow references if present |

## What This Does NOT Change

- The `agent` → `agent:plan-approved` flow is completely untouched.
- `handle_implement()` behavior is unchanged when called via `agent:plan-approved` — the guard only activates when `AGENT_PLAN_CONTENT` is pre-set.
- Tool permissions are unchanged — validation uses triage tools (read-only), implementation uses implementation tools (read-write).
- Circuit breaker, concurrency groups, error traps, and all safety mechanisms apply identically.
- The update skill for standalone mode requires no changes — new files are detected as "new upstream" automatically.
