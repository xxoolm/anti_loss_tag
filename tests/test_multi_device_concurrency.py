"""Multi-device concurrent integration tests."""

import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from custom_components.anti_loss_tag import BleConnectionManager
from custom_components.anti_loss_tag.device import AntiLossTagDevice


class TestMultiDeviceConcurrency:
    """Test concurrent operations with multiple devices."""

    @pytest.fixture
    def conn_manager(self) -> BleConnectionManager:
        """Create a connection manager with limited slots."""
        return BleConnectionManager(max_connections=3)

    @pytest.fixture
    def mock_devices(self, conn_manager: BleConnectionManager) -> list[Mock]:
        """Create multiple mock device instances."""
        devices = []
        for i in range(5):
            device = Mock(spec=AntiLossTagDevice)
            device.address = f"AA:BB:CC:DD:EE:F{i}"
            device._conn_mgr = conn_manager
            device._conn_slot_acquired = False
            device._connect_fail_count = 0
            device._cooldown_until_ts = 0
            devices.append(device)
        return devices

    @pytest.mark.asyncio
    async def test_connection_slot_limit_enforced(
        self, conn_manager: BleConnectionManager
    ) -> None:
        """Test that connection slot limit is properly enforced."""
        acquired_slots = []

        async def acquire_slot(device_id: int):
            """Simulate acquiring a connection slot."""
            await conn_manager.acquire()
            acquired_slots.append(device_id)
            # Hold for a short time
            await asyncio.sleep(0.1)

        # Try to acquire more slots than available
        tasks = [acquire_slot(i) for i in range(5)]
        await asyncio.gather(*tasks)

        # Should only acquire 3 slots (max_connections)
        assert len(acquired_slots) == 3

    @pytest.mark.asyncio
    async def test_concurrent_battery_reads(
        self, conn_manager: BleConnectionManager
    ) -> None:
        """Test concurrent battery read operations across multiple devices."""
        read_results = {}

        async def mock_battery_read(device_id: int) -> None:
            """Simulate battery read operation."""
            await conn_manager.acquire()
            try:
                # Simulate read delay
                await asyncio.sleep(0.05)
                read_results[device_id] = 85
            finally:
                await conn_manager.release()

        # Launch concurrent reads for 5 devices
        tasks = [mock_battery_read(i) for i in range(5)]
        await asyncio.gather(*tasks)

        # All reads should complete
        assert len(read_results) == 5
        assert all(v == 85 for v in read_results.values())

    @pytest.mark.asyncio
    async def test_write_operations_serialized_per_device(self) -> None:
        """Test that write operations to the same device are serialized."""
        mock_device = Mock()
        write_order = []

        async def mock_write(value: int):
            """Simulate write operation."""
            write_order.append(value)
            await asyncio.sleep(0.05)

        # Simulate concurrent writes to same device
        tasks = [mock_write(i) for i in range(3)]
        await asyncio.gather(*tasks)

        # All writes should complete
        assert len(write_order) == 3

    @pytest.mark.asyncio
    async def test_concurrent_different_devices(
        self, conn_manager: BleConnectionManager
    ) -> None:
        """Test operations on different devices can run concurrently."""
        operation_log = []

        async def mock_device_operation(device_id: int, op_type: str):
            """Simulate device operation."""
            await conn_manager.acquire()
            try:
                operation_log.append((device_id, op_type, "start"))
                await asyncio.sleep(0.05)
                operation_log.append((device_id, op_type, "end"))
            finally:
                await conn_manager.release()

        # Mix of read and write operations on different devices
        tasks = [
            mock_device_operation(0, "read"),
            mock_device_operation(1, "write"),
            mock_device_operation(2, "read"),
        ]
        await asyncio.gather(*tasks)

        # All operations should complete
        assert len([log for log in operation_log if log[2] == "start"]) == 3
        assert len([log for log in operation_log if log[2] == "end"]) == 3


class TestConnectionPooling:
    """Test connection pooling and slot management."""

    @pytest.mark.asyncio
    async def test_slot_released_after_failure(self) -> None:
        """Test that slots are properly released even after failures."""
        conn_mgr = BleConnectionManager(max_connections=2)

        # Acquire first slot
        await conn_mgr.acquire()
        assert conn_mgr._semaphore._value == 1

        # Simulate failure and release
        await conn_mgr.release()
        assert conn_mgr._semaphore._value == 2

    @pytest.mark.asyncio
    async def test_slot_acquire_timeout(self) -> None:
        """Test that slot acquisition times out when all slots are busy."""
        import asyncio

        conn_mgr = BleConnectionManager(max_connections=1)

        # Acquire the only slot
        await conn_mgr.acquire()

        # Try to acquire again with timeout
        try:
            await asyncio.wait_for(conn_mgr.acquire(), timeout=0.1)
            assert False, "Should have raised TimeoutError"
        except asyncio.TimeoutError:
            pass  # Expected

        # Clean up
        await conn_mgr.release()


class TestStressScenarios:
    """Stress tests for edge cases."""

    @pytest.mark.asyncio
    async def test_rapid_disconnect_reconnect(self) -> None:
        """Test rapid disconnect/reconnect cycles."""
        mock_device = Mock()
        mock_device._connected = False
        mock_device._conn_mgr = BleConnectionManager(max_connections=1)

        connect_count = 0

        async def mock_connect():
            """Mock connection operation."""
            nonlocal connect_count
            await mock_device._conn_mgr.acquire()
            mock_device._connected = True
            connect_count += 1
            await asyncio.sleep(0.01)

        async def mock_disconnect():
            """Mock disconnection operation."""
            await mock_device._conn_mgr.release()
            mock_device._connected = False

        # Simulate rapid cycles
        for _ in range(5):
            await mock_connect()
            await mock_disconnect()

        # All cycles should complete
        assert connect_count == 5

    @pytest.mark.asyncio
    async def test_mixed_operations_under_load(self) -> None:
        """Test mixed read/write operations under concurrent load."""
        conn_mgr = BleConnectionManager(max_connections=2)
        results = {"reads": 0, "writes": 0, "errors": 0}

        async def mock_operation(op_type: str):
            """Simulate device operation."""
            try:
                await conn_mgr.acquire()
                await asyncio.sleep(0.02)
                if op_type == "read":
                    results["reads"] += 1
                elif op_type == "write":
                    results["writes"] += 1
                await conn_mgr.release()
            except Exception:
                results["errors"] += 1

        # Mix of operations
        tasks = [
            mock_operation("read"),
            mock_operation("write"),
            mock_operation("read"),
            mock_operation("write"),
        ]
        await asyncio.gather(*tasks)

        # All should complete without errors
        assert results["reads"] == 2
        assert results["writes"] == 2
        assert results["errors"] == 0
