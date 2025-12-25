
import pytest

from src.common.events.bus import get_event_bus


@pytest.fixture
def event_bus():
    bus = get_event_bus()
    bus.reset()
    return bus

@pytest.mark.asyncio
async def test_event_bus_basic(event_bus):
    received = []

    async def handler(event):
        received.append(event)

    event_bus.on("test.event", handler)

    await event_bus.emit("test.event", data="payload")

    assert len(received) == 1
    assert received[0].data == "payload"

@pytest.mark.asyncio
async def test_wildcard_matching(event_bus):
    received = []

    async def handler(event):
        received.append(event.event_type)

    event_bus.on("game.*", handler)

    await event_bus.emit("game.start")
    await event_bus.emit("game.end")
    await event_bus.emit("player.move") # Should not match

    assert len(received) == 2
    assert "game.start" in received
    assert "game.end" in received

@pytest.mark.asyncio
async def test_priority(event_bus):
    execution_order = []

    async def handler_low(event):
        execution_order.append("low")

    async def handler_high(event):
        execution_order.append("high")

    event_bus.on("test", handler_low, priority=1)
    event_bus.on("test", handler_high, priority=10)

    await event_bus.emit("test")

    assert execution_order == ["high", "low"]

