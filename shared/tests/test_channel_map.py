from dispatch_bot.channel_map import parse_channel_map, resolve_channel


class TestParseChannelMap:
    def test_empty_string_returns_empty_dict(self):
        assert parse_channel_map("") == {}

    def test_single_entry(self):
        assert parse_channel_map("owner/repo=123") == {"owner/repo": "123"}

    def test_multi_entry(self):
        result = parse_channel_map("a/b=1,c/d=2,e/f=3")
        assert result == {"a/b": "1", "c/d": "2", "e/f": "3"}

    def test_whitespace_trimmed_around_entries(self):
        assert parse_channel_map(" a/b = 1 , c/d = 2 ") == {"a/b": "1", "c/d": "2"}

    def test_preserves_empty_value_as_mute(self):
        assert parse_channel_map("muted/repo=") == {"muted/repo": ""}

    def test_skips_malformed_no_equals(self):
        assert parse_channel_map("bad_entry,good/repo=1") == {"good/repo": "1"}

    def test_skips_empty_key(self):
        assert parse_channel_map("=123,good/repo=1") == {"good/repo": "1"}

    def test_skips_leading_and_trailing_commas(self):
        assert parse_channel_map(",,good/repo=1,,") == {"good/repo": "1"}

    def test_splits_on_first_equals_only(self):
        # Future-proofs for URL-like values containing '='
        result = parse_channel_map("org/repo=https://hook?a=b&c=d")
        assert result == {"org/repo": "https://hook?a=b&c=d"}

    def test_trims_whitespace_around_key_and_value(self):
        assert parse_channel_map("  a/b  =  123  ") == {"a/b": "123"}


class TestResolveChannel:
    def test_returns_mapped_value_when_found(self):
        m = {"owner/repo": "123"}
        assert resolve_channel("owner/repo", m, "fallback") == "123"

    def test_returns_empty_string_for_explicit_mute(self):
        # Caller distinguishes mute (empty string) from no-mapping (None)
        m = {"owner/repo": ""}
        assert resolve_channel("owner/repo", m, "fallback") == ""

    def test_falls_back_to_default_when_repo_not_in_map(self):
        m = {"other/repo": "123"}
        assert resolve_channel("owner/repo", m, "fallback") == "fallback"

    def test_returns_none_when_no_mapping_and_no_default(self):
        m = {"other/repo": "123"}
        assert resolve_channel("owner/repo", m, "") is None

    def test_returns_none_when_empty_map_and_empty_default(self):
        assert resolve_channel("owner/repo", {}, "") is None

    def test_exact_match_only_no_prefix_matching(self):
        m = {"owner/repo": "123"}
        assert resolve_channel("owner/repo-fork", m, "fallback") == "fallback"
