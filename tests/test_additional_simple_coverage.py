"""
Simple Additional Tests for 85%+ Coverage
==========================================

Simple, focused tests targeting specific uncovered lines
to push coverage from 82% to 85%+.
"""

import tempfile
from pathlib import Path

from src.common.config import Config, GameConfig, LeagueConfig, LLMConfig, RetryConfig, ServerConfig
from src.common.protocol import (
    Acknowledgement,
    ErrorMessage,
    GameEnd,
    GameInvite,
    GameInviteResponse,
    Heartbeat,
    HeartbeatResponse,
    MessageFactory,
    generate_auth_token,
)
from src.common.repositories import (
    DataManager,
    MatchData,
    MatchRepository,
    PlayerHistoryData,
    PlayerHistoryRepository,
    RoundsData,
    RoundsRepository,
    StandingsData,
    StandingsEntry,
    StandingsRepository,
)
from src.game.match import Match
from src.game.odd_even import GamePhase, GameRole, OddEvenGame


class TestSimpleConfigCoverage:
    """Simple config tests."""

    def test_server_config_custom(self):
        """Test ServerConfig with custom values."""
        config = ServerConfig(
            name="test_server",
            host="127.0.0.1",
            port=8888,
        )
        assert config.host == "127.0.0.1"

    def test_llm_config_openai(self):
        """Test LLM config with OpenAI."""
        config = LLMConfig(provider="openai", model="gpt-4o-mini")
        assert config.provider == "openai"

    def test_game_config_custom_timeout(self):
        """Test GameConfig with custom timeout."""
        config = GameConfig(move_timeout=60.0)
        assert config.move_timeout == 60.0

    def test_league_config_round_robin(self):
        """Test LeagueConfig round robin setting."""
        config = LeagueConfig(round_robin=False)
        assert config.round_robin is False

    def test_retry_config_values(self):
        """Test RetryConfig values."""
        config = RetryConfig(max_retries=5, base_delay=2.0)
        assert config.max_retries == 5


class TestSimpleProtocolCoverage:
    """Simple protocol tests."""

    def test_auth_token_generation(self):
        """Test auth token generation."""
        token = generate_auth_token("P1", "league_1")
        assert "tok_" in token

    def test_auth_token_uniqueness(self):
        """Test tokens are unique."""
        t1 = generate_auth_token("P1", "league")
        t2 = generate_auth_token("P1", "league")
        assert t1 != t2

    def test_message_factory_auth(self):
        """Test message factory auth token."""
        factory = MessageFactory(sender="P1", league_id="test")
        factory.set_auth_token("tok_123")
        assert factory.auth_token == "tok_123"

    def test_heartbeat_creation(self):
        """Test Heartbeat message."""
        msg = Heartbeat()
        assert msg is not None

    def test_heartbeat_response(self):
        """Test HeartbeatResponse."""
        msg = HeartbeatResponse(status="alive")
        assert msg.status == "alive"

    def test_error_message(self):
        """Test ErrorMessage."""
        msg = ErrorMessage(error_code="TEST", error_message="Test error")
        assert msg.error_code == "TEST"

    def test_acknowledgement(self):
        """Test Acknowledgement."""
        msg = Acknowledgement(success=True)
        assert msg.success is True

    def test_game_invite(self):
        """Test GameInvite."""
        from src.game.odd_even import GameRole
        msg = GameInvite(game_id="g1", opponent_id="P2", assigned_role=GameRole.ODD, rounds_to_play=5)
        assert msg.game_id == "g1"

    def test_game_invite_response(self):
        """Test GameInviteResponse."""
        msg = GameInviteResponse(game_id="g1", accepted=True)
        assert msg.accepted is True

    def test_game_end(self):
        """Test GameEnd."""
        msg = GameEnd(game_id="g1", winner_id="P1", final_score={"P1": 3, "P2": 2})
        assert msg.winner_id == "P1"


