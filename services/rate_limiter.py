import time
import logging
import asyncio
from collections import deque
import config

logger = logging.getLogger(__name__)

class RateLimiter:
    """Class to handle rate limiting for API requests"""
    
    _instances = {}
    
    def __new__(cls, platform):
        """Implement as singleton per platform"""
        if platform not in cls._instances:
            cls._instances[platform] = super(RateLimiter, cls).__new__(cls)
            cls._instances[platform].platform = platform
            cls._instances[platform].window = config.RATE_LIMIT_WINDOW
            cls._instances[platform].max_requests = config.RATE_LIMIT_MAX_REQUESTS.get(platform, 10)
            cls._instances[platform].request_times = deque()
            cls._instances[platform].logger = logging.getLogger(f"{__name__}.{platform}")
        return cls._instances[platform]
    
    async def wait(self):
        """
        Asynchronously wait if rate limit is reached
        
        Returns:
            bool: True if waited, False otherwise
        """
        now = time.time()
        
        # Remove timestamps older than the window
        while self.request_times and now - self.request_times[0] > self.window:
            self.request_times.popleft()
        
        # If we've hit the rate limit, wait until oldest request expires
        if len(self.request_times) >= self.max_requests:
            wait_time = self.window - (now - self.request_times[0])
            if wait_time > 0:
                self.logger.info(f"Rate limit reached for {self.platform}. Waiting {wait_time:.2f} seconds.")
                await asyncio.sleep(wait_time)
                # Recursively check again after waiting
                return await self.wait()
        
        # Add current request time
        self.request_times.append(time.time())
        return False
    
    def wait_blocking(self):
        """
        Synchronously wait if rate limit is reached
        
        Returns:
            bool: True if waited, False otherwise
        """
        now = time.time()
        
        # Remove timestamps older than the window
        while self.request_times and now - self.request_times[0] > self.window:
            self.request_times.popleft()
        
        # If we've hit the rate limit, wait until oldest request expires
        if len(self.request_times) >= self.max_requests:
            wait_time = self.window - (now - self.request_times[0])
            if wait_time > 0:
                self.logger.info(f"Rate limit reached for {self.platform}. Waiting {wait_time:.2f} seconds.")
                time.sleep(wait_time)
                # Recursively check again after waiting
                return self.wait_blocking()
        
        # Add current request time
        self.request_times.append(time.time())
        return False
    
    def get_current_rate(self):
        """
        Get current request rate
        
        Returns:
            tuple: (current_count, max_requests, reset_time)
        """
        now = time.time()
        
        # Remove timestamps older than the window
        while self.request_times and now - self.request_times[0] > self.window:
            self.request_times.popleft()
        
        current_count = len(self.request_times)
        reset_time = self.request_times[0] + self.window if self.request_times else now
        
        return (current_count, self.max_requests, reset_time)
