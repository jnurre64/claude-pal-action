# Self-Hosted Runner Setup

## Why Self-Hosted Runners

Claude Agent Dispatch requires self-hosted GitHub Actions runners because:

- **Claude Code CLI**: The `claude` CLI must be installed on the runner. GitHub-hosted runners do not have it pre-installed, and installing it fresh on every run would add latency and complexity.
- **Persistent state**: The dispatch script maintains per-runner repository clones and git worktrees that persist across workflow runs. This avoids re-cloning the entire repository for every agent invocation and allows the plan phase to leave a worktree for the implement phase to reuse.
- **Project-specific tooling**: Your project may require build tools, test frameworks, or runtime environments that are impractical to install on every run.
- **Performance**: Self-hosted runners avoid the startup overhead of provisioning a fresh container for each job.

## Prerequisites

The runner machine needs the following installed:

| Tool | Purpose | Install |
|------|---------|---------|
| **Linux** (recommended) | Host OS | Ubuntu 22.04+ or similar |
| **Node.js** (18+) | Required by Claude Code | Via [nvm](https://github.com/nvm-sh/nvm) or system package |
| **Claude Code** | The AI agent CLI | `npm install -g @anthropic-ai/claude-code` |
| **gh** | GitHub CLI for API operations | [cli.github.com](https://cli.github.com/) |
| **git** | Version control | System package |
| **jq** | JSON processing in shell scripts | System package |
| **curl** | Downloading attachments | System package |

Verify the tools are available:

```bash
node --version       # v18+ required
claude --version     # Claude Code CLI
gh --version         # GitHub CLI
git --version
jq --version
```

The runner user must have `ANTHROPIC_API_KEY` (or equivalent) set in their environment for Claude Code to authenticate.

## Installing a GitHub Actions Runner

Full instructions are in the [GitHub docs](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/adding-self-hosted-runners).

Summary for Linux:

```bash
# Create a directory for the runner
mkdir -p ~/actions-runner-agent && cd ~/actions-runner-agent

# Download the latest runner (check GitHub for current version)
curl -o actions-runner-linux-x64.tar.gz -L \
  https://github.com/actions/runner/releases/latest/download/actions-runner-linux-x64-2.322.0.tar.gz
tar xzf actions-runner-linux-x64.tar.gz

# Get a registration token from your org or repo settings:
#   Org:  Settings -> Actions -> Runners -> New self-hosted runner
#   Repo: Settings -> Actions -> Runners -> New self-hosted runner

# Configure the runner
./config.sh \
  --url https://github.com/your-org \
  --token YOUR_REGISTRATION_TOKEN \
  --name agent-runner-1 \
  --labels agent \
  --work _work

# Install and start as a systemd service
sudo ./svc.sh install $(whoami)
sudo ./svc.sh start
```

Registration tokens expire in 1 hour. Generate them immediately before configuring.

## Installing Claude Code on the Runner

Install Claude Code globally so it is available to the runner process:

```bash
# If using nvm
nvm install 22
nvm use 22
npm install -g @anthropic-ai/claude-code

# Verify
claude --version
```

Make sure the runner's shell profile (`.bashrc` or `.profile`) sources nvm so that `claude` is in PATH when GitHub Actions runs the dispatch script. The dispatch script includes nvm sourcing as a fallback:

```bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
```

Set the API key in the runner user's environment:

```bash
# Add to ~/.bashrc or ~/.profile
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Runner Labels

Labels control which runners pick up which workflow jobs. The reusable workflows accept a `runner_labels` input (default: `["self-hosted", "agent"]`).

Recommended label scheme:

| Label | Purpose | Used by |
|-------|---------|---------|
| `self-hosted` | Required by GitHub for all self-hosted runners | All workflows |
| `agent` | Marks runners that handle agent dispatch (triage, implement, reply, review) | `dispatch-triage.yml`, `dispatch-implement.yml`, `dispatch-reply.yml`, `dispatch-review.yml` |
| `cleanup` | Marks runners that handle periodic cleanup | `cleanup.yml` |
| `ci` | Marks runners that handle CI test suites | Your CI workflow |

A single runner can have multiple labels. For example, a flex runner with labels `agent`, `cleanup`, and `ci` can pick up any job type when other runners are busy.

Your caller workflows specify which labels to require:

```yaml
jobs:
  triage:
    uses: your-org/claude-agent-dispatch/.github/workflows/dispatch-triage.yml@main
    with:
      bot_user: your-bot
      runner_labels: '["self-hosted", "agent"]'
    secrets:
      agent_pat: ${{ secrets.AGENT_PAT }}
```

### Changing Runner Labels

The easiest way is via the GitHub UI: **Settings -> Actions -> Runners** -> click the runner -> edit labels.

Alternatively, remove and reconfigure:

```bash
cd ~/actions-runner-agent
./config.sh remove
# Get a fresh registration token
./config.sh --url https://github.com/your-org --token NEW_TOKEN \
  --name agent-runner-1 --labels agent,cleanup --work _work
sudo ./svc.sh install $(whoami)
sudo ./svc.sh start
```

## Per-Runner Isolation

When multiple runners handle agent workloads on the same machine, each runner needs its own repository clone and worktree directory to prevent git lock races.

The dispatch script uses the `RUNNER_NAME` environment variable (set automatically by GitHub Actions) to create isolated paths:

```
~/repos/
  <RUNNER_NAME>/
    your-repo/                     <-- this runner's clone (auto-created on first use)

~/.claude/worktrees/
  <RUNNER_NAME>/
    your-repo-issue-42/            <-- per-issue worktree
    your-repo-issue-43/            <-- no conflicts between concurrent issues
```

For example, with two runners named `AGENT-1` and `AGENT-2`:

```
~/repos/
  AGENT-1/your-repo/              <-- AGENT-1's clone
  AGENT-2/your-repo/              <-- AGENT-2's clone

~/.claude/worktrees/
  AGENT-1/your-repo-issue-42/     <-- AGENT-1 working on issue 42
  AGENT-2/your-repo-issue-43/     <-- AGENT-2 working on issue 43
```

The dispatch script creates these directories automatically. You do not need to pre-create them unless you want to pre-clone the repository for faster first runs:

```bash
mkdir -p ~/repos/AGENT-1
git clone https://github.com/your-org/your-repo.git ~/repos/AGENT-1/your-repo
```

## Multiple Runners on One Machine

For handling concurrent issues, register multiple runners on the same machine. Each runner is an independent process with its own directory:

```bash
# Runner 1: primary agent runner
mkdir -p ~/actions-runner-agent-1
cd ~/actions-runner-agent-1
# ... download, extract, configure with --name AGENT-1 --labels agent ...
sudo ./svc.sh install $(whoami)
sudo ./svc.sh start

# Runner 2: overflow agent runner
mkdir -p ~/actions-runner-agent-2
cd ~/actions-runner-agent-2
# ... download, extract, configure with --name AGENT-2 --labels agent ...
sudo ./svc.sh install $(whoami)
sudo ./svc.sh start

# Runner 3: dedicated to CI (no agent label)
mkdir -p ~/actions-runner-ci
cd ~/actions-runner-ci
# ... download, extract, configure with --name CI-1 --labels ci ...
sudo ./svc.sh install $(whoami)
sudo ./svc.sh start
```

All runners share the same OS user, home directory, and installed tools (Claude Code, gh, git). Per-runner isolation via `RUNNER_NAME` prevents git conflicts.

**Resource considerations**: Agent work is primarily I/O-bound (API calls to Claude and GitHub). Multiple agent runners on the same machine rarely cause resource contention. CI test suites may be CPU-bound -- if your tests are heavy, consider dedicating a separate machine or runner for CI.

## Monitoring Runner Health

### From the GitHub UI

Navigate to your org or repo **Settings -> Actions -> Runners**. Each runner shows its status (Idle, Active, Offline).

### From the Command Line

Check systemd service status:

```bash
# Replace with your actual service name
# Service names follow the pattern: actions.runner.<org-or-repo>.<runner-name>.service
sudo systemctl status actions.runner.your-org.AGENT-1.service
```

View runner logs:

```bash
journalctl -u actions.runner.your-org.AGENT-1.service -f
```

Check agent dispatch logs:

```bash
tail -f ~/.claude/agent-logs/agent-dispatch.log
```

List recent Claude stderr logs (non-empty files indicate errors):

```bash
ls -lt ~/.claude/agent-logs/claude-stderr-*.log | head -10
```

### Quick Health Check Script

```bash
#!/bin/bash
# Check all runner services on this machine
for svc in $(systemctl list-units --type=service --state=running \
  | grep actions.runner | awk '{print $1}'); do
  status=$(systemctl is-active "$svc")
  echo "$svc: $status"
done

# Check disk space (worktrees accumulate)
echo ""
echo "Disk usage:"
du -sh ~/repos/ ~/.claude/worktrees/ ~/.claude/agent-logs/ 2>/dev/null
```

## Systemd Service Setup

The GitHub Actions runner includes built-in systemd support. After configuring a runner:

```bash
# Install the service (runs as the specified user)
sudo ./svc.sh install $(whoami)

# Start the service
sudo ./svc.sh start

# Check status
sudo ./svc.sh status

# Stop the service
sudo ./svc.sh stop

# Uninstall the service
sudo ./svc.sh uninstall
```

The service starts automatically on boot. The runner auto-updates itself when GitHub releases new runner versions.

For full details on runner service management, see the [GitHub documentation on configuring the self-hosted runner application as a service](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/configuring-the-self-hosted-runner-application-as-a-service).

### Notes

- **Same OS user**: All runners on a machine typically share a single OS user. This is fine for single-developer or small-team setups. For stronger isolation between runners, create separate OS users.
- **Shared filesystem**: Runners share the home directory. The dispatch script, Claude Code, `gh`, and `git` are installed once. Only the per-runner repo clones and worktrees are isolated.
- **Runner auto-updates**: GitHub pushes runner updates automatically. You do not need to manage runner versions.
- **Removing a runner**: Stop the service, uninstall it, remove the runner from GitHub UI (or `./config.sh remove`), then delete the directory and its isolation directories under `~/repos/<RUNNER_NAME>` and `~/.claude/worktrees/<RUNNER_NAME>`.
