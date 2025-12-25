"""
Message Queue
=============

Priority-based message queue for MCP communication.
"""

import asyncio
import heapq
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any

from ..common.logger import get_logger

logger = get_logger(__name__)


class MessagePriority(IntEnum):
    """Message priority levels (lower = higher priority)."""

    URGENT = 0  # System critical, bypass queue
    HIGH = 1  # Game state, moves
    NORMAL = 2  # Regular operations
    LOW = 3  # Background tasks


@dataclass(order=True)
class Message:
    """
    Message in the queue.

    Comparable by (priority, timestamp) for heap ordering.
    """

    # Comparison fields (used by heapq)
    priority: MessagePriority = field(compare=True)
    timestamp: float = field(compare=True, default_factory=lambda: datetime.utcnow().timestamp())

    # Message content (not used in comparison)
    id: str = field(compare=False, default_factory=lambda: str(uuid.uuid4()))
    data: dict[str, Any] = field(compare=False, default_factory=dict)
    target_server: str | None = field(compare=False, default=None)
    callback: asyncio.Future | None = field(compare=False, default=None)

    # Metadata
    created_at: datetime = field(compare=False, default_factory=datetime.utcnow)
    retries: int = field(compare=False, default=0)
    max_retries: int = field(compare=False, default=3)
    timeout: float = field(compare=False, default=30.0)

    @property
    def is_expired(self) -> bool:
        """Check if message has expired."""
        elapsed = (datetime.utcnow() - self.created_at).total_seconds()
        return elapsed > self.timeout

    @property
    def can_retry(self) -> bool:
        """Check if message can be retried."""
        return self.retries < self.max_retries


class MessageQueue:
    """
    Thread-safe priority message queue.

    Features:
    - Priority-based ordering
    - FIFO within same priority
    - Rate limiting
    - Overflow protection
    """

    def __init__(
        self,
        max_size: int = 1000,
        rate_limit: int | None = None,  # Messages per second
    ):
        self.max_size = max_size
        self.rate_limit = rate_limit

        # Priority queue (min-heap)
        self._queue: list[Message] = []

        # Synchronization
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition(self._lock)
        self._not_full = asyncio.Condition(self._lock)

        # Rate limiting
        self._last_dequeue_time: datetime | None = None
        self._rate_limit_delay = 1.0 / rate_limit if rate_limit else 0

        # Statistics
        self._total_enqueued = 0
        self._total_dequeued = 0
        self._total_dropped = 0

    async def enqueue(
        self,
        data: dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        target_server: str | None = None,
        timeout: float = 30.0,
        block: bool = True,
    ) -> Message:
        """
        Add a message to the queue.

        Args:
            data: Message data
            priority: Message priority
            target_server: Target server name
            timeout: Message timeout
            block: Whether to block if queue is full

        Returns:
            Enqueued Message

        Raises:
            asyncio.QueueFull: If queue is full and not blocking
        """
        message = Message(
            priority=priority,
            data=data,
            target_server=target_server,
            timeout=timeout,
        )

        async with self._not_full:
            if block:
                while len(self._queue) >= self.max_size:
                    await self._not_full.wait()
            elif len(self._queue) >= self.max_size:
                self._total_dropped += 1
                raise asyncio.QueueFull()

            heapq.heappush(self._queue, message)
            self._total_enqueued += 1

            self._not_empty.notify()

        logger.debug(f"Enqueued message: {message.id} (priority: {priority.name})")
        return message

    async def dequeue(
        self,
        block: bool = True,
        timeout: float | None = None,
    ) -> Message | None:
        """
        Get next message from queue.

        Args:
            block: Whether to block if queue is empty
            timeout: Maximum time to wait

        Returns:
            Message or None if timeout/empty
        """
        async with self._not_empty:
            if block:
                while not self._queue:
                    try:
                        await asyncio.wait_for(self._not_empty.wait(), timeout=timeout)
                    except TimeoutError:
                        return None
            elif not self._queue:
                return None

            # Rate limiting
            if self._rate_limit_delay and self._last_dequeue_time:
                elapsed = (datetime.utcnow() - self._last_dequeue_time).total_seconds()
                if elapsed < self._rate_limit_delay:
                    await asyncio.sleep(self._rate_limit_delay - elapsed)

            message = heapq.heappop(self._queue)
            self._total_dequeued += 1
            self._last_dequeue_time = datetime.utcnow()

            self._not_full.notify()

        # Skip expired messages
        if message.is_expired:
            logger.warning(f"Dropping expired message: {message.id}")
            self._total_dropped += 1
            return await self.dequeue(block, timeout)

        logger.debug(f"Dequeued message: {message.id}")
        return message

    async def peek(self) -> Message | None:
        """Peek at next message without removing."""
        async with self._lock:
            if self._queue:
                return self._queue[0]
            return None

    async def clear(self) -> int:
        """Clear all messages from queue."""
        async with self._lock:
            count = len(self._queue)
            self._queue.clear()
            self._not_full.notify_all()
            return count

    async def remove_by_server(self, server_name: str) -> int:
        """Remove all messages for a specific server."""
        async with self._lock:
            original_size = len(self._queue)
            self._queue = [m for m in self._queue if m.target_server != server_name]
            heapq.heapify(self._queue)
            removed = original_size - len(self._queue)
            self._not_full.notify_all()
            return removed

    @property
    def size(self) -> int:
        """Get queue size."""
        return len(self._queue)

    @property
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._queue) == 0

    @property
    def is_full(self) -> bool:
        """Check if queue is full."""
        return len(self._queue) >= self.max_size

    async def get_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        async with self._lock:
            priority_counts = {p.name: 0 for p in MessagePriority}
            for msg in self._queue:
                priority_counts[msg.priority.name] += 1

            return {
                "size": len(self._queue),
                "max_size": self.max_size,
                "total_enqueued": self._total_enqueued,
                "total_dequeued": self._total_dequeued,
                "total_dropped": self._total_dropped,
                "by_priority": priority_counts,
            }


