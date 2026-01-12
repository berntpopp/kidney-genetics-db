"""
Event-driven architecture for WebSocket updates.
Replaces inefficient database polling with pub/sub pattern.
"""

import asyncio
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class EventBus:
    """
    In-memory event bus for single-server deployments.
    Implements pub/sub pattern to eliminate database polling.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[..., Any]]] = defaultdict(list)
        self._queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
        self._running = False
        self._processor_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the event processor"""
        if not self._running:
            self._running = True
            self._processor_task = asyncio.create_task(self._process_events())
            logger.sync_info("EventBus started")

    async def stop(self) -> None:
        """Stop the event processor"""
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        logger.sync_info("EventBus stopped")

    async def _process_events(self) -> None:
        """Process events from the queue"""
        while self._running:
            try:
                # Wait for events with a timeout to allow checking _running flag
                event_type, data = await asyncio.wait_for(self._queue.get(), timeout=1.0)

                # Call all subscribers for this event type
                subscribers = self._subscribers.get(event_type, [])
                for callback in subscribers:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(data)
                        else:
                            callback(data)
                    except Exception as e:
                        logger.sync_error(
                            "Error in event handler", event_type=event_type, error=str(e)
                        )

            except asyncio.TimeoutError:
                # No events in queue, continue loop
                continue
            except Exception as e:
                logger.sync_error("Error processing events", error=str(e))

    async def publish(self, event_type: str, data: Any) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event_type: Type of event (e.g., 'progress_update', 'task_complete')
            data: Event data to send to subscribers
        """
        await self._queue.put((event_type, data))
        logger.sync_debug("Published event", event_type=event_type)

    def subscribe(self, event_type: str, callback: Callable[..., Any]) -> None:
        """
        Subscribe to an event type.

        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event is published
        """
        self._subscribers[event_type].append(callback)
        logger.sync_debug("Subscribed to event", event_type=event_type)

    def unsubscribe(self, event_type: str, callback: Callable[..., Any]) -> None:
        """
        Unsubscribe from an event type.

        Args:
            event_type: Type of event to unsubscribe from
            callback: Function to remove from subscribers
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                logger.sync_debug("Unsubscribed from event", event_type=event_type)
            except ValueError:
                pass  # Callback was not in the list

    def get_subscriber_count(self, event_type: str | None = None) -> int:
        """Get count of subscribers for an event type"""
        if event_type:
            return len(self._subscribers.get(event_type, []))
        return sum(len(subs) for subs in self._subscribers.values())


# Singleton instance for the application
event_bus = EventBus()


# Event types as constants to avoid typos
class EventTypes:
    """Standard event types used in the application"""

    PROGRESS_UPDATE = "progress_update"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    DATA_SOURCE_UPDATE = "data_source_update"
    CACHE_INVALIDATED = "cache_invalidated"
