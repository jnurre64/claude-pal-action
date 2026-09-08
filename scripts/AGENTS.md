# Scripts

Read `CLAUDE.md` in this directory for script conventions and configuration
precedence. Verify the current sourcing chain and event handlers in
`sandbox-pal-dispatch.sh`; they have expanded beyond the original four handlers.

Run the root ShellCheck and BATS commands for runtime changes. Changes to
installation assets must cover both `setup.sh` and `update.sh`, including
standalone installations and checksum tracking.
