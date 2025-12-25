"""
Tests for Agent Lifecycle Management.
"""

import pytest

from src.common.lifecycle import (
    AgentLifecycleManager,
    LifecycleEvent,
    LifecycleRegistry,
    StateTransition,
    get_lifecycle_registry,
)
from src.common.protocol import AgentState


class TestAgentLifecycleManager:
    """Test AgentLifecycleManager class."""

    def setup_method(self):
        """Setup test lifecycle manager."""
        self.lifecycle = AgentLifecycleManager(
            agent_id="P01",
            agent_type="player",
        )

    def test_initial_state(self):
        """Test initial state is INIT."""
        assert self.lifecycle.state == AgentState.INIT
        assert self.lifecycle.is_active is True
        assert self.lifecycle.can_participate is False

    @pytest.mark.asyncio
    async def test_register_success_transition(self):
        """Test transition from INIT to REGISTERED."""
        result = await self.lifecycle.transition(LifecycleEvent.REGISTER_SUCCESS)

        assert result is True
        assert self.lifecycle.state == AgentState.REGISTERED
        assert self.lifecycle.can_participate is True

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test full lifecycle: INIT -> REGISTERED -> ACTIVE -> SHUTDOWN."""
        # Register
        await self.lifecycle.transition(LifecycleEvent.REGISTER_SUCCESS)
        assert self.lifecycle.state == AgentState.REGISTERED

        # Start league
        await self.lifecycle.transition(LifecycleEvent.LEAGUE_START)
        assert self.lifecycle.state == AgentState.ACTIVE

        # End league
        await self.lifecycle.transition(LifecycleEvent.LEAGUE_END)
        assert self.lifecycle.state == AgentState.SHUTDOWN
        assert self.lifecycle.is_active is False

    @pytest.mark.asyncio
    async def test_suspend_and_recover(self):
        """Test ACTIVE -> SUSPENDED -> ACTIVE."""
        await self.lifecycle.transition(LifecycleEvent.REGISTER_SUCCESS)
        await self.lifecycle.transition(LifecycleEvent.LEAGUE_START)

        # Timeout causes suspension
        await self.lifecycle.transition(LifecycleEvent.TIMEOUT)
        assert self.lifecycle.state == AgentState.SUSPENDED

        # Recover
        await self.lifecycle.transition(LifecycleEvent.RECOVER)
        assert self.lifecycle.state == AgentState.ACTIVE

    @pytest.mark.asyncio
    async def test_invalid_transition(self):
        """Test invalid transition returns False."""
        # Can't go from INIT to ACTIVE directly
        result = await self.lifecycle.transition(LifecycleEvent.LEAGUE_START)

        assert result is False
        assert self.lifecycle.state == AgentState.INIT

    @pytest.mark.asyncio
    async def test_history_tracking(self):
        """Test transition history is recorded."""
        await self.lifecycle.transition(LifecycleEvent.REGISTER_SUCCESS)
        await self.lifecycle.transition(LifecycleEvent.LEAGUE_START)

        history = self.lifecycle.history

        assert len(history) == 2
        assert history[0].from_state == AgentState.INIT
        assert history[0].to_state == AgentState.REGISTERED
        assert history[1].from_state == AgentState.REGISTERED
        assert history[1].to_state == AgentState.ACTIVE

    @pytest.mark.asyncio
    async def test_callback_on_transition(self):
        """Test callbacks are called on state change."""
        callback_results = []

        def on_change(old_state: AgentState, new_state: AgentState):
            callback_results.append((old_state, new_state))

        self.lifecycle.on_state_change(on_change)

        await self.lifecycle.transition(LifecycleEvent.REGISTER_SUCCESS)

        assert len(callback_results) == 1
        assert callback_results[0] == (AgentState.INIT, AgentState.REGISTERED)

    @pytest.mark.asyncio
    async def test_async_callback(self):
        """Test async callbacks are called."""
        callback_results = []

        async def async_on_change(old_state: AgentState, new_state: AgentState):
            callback_results.append((old_state, new_state))

        self.lifecycle.on_state_change_async(async_on_change)

        await self.lifecycle.transition(LifecycleEvent.REGISTER_SUCCESS)

        assert len(callback_results) == 1

    def test_can_transition(self):
        """Test can_transition validation."""
        assert self.lifecycle.can_transition(LifecycleEvent.REGISTER_SUCCESS) is True
        assert self.lifecycle.can_transition(LifecycleEvent.LEAGUE_START) is False

    def test_get_next_state(self):
        """Test get_next_state returns correct state."""
        assert (
            self.lifecycle.get_next_state(LifecycleEvent.REGISTER_SUCCESS) == AgentState.REGISTERED
        )
        assert self.lifecycle.get_next_state(LifecycleEvent.LEAGUE_START) is None

    def test_failure_tracking(self):
        """Test failure count tracking."""
        assert self.lifecycle.record_failure() is False  # 1/3
        assert self.lifecycle.record_failure() is False  # 2/3
        assert self.lifecycle.record_failure() is True  # 3/3 - max reached

    def test_reset_failures(self):
        """Test failure count reset."""
        self.lifecycle.record_failure()
        self.lifecycle.record_failure()
        self.lifecycle.reset_failures()

        # Should start fresh
        assert self.lifecycle.record_failure() is False

    def test_get_state_info(self):
        """Test get_state_info returns correct info."""
        info = self.lifecycle.get_state_info()

        assert info["agent_id"] == "P01"
        assert info["agent_type"] == "player"
        assert info["state"] == "INIT"
        assert info["is_active"] is True
        assert "uptime_seconds" in info

    def test_get_uptime(self):
        """Test uptime calculation."""
        uptime = self.lifecycle.get_uptime()

        assert uptime >= 0


class TestStateTransition:
    """Test StateTransition dataclass."""

    def test_to_dict(self):
        """Test serialization to dict."""
        transition = StateTransition(
            from_state=AgentState.INIT,
            to_state=AgentState.REGISTERED,
            event=LifecycleEvent.REGISTER_SUCCESS,
            metadata={"test": "value"},
        )

        data = transition.to_dict()

        assert data["from_state"] == "INIT"
        assert data["to_state"] == "REGISTERED"
        assert data["event"] == "register_success"
        assert data["metadata"]["test"] == "value"
        assert "timestamp" in data


class TestLifecycleRegistry:
    """Test LifecycleRegistry class."""

    def setup_method(self):
        """Setup test registry."""
        self.registry = LifecycleRegistry()

    def test_register_agent(self):
        """Test registering an agent lifecycle."""
        lifecycle = AgentLifecycleManager("P01", "player")
        self.registry.register(lifecycle)

        retrieved = self.registry.get("P01", "player")

        assert retrieved is lifecycle

    def test_unregister_agent(self):
        """Test unregistering an agent lifecycle."""
        lifecycle = AgentLifecycleManager("P01", "player")
        self.registry.register(lifecycle)
        self.registry.unregister("P01", "player")

        retrieved = self.registry.get("P01", "player")

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_by_state(self):
        """Test getting agents by state."""
        lc1 = AgentLifecycleManager("P01", "player")
        lc2 = AgentLifecycleManager("P02", "player")

        await lc1.transition(LifecycleEvent.REGISTER_SUCCESS)

        self.registry.register(lc1)
        self.registry.register(lc2)

        registered = self.registry.get_by_state(AgentState.REGISTERED)
        init = self.registry.get_by_state(AgentState.INIT)

        assert len(registered) == 1
        assert registered[0].agent_id == "P01"
        assert len(init) == 1
        assert init[0].agent_id == "P02"

    @pytest.mark.asyncio
    async def test_get_active_agents(self):
        """Test getting active agents."""
        lc1 = AgentLifecycleManager("P01", "player")
        lc2 = AgentLifecycleManager("P02", "player")

        await lc2.transition(LifecycleEvent.ERROR)  # INIT -> SHUTDOWN

        self.registry.register(lc1)
        self.registry.register(lc2)

        active = self.registry.get_active_agents()

        assert len(active) == 1
        assert active[0].agent_id == "P01"

    def test_get_summary(self):
        """Test getting registry summary."""
        lc1 = AgentLifecycleManager("P01", "player")
        lc2 = AgentLifecycleManager("REF01", "referee")

        self.registry.register(lc1)
        self.registry.register(lc2)

        summary = self.registry.get_summary()

        assert summary["total_agents"] == 2
        assert summary["active_agents"] == 2
        assert summary["state_counts"]["INIT"] == 2


class TestGlobalRegistry:
    """Test global lifecycle registry."""

    def test_get_lifecycle_registry(self):
        """Test getting global registry returns singleton."""
        registry1 = get_lifecycle_registry()
        registry2 = get_lifecycle_registry()

        assert registry1 is registry2


class TestMaxFailsTransition:
    """Test max failures triggering shutdown."""

    @pytest.mark.asyncio
    async def test_max_fails_causes_shutdown(self):
        """Test that max failures leads to SHUTDOWN state."""
        lifecycle = AgentLifecycleManager("P01", "player")

        # Get to SUSPENDED state
        await lifecycle.transition(LifecycleEvent.REGISTER_SUCCESS)
        await lifecycle.transition(LifecycleEvent.LEAGUE_START)
        await lifecycle.transition(LifecycleEvent.TIMEOUT)

        assert lifecycle.state == AgentState.SUSPENDED

        # Now trigger max_fails
        await lifecycle.transition(LifecycleEvent.MAX_FAILS)

        assert lifecycle.state == AgentState.SHUTDOWN
        assert lifecycle.is_active is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
