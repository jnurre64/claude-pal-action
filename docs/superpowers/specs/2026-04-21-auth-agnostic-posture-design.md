# Auth-Agnostic Posture: Documentation Realignment

**Status:** Draft
**Date:** 2026-04-21
**Author:** jnurre64 (with Claude)
**Supersedes:** [`2026-04-17-authentication-docs-design.md`](2026-04-17-authentication-docs-design.md)

## Problem

The project currently documents two authentication methods for the `claude` CLI on the runner — `ANTHROPIC_API_KEY` (Console API key) and `CLAUDE_CODE_OAUTH_TOKEN` (subscription OAuth token from `claude setup-token`) — with a decision matrix, Path A / Path B framing, and prescriptive guidance about which applies in which situation. This "informational-neutral" posture landed on 2026-04-17 as a walk-back from an earlier "API key only" stance.

It is still more prescriptive than it needs to be. The project's code is already authentication-agnostic: `scripts/lib/common.sh:170` invokes `claude -p` without touching any credential env var, and Claude Code's own authentication precedence resolves whatever the operator configured. The documentation, however, encodes a specific posture: enumerating env vars, paraphrasing Anthropic's Terms of Service, warning about the `ANTHROPIC_API_KEY` silent-override footgun, and walking users through both token types.

Two concerns follow from that:

1. **The project paraphrases Anthropic's terms.** Any paraphrase of Terms of Service will drift out of sync with authoritative language as Anthropic updates its policies. The 2026-04-17 work was itself a reaction to such drift. Centralizing that content in the project creates ongoing maintenance exposure.

2. **The project implicitly endorses specific credential patterns.** Documenting `CLAUDE_CODE_OAUTH_TOKEN` + `claude setup-token` as a supported path — even with guardrails — puts the project in the position of steering users toward subscription-OAuth-in-CI, which is a supported-but-gray-zone pattern. A user who configures it incorrectly (shared runner, team use, high-volume automation) has a plausible defense that the project guided them there. Removing that path from the project's documentation shifts the posture question entirely to the user's situation: the project does not tell anyone how to authenticate; it only requires that Claude Code is authenticated.

The goal of this work is to make the project's documentation **auth-agnostic in posture as well as in code**. The project documents the prerequisite — Claude Code must be authenticated on the runner — and defers the method, the Terms of Service analysis, and the silent-override footgun to Anthropic's own documentation. Whether a user's authentication choice is Terms-compliant becomes a function of *their* situation (solo vs. team, Consumer vs. Commercial Terms, ordinary vs. service-pattern use) rather than a function of the project's recommendations.

## Design principle

**The project documents the installation prerequisite, not the authentication method.** Specific credential environment variables, token types, decision matrices, and ToS analysis all move off-project and into Anthropic's own authoritative docs. Users pick a method based on their own situation; the same situation determines what Anthropic's Terms require of them. The project takes no position and makes no endorsement.

**Accuracy check against Anthropic's published terms (verified 2026-04-21):**

