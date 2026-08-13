import time
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, HTTPException, status


class RateLimiter:
    """
    In-Memory Sliding Window Rate Limiter for FastAPI Endpoints.
    Prevents API spamming without external Redis dependency.
    """
    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.history: Dict[str, List[float]] = defaultdict(list)

    async def __call__(self, request: Request):
        # Identify client by IP address or auth header
        client_ip = request.client.host if request.client else "127.0.0.1"
        auth_header = request.headers.get("Authorization", "")
        identifier = f"{client_ip}:{auth_header[:30]}"

        now = time.time()
        cutoff = now - self.window_seconds

        # Clean old timestamps
        self.history[identifier] = [t for t in self.history[identifier] if t > cutoff]

        if len(self.history[identifier]) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - self.history[identifier][0]))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.max_requests} requests allowed per {self.window_seconds}s. Try again in {retry_after}s.",
                headers={"Retry-After": str(max(1, retry_after))}
            )

        self.history[identifier].append(now)


# Standard rate limit instances
incident_rate_limiter = RateLimiter(max_requests=5, window_seconds=60)
simulate_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
