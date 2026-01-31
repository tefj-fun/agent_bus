"""Redis client for task queue and caching."""

import redis.asyncio as redis
from typing import Optional
from ..config import settings


class RedisClient:
    """Redis client wrapper for agent_bus."""

    def __init__(self):
        self._client: Optional[redis.Redis] = None

    async def connect(self) -> redis.Redis:
        """Connect to Redis."""
        if self._client is None:
            # redis.asyncio.from_url returns a configured client (not awaitable)
            self._client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self._client

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

    async def get_client(self) -> redis.Redis:
        """Get Redis client instance."""
        if self._client is None:
            await self.connect()
        return self._client

    async def enqueue_task(self, queue_name: str, task_data: dict) -> str:
        """
        Add a task to a queue.

        Args:
            queue_name: Name of the queue
            task_data: Task data to enqueue

        Returns:
            Task ID
        """
        client = await self.get_client()
        task_id = task_data.get("task_id")

        # Push JSON to queue
        import json
        await client.lpush(queue_name, json.dumps(task_data))

        return task_id

    async def dequeue_task(self, queue_name: str, timeout: int = 5) -> Optional[dict]:
        """
        Remove and return a task from queue (blocking).

        Args:
            queue_name: Name of the queue
            timeout: Timeout in seconds

        Returns:
            Task data or None
        """
        client = await self.get_client()
        result = await client.brpop(queue_name, timeout=timeout)

        if result:
            _, task_data = result
            import json
            return json.loads(task_data)
        return None

    async def publish_event(self, channel: str, message: dict) -> None:
        """
        Publish an event to a channel.

        Args:
            channel: Channel name
            message: Message to publish
        """
        client = await self.get_client()
        await client.publish(channel, str(message))

    async def set_with_expiry(self, key: str, value: str, ttl: int) -> None:
        """
        Set a key with expiry.

        Args:
            key: Key name
            value: Value to set
            ttl: Time to live in seconds
        """
        client = await self.get_client()
        await client.setex(key, ttl, value)

    async def get(self, key: str) -> Optional[str]:
        """
        Get a value by key.

        Args:
            key: Key name

        Returns:
            Value or None
        """
        client = await self.get_client()
        return await client.get(key)


# Global Redis client instance
redis_client = RedisClient()
