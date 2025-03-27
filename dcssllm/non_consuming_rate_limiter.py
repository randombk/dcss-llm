import time
from langchain_core.rate_limiters import InMemoryRateLimiter

class NonConsumingRateLimiter(InMemoryRateLimiter):
    """
    A custom in memory rate limiter that creates a method
    to not consume tokens and simply check if there are enough tokens available.

    This is useful when we want to check multiple rate limiters, and only proceed
    with consuming tokens if all the rate limiters allow it.

    This does introduce a small race condition where a token might be consumed
    after the check, but it's OK in this context.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    
    def can_consume(self) -> bool:
        """Returns whether we can consume a token."""
        with self._consume_lock:
            now = time.monotonic()

            # initialize on first call to avoid a burst
            if self.last is None:
                self.last = now

            elapsed = now - self.last

            if elapsed * self.requests_per_second >= 1:
                self.available_tokens += elapsed * self.requests_per_second
                self.last = now

            # Make sure that we don't exceed the bucket size.
            # This is used to prevent bursts of requests.
            self.available_tokens = min(self.available_tokens, self.max_bucket_size)

            # As long as we have at least one token, we can proceed.
            return self.available_tokens >= 1