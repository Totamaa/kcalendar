# Test suite for EsportAPIService
# Framework: pytest (with unittest.mock for patching)
import types
from datetime import timedelta
from unittest.mock import patch, MagicMock

import pytest

try:
    # Prefer Box if available in project (used by the implementation)
    from box import Box
except (ImportError, ModuleNotFoundError):
    # Minimal fallback to mimic attribute access if box is unavailable at test discovery time.
    class Box(dict):
        def __getattr__(self, item):
            val = self[item]
            if isinstance(val, dict) and not isinstance(val, Box):
                return Box(val)
            if isinstance(val, list):
                return [Box(x) if isinstance(x, dict) else x for x in val]
            return val

        def __setattr__(self, key, value):
            self[key] = value


# Attempt to import service from likely module paths.
# If your project uses a different path, adjust the import below.
_SERVICE_IMPORT_ERRORS = []
_EsportAPIService = None
for _mod in [
    "backend.services",             # common
    "services.backend",             # alternate
    "app.services.backend",         # fastapi-styled apps
    "src.services.backend",         # src layout
    "services.esport_api_service",  # explicit module
    "esports.services.backend",     # domain-oriented
]:
    try:
        _module = __import__(_mod, fromlist=["EsportAPIService"])
        _EsportAPIService = getattr(_module, "EsportAPIService", None)
        if _EsportAPIService:
            break
    except (ImportError, ModuleNotFoundError, AttributeError) as e:
        _SERVICE_IMPORT_ERRORS.append(( _mod, repr(e) ))

if _EsportAPIService is None:
    pytest.skip(f"Could not locate EsportAPIService import. Tried: { _SERVICE_IMPORT_ERRORS }", allow_module_level=True)

EsportAPIService = _EsportAPIService


@pytest.fixture
def fake_settings():
    class S:
        BACK_PANDA_BASE_URL = "https://api.example.com"
        BACK_PANDA_API_KEY = "test-api-key"
    return S()


@pytest.fixture
def patched_env(monkeypatch, fake_settings):
    # Patch get_settings to avoid reading real env
    monkeypatch.setenv("PYTHONWARNINGS", "ignore")  # avoid noisy warnings
    def _get_settings():
        return fake_settings
    # Resolve module where service actually lives to patch consistently
    mod = EsportAPIService.__module__
    monkeypatch.setattr(f"{mod}.get_settings", _get_settings, raising=True)

    # Stub LoggerManager with no-op info/error
    class _Logger:
        def __init__(self): pass
        def info(self, *a, **k): pass
        def error(self, *a, **k): pass
    monkeypatch.setattr(f"{mod}.LoggerManager", _Logger, raising=True)
    return mod


def make_stream(main=True, language="fr", raw_url="http://stream"):
    return Box({"main": main, "language": language, "raw_url": raw_url})


def make_opponent(acronym, name, location="EU"):
    return Box({"opponent": {"acronym": acronym, "name": name, "location": location}})


def make_match_base(**overrides):
    base = {
        "league_id": 10,
        "tournament_id": 20,
        "serie_id": 30,
        "id": 40,
        "tournament": {"name": "Spring Split", "slug": "spring-split", "tier": "A"},
        "videogame": {"name": "League of Legends", "slug": "lol"},
        "begin_at": "2025-09-15T12:00:00Z",
        "number_of_games": 3,
        "opponents": [make_opponent("AAA", "Team A"), make_opponent("BBB", "Team B")],
        "slug": "match-slug",
        "league": {"name": "LCS"},
        "streams_list": [make_stream(main=True, language="fr", raw_url="http://fr"), make_stream(main=True, language="en", raw_url="http://en")],
        "players": [{"name": "p1"}, {"name": "p2"}],
    }
    base.update(overrides)
    return Box(base)


