# Issue 116: use working Claude behavior as the compatibility baseline

## Operator direction and resulting behavior

The operator explicitly instructed us to match the existing working Claude
integration and preserve its behavior. Absolute prevention of every instruction
file mutation and containment of deliberately escaped descendants are deferred
hardening. They are not requirements the Claude baseline enforces and no longer
block Codex selection. The retired broker, custom outer sandbox and AppArmor work
remain out of scope. Do not ask to reopen those decisions.

Claude remains the default engine. `AGENT_ENGINE=codex` and existing phase
overrides now invoke the production Codex adapter without a special release gate.
Native Codex policy is the default for Codex selection; a second migration flag is
not required. The earlier optional `AGENT_CODEX_USE_NATIVE_POLICY=false` still
requests strict rejection of legacy Claude controls instead of scoping them to
Claude. Unsupported dollar caps and phase permission modes still produce concrete
configuration errors; the adapter does not falsely claim to enforce those controls.

The committed Claude adapter and defaults are byte-for-byte unchanged. The shared
phase schema files also remain unchanged. Existing tool settings, standard login,
human plan approval, fresh reviews, test/retry gates, locks, branch recovery and
semantic success checks are retained. No existing project is switched to Codex.

## Concrete Codex schema fix

The previous adapter passed Claude's schemas directly to Codex's strict output
API. The API requires closed objects and every declared property to be required;
the shared schemas did not provide that shape. The Codex adapter now constructs
a separate wire copy with `additionalProperties=false` and declared properties
required, recursively including nested objects and array items. It tells the
worker to supply empty values for unused fields where the schema permits them.
The original phase schema still validates returned results. This does not edit
Claude's schemas or require Claude users to migrate them.

Custom schemas with unsupported composition, arbitrary object-key schemas or
undeclared required fields fail preflight. The adapter does not pretend to support
every JSON Schema feature. Reference:
[OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

## Validation

The 42-test focused engine/phase/transport suite passes after removing test-only
gate substitutions. Added two `REGRESSION v1.2.0:` cases for strict wire schema
compatibility across all shipped phase schemas and pre-launch rejection of an
unsupported schema. All **527 BATS tests** pass; log:
`/tmp/codex-claude-parity-full.log`. Prerequisites, ShellCheck, Python syntax,
current handoff links and `git diff --check` pass. The existing BW01 warning at
`tests/test_defaults.bats:13` remains; that test passes.

All five [actual-CLI no-model checks](evidence/2026-09-07-codex-cli-integration/README.md)
pass without substituting `agent_engine_enabled` or setting the native-policy flag.
The fixture additionally rejects malformed strict object schemas, checking the
wire fix. Review, multiline triage publication, invalid output, quota and timeout
retain their expected outcomes. Both hybrid directions retain mock coverage.

This is local implementation/compatibility validation. It does not claim a paid
provider or complete GitHub pipeline has run. Those acceptance checks still need
the previously unset time/spend ceiling; they are not a reason to restart the
deferred security project. No paid worker, production configuration, authentication,
host policy, GitHub mutation, commit or push was performed. All edits remain local.