class TestSimpleRepositoryCoverage:
    """Simple repository tests."""

    def test_standings_save_load(self):
        """Test standings repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = StandingsRepository(base_path=Path(tmpdir), league_id="test")
            entry = StandingsEntry(rank=1, player_id="P1", display_name="Player1",
                                   wins=5, losses=0, draws=0, points=15)
            standings = StandingsData(league_id="test", round_id=1, standings=[entry])
            repo.save(standings)
            loaded = repo.load()
            assert loaded.standings[0].wins == 5

    def test_rounds_save_load(self):
        """Test rounds repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = RoundsRepository(base_path=Path(tmpdir), league_id="test")
            rounds = RoundsData(league_id="test", total_rounds=3, current_round=1, rounds=[])
            repo.save(rounds)
            loaded = repo.load()
            assert loaded.current_round == 1

    def test_match_repository(self):
        """Test match repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = MatchRepository(base_path=Path(tmpdir), league_id="test")
            match_data = MatchData(match_id="m1", league_id="test", round_id=1,
                                   player_A_id="P1", player_B_id="P2")
            repo.save(match_data)
            loaded = repo.load("m1")
            assert loaded.match_id == "m1"

    def test_player_history_repository(self):
        """Test player history repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = PlayerHistoryRepository(base_path=Path(tmpdir), player_id="P1")
            history = PlayerHistoryData(player_id="P1", display_name="Player1", total_games=10)
            repo.save(history)
            loaded = repo.load()
            assert loaded.total_games == 10

    def test_data_manager_caching(self):
        """Test DataManager caches repos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DataManager(base_path=str(tmpdir))
            r1 = dm.standings("league1")
            r2 = dm.standings("league1")
            assert r1 is r2


class TestSimpleGameCoverage:
    """Simple game logic tests."""

    def test_game_phases(self):
        """Test game phases."""
        assert GamePhase.WAITING_FOR_PLAYERS is not None
        assert GamePhase.COLLECTING_CHOICES is not None
        assert GamePhase.FINISHED is not None

    def test_game_roles(self):
        """Test game roles."""
        assert GameRole.ODD is not None
        assert GameRole.EVEN is not None

    def test_game_creation(self):
        """Test game creation."""
        game = OddEvenGame(
            game_id="g1",
            player1_id="P1",
            player2_id="P2",
            player1_role=GameRole.ODD,
            total_rounds=3,
        )
        assert game.game_id == "g1"
        assert game.total_rounds == 3

    def test_match_creation(self):
        """Test match creation."""
        match = Match(match_id="m1", league_id="test")
        assert match.match_id == "m1"

    def test_match_set_players(self):
        """Test match set players."""
        match = Match(match_id="m1", league_id="test")
        match.set_players("P1", "http://p1", "P2", "http://p2")
        assert match.player1 is not None


class TestProtocolMessageSerialization:
    """Test message serialization."""

    def test_heartbeat_to_dict(self):
        """Test Heartbeat to_dict."""
        msg = Heartbeat()
        d = msg.to_dict()
        assert isinstance(d, dict)

    def test_error_to_dict(self):
        """Test ErrorMessage to_dict."""
        msg = ErrorMessage(error_code="ERR", error_message="Error")
        d = msg.to_dict()
        assert "error_code" in d

    def test_ack_to_dict(self):
        """Test Acknowledgement to_dict."""
        msg = Acknowledgement(success=True)
        d = msg.to_dict()
        assert "success" in d


class TestConfigDefaults:
    """Test configuration defaults."""

    def test_config_has_defaults(self):
        """Test Config has defaults."""
        config = Config()
        assert config.league_manager is not None
        assert config.game is not None

    def test_config_log_level(self):
        """Test Config log level."""
        config = Config()
        assert hasattr(config, "log_level")

    def test_config_debug(self):
        """Test Config debug flag."""
        config = Config()
        assert hasattr(config, "debug")
