import time
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, HTTPException, status

class RateLimiter:
    """
    In-memory rate limiter tracking requests by key (IP / identifier) within a time window.
    """
    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def check_rate_limit(self, key: str):
        now = time.time()
        # Clean up timestamps outside window
        self.requests[key] = [t for t in self.requests[key] if now - t < self.window_seconds]

        if len(self.requests[key]) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests. Limit is {self.max_requests} requests per {self.window_seconds} seconds. Please wait before trying again."
            )
        self.requests[key].append(now)


login_rate_limiter = RateLimiter(max_requests=5, window_seconds=60)
reset_rate_limiter = RateLimiter(max_requests=3, window_seconds=300)
