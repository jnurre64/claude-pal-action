# Actual Codex CLI / native adapter integration without inference

Checked 2026-09-07 with installed Codex CLI 0.153.4. All five scored cases pass
through the production shell preflight, frozen phase configuration, Codex adapter,
Python transport and result normalizer. The latest run uses production engine
selection without a gate override and verifies closed/required native object
schemas. The worker executable is the actual CLI.
The model service is a canned loopback HTTP/SSE fixture; no inference is performed.

## Results

| Case | Actual adapter result |
| --- | --- |
| Structured post-implementation review | Success; schema valid; usage preserved |
| Triage plan | Success; schema transmitted to CLI with `plan_markdown`; harness publishes actual multiline Markdown and removes internal field from structured result |
| Schema-invalid final JSON | Semantic failure with `error.kind=schema` |
| HTTP 429 quota response | Semantic failure with `error.kind=quota` |
| Stalled response | `timed_out`; terminal output cannot advance the phase |

Each case reached the local service once. Every adapter invocation returned one
JSON envelope, including failures whose shell exit remained zero. All source
sentinels remained unchanged. Each capture directory retained only `result.json`
and `stderr.log`; raw event, schema and final-message captures were removed.
The checks require these outcomes, rather than treating any returned JSON as a pass.
Exact reports are in [results.json](results.json).

## Fixture and reproduction

[probe.py](probe.py) creates disposable `/tmp` workspaces, Git repositories,
synthetic homes and Codex configuration stores. A custom provider points solely
at a loopback server returning scripted Responses events. A synthetic API-key
value satisfies the adapter's local credential-presence check; the provider
requires no real authentication. The fixture does not open or copy personal
credential stores. Request reports retain model/schema metadata, not headers.

The shell fixture supplies the dispatcher's schema/logging variables, loads the
real defaults and adapters, and selects `AGENT_ENGINE=codex` with ordinary
native-policy defaults. It does not substitute an engine gate. It retains real
Claude tool defaults. It invokes fresh TRIAGE or POST_IMPL_REVIEW phases directly,
not GitHub handlers. There are no GitHub mutations, commits, pushes, real model
requests or host-policy changes.

Run as the ordinary user in host context, with the existing worker Python
dependencies and actual Codex CLI on PATH:

```bash
PATH="/tmp/sandbox-pal-worker-venv/bin:$PATH" python3 probe.py
```

The earlier fixture attempts stopped before CLI invocation because the test
environment lost its virtualenv or omitted the dispatcher's schema directory.
Those fixture setup errors were corrected; they were not runtime adapter defects.
The latest run exits 0 with all five explicit outcome checks passing. The initial
pre-parity report is preserved as [initial-results.json](initial-results.json).
See the [compatibility baseline record](../../2026-09-07-codex-worker-engine-claude-parity.md)
for the accompanying runtime changes and full regression validation. Changes remain local and uncommitted.

## What this does not establish

The canned service accepts the CLI's schema request; a real provider's acceptance
of the schemas and model-generated compliance remain unverified. Both schemas
are transmitted with `strict: true`; successful local normalization must not be
presented as provider-side strict-schema acceptance. Authentication presence is
not validation of a real login, quota or credential isolation.

No tool calls, native source edits, research requests, mixed-engine author/reviewer
sessions or full GitHub handler lifecycle run in this fixture. Web search is
disabled only in the synthetic fixture configuration to avoid external requests;
this is not a change to production research behavior. Timeout checks cover a
stalled actual CLI, not hostile descendants that deliberately leave their process
group. Absolute instruction-file prevention and hostile process containment are deferred
hardening, not additional enablement requirements over existing Claude behavior.

Next acceptance work needs actual tool-path/operational checks and real-provider
schema validation, followed by the isolated all-Codex and hybrid pipelines. Paid
or GitHub-mutating acceptance still requires a time/spend ceiling and verified
intended PAT access to `Frightful-Games/recipe-manager-demo`. The successful no-model check does not
establish paid production acceptance or the deferred hardening guarantees.