class TestApiParsers:
    def test_api_parse_duo_happy_path_stream_prefers_fr(self, patched_env):
        _ = patched_env
        svc = EsportAPIService()
        match = make_match_base(number_of_games=5)  # BO5 => 3h
        res = svc._api_parse_duo(match)
        assert res is not None
        assert res.stream_url == "http://fr"
        assert res.duration == timedelta(hours=3)
        # ID concatenation check
        assert res.id == "10203040"
        # Opponents mapping
        assert isinstance(res.opponents, list) and len(res.opponents) == 2
        assert res.opponents[0]["acronym"] == "AAA"
        assert res.opponents[1]["name"] == "Team B"

    def test_api_parse_duo_fallback_to_any_main_then_empty(self, patched_env):
        _ = patched_env
        svc = EsportAPIService()
        # First case: no 'fr' language, but has a main stream in EN
        match_en = make_match_base(streams_list=[make_stream(main=True, language="en", raw_url="http://en")], number_of_games=3)
        res_en = svc._api_parse_duo(match_en)
        assert res_en.stream_url == "http://en"
        assert res_en.duration == timedelta(hours=2)

        # Second case: no streams at all -> empty string
        match_none = make_match_base(streams_list=[], number_of_games=1)
        res_none = svc._api_parse_duo(match_none)
        assert res_none.stream_url == ""
        assert res_none.duration == timedelta(hours=1)

    def test_api_parse_duo_unknown_opponent_returns_none(self, patched_env):
        _ = patched_env
        svc = EsportAPIService()
        match = make_match_base(opponents=[make_opponent("AAA","Team A")])  # only one opponent
        assert svc._api_parse_duo(match) is None

    def test_api_parse_rl_durations(self, patched_env):
        _ = patched_env
        svc = EsportAPIService()
        m5 = make_match_base(number_of_games=5, videogame={"name": "Rocket League", "slug": "rl"})
        r5 = svc._api_parse_rl(m5)
        assert r5.duration == timedelta(hours=1)

        m7 = make_match_base(number_of_games=7, videogame={"name": "Rocket League", "slug": "rl"})
        r7 = svc._api_parse_rl(m7)
        assert r7.duration == timedelta(minutes=90)

        mX = make_match_base(number_of_games=9, videogame={"name": "Rocket League", "slug": "rl"})
        rX = svc._api_parse_rl(mX)
        assert rX.duration == timedelta(hours=1)

    def test_api_parse_multi_defaults(self, patched_env):
        _ = patched_env
        svc = EsportAPIService()
        # When players not present => []
        match = make_match_base(videogame={"name":"Fortnite","slug":"FORTNITE"}, players=None)
        match.pop("players", None)  # remove to trigger hasattr False
        res = svc._api_parse_multi(match)
        assert res.players == []
        assert res.videogame_slug == "fortnite"  # lowercased
        assert res.duration == timedelta(hours=1)


