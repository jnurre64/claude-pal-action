# Issue 116: simplicity review and standard authentication decision

**Current scope override:** The operator has explicitly selected compatibility
with the existing working Claude integration. Absolute instruction prevention and
hostile-process containment are deferred hardening, not Codex enablement gates.
See [the compatibility baseline](2026-09-07-codex-worker-engine-claude-parity.md).
Earlier stricter release requirements below are historical and superseded.

Current implementation status is in the [phase integration record](2026-09-07-codex-worker-engine-phase-integration.md).
The decisions here still apply; its earlier inventory predates the native adapter.

Operator clarification on 2026-09-07: use standard authentication only. A custom
relay is out of scope unless the operator explicitly requests it. This decision
supersedes earlier evidence/handoff language requiring a separate authentication
transport or treating a relay as an automatic fallback.

## Assessment

Some work on this branch is necessarily project-specific integration, and some
recent work is substantial custom experimentation. It would be inaccurate to
describe everything as stock Codex behavior or a minimal implementation.

| Work | Current status | Decision |
| --- | --- | --- |
| Engine/model resolution, normalized results and semantic failure handling | Committed repository runtime changes; Claude remains default and Codex is disabled | Keep: directly supports #116 and existing review/dispatch contracts |
| Shared installer inventory and recoverable updates | Committed repository runtime changes | Keep: addresses #112 dependency/asset delivery |
| Repository instruction files and shared skill links | Committed additive client guidance | Keep: retains Claude entry points |
| Scripted response services, hostile fixtures and result archives | Offline test infrastructure under `docs/superpowers/plans/evidence/` | Preserve evidence; these are not model-serving or authentication infrastructure |
| Custom outer Bubblewrap launcher/profile | Historical experiment, not dispatcher/installer code | Remove from the production proposal; it breaks native image helpers |
| Edit broker, bounded protocol and MCP shim | Historical experiment, not dispatcher/installer code | Retire from the production proposal; use native editing |
| Source exporter and candidate manifest validator | Historical experiment, not a production import path | Retire from the production proposal; reuse existing worktrees |
| Authentication relay/custom refresh logic | Neither implemented nor deployed | Out of scope unless explicitly requested by the operator |

Historical audit at the simplicity decision (before native adapter work): the working-tree changes were plans/evidence; no installed runtime files
changed in the recent broker continuations. Searches found no production or
installer references to the broker, shim or snapshot modules. The installer
inventory excludes this evidence directory. Codex execution remains refused in
both `scripts/lib/agent-config.sh` and `scripts/lib/agent.sh`. Earlier committed
runtime work is real project-specific code; it should not be described as an
unchanged runtime or as stock Codex implementation.

The earlier recorded host adjustment was the operator-approved standard Ubuntu
Bubblewrap AppArmor profile. No custom authentication service or personal login
change was made during the experiments.

## Standard authentication only

Use Codex's supported login/API-key mechanisms and credential storage. Preserve
the operator's existing login and configured standard store/location. Let Codex
own credential loading and token refresh. Do not introduce a separate token
store, custom OAuth flow, custom refresh implementation, model proxy or relay.

The trusted Codex process may access its normal credentials. Verify that
model-accessible tools and repository build/test processes cannot read the store,
inherit credential environment variables/descriptors, or inspect the authenticated
process. Keep GitHub publishing credentials with the existing harness. Standard
authentication does not require exposing the entire personal configuration tree to
project code; apply the narrowest supported configuration/process controls.

The exact process/mount arrangement still requires executable verification. Do
not assume that the previous outer sandbox, synthetic CODEX_HOME or broker
architecture must remain unchanged to accommodate authentication. If standard
mechanisms cannot meet a required boundary, report the specific gap and keep
Codex disabled. Do not build or propose a relay as the default next step; the
operator will raise that scope if desired.

