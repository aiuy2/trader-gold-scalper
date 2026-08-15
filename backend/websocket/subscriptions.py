"""subscriptions.py - lets a WebSocket client opt into specific topics
(trades, positions, notifications) instead of receiving every event."""
import threading

ALL_TOPICS = {"trades", "positions", "bot_status", "notifications"}


class SubscriptionRegistry:
    def __init__(self):
        self._subs: dict = {}  # websocket -> set[topic]
        self._lock = threading.Lock()

    def subscribe(self, websocket, topics):
        topics = set(topics) & ALL_TOPICS
        with self._lock:
            self._subs[websocket] = topics

    def is_subscribed(self, websocket, topic: str) -> bool:
        with self._lock:
            return topic in self._subs.get(websocket, ALL_TOPICS)

    def drop(self, websocket):
        with self._lock:
            self._subs.pop(websocket, None)


subscriptions = SubscriptionRegistry()
