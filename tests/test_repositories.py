"""
Tests for data repositories.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from src.common.repositories import (
    DataManager,
    StandingsRepository,
    RoundsRepository,
    MatchRepository,
    PlayerHistoryRepository,
    StandingsData,
    StandingsEntry,
    RoundsData,
    RoundEntry,
    MatchData,
    PlayerHistoryData,
    PlayerHistoryEntry,
)


class TestStandingsRepository:
    """Test standings repository."""
    
    def setup_method(self):
        """Setup temp directory for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo = StandingsRepository(self.temp_dir, "test_league")
    
    def teardown_method(self):
        """Cleanup temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_save_and_load_standings(self):
        """Test saving and loading standings."""
        standings = StandingsData(
            league_id="test_league",
            round_id=1,
            standings=[
                StandingsEntry(rank=1, player_id="P01", display_name="Player 1", wins=2, points=6),
                StandingsEntry(rank=2, player_id="P02", display_name="Player 2", wins=1, points=3),
            ],
        )
        
        self.repo.save(standings)
        loaded = self.repo.load()
        
        assert loaded is not None
        assert loaded.league_id == "test_league"
        assert loaded.round_id == 1
        assert len(loaded.standings) == 2
        assert loaded.standings[0].player_id == "P01"
        assert loaded.standings[0].points == 6
    
    def test_get_player_rank(self):
        """Test getting player rank."""
        standings = StandingsData(
            league_id="test_league",
            round_id=1,
            standings=[
                StandingsEntry(rank=1, player_id="P01", display_name="Player 1"),
                StandingsEntry(rank=2, player_id="P02", display_name="Player 2"),
            ],
        )
        
        self.repo.save(standings)
        
        assert self.repo.get_player_rank("P01") == 1
        assert self.repo.get_player_rank("P02") == 2
        assert self.repo.get_player_rank("P99") is None


class TestRoundsRepository:
    """Test rounds repository."""
    
    def setup_method(self):
        """Setup temp directory."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo = RoundsRepository(self.temp_dir, "test_league")
    
    def teardown_method(self):
        """Cleanup."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_save_and_load_rounds(self):
        """Test saving and loading rounds."""
        rounds_data = RoundsData(
            league_id="test_league",
            total_rounds=3,
            current_round=1,
            rounds=[
                RoundEntry(
                    round_id=1,
                    started_at="2024-01-01T10:00:00Z",
                    matches=[{"match_id": "R1M1"}],
                ),
            ],
        )
        
        self.repo.save(rounds_data)
        loaded = self.repo.load()
        
        assert loaded is not None
        assert loaded.total_rounds == 3
        assert loaded.current_round == 1
        assert len(loaded.rounds) == 1
    
    def test_add_round(self):
        """Test adding a round."""
        round_entry = RoundEntry(
            round_id=1,
            started_at="2024-01-01T10:00:00Z",
            matches=[{"match_id": "R1M1"}],
        )
        
        self.repo.add_round(round_entry)
        
        loaded = self.repo.load()
        assert loaded is not None
        assert loaded.current_round == 1
        assert len(loaded.rounds) == 1
    
    def test_complete_round(self):
        """Test completing a round with results."""
        round_entry = RoundEntry(
            round_id=1,
            started_at="2024-01-01T10:00:00Z",
        )
        self.repo.add_round(round_entry)
        
        results = [{"match_id": "R1M1", "winner_id": "P01"}]
        self.repo.complete_round(1, results)
        
        loaded = self.repo.load()
        assert loaded.rounds[0].completed_at is not None
        assert loaded.rounds[0].results == results


class TestMatchRepository:
    """Test match repository."""
    
    def setup_method(self):
        """Setup temp directory."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo = MatchRepository(self.temp_dir, "test_league")
    
    def teardown_method(self):
        """Cleanup."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_save_and_load_match(self):
        """Test saving and loading a match."""
        match = MatchData(
            match_id="R1M1",
            league_id="test_league",
            round_id=1,
            player_A_id="P01",
            player_B_id="P02",
        )
        
        self.repo.save(match)
        loaded = self.repo.load("R1M1")
        
        assert loaded is not None
        assert loaded.match_id == "R1M1"
        assert loaded.player_A_id == "P01"
        assert loaded.player_B_id == "P02"
    
    def test_list_matches(self):
        """Test listing matches."""
        for i in range(3):
            match = MatchData(
                match_id=f"R1M{i+1}",
                league_id="test_league",
                round_id=1,
            )
            self.repo.save(match)
        
        matches = self.repo.list_matches()
        assert len(matches) == 3
        assert "R1M1" in matches
    
    def test_update_status(self):
        """Test updating match status."""
        match = MatchData(
            match_id="R1M1",
            league_id="test_league",
            round_id=1,
            status="pending",
        )
        self.repo.save(match)
        
        self.repo.update_status("R1M1", "in_progress")
        
        loaded = self.repo.load("R1M1")
        assert loaded.status == "in_progress"
        assert loaded.started_at is not None
    
    def test_record_result(self):
        """Test recording match result."""
        match = MatchData(
            match_id="R1M1",
            league_id="test_league",
            round_id=1,
            player_A_id="P01",
            player_B_id="P02",
        )
        self.repo.save(match)
        
        self.repo.record_result(
            match_id="R1M1",
            winner_id="P01",
            player_A_score=3,
            player_B_score=2,
            rounds_played=5,
        )
        
        loaded = self.repo.load("R1M1")
        assert loaded.winner_id == "P01"
        assert loaded.player_A_score == 3
        assert loaded.player_B_score == 2
        assert loaded.status == "completed"


class TestPlayerHistoryRepository:
    """Test player history repository."""
    
    def setup_method(self):
        """Setup temp directory."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo = PlayerHistoryRepository(self.temp_dir, "P01")
    
    def teardown_method(self):
        """Cleanup."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_save_and_load_history(self):
        """Test saving and loading history."""
        history = PlayerHistoryData(
            player_id="P01",
            display_name="Player 1",
            total_games=2,
            wins=1,
            losses=1,
        )
        
        self.repo.save(history)
        loaded = self.repo.load()
        
        assert loaded is not None
        assert loaded.player_id == "P01"
        assert loaded.total_games == 2
    
    def test_add_game(self):
        """Test adding a game to history."""
        entry = PlayerHistoryEntry(
            match_id="R1M1",
            opponent_id="P02",
            opponent_name="Player 2",
            result="win",
            my_score=3,
            opponent_score=2,
            my_role="odd",
            played_at="2024-01-01T10:00:00Z",
            round_id=1,
        )
        
        self.repo.add_game(entry)
        
        loaded = self.repo.load()
        assert loaded.total_games == 1
        assert loaded.wins == 1
        assert len(loaded.games) == 1
    
    def test_get_recent_games(self):
        """Test getting recent games."""
        for i in range(5):
            entry = PlayerHistoryEntry(
                match_id=f"R{i+1}M1",
                opponent_id="P02",
                opponent_name="Player 2",
                result="win" if i % 2 == 0 else "loss",
                my_score=3,
                opponent_score=2,
                my_role="odd",
                played_at=f"2024-01-0{i+1}T10:00:00Z",
                round_id=i+1,
            )
            self.repo.add_game(entry)
        
        recent = self.repo.get_recent_games(3)
        assert len(recent) == 3
        # Should be the last 3
        assert recent[0].match_id == "R3M1"
    
    def test_get_opponent_history(self):
        """Test getting history against specific opponent."""
        # Add games against different opponents
        self.repo.add_game(PlayerHistoryEntry(
            match_id="R1M1", opponent_id="P02", opponent_name="Player 2",
            result="win", my_score=3, opponent_score=2, my_role="odd",
            played_at="2024-01-01T10:00:00Z", round_id=1,
        ))
        self.repo.add_game(PlayerHistoryEntry(
            match_id="R2M1", opponent_id="P03", opponent_name="Player 3",
            result="loss", my_score=2, opponent_score=3, my_role="even",
            played_at="2024-01-02T10:00:00Z", round_id=2,
        ))
        self.repo.add_game(PlayerHistoryEntry(
            match_id="R3M1", opponent_id="P02", opponent_name="Player 2",
            result="win", my_score=3, opponent_score=1, my_role="odd",
            played_at="2024-01-03T10:00:00Z", round_id=3,
        ))
        
        p02_games = self.repo.get_opponent_history("P02")
        assert len(p02_games) == 2
        
        p03_games = self.repo.get_opponent_history("P03")
        assert len(p03_games) == 1


class TestDataManager:
    """Test data manager."""
    
    def setup_method(self):
        """Setup temp directory."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = DataManager(str(self.temp_dir))
    
    def teardown_method(self):
        """Cleanup."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_standings_repo(self):
        """Test getting standings repository."""
        repo = self.manager.standings("league_1")
        assert repo is not None
        assert repo.league_id == "league_1"
        
        # Should return same instance
        repo2 = self.manager.standings("league_1")
        assert repo is repo2
    
    def test_get_different_league_repos(self):
        """Test getting repos for different leagues."""
        repo1 = self.manager.standings("league_1")
        repo2 = self.manager.standings("league_2")
        
        assert repo1 is not repo2
        assert repo1.league_id == "league_1"
        assert repo2.league_id == "league_2"
    
    def test_get_all_repo_types(self):
        """Test getting all repository types."""
        standings = self.manager.standings("test_league")
        rounds = self.manager.rounds("test_league")
        matches = self.manager.matches("test_league")
        history = self.manager.player_history("P01")
        
        assert standings is not None
        assert rounds is not None
        assert matches is not None
        assert history is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

