"""
Tests for Research Display Module
==================================

Tests the research display functionality to ensure proper
visualization data is returned.
"""

from src.visualization.research_display import ResearchDisplay


class TestResearchDisplay:
    """Test ResearchDisplay class."""

    def test_get_completed_innovations(self):
        """Test getting completed innovations."""
        innovations = ResearchDisplay.get_completed_innovations()

        # Should return a list
        assert isinstance(innovations, list)
        assert len(innovations) > 0

        # Each innovation should have required fields
        for innovation in innovations:
            assert "id" in innovation
            assert "title" in innovation
            assert "status" in innovation
            assert "grade" in innovation

    def test_get_future_innovations(self):
        """Test getting future innovations."""
        innovations = ResearchDisplay.get_future_innovations()

        # Should return a list
        assert isinstance(innovations, list)
        assert len(innovations) > 0

        # Each innovation should have required fields
        for innovation in innovations:
            assert "id" in innovation
            assert "title" in innovation
            assert "status" in innovation

    def test_get_current_score(self):
        """Test getting current score."""
        score = ResearchDisplay.get_current_score()

        # Should return a dictionary
        assert isinstance(score, dict)

        # Should have score metrics
        assert "current" in score or "total" in score or len(score) > 0

    def test_get_research_statistics(self):
        """Test getting research statistics."""
        stats = ResearchDisplay.get_research_statistics()

        # Should return a dictionary
        assert isinstance(stats, dict)

        # Should have key metrics
        assert len(stats) > 0

    def test_get_simulation_results(self):
        """Test getting simulation results."""
        sim_data = ResearchDisplay.get_simulation_results()

        # Should return a dictionary
        assert isinstance(sim_data, dict)

        # Should have simulation results
        assert len(sim_data) > 0

