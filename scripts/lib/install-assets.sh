#!/bin/bash
set -euo pipefail

# Shared standalone inventory. Paths stay relative to the distribution root.
# Templates are reference assets; setup renders them into .github/workflows.
# Only shared orchestration skills belong in the client-facing inventory.
list_install_assets() {
    local root="$1" directory file
    for directory in scripts prompts schemas skills .claude/skills/setup/templates \
        .claude/skills/sp-work .claude/skills/sp-status \
        .claude/skills/sp-revise .claude/skills/sp-post-merge; do
        [ -d "$root/$directory" ] || continue
        while IFS= read -r -d '' file; do
            printf '%s\0' "${file#"$root/"}"
        done < <(find "$root/$directory" -type f -print0 | sort -z)
    done
    if [ -f "$root/agent-profiles.example.json" ]; then
        printf '%s\0' agent-profiles.example.json
    fi
    if [ -f "$root/labels.txt" ]; then
        printf '%s\0' labels.txt
    fi
}

# Expose installed, checksummed sources to both clients. Never copy checkout
# symlinks or overwrite a project's own skill (including dangling symlinks).
# Nonstandard install locations need explicit client setup: shared skill text
# locates the dispatcher at .sandbox-pal-dispatch/scripts/.
link_install_client_skills() {
    local install="${1%/}" project client skill destination target parent
    [ "$(basename "$install")" = .sandbox-pal-dispatch ] || return 0
    project=$(dirname "$install")
    for client in .claude .agents; do
        for parent in "$project/$client" "$project/$client/skills"; do
            if [ -L "$parent" ] || { [ -e "$parent" ] && [ ! -d "$parent" ]; }; then
                echo "Preserved $parent; configure shared skill discovery manually."
                continue 2
            fi
        done
        for skill in sp-work sp-status sp-revise sp-post-merge; do
            [ -f "$install/.claude/skills/$skill/SKILL.md" ] || continue
            destination="$project/$client/skills/$skill"
            target="../../.sandbox-pal-dispatch/.claude/skills/$skill"
            if [ -L "$destination" ] && [ "$(readlink "$destination")" = "$target" ]; then
                continue
            fi
            if [ -e "$destination" ] || [ -L "$destination" ]; then
                echo "Preserved $destination; installed shared skill is at $install/.claude/skills/$skill."
                continue
            fi
            mkdir -p "$project/$client/skills"
            ln -s "$target" "$destination"
        done
    done
}

# Replace an asset by rename: interruption cannot truncate an existing file,
# including update.sh when an installed updater replaces itself.
copy_install_asset() {
    local source="$1" destination="$2" temporary
    mkdir -p "$(dirname "$destination")"
    temporary=$(mktemp "$(dirname "$destination")/.asset-XXXXXX")
    if cp -p "$source" "$temporary" && mv -f "$temporary" "$destination"; then
        return 0
    fi
    rm -f "$temporary"
    return 1
}
