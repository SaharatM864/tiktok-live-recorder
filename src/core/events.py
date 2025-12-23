import asyncio
from typing import Callable, Dict, List, Any
from src.utils.logger_manager import logger


class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable):
        """Subscribe a handler to an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed to {event_type}")

    async def publish(self, event_type: str, data: Any = None):
        """Publish an event to all subscribers."""
        if event_type not in self._subscribers:
            return

        logger.info(f"Event published: {event_type}")

        # Run all handlers concurrently
        tasks = []
        for handler in self._subscribers[event_type]:
            tasks.append(asyncio.create_task(handler(data)))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


# Global Event Bus instance
event_bus = EventBus()


# Event Types
class Events:
    RECORDING_STARTED = "recording_started"
    RECORDING_FINISHED = "recording_finished"
    RECORDING_ERROR = "recording_error"
