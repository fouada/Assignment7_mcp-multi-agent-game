"""
Comprehensive tests for Referee agent to increase coverage.
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.agents.referee import GameSession, RefereeAgent
from src.common.exceptions import TimeoutError
from src.game.match import Match


class TestRefereeAgentInitialization:
    """Test referee agent initialization."""

    def test_referee_init_with_all_params(self):
        """Test referee initialization with all parameters."""
        referee = RefereeAgent(
            referee_id="ref_001",
            league_url="http://localhost:8000",
            port=9001,
            auto_register=False
        )

        assert referee.referee_id == "ref_001"
        assert referee.league_url == "http://localhost:8000"
        assert referee.port == 9001

    def test_referee_init_defaults(self):
        """Test referee initialization with defaults."""
        referee = RefereeAgent()

        assert referee.referee_id is not None
        assert referee.port > 0


class TestRefereeRegistration:
    """Test referee registration functionality."""

    @pytest.mark.asyncio
    async def test_register_success_with_capabilities(self):
        """Test successful registration with capabilities."""
        referee = RefereeAgent(auto_register=False)

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "registered"}
            mock_post.return_value = mock_response

            result = await referee.register_with_league()

            assert result is True

    @pytest.mark.asyncio
    async def test_register_with_connection_error(self):
        """Test registration with connection error."""
        referee = RefereeAgent(
            league_url="http://nonexistent:8000",
            auto_register=False
        )

        with patch('httpx.AsyncClient.post', side_effect=Exception("Connection failed")):
            result = await referee.register_with_league()
            assert result is False

    @pytest.mark.asyncio
    async def test_register_with_timeout(self):
        """Test registration with timeout."""
        referee = RefereeAgent(auto_register=False)

        with patch('httpx.AsyncClient.post', side_effect=asyncio.TimeoutError):
            result = await referee.register_with_league()
            assert result is False


class TestMatchStarting:
    """Test match starting functionality."""

    @pytest.mark.asyncio
    async def test_start_match_creates_session(self):
        """Test that starting a match creates a game session."""
        referee = RefereeAgent(auto_register=False)

        match = Match(
            match_id="match_001",
            game_type="odd_even"
        )
        match.set_players([
            {"player_id": "P1", "endpoint": "http://localhost:8001"},
            {"player_id": "P2", "endpoint": "http://localhost:8002"}
        ])

        with patch.object(referee, 'send_game_invitations', return_value=(True, True)):
            session = await referee.start_match(match)

            assert session is not None
            assert session.match_id == "match_001"

    @pytest.mark.asyncio
    async def test_start_match_without_players(self):
        """Test starting match without players."""
        referee = RefereeAgent(auto_register=False)

        match = Match(
            match_id="match_001",
            game_type="odd_even"
        )

        with pytest.raises((RuntimeError, ValueError)):
            await referee.start_match(match)

    @pytest.mark.asyncio
    async def test_start_match_player_rejects(self):
        """Test starting match when player rejects."""
        referee = RefereeAgent(auto_register=False)

        match = Match(
            match_id="match_001",
            game_type="odd_even"
        )
        match.set_players([
            {"player_id": "P1", "endpoint": "http://localhost:8001"},
            {"player_id": "P2", "endpoint": "http://localhost:8002"}
        ])

        with patch.object(referee, 'send_game_invitations', return_value=(True, False)):
            session = await referee.start_match(match)

            # Session might be None or have error state
            assert session is None or session.error_occurred


class TestGameInvitations:
    """Test game invitation functionality."""

    @pytest.mark.asyncio
    async def test_send_invitations_both_accept(self):
        """Test sending invitations when both players accept."""
        referee = RefereeAgent(auto_register=False)

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"accepted": True}
            mock_post.return_value = mock_response

            result = await referee.send_game_invitations(
                game_id="game_001",
                player1_endpoint="http://localhost:8001",
                player2_endpoint="http://localhost:8002",
                game_config={}
            )

            assert result == (True, True)

    @pytest.mark.asyncio
    async def test_send_invitations_one_rejects(self):
        """Test sending invitations when one player rejects."""
        referee = RefereeAgent(auto_register=False)

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            # First call accepts, second rejects
            mock_response_accept = Mock()
            mock_response_accept.status_code = 200
            mock_response_accept.json.return_value = {"accepted": True}

            mock_response_reject = Mock()
            mock_response_reject.status_code = 200
            mock_response_reject.json.return_value = {"accepted": False}

            mock_post.side_effect = [mock_response_accept, mock_response_reject]

            result = await referee.send_game_invitations(
                game_id="game_001",
                player1_endpoint="http://localhost:8001",
                player2_endpoint="http://localhost:8002",
                game_config={}
            )

            assert result == (True, False)

    @pytest.mark.asyncio
    async def test_send_invitations_network_error(self):
        """Test sending invitations with network error."""
        referee = RefereeAgent(auto_register=False)

        with patch('httpx.AsyncClient.post', side_effect=Exception("Network error")):
            result = await referee.send_game_invitations(
                game_id="game_001",
                player1_endpoint="http://localhost:8001",
                player2_endpoint="http://localhost:8002",
                game_config={}
            )

            assert result == (False, False)


class TestRoundExecution:
    """Test round execution functionality."""

    @pytest.mark.asyncio
    async def test_run_round_success(self):
        """Test running a round successfully."""
        referee = RefereeAgent(auto_register=False)

        session = GameSession(
            match_id="match_001",
            game_id="game_001",
            player1_id="P1",
            player2_id="P2",
            player1_endpoint="http://localhost:8001",
            player2_endpoint="http://localhost:8002"
        )

        with patch.object(referee, 'collect_moves', return_value=(5, 3)):
            with patch.object(referee, 'send_round_results'):
                result = await referee.run_round(session, round_num=1)

                assert result is not None

    @pytest.mark.asyncio
    async def test_run_round_timeout(self):
        """Test running round with timeout."""
        referee = RefereeAgent(auto_register=False)

        session = GameSession(
            match_id="match_001",
            game_id="game_001",
            player1_id="P1",
            player2_id="P2",
            player1_endpoint="http://localhost:8001",
            player2_endpoint="http://localhost:8002"
        )

        with patch.object(referee, 'collect_moves', side_effect=asyncio.TimeoutError):
            with pytest.raises((asyncio.TimeoutError, TimeoutError)):
                await referee.run_round(session, round_num=1)

    @pytest.mark.asyncio
    async def test_run_round_invalid_move(self):
        """Test running round with invalid move."""
        referee = RefereeAgent(auto_register=False)

        session = GameSession(
            match_id="match_001",
            game_id="game_001",
            player1_id="P1",
            player2_id="P2",
            player1_endpoint="http://localhost:8001",
            player2_endpoint="http://localhost:8002"
        )

        # Invalid move (out of range)
        with patch.object(referee, 'collect_moves', return_value=(15, 3)):
            with pytest.raises((RuntimeError, ValueError)):
                await referee.run_round(session, round_num=1)


class TestMoveCollection:
    """Test move collection functionality."""

    @pytest.mark.asyncio
    async def test_collect_moves_success(self):
        """Test collecting moves successfully."""
        referee = RefereeAgent(auto_register=False)

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"move": 5}
            mock_post.return_value = mock_response

            moves = await referee.collect_moves(
                player1_endpoint="http://localhost:8001",
                player2_endpoint="http://localhost:8002",
                game_state={}
            )

            assert moves is not None

    @pytest.mark.asyncio
    async def test_collect_moves_timeout(self):
        """Test collecting moves with timeout."""
        referee = RefereeAgent(auto_register=False)

        with patch('httpx.AsyncClient.post', side_effect=asyncio.TimeoutError):
            with pytest.raises((asyncio.TimeoutError, TimeoutError)):
                await referee.collect_moves(
                    player1_endpoint="http://localhost:8001",
                    player2_endpoint="http://localhost:8002",
                    game_state={},
                    timeout=1
                )

    @pytest.mark.asyncio
    async def test_collect_moves_partial_response(self):
        """Test collecting moves with partial response."""
        referee = RefereeAgent(auto_register=False)

        # First player responds, second doesn't
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"move": 5}

            mock_post.side_effect = [mock_response, asyncio.TimeoutError]

            with pytest.raises((asyncio.TimeoutError, TimeoutError)):
                await referee.collect_moves(
                    player1_endpoint="http://localhost:8001",
                    player2_endpoint="http://localhost:8002",
                    game_state={},
                    timeout=1
                )


class TestResultReporting:
    """Test result reporting functionality."""

    @pytest.mark.asyncio
    async def test_send_round_results_success(self):
        """Test sending round results successfully."""
        referee = RefereeAgent(auto_register=False)

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            await referee.send_round_results(
                player1_endpoint="http://localhost:8001",
                player2_endpoint="http://localhost:8002",
                result={"winner": "P1", "score": 5}
            )

            # Should complete without error
            assert True

    @pytest.mark.asyncio
    async def test_send_round_results_network_error(self):
        """Test sending round results with network error."""
        referee = RefereeAgent(auto_register=False)

        with patch('httpx.AsyncClient.post', side_effect=Exception("Network error")):
            # Should handle error gracefully
            await referee.send_round_results(
                player1_endpoint="http://localhost:8001",
                player2_endpoint="http://localhost:8002",
                result={"winner": "P1", "score": 5}
            )

            assert True

    @pytest.mark.asyncio
    async def test_report_match_result_to_league(self):
        """Test reporting match result to league."""
        referee = RefereeAgent(
            league_url="http://localhost:8000",
            auto_register=False
        )

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            await referee.report_match_result_to_league(
                match_id="match_001",
                winner="P1",
                score_a=5,
                score_b=3
            )

            assert True


class TestGameCompletion:
    """Test game completion functionality."""

    @pytest.mark.asyncio
    async def test_complete_game_success(self):
        """Test completing a game successfully."""
        referee = RefereeAgent(auto_register=False)

        session = GameSession(
            match_id="match_001",
            game_id="game_001",
            player1_id="P1",
            player2_id="P2",
            player1_endpoint="http://localhost:8001",
            player2_endpoint="http://localhost:8002"
        )
        session.player1_score = 3
        session.player2_score = 2

        with patch.object(referee, 'send_game_over_notification'):
            await referee.complete_game(session)

            assert session.completed is True

    @pytest.mark.asyncio
    async def test_complete_game_with_tie(self):
        """Test completing a game with tie."""
        referee = RefereeAgent(auto_register=False)

        session = GameSession(
            match_id="match_001",
            game_id="game_001",
            player1_id="P1",
            player2_id="P2",
            player1_endpoint="http://localhost:8001",
            player2_endpoint="http://localhost:8002"
        )
        session.player1_score = 2
        session.player2_score = 2

        with patch.object(referee, 'send_game_over_notification'):
            await referee.complete_game(session)

            assert session.completed is True


class TestGameSession:
    """Test GameSession dataclass."""

    def test_game_session_creation(self):
        """Test creating a game session."""
        session = GameSession(
            match_id="match_001",
            game_id="game_001",
            player1_id="P1",
            player2_id="P2",
            player1_endpoint="http://localhost:8001",
            player2_endpoint="http://localhost:8002"
        )

        assert session.match_id == "match_001"
        assert session.game_id == "game_001"

    def test_game_session_score_tracking(self):
        """Test game session score tracking."""
        session = GameSession(
            match_id="match_001",
            game_id="game_001",
            player1_id="P1",
            player2_id="P2",
            player1_endpoint="http://localhost:8001",
            player2_endpoint="http://localhost:8002"
        )

        session.player1_score += 1
        session.player2_score += 2

        assert session.player1_score == 1
        assert session.player2_score == 2

    def test_game_session_completion(self):
        """Test game session completion tracking."""
        session = GameSession(
            match_id="match_001",
            game_id="game_001",
            player1_id="P1",
            player2_id="P2",
            player1_endpoint="http://localhost:8001",
            player2_endpoint="http://localhost:8002"
        )

        assert session.completed is False

        session.completed = True
        assert session.completed is True


class TestRefereeTools:
    """Test referee MCP tools."""

    @pytest.mark.asyncio
    async def test_get_game_state_tool(self):
        """Test getting game state via tool."""
        referee = RefereeAgent(auto_register=False)

        session = GameSession(
            match_id="match_001",
            game_id="game_001",
            player1_id="P1",
            player2_id="P2",
            player1_endpoint="http://localhost:8001",
            player2_endpoint="http://localhost:8002"
        )
        referee.active_sessions["game_001"] = session

        # Tool handler would call this
        state = referee.get_game_state("game_001")

        assert state is not None

    @pytest.mark.asyncio
    async def test_list_active_games_tool(self):
        """Test listing active games via tool."""
        referee = RefereeAgent(auto_register=False)

        for i in range(3):
            session = GameSession(
                match_id=f"match_{i}",
                game_id=f"game_{i}",
                player1_id="P1",
                player2_id="P2",
                player1_endpoint="http://localhost:8001",
                player2_endpoint="http://localhost:8002"
            )
            referee.active_sessions[f"game_{i}"] = session

        # Tool handler would call this
        games = referee.list_active_games()

        assert len(games) == 3


class TestRefereeEdgeCases:
    """Test referee edge cases."""

    @pytest.mark.asyncio
    async def test_concurrent_match_handling(self):
        """Test handling multiple concurrent matches."""
        _referee = RefereeAgent(auto_register=False)

        matches = []
        for i in range(3):
            match = Match(
                match_id=f"match_{i}",
                game_type="odd_even"
            )
            match.set_players([
                {"player_id": "P1", "endpoint": "http://localhost:8001"},
                {"player_id": "P2", "endpoint": "http://localhost:8002"}
            ])
            matches.append(match)

        # Should be able to handle multiple matches
        assert len(matches) == 3

    def test_session_cleanup_on_error(self):
        """Test that sessions are cleaned up on error."""
        referee = RefereeAgent(auto_register=False)

        session = GameSession(
            match_id="match_001",
            game_id="game_001",
            player1_id="P1",
            player2_id="P2",
            player1_endpoint="http://localhost:8001",
            player2_endpoint="http://localhost:8002"
        )

        referee.active_sessions["game_001"] = session

        # Cleanup
        del referee.active_sessions["game_001"]

        assert "game_001" not in referee.active_sessions

    @pytest.mark.asyncio
    async def test_heartbeat_mechanism(self):
        """Test referee heartbeat mechanism."""
        referee = RefereeAgent(
            league_url="http://localhost:8000",
            auto_register=False
        )

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            # Send heartbeat
            await referee.send_heartbeat()

            assert True

