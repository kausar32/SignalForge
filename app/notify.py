"""Notification router: one signal is created once, then fanned out to its subscribers.

Each subscription lists the channels the user wants. A channel without a registered
handler is skipped, so adding Telegram later means registering one more handler.
"""

import logging
from typing import Protocol

from .domain import Signal
from .repository import Repository

log = logging.getLogger(__name__)


class Channel(Protocol):
    name: str

    def send(self, user_id: int, signal_id: int, signal: Signal) -> bool: ...


class InAppChannel:
    """Writes to the user's notification inbox."""

    name = "in_app"

    def __init__(self, repo: Repository) -> None:
        self.repo = repo

    def send(self, user_id: int, signal_id: int, signal: Signal) -> bool:
        self.repo.add_notification(user_id, signal_id, self.name)
        return True


def dispatch(signal_id: int, signal: Signal, repo: Repository, channels: dict[str, Channel]) -> int:
    """Deliver a signal to every subscriber of its asset. Returns deliveries made."""
    delivered = 0
    for sub in repo.subscriptions_for(signal.asset):
        for channel_name in sub.channels:
            handler = channels.get(channel_name)
            if handler is None:
                log.debug("No handler for channel '%s'; skipping user %s", channel_name, sub.user_id)
                continue
            try:
                if handler.send(sub.user_id, signal_id, signal):
                    delivered += 1
            except Exception:
                log.exception("Delivery failed: user=%s channel=%s", sub.user_id, channel_name)
    return delivered
