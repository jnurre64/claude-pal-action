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