- [Consumer Terms §3(7)](https://www.anthropic.com/legal/consumer-terms): "Except when you are accessing our Services via an Anthropic API Key or where we otherwise explicitly permit it, to access the Services through automated or non-human means…" — automated access is permitted via API key, or via explicitly-documented OAuth paths (e.g., `claude setup-token` is Anthropic's explicit carve-out for CI). Either is consistent with the new posture; the project does not need to choose between them on the user's behalf.
- [Consumer Terms §2](https://www.anthropic.com/legal/consumer-terms): "You may not share your Account login information, Anthropic API key, or Account credentials with anyone else." — a per-user obligation. The project cannot and does not share credentials on anyone's behalf; whether a user's deployment shares credentials is their call.
- [Claude Code Legal and Compliance](https://code.claude.com/docs/en/legal-and-compliance): "OAuth authentication is intended exclusively for purchasers of Claude Free, Pro, Max, Team, and Enterprise subscription plans and is designed to support ordinary use of Claude Code and other native Anthropic applications." — applies to how the user configures Claude Code, not to how the project documents it. The project invokes the native `claude` CLI (not the Agent SDK), which is within the scope of "native Anthropic applications" regardless of the user's credential choice.
- [Claude Code Legal and Compliance](https://code.claude.com/docs/en/legal-and-compliance): "Advertised usage limits for Pro and Max plans assume ordinary, individual usage of Claude Code and the Agent SDK." — a user-posture rule. Whether a particular deployment counts as "ordinary individual usage" depends on how the user runs it, not on which env var they set.

No Terms-of-Service clause requires the project to document credential methods. Removing that content from the project's docs does not create a new compliance gap; it relocates the Terms-of-Service analysis to where it has always belonged — with the user and Anthropic.

**Acknowledged trade-off.** By not pointing users at `claude setup-token`, the project may nudge subscription-oriented users toward interactive `claude /login` on the runner. `setup-token` is Anthropic's *explicitly documented* path for CI ("Use this for CI pipelines and scripts where browser login isn't available" — [Claude Code Authentication](https://code.claude.com/docs/en/authentication)); `/login` used headlessly under a systemd-invoked runner is within "ordinary use of Claude Code" but lacks that explicit carve-out. This is a known consequence of the deliberate choice to minimize project prescription. Users who want the explicitly-carved-out path will find `setup-token` in Anthropic's own docs, linked from `authentication.md`.

## Non-goals

- **Not** adding any runtime code branch, env-var check, or credential validation to the dispatch scripts. The code is already agnostic; no change is needed there.
- **Not** removing the existence of a project-level `docs/authentication.md`. Users still need a project-specific entry point that says "Claude Code must be authenticated" and links to Anthropic's docs. The doc shrinks; it does not disappear.
- **Not** altering `scripts/lib/common.sh`, workflow YAML, `config.env.example`, `config.defaults.env.example`, Python bot code under `discord-bot/`/`slack-bot/`/`shared/`, or any prompts under `prompts/`. Verified via exhaustive grep on 2026-04-21: no `.sh`, `.yml`, `.yaml`, `.py`, `.ts`, `.js`, `.bats`, or config file outside `scripts/setup.sh` references `ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_AUTH_TOKEN`, `apiKeyHelper`, `sk-ant-api`, `sk-ant-oat`, or `setup-token`.
- **Not** adding new Terms-of-Service analysis, legal disclaimers, or usage guidance beyond a single "not legal advice" line plus pointers to Anthropic's authoritative pages.
- **Not** re-documenting methods the prior spec deliberately excluded (`ANTHROPIC_AUTH_TOKEN` gateway path, `--bare` mode, `apiKeyHelper`).
- **Not** revising the 2026-04-17 spec or plan documents themselves beyond a one-line supersession note. Those remain historical records of the prior posture.

## Full inventory of files to change

Audit performed on 2026-04-21 across all markdown, shell, YAML, Python, and config files in the repo (excluding `tests/bats/` vendored submodules, `docs/issues/`, and `docs/superpowers/` historical records):

| File | Current auth content | Change type |
|---|---|---|
| `README.md` | L17 feature bullet naming "Pro/Max subscription or API key"; L64 prerequisite naming both env vars | Rewrite two lines |
| `docs/authentication.md` | 131-line Path A / Path B prescription with decision matrix, Never-OK patterns, verification checklist | Full rewrite to ~25 lines |
| `docs/getting-started.md` | Step 4 (L85-115) with both env-var options, code examples, silent-override warning | Rewrite the step |
| `docs/runners.md` | L118-148 "Claude Code authentication" subsection with both options and silent-override warning | Rewrite the subsection |
| `docs/security.md` | L122-139 "Anthropic Authentication Model" section; L154-156 three checklist lines | Shrink the section; collapse checklist to one line |
| `docs/faq.md` | L29-37 ToS and Pro/Max Qs; L49-53 costs Q | Rewrite three answers |
| `.claude/skills/setup/SKILL.md` | Step 9d (L229-272) with auth-path branching and two credential branches | Replace branching with neutral instruction |
| `scripts/setup.sh` | L337-345 post-setup instructions naming both env vars | Replace with pointer to `docs/authentication.md` |
| `docs/claude-code-subscription-automation-guide.md` | Entire 121-line opinion piece on subscription + automation ranking | **Delete** |
| `docs/superpowers/specs/2026-04-17-authentication-docs-design.md` | Prior spec, now superseded | Add one-line supersession note at top |
| `docs/superpowers/plans/2026-04-17-authentication-docs-realignment.md` | Prior plan, now superseded | Add one-line supersession note at top |

Files confirmed **not** requiring changes (verified by grep on 2026-04-21):

- All files under `.github/workflows/` — no auth env var references
- `scripts/lib/common.sh`, `scripts/lib/*.sh`, `scripts/agent-dispatch.sh`, `scripts/cleanup.sh`, all other shell scripts under `scripts/` — no auth env var references
- `config.env.example`, `config.defaults.env.example` — no auth env var references (credentials belong in the runner's `.env`, not in project config)
- All files under `discord-bot/`, `slack-bot/`, `shared/` — no Claude auth references (these handle Discord/Slack auth, not Anthropic auth)
- All files under `prompts/` — no auth references
- All files under `tests/` — no auth env var references in tests we own (vendored `tests/bats/` not audited, but not modified either)
- `CLAUDE.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CHANGELOG.md` — no prescriptive auth references

## New `docs/authentication.md`

Full content (approximately 25 lines of rendered body, plus headings):

```markdown
# Authentication

Claude Agent Dispatch runs `claude -p` (the headless mode of the native Claude Code CLI) on a self-hosted GitHub Actions runner. The dispatch scripts do not reference any credential environment variable — Claude Code's own authentication resolves whatever the operator has configured on the runner.

## Requirement

Claude Code must be authenticated on the runner before the first dispatch run. See Anthropic's [Claude Code authentication docs](https://code.claude.com/docs/en/authentication) for the supported methods and setup instructions.

After configuring authentication, verify with `claude /status` on the runner. If you configured a method that uses environment variables set in the runner's `.env` file, restart the runner service so workflow jobs pick up the variables.

## Terms of Service

Which of Anthropic's terms apply to your use of this project — and which authentication methods are appropriate — depend on how you are using the project, not on the project itself. Review the relevant Anthropic pages directly:

- [Claude Code Legal and Compliance](https://code.claude.com/docs/en/legal-and-compliance)
- [Anthropic Consumer Terms of Service](https://www.anthropic.com/legal/consumer-terms) (for subscription-backed accounts)
- [Anthropic Commercial Terms](https://www.anthropic.com/legal/commercial-terms) (for API-key and commercial accounts)
- [Anthropic Acceptable Use Policy](https://www.anthropic.com/legal/aup)

## Runner hygiene

Regardless of authentication method:

- If your chosen method uses environment variables in the runner's `.env` file, that file must be `chmod 600` — readable only by the runner user.
- Never commit credentials to any repository.
- Use `claude /status` on the runner to confirm the runner is authenticated with the account you intend.

## Disclaimer

This page describes an installation prerequisite. It is not legal advice. Review Anthropic's current Terms of Service, Usage Policies, and Claude Code documentation for the authoritative statement on authentication methods and their permitted uses.
```

**Design notes:**

- No env var names (`ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, etc.).
- No Path A / Path B or any decision matrix.
- No paraphrasing of Anthropic's ToS clauses. The project links to Anthropic's pages and does not restate the rules.
- No "silent override" warning — that is Claude Code's behavior and Anthropic's footgun to document.
- Preserves the "runner hygiene" items (`chmod 600`, don't commit) because those are project-operator responsibilities, not method-specific auth instructions.
- The `claude /status` recommendation stays because verifying that the runner picks up the configured credentials is a project-reasonable checkpoint before the first dispatch run.

## Downstream changes (exact wording)

### `README.md`

**L17 feature bullet.** Replace:

```markdown
- **No third-party platform layers** — runs on the official Claude Code CLI and GitHub Actions, with no additional SaaS dependencies on top. Authentication uses either your Pro/Max subscription (individual use) or an Anthropic API key (required for team/commercial use) — see [authentication.md](docs/authentication.md).
```

With:

```markdown
- **No third-party platform layers** — runs on the official Claude Code CLI and GitHub Actions, with no additional SaaS dependencies on top. Authenticate Claude Code on the runner however fits your use — the dispatch scripts do not prescribe a method; see [authentication.md](docs/authentication.md).
```

**L64 prerequisite bullet.** Replace:

```markdown
  - Claude Code authentication configured — either `ANTHROPIC_API_KEY` (Console API key) or `CLAUDE_CODE_OAUTH_TOKEN` (OAuth token from `claude setup-token`); see [authentication.md](docs/authentication.md) for which applies to your use
```

With:

```markdown
  - Claude Code CLI authenticated on the runner — see [authentication.md](docs/authentication.md)
```

### `docs/getting-started.md` Step 4

Replace the existing block (L85-115 — from "Configure Claude Code authentication on the runner. Choose one of two paths" through "verify the CLI works: `claude --version`") with:

```markdown
Authenticate the Claude Code CLI on the runner. The dispatch scripts do not prescribe a method — see Anthropic's [Claude Code authentication docs](https://code.claude.com/docs/en/authentication) for the supported options, or [authentication.md](authentication.md) for the project's summary and the Terms-of-Service pointers.

After authenticating, verify with `claude /status` on the runner. If your method uses environment variables set in the runner's `.env` file, restart the runner service so workflow jobs pick them up:

​```bash
sudo systemctl restart actions.runner.<org>-<repo>.<runner-name>.service
​```

Verify the CLI is installed:

​```bash
claude --version
​```
```

(Note: the surrounding `---` horizontal rules and the step heading itself — `## Step 4: Install Claude Code on the Runner` — are unchanged.)

### `docs/runners.md` — "Claude Code authentication" subsection

Replace L118-148 (from `### Claude Code authentication` through the last "Security notes" bullet) with:

```markdown
### Claude Code authentication

The Claude Code CLI must be authenticated on the runner. The dispatch scripts do not reference any credential environment variable — see [authentication.md](authentication.md) and Anthropic's [Claude Code authentication docs](https://code.claude.com/docs/en/authentication) for the available methods.

If you choose a method that uses environment variables, the runner's `.env` file (in the runner installation directory, not `~/.bashrc` — systemd services do not source shell profiles) is the right place to set them:

​```bash
# Example — the exact variable depends on the method you chose
chmod 600 .env
​```

After configuring authentication (by whichever method), verify with `claude /status` on the runner before the first dispatch run.

**Security notes:**

- If `.env` holds any credential, it must be `chmod 600` (readable only by the runner user).
- Every workflow job on this runner can access credentials present in `.env`.
- If you want per-workflow injection instead, store the credential as a [GitHub Actions secret](https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions) and reference it in the `env:` block of your workflow files.
- Refer to Anthropic's authentication docs for guidance on rotating or refreshing whichever credential type you chose.
```

### `docs/security.md`

**"Anthropic Authentication Model" section (L122-139).** Replace with:

```markdown
## Anthropic Authentication Model

Claude Code must be authenticated on the runner for the dispatch scripts to function. The scripts themselves are agnostic to the authentication method — the `claude -p` invocation in `scripts/lib/common.sh` does not reference any credential environment variable, and Claude Code's own authentication precedence handles the rest.

See [authentication.md](authentication.md) for the project's authentication notes and links to Anthropic's authoritative documentation (authentication methods, legal and compliance, Terms of Service, Acceptable Use Policy).

*This section describes an installation prerequisite. It is not legal advice — review Anthropic's current terms to confirm fit for your specific use.*
```

**Security Checklist lines (L154-156).** Replace the three auth-specific lines:

```markdown
- [ ] Authentication configured on the runner matches the intended use path per [authentication.md](authentication.md) — API key for team/commercial/shared-runner use; OAuth token only for individual solo-developer use
- [ ] Exactly one of `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` is set on the runner (never both — `ANTHROPIC_API_KEY` silently overrides `CLAUDE_CODE_OAUTH_TOKEN` and routes billing to the Console account)
- [ ] `claude /status` on the runner confirms the active auth method matches expectations
```

With one line:

```markdown
- [ ] Claude Code is authenticated on the runner (`claude /status` confirms the expected account) and the authenticated account is appropriate for your intended use — see [authentication.md](authentication.md)
```

### `docs/faq.md`

**"Is this setup aligned with Anthropic's Terms of Service?" Q (L29-31).** Replace the answer with:

```markdown
Whether the project's use aligns with Anthropic's Terms of Service depends on how you are using the project — your authentication choice, whether the runner serves one person or many, whether use is individual or commercial, and whether usage stays within Anthropic's "ordinary individual usage" boundaries for subscription plans. The project does not take a position on any of these: the dispatch scripts simply invoke the `claude` CLI and rely on Anthropic's authentication precedence.

Review Anthropic's authoritative pages for the applicable rules: [Claude Code Legal and Compliance](https://code.claude.com/docs/en/legal-and-compliance), [Consumer Terms of Service](https://www.anthropic.com/legal/consumer-terms), [Commercial Terms](https://www.anthropic.com/legal/commercial-terms), and the [Acceptable Use Policy](https://www.anthropic.com/legal/aup). See [authentication.md](authentication.md) for the project's notes on the installation prerequisite.
```

**"Can I use my Pro/Max subscription instead of an API key?" Q (L33-37).** Replace the answer with:

```markdown
Claude Code supports multiple authentication methods, including subscription-backed ones. Whether any specific method is appropriate for *your* use of this project is covered by Anthropic's terms, not by the project. See [authentication.md](authentication.md) and Anthropic's [Claude Code authentication docs](https://code.claude.com/docs/en/authentication).
```

**"What about costs?" Q (L49-53).** Replace the answer with:

```markdown
Costs depend on the authentication method you configured on the runner. API-key authentication is billed per token against the owning Anthropic Console account; subscription-based authentication counts against the plan's quota. The project itself adds no billing layer — whatever Claude Code charges to the account tied to the runner's credentials is whatever a corresponding interactive Claude Code session would charge.

Cost controls built into the system regardless of authentication method: the circuit breaker limits the agent to 8 bot comments per hour per issue, preventing runaway loops; timeouts kill stuck processes; and you control which issues get the `agent` label — it's opt-in per issue, not automatic.
```

### `.claude/skills/setup/SKILL.md` — Step 9d

Replace the existing Step 9d body (L229-272 — from the heading `### Step 9d: Configure credentials` through the "Verification (both branches)" paragraph, but keeping the following `**Node/Claude path** — If using nvm` paragraph unchanged) with:

```markdown
### Step 9d: Configure credentials

The Claude Code CLI needs to be authenticated on the runner. The dispatch scripts do not prescribe a method — point the user to Anthropic's [Claude Code authentication docs](https://code.claude.com/docs/en/authentication) for the available options, or [authentication.md](../../../docs/authentication.md) for the project's summary and Terms-of-Service pointers.

If the user chose a method that uses environment variables, the runner's `.env` file (in the runner installation directory, not `~/.bashrc` — systemd services do not source shell profiles) is the right place to set them. Any `.env` holding credentials must be `chmod 600`.

**Verification:** After the runner service is restarted in Step 9f, have the user run `claude /status` on the runner (as the runner user). It should report that the runner is authenticated with the expected account.
```

### `scripts/setup.sh`

Replace L337-345 (from `echo "  4. Add ANTHROPIC_API_KEY to the runner's .env file (systemd does not"` through the last line of that block — the closing blank `echo ""`) with:

```bash
echo "  4. Authenticate the Claude Code CLI on the runner (as the runner user)."
echo "     The dispatch scripts do not prescribe a method — see Anthropic's"
echo "     Claude Code authentication docs and the project's authentication.md"
echo "     for setup options and Terms-of-Service pointers:"
echo ""
echo -e "     ${CYAN}https://code.claude.com/docs/en/authentication${NC}"
echo -e "     ${CYAN}docs/authentication.md${NC}"
echo ""
echo "     After configuring, verify with: claude /status"
echo ""
```

Step 5 of the existing output (the nvm path note) is unchanged.

### `docs/claude-code-subscription-automation-guide.md`

**Delete the file.** This is a 121-line opinion piece that ranks Docker sandbox options, discusses OAuth token use patterns in CI, and restates Anthropic policy positions. All of its content either duplicates what Anthropic's own docs cover, restates the project's prior prescriptive posture, or expresses opinions about third-party tools that fall outside the project's scope. Under the new posture there is no version of this file that belongs in the project — it is pure surface area for claims about how the project recommends users handle auth.

If users want the kind of auth-and-sandbox decision guidance this file contains, they can find it in Anthropic's own docs or in community resources — those are better-maintained sources for that content than a static file in this repo.

### Prior spec and plan — supersession notes

**`docs/superpowers/specs/2026-04-17-authentication-docs-design.md`.** Add a single line at the top of the file, immediately after the `# Authentication Documentation Realignment` heading:

```markdown
> **Status — 2026-04-21:** Superseded by [`2026-04-21-auth-agnostic-posture-design.md`](2026-04-21-auth-agnostic-posture-design.md), which moves the project from informational-neutral path-documentation to full auth-agnosticism. This spec is preserved as a historical record.
```

**`docs/superpowers/plans/2026-04-17-authentication-docs-realignment.md`.** Add an analogous line at the top:

```markdown
> **Status — 2026-04-21:** This plan was executed and its work has since been superseded by the [auth-agnostic posture spec](../specs/2026-04-21-auth-agnostic-posture-design.md). Preserved as a historical record.
```

## Code and test impact

**Code:** None. Verified on 2026-04-21 by exhaustive grep across `.sh`, `.yml`, `.yaml`, `.py`, `.ts`, `.js`, `.bats`, and `.env*` files for `ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_AUTH_TOKEN`, `apiKeyHelper`, `sk-ant-api`, `sk-ant-oat`, and `setup-token`. The only hits outside documentation are the four `echo` statements in `scripts/setup.sh:337-344`, which are already in the change set above.

**Tests:** None. No behavioral change to scripts, no new tests needed. ShellCheck must still pass on the modified `scripts/setup.sh`.

**Commits:** One per file for clean history. Expected sequence:

1. `docs/authentication.md` rewrite (foundation — everything else links here)
2. `README.md` updates
3. `docs/getting-started.md` Step 4 rewrite
4. `docs/runners.md` subsection rewrite
5. `docs/security.md` section shrink + checklist collapse
6. `docs/faq.md` three-Q rewrite
7. `.claude/skills/setup/SKILL.md` Step 9d rewrite
8. `scripts/setup.sh` block rewrite (ShellCheck gate)
9. `docs/claude-code-subscription-automation-guide.md` deletion
10. Supersession notes on the 2026-04-17 spec and plan (one commit for both)

Roughly 10 commits on a dedicated branch.

## Risks and trade-offs

**Risk: onboarding friction increases.** New users following the Quick Start lose a self-contained explanation of how to authenticate Claude Code on the runner and instead have to context-switch to Anthropic's docs. Mitigation: `docs/authentication.md` remains a project-level entry point with a direct link to Anthropic's page. The project's getting-started, runners, and setup-skill docs all name `claude /status` as the verification step, which gives users an actionable checkpoint even without method-specific instructions.

**Risk: subscription-oriented users drift toward weaker ToS postures.** Without a pointer to `claude setup-token`, users may default to interactive `claude /login` on the runner. `setup-token` is Anthropic's explicitly-documented CI path; `/login` used headlessly under systemd is within "ordinary use" but lacks that explicit carve-out. Mitigation: `authentication.md` links to Anthropic's authentication page, which documents `setup-token` prominently. Users who care about the explicit carve-out will find it. The project's choice is to not editorialize on which option to pick.

**Risk: supersession of the 2026-04-17 spec creates confusion.** A future reader browsing `docs/superpowers/specs/` may see both specs and not know which reflects current practice. Mitigation: the supersession banner on the 2026-04-17 spec (and its corresponding plan) is at the top of each file, and the new spec explicitly references what it supersedes.

**Trade-off: the project's docs carry less Terms-of-Service information than before.** A user who wanted a concise summary of "which auth path for which situation" no longer finds it in the project. They will find it in Anthropic's own docs, which are the authoritative source and which stay in sync with Anthropic's policy updates. The project accepts the loss of that curated summary in exchange for not maintaining a paraphrase that can drift.

**Trade-off: deleting the subscription-automation guide removes 121 lines of community-oriented content.** Some users may have relied on its ranked Docker-sandbox recommendations or its Terms-of-Service summary. The content is outside the project's scope and is better-covered by Anthropic's own docs and by community resources. Retaining it under the new posture would undermine the reason for the posture change.

## Implementation order

When this moves to an implementation plan, the natural order is:

1. Rewrite `docs/authentication.md` (foundation — everything else links here).
2. Update `README.md`, `docs/getting-started.md`, `docs/runners.md`, `docs/security.md`, `docs/faq.md` in any order (all link to `authentication.md`).
3. Update `.claude/skills/setup/SKILL.md` Step 9d.
4. Update `scripts/setup.sh` (ShellCheck gate — must pass before commit).
5. Delete `docs/claude-code-subscription-automation-guide.md`.
6. Add supersession notes to the 2026-04-17 spec and plan.
7. End-to-end read-through: confirm internal links resolve; confirm no file still carries the prior prescriptive framing (env var names, Path A / Path B, decision matrix, silent-override warning).
8. Confirm ShellCheck on the entire `scripts/` tree still passes.

## References

- [Claude Code Authentication](https://code.claude.com/docs/en/authentication)
- [Claude Code Legal and Compliance](https://code.claude.com/docs/en/legal-and-compliance)
- [Anthropic Consumer Terms of Service](https://www.anthropic.com/legal/consumer-terms)
- [Anthropic Commercial Terms](https://www.anthropic.com/legal/commercial-terms)
- [Anthropic Acceptable Use Policy](https://www.anthropic.com/legal/aup)
- Prior spec — [`2026-04-17-authentication-docs-design.md`](2026-04-17-authentication-docs-design.md) (superseded)
- Prior plan — [`2026-04-17-authentication-docs-realignment.md`](../plans/2026-04-17-authentication-docs-realignment.md) (superseded)
