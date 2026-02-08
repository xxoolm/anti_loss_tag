# SPDX-License-Identifier: MIT
# Copyright (c) 2025-2026 MMMM
# See LICENSE file for details
from __future__ import annotations

import asyncio
import logging
import time
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
        self._acquire_total = 0
        self._acquire_timeout = 0
        self._acquire_error = 0
        self._acquire_wait_total = 0.0

    @property
    def max_connections(self) -> int:
        """Return configured maximum concurrent connections."""
        return self._max

    @property
    def in_use(self) -> int:
        """Return currently occupied connection slots."""
        return self._in_use

    @property
    def acquire_total(self) -> int:
        """Return total acquire attempts."""
        return self._acquire_total

    @property
    def acquire_timeout(self) -> int:
        """Return number of acquire timeouts."""
        return self._acquire_timeout

    @property
    def acquire_error(self) -> int:
        """Return number of acquire errors."""
        return self._acquire_error

    @property
    def average_wait_ms(self) -> float:
        """Return average successful acquire wait time in milliseconds."""
        success = self._acquire_total - self._acquire_timeout - self._acquire_error
        if success <= 0:
            return 0.0
        return (self._acquire_wait_total / success) * 1000.0

    async def acquire(self, *, timeout: float | None = 30.0) -> AcquireResult:
        """Acquire one slot, optionally timing out."""
        start = time.monotonic()
        self._acquire_total += 1
        try:
            if timeout is None:
                await self._sem.acquire()
            else:
                await asyncio.wait_for(self._sem.acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            self._acquire_timeout += 1
            return AcquireResult(acquired=False, reason="timeout")
        except (OSError, RuntimeError) as err:
            self._acquire_error += 1
            return AcquireResult(acquired=False, reason=f"error:{err}")

        self._acquire_wait_total += max(0.0, time.monotonic() - start)
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