class TestFetchMatchesForTeam:
    def test_fetch_matches_paginates_and_uses_parser_mapping(self, monkeypatch, patched_env):
        _ = patched_env
        svc = EsportAPIService()
        mod = EsportAPIService.__module__

        # Prepare two matches with different game slugs to verify parser selection
        match_duo = make_match_base(videogame={"name":"VALORANT", "slug":"valo"})
        match_rl  = make_match_base(videogame={"name":"Rocket League", "slug":"rocket-league"})
        # Page 1 returns two matches; Page 2 returns empty to stop loop
        responses = [
            [match_duo, match_rl],
            []
        ]

        class _Resp:
            def __init__(self, payload, status=200):
                self._payload = payload
                self.status_code = status
            def raise_for_status(self):
                if self.status_code >= 400:
                    raise RuntimeError()
            def json(self):
                return self._payload

        get_calls = {"i": 0}
        def fake_get(url, headers):
            _ = url
            _ = headers
            idx = get_calls["i"]
            get_calls["i"] += 1
            return _Resp(responses[idx])

        # Force mapping: valo -> DUO, rocket-league -> RL
        # Patch the mapping in the service module directly
        class _EnumLike:
            DUO = "DUO"
            RL = "RL"
            MULTI = "MULTI"
        monkeypatch.setattr(f"{mod}.GAME_API_PARSER_MAPPING", {"valo": _EnumLike.DUO, "rocket-league": _EnumLike.RL}, raising=False)
        monkeypatch.setattr(f"{mod}.GameApiParser", _EnumLike, raising=False)

        # Spy on parser methods to ensure correct dispatch
        with patch.object(svc, "_api_parse_duo", return_value="DUO_RES") as p_duo, \
             patch.object(svc, "_api_parse_rl", return_value="RL_RES") as p_rl, \
             patch.object(svc, "_api_parse_multi", return_value="MULTI_RES") as p_multi, \
             patch(f"{mod}.requests.get", side_effect=fake_get) as p_get:

            out = svc.fetch_matches_for_team(team_id=123)
            # verify correct parser used
            p_duo.assert_called_once()
            p_rl.assert_called_once()
            p_multi.assert_not_called()
            # verify pagination (2 GETs: page=1 then page=2)
            assert p_get.call_count == 2
            # verify collected results
            assert out == ["DUO_RES", "RL_RES"]

    def test_fetch_matches_handles_request_exception_and_returns_partial(self, monkeypatch, patched_env):
        _ = monkeypatch
        _ = patched_env
        svc = EsportAPIService()
        mod = EsportAPIService.__module__

        match_duo = make_match_base()
        class _Resp:
            def raise_for_status(self): pass
            def json(self): return [match_duo]

        calls = {"i": 0}
        def fake_get(url, headers):
            _ = url
            _ = headers
            i = calls["i"]
            calls["i"] += 1
            if i == 0:
                return _Resp()
            # On second page, raise a requests.RequestException-like error
            exc = Exception("boom")
            # Simulate requests exceptions path by raising in requests.get
            raise exc

        # Patch mapping default to DUO; ensure parse returns object
        with patch.object(svc, "_api_parse_duo", return_value={"ok": True}) as p_duo, \
             patch(f"{mod}.requests.get", side_effect=fake_get) as p_get:
            out = svc.fetch_matches_for_team(team_id=5)
            # First page parsed, second page error stops loop
            assert out == [{"ok": True}]
            assert p_duo.called
            assert p_get.call_count == 2  # first success, second raised

    def test_fetch_matches_skips_none_results_from_parser(self, monkeypatch, patched_env):
        _ = monkeypatch
        _ = patched_env
        svc = EsportAPIService()
        mod = EsportAPIService.__module__

        match_bad = make_match_base(opponents=[make_opponent("AAA","Team A")])  # duo parser -> None
        class _Resp:
            def raise_for_status(self): pass
            def json(self): return [match_bad]
        def fake_get(url, headers):
            _ = url
            _ = headers
            return _Resp()

        with patch.object(svc, "_api_parse_duo", return_value=None) as p_duo, \
             patch(f"{mod}.requests.get", side_effect=fake_get):
            out = svc.fetch_matches_for_team(team_id=1)
            assert out == []
            p_duo.assert_called_once()

    def test_fetch_matches_builds_correct_url_and_headers(self, monkeypatch, patched_env):
        _ = monkeypatch
        _ = patched_env
        svc = EsportAPIService()
        mod = EsportAPIService.__module__

        captured = {}
        class _Resp:
            def raise_for_status(self): pass
            def json(self): return []

        def fake_get(url, headers):
            captured["url"] = url
            captured["headers"] = headers
            return _Resp()

        with patch(f"{mod}.requests.get", side_effect=fake_get):
            _ = svc.fetch_matches_for_team(team_id=777)

        assert captured["url"].startswith("https://api.example.com/teams/777/matches")
        assert "Authorization" in captured["headers"]
        assert captured["headers"]["Authorization"] == "Bearer test-api-key"
        assert captured["headers"]["Accept"] == "application/json"