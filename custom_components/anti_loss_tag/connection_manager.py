# SPDX-License-Identifier: MIT
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

_LOGGER = logging.getLogger(__name__)


@dataclass
class AcquireResult:
    """Result of acquiring a global BLE connection slot."""

    acquired: bool
    reason: str | None = None


class BleConnectionManager:
    """
    全局 BLE 连接槽位管理器：
    - 用 Semaphore 控制“同时保持的 GATT 连接数”
    - 防止多设备同时 maintain_connection 时产生连接风暴，导致 out-of-slots/适配器不稳定
    """

    def __init__(self, max_connections: int) -> None:
        """Initialize connection slot manager."""
        self._max = max(1, int(max_connections))
        self._sem = asyncio.Semaphore(self._max)
        self._in_use = 0
        self._lock = asyncio.Lock()

    @property
    def max_connections(self) -> int:
        """Return configured maximum concurrent connections."""
        return self._max

    @property
    def in_use(self) -> int:
        """Return currently occupied connection slots."""
        return self._in_use

    async def acquire(self, *, timeout: float | None = 30.0) -> AcquireResult:
        """Acquire one slot, optionally timing out."""
        try:
            if timeout is None:
                await self._sem.acquire()
            else:
                await asyncio.wait_for(self._sem.acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            return AcquireResult(acquired=False, reason="timeout")
        except (OSError, RuntimeError) as err:
            return AcquireResult(acquired=False, reason=f"error:{err}")

        async with self._lock:
            self._in_use += 1
        return AcquireResult(acquired=True)

    async def release(self) -> None:
        """Release one previously acquired slot."""
        async with self._lock:
            if self._in_use > 0:
                self._in_use -= 1
        try:
            self._sem.release()
        except ValueError:
            # release 次数超了（理论不该发生），保护一下
            _LOGGER.debug("Semaphore released too many times; ignoring.")
