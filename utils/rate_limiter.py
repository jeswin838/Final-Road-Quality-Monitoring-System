import time
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Ensures that calls to a function do not exceed a specified rate.
    Uses a token bucket or simple last_call timestamp.
    """
    def __init__(self, calls_per_second: float):
        self.interval = 1.0 / calls_per_second
        self.last_call = 0.0

    def wait(self):
        """Block until it's safe to make the next call."""
        now = time.time()
        elapsed = now - self.last_call
        if elapsed < self.interval:
            time.sleep(self.interval - elapsed)
        self.last_call = time.time()