class MessageDispatcher:
    """
    Dispatches messages from queue to handlers.

    Runs as background task processing messages.
    """

    def __init__(
        self,
        queue: MessageQueue,
        handler: Any,  # MCPClient or similar
        concurrency: int = 5,
    ):
        self.queue = queue
        self.handler = handler
        self.concurrency = concurrency

        self._running = False
        self._tasks: list[asyncio.Task] = []
        self._semaphore: asyncio.Semaphore | None = None

    async def start(self) -> None:
        """Start the dispatcher."""
        if self._running:
            return

        self._running = True
        self._semaphore = asyncio.Semaphore(self.concurrency)

        # Start worker tasks
        for i in range(self.concurrency):
            task = asyncio.create_task(self._worker(i))
            self._tasks.append(task)

        logger.info(f"Message dispatcher started with {self.concurrency} workers")

    async def stop(self) -> None:
        """Stop the dispatcher."""
        self._running = False

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()

        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks.clear()
        logger.info("Message dispatcher stopped")

    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine."""
        while self._running:
            try:
                # Get message
                message = await self.queue.dequeue(timeout=1.0)
                if message is None:
                    continue

                # Process message
                async with self._semaphore:
                    await self._process_message(message)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Worker {worker_id} error: {e}")

    async def _process_message(self, message: Message) -> None:
        """Process a single message."""
        try:
            # Send via handler
            result = await self.handler.send_request(
                server_name=message.target_server,
                data=message.data,
            )

            # Complete callback if present
            if message.callback and not message.callback.done():
                message.callback.set_result(result)

        except Exception as e:
            logger.error(f"Failed to process message {message.id}: {e}")

            # Retry if possible
            if message.can_retry:
                message.retries += 1
                await self.queue.enqueue(
                    message.data,
                    priority=message.priority,
                    target_server=message.target_server,
                )
            elif message.callback and not message.callback.done():
                message.callback.set_exception(e)