Standard behavior reference, checked in the preceding discussion:
[Codex authentication](https://learn.chatgpt.com/docs/auth).

## Updated scope: ordinary engine compatibility

The operator subsequently requested removal of unnecessary nonstandard complexity,
research support, and seamless Claude/Codex and mixed-phase operation. The default
production proposal is now a thin native CLI adapter. Do not continue developing
the custom broker, MCP shim, source exporter/importer or outer sandbox. Keep their
source and results as historical, reproducible evidence only; none is installed or
referenced by runtime code. This supersedes earlier instructions to finish those
experiments as prerequisites for the adapter.

Keep the existing worktree, configuration, instruction/skill discovery, dispatch,
artifact, test and review lifecycle. Interactive client choice is independent of
worker engine choice. Retain the already implemented dispatch default and per-phase
engine/model overrides, including Claude implementation with fresh Codex review.
Existing Claude projects must not require Codex installation or authentication for
Claude-only events. Do not rename existing state/lock locations or rewrite project
Claude configuration to enable Codex.

### Separate engine capabilities from optional stronger requirements

| Concern | Minimal integration contract |
| --- | --- |
| Authentication | Standard engine authentication only; no relay, custom refresh or copied token store |
| Human approval and reviews | Preserve plan approval, fresh adversarial sessions, test gates and semantic outcomes |
| Editing | Native editing in the existing implementation worktree; native read-only policy for advisory reviews, with findings captured by the harness |
| Research | Research is a supported use case; a network-disabled probe is not a product-wide prohibition. Use native research/network controls and preserve existing project settings; add phase overrides only for a demonstrated need |
| Instruction files | Workers must not modify AGENTS.md or CLAUDE.md; submit suggestions to the orchestrator, which may apply them or request review. Instructions and post-run diff checks alone do not prove prevention |
| Commands and integrations | Use native controls; do not translate Claude tool strings into purportedly equivalent Codex permissions or disable all project integrations as an incidental adapter effect |
| Explicit unsupported restrictions | Report the exact unsupported setting; never silently drop a requested restriction or introduce a custom broker to emulate it |
| Credentials | Avoid unnecessary secret inheritance and secret logging. Native authentication access does not establish that hostile same-user processes cannot reach credentials; do not claim that stronger isolation |
| Operational correctness | Validate results/schemas, failures, timeout/cancellation, recovery and mixed-engine phase routing before enablement |

The hardlink/replacement observations are real failures of the proposed immutable
instruction-file policy. They are not evidence that Codex cannot support a normal
reviewed development workflow. Likewise, command allowlists, shell network access,
web research tools and MCP access are different capabilities; a single universal
permission switch would obscure meaningful differences between engines.

### Confirmed operator answers

Both scope questions are settled. Workers must not edit `AGENTS.md` or `CLAUDE.md`
(including nested copies and case variants such as `Agents.md`). They may return
suggested changes as findings for the orchestrator. The orchestrator can apply the
updates within its authorized scope or request review; a worker suggestion is not
an automatic instruction to apply it. Keep suggested updates outside the protected
files, using existing phase artifacts where possible rather than a new service.

This is a prevention requirement, not merely a request to detect/revert changes
after execution. Test direct edits, shell writes, deletion/rename/replacement,
hardlink and symlink aliases, and newly introduced instruction files. The prior
native-profile failures remain relevant to this requirement. First assess supported
native controls in both engines; do not promise equivalent enforcement without
evidence. Do not silently broaden this decision to make every `.claude/`, `.agents/`
or `.codex/` file immutable. Preserve applicable existing configuration protections.

Research access is accepted using native engine controls and existing project
settings. There is no need for a blanket research ban or a new per-phase permissions
system initially. Treat retrieved material as untrusted task data and preserve
existing secret handling and publishing gates. Research authorization is not blanket
permission for arbitrary shell networking or credential access.

If required instruction protection cannot be enforced with supported native
controls, report the precise limitation and the smallest additional option for
review. Keep Codex disabled where the contract is unmet; do not restart the retired
broker/outer-sandbox design or weaken Claude policy silently. Audit Claude's existing
behavior too: preserving its defaults is not evidence that they enforce this new
cross-engine requirement. Report any compatibility conflict before changing those
defaults. These answers supersede the earlier suggestion that reviewed worker edits
to instruction files would be acceptable.

### Next implementation

With those choices settled, revise the capability/preflight contract around supported
native settings, then implement CLI invocation and JSONL normalization in the
existing adapter interface. Verify Claude-only compatibility, all-Codex routing,
Claude implementation/Codex review, and the reverse. Preserve user/project
configuration deliberately; do not invent universal MCP/hook suppression as a
release requirement. Document engine differences that affect existing project
settings before migration. Codex remains disabled until the selected native
contract and adapter tests pass; historical broker experiments are not release
gates for that contract.

This scope update changes documentation only. Runtime checks must run when the
adapter changes; earlier BATS results do not validate an unimplemented adapter.
