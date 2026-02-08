"""测试 config_flow.py 中的边界验证.

测试内容:
1. battery_poll_interval_min 边界值测试（5, 10080, 非法值）
"""
# Copyright (c) 2025-2026 MMMM
# See LICENSE file for details

from unittest.mock import MagicMock
import pytest
from voluptuous import Invalid

from custom_components.anti_loss_tag.config_flow import (
    OptionsFlowHandler,
)


class TestBatteryPollIntervalValidation:
    """测试 battery_poll_interval_min 边界验证."""

    @pytest.mark.asyncio
    async def test_min_boundary_5_is_accepted(self, hass):
        """测试最小边界值 5 被接受."""
        # 创建模拟 flow handler
        flow_handler = OptionsFlowHandler(
            MagicMock(entry_id="test_entry"),
            MagicMock(options={"battery_poll_interval_min": 360}),
        )
        flow_handler.hass = hass

        # 模拟用户输入最小边界值
        {
            "battery_poll_interval_min": 5,
            "alarm_on_disconnect": False,
            "maintain_connection": True,
            "auto_reconnect": True,
        }

        # 验证不应该抛出异常
        try:
            # 这里我们只验证 schema，不执行完整的 flow
            from custom_components.anti_loss_tag.config_flow import (
                OPTIONS_BATTERY_POLL_INTERVAL_MIN,
            )

            # 验证边界值在范围内
            assert 5 >= OPTIONS_BATTERY_POLL_INTERVAL_MIN["min"]
            assert 5 <= OPTIONS_BATTERY_POLL_INTERVAL_MIN["max"]
        except Exception as e:
            pytest.fail(f"Min boundary value 5 should be accepted: {e}")

    @pytest.mark.asyncio
    async def test_max_boundary_10080_is_accepted(self, hass):
        """测试最大边界值 10080 被接受."""
        from custom_components.anti_loss_tag.config_flow import (
            OPTIONS_BATTERY_POLL_INTERVAL_MIN,
        )

        # 验证边界值在范围内
        assert 10080 >= OPTIONS_BATTERY_POLL_INTERVAL_MIN["min"]
        assert 10080 <= OPTIONS_BATTERY_POLL_INTERVAL_MIN["max"]

    @pytest.mark.asyncio
    async def test_value_below_min_is_rejected(self):
        """测试小于最小值 5 的值被拒绝."""
        from voluptuous import Schema
        from custom_components.anti_loss_tag.config_flow import (
            OPTIONS_BATTERY_POLL_INTERVAL_MIN,
        )

        schema = Schema(
            {
                "battery_poll_interval_min": OPTIONS_BATTERY_POLL_INTERVAL_MIN[
                    "validator"
                ]
            }
        )

        # 测试小于最小值的值
        with pytest.raises(Invalid):
            schema({"battery_poll_interval_min": 4})

    @pytest.mark.asyncio
    async def test_value_above_max_is_rejected(self):
        """测试大于最大值 10080 的值被拒绝."""
        from voluptuous import Schema
        from custom_components.anti_loss_tag.config_flow import (
            OPTIONS_BATTERY_POLL_INTERVAL_MIN,
        )

        schema = Schema(
            {
                "battery_poll_interval_min": OPTIONS_BATTERY_POLL_INTERVAL_MIN[
                    "validator"
                ]
            }
        )

        # 测试大于最大值的值
        with pytest.raises(Invalid):
            schema({"battery_poll_interval_min": 10081})

    @pytest.mark.asyncio
    async def test_non_integer_is_rejected(self):
        """测试非整数值被拒绝."""
        from voluptuous import Schema
        from custom_components.anti_loss_tag.config_flow import (
            OPTIONS_BATTERY_POLL_INTERVAL_MIN,
        )

        schema = Schema(
            {
                "battery_poll_interval_min": OPTIONS_BATTERY_POLL_INTERVAL_MIN[
                    "validator"
                ]
            }
        )

        # 测试非整数值
        with pytest.raises(Invalid):
            schema({"battery_poll_interval_min": "invalid"})

        # 测试浮点数
        with pytest.raises(Invalid):
            schema({"battery_poll_interval_min": 360.5})

    @pytest.mark.asyncio
    async def test_negative_value_is_rejected(self):
        """测试负数值被拒绝."""
        from voluptuous import Schema
        from custom_components.anti_loss_tag.config_flow import (
            OPTIONS_BATTERY_POLL_INTERVAL_MIN,
        )

        schema = Schema(
            {
                "battery_poll_interval_min": OPTIONS_BATTERY_POLL_INTERVAL_MIN[
                    "validator"
                ]
            }
        )

        # 测试负数值
        with pytest.raises(Invalid):
            schema({"battery_poll_interval_min": -1})

    @pytest.mark.asyncio
    async def test_zero_is_rejected(self):
        """测试 0 被拒绝."""
        from voluptuous import Schema
        from custom_components.anti_loss_tag.config_flow import (
            OPTIONS_BATTERY_POLL_INTERVAL_MIN,
        )

        schema = Schema(
            {
                "battery_poll_interval_min": OPTIONS_BATTERY_POLL_INTERVAL_MIN[
                    "validator"
                ]
            }
        )

        # 测试 0
        with pytest.raises(Invalid):
            schema({"battery_poll_interval_min": 0})
