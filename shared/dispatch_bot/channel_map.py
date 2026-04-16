"""Per-repo channel routing map parsing and lookup.

Used by Discord and Slack bots, and the notify.sh webhook backends,
to route notifications to different channels based on source repo.
"""

from __future__ import annotations


def parse_channel_map(env_value: str) -> dict[str, str]:
    """Parse 'owner/repo=channel,owner/repo=channel' into a dict.

    Empty values are preserved (semantically: explicit mute).
    Malformed entries (no '=', empty key) are skipped.
    Whitespace around entries, keys, and values is trimmed.
    Splits on the first '=' only so values may contain '=' (e.g., URLs).
    """
    result: dict[str, str] = {}
    if not env_value:
        return result
    for entry in env_value.split(","):
        entry = entry.strip()
        if not entry or "=" not in entry:
            continue
        key, _, val = entry.partition("=")
        key = key.strip()
        val = val.strip()
        if not key:
            continue
        result[key] = val
    return result


def resolve_channel(
    repo: str, channel_map: dict[str, str], default: str
) -> str | None:
    """Resolve channel for repo.

    Returns:
        - mapped value (may be empty string = explicit mute; caller must
          treat the empty string as "do not send")
        - default if repo not in map and default is non-empty
        - None if repo not in map and default is empty
    """
    if repo in channel_map:
        return channel_map[repo]
    if default:
        return default
    return None
