"""Shared health state between Discord bot and web server."""
import threading
from datetime import datetime, timedelta

# Grace period for startup - don't fail health checks until bot has had time to connect
STARTUP_GRACE_SECONDS = 60

class HealthState:
    """Thread-safe health state for the application."""

    def __init__(self):
        self._lock = threading.Lock()
        self._discord_connected = False
        self._last_connected_at = None
        self._last_disconnected_at = None
        self._startup_time = datetime.utcnow()

    def set_connected(self):
        """Mark Discord as connected."""
        with self._lock:
            self._discord_connected = True
            self._last_connected_at = datetime.utcnow()

    def set_disconnected(self):
        """Mark Discord as disconnected."""
        with self._lock:
            self._discord_connected = False
            self._last_disconnected_at = datetime.utcnow()

    @property
    def is_discord_connected(self) -> bool:
        """Check if Discord is connected."""
        with self._lock:
            return self._discord_connected

    def _is_in_startup_grace_period(self) -> bool:
        """Check if we're still in the startup grace period."""
        return datetime.utcnow() < self._startup_time + timedelta(seconds=STARTUP_GRACE_SECONDS)

    def is_healthy(self) -> bool:
        """Check if the application is healthy.

        Returns True if:
        - Discord is connected, OR
        - We're still in the startup grace period (bot hasn't had time to connect yet)
        """
        with self._lock:
            if self._discord_connected:
                return True
            # During startup, give the bot time to connect
            if self._is_in_startup_grace_period():
                return True
            return False

    def get_status(self) -> dict:
        """Get full health status."""
        with self._lock:
            in_grace_period = self._is_in_startup_grace_period()
            return {
                'discord_connected': self._discord_connected,
                'last_connected_at': self._last_connected_at.isoformat() if self._last_connected_at else None,
                'last_disconnected_at': self._last_disconnected_at.isoformat() if self._last_disconnected_at else None,
                'startup_grace_period': in_grace_period,
            }

# Global singleton instance
health_state = HealthState()
