#!/bin/bash
set -euo pipefail

# Shared standalone inventory. Paths stay relative to the distribution root.
# Templates are reference assets; setup renders them into .github/workflows.
# Client instruction/skill destination mapping is a separate rollout milestone.
list_install_assets() {
    local root="$1" directory file
    for directory in scripts prompts schemas skills .claude/skills/setup/templates; do
        [ -d "$root/$directory" ] || continue
        while IFS= read -r -d '' file; do
            printf '%s\0' "${file#"$root/"}"
        done < <(find "$root/$directory" -type f -print0 | sort -z)
    done
    if [ -f "$root/labels.txt" ]; then
        printf '%s\0' labels.txt
    fi
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
