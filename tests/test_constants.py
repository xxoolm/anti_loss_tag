"""测试常量定义."""
# Copyright (c) 2025-2026 MMMM
# See LICENSE file for details

from custom_components.anti_loss_tag.utils.constants import (
    # BLE 配置
    DEFAULT_BLEAK_TIMEOUT,
    CONNECTION_SLOT_ACQUIRE_TIMEOUT,
    # 电池轮询
    BATTERY_POLL_JITTER_SECONDS,
    MIN_BATTERY_POLL_INTERVAL_MIN,
    MAX_BATTERY_POLL_INTERVAL_MIN,
    # 连接退避
    MIN_CONNECT_BACKOFF_SECONDS,
    MAX_CONNECT_BACKOFF_SECONDS,
    MAX_CONNECT_FAIL_COUNT,
    # 实体更新
    ENTITY_UPDATE_DEBOUNCE_SECONDS,
)


class TestBLETimeouts:
    """测试 BLE 超时配置."""

    def test_bleak_timeout_is_positive(self):
        """测试 bleak 超时是正数."""
        assert DEFAULT_BLEAK_TIMEOUT > 0
        assert DEFAULT_BLEAK_TIMEOUT == 20.0

    def test_connection_slot_timeout_is_positive(self):
        """测试连接槽位超时是正数."""
        assert CONNECTION_SLOT_ACQUIRE_TIMEOUT > 0
        assert CONNECTION_SLOT_ACQUIRE_TIMEOUT == 20.0


class TestBatteryPolling:
    """测试电池轮询配置."""

    def test_poll_interval_is_reasonable(self):
        """测试轮询间隔是合理的."""
        # 轮询间隔应该在 5 分钟到 24 小时之间
        assert MIN_BATTERY_POLL_INTERVAL_MIN >= 5
        assert MAX_BATTERY_POLL_INTERVAL_MIN <= 7 * 24 * 60  # 7 天
        assert MIN_BATTERY_POLL_INTERVAL_MIN < MAX_BATTERY_POLL_INTERVAL_MIN

    def test_jitter_is_reasonable(self):
        """测试抖动时间是合理的."""
        assert BATTERY_POLL_JITTER_SECONDS >= 0
        assert BATTERY_POLL_JITTER_SECONDS <= 60  # 最多 1 分钟抖动


class TestConnectBackoff:
    """测试连接退避配置."""

    def test_backoff_range_is_valid(self):
        """测试退避范围是有效的."""
        assert MIN_CONNECT_BACKOFF_SECONDS < MAX_CONNECT_BACKOFF_SECONDS
        assert MIN_CONNECT_BACKOFF_SECONDS >= 1
        assert MAX_CONNECT_BACKOFF_SECONDS <= 300  # 最多 5 分钟

    def test_max_fail_count_is_positive(self):
        """测试最大失败次数是正数."""
        assert MAX_CONNECT_FAIL_COUNT > 0
        assert MAX_CONNECT_FAIL_COUNT <= 10  # 最多 10 次


class TestEntityUpdateDebounce:
    """测试实体更新防抖动."""

    def test_debounce_is_positive(self):
        """测试防抖动时间是正数."""
        assert ENTITY_UPDATE_DEBOUNCE_SECONDS > 0
        assert ENTITY_UPDATE_DEBOUNCE_SECONDS <= 5.0  # 最多 5 秒


class TestConstantTypes:
    """测试常量类型."""

    def test_timeout_constants_are_floats(self):
        """测试超时常量是浮点数."""
        assert isinstance(DEFAULT_BLEAK_TIMEOUT, float)
        assert isinstance(CONNECTION_SLOT_ACQUIRE_TIMEOUT, float)
        assert isinstance(ENTITY_UPDATE_DEBOUNCE_SECONDS, float)

    def test_interval_constants_are_ints(self):
        """测试间隔常量是整数."""
        assert isinstance(BATTERY_POLL_JITTER_SECONDS, int)
        assert isinstance(MIN_BATTERY_POLL_INTERVAL_MIN, int)
        assert isinstance(MAX_BATTERY_POLL_INTERVAL_MIN, int)
        assert isinstance(MIN_CONNECT_BACKOFF_SECONDS, int)
        assert isinstance(MAX_CONNECT_BACKOFF_SECONDS, int)
        assert isinstance(MAX_CONNECT_FAIL_COUNT, int)
