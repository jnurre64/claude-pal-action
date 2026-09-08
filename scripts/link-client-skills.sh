#!/bin/bash
# Connect a consumer's interactive clients to an existing runtime installation.
# Usage: link-client-skills.sh <project-directory> <runtime-directory>
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091  # Runtime sibling path.
source "$SCRIPT_DIR/lib/install-assets.sh"

if [ "$#" -ne 2 ]; then
    echo 'Usage: link-client-skills.sh <project-directory> <runtime-directory>' >&2
    exit 2
fi
project=$(cd "$1" && pwd -P)
runtime=$(cd "$2" && pwd -P)
if [ ! -f "$runtime/scripts/sandbox-pal-dispatch.sh" ]; then
    echo 'Runtime directory must contain scripts/sandbox-pal-dispatch.sh' >&2
    exit 1
fi
for skill in sp-work sp-status sp-revise sp-post-merge; do
    if [ ! -f "$runtime/.claude/skills/$skill/SKILL.md" ]; then
        echo "Runtime is missing shared skill $skill; update its assets first." >&2
        exit 1
    fi
done

# Skills locate the dispatcher through this conventional path. Link the whole
# runtime so its sibling libraries/schemas and existing lock/config paths survive.
destination="$project/.sandbox-pal-dispatch"
if [ -e "$destination" ] || [ -L "$destination" ]; then
    if [ ! -d "$destination" ] || [ "$(cd "$destination" && pwd -P)" != "$runtime" ]; then
        echo "Preserved $destination; it already names a different installation." >&2
        exit 1
    fi
else
    relative=$(python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "$runtime" "$project")
    ln -s "$relative" "$destination"
fi
link_install_client_skills "$destination"
case "$runtime/" in
    "$project/"*) echo 'Runtime and client discovery links are inside the project; review and commit them together.' ;;
    *) echo 'Runtime is outside this project. Keep the .sandbox-pal-dispatch link local; recreate it on other machines.' ;;
esac
echo 'Reference mode: set AGENT_CONFIG to the intended project config.env before invoking a dispatch skill.'
echo 'Use the existing runtime updater for asset updates; rerun this command to repair missing discovery links.'
