# SPDX-License-Identifier: MIT
"""常量定义模块。"""

from __future__ import annotations

# 电量轮询相关
BATTERY_POLL_JITTER_SECONDS = 30  # 抖动秒数
MIN_BATTERY_POLL_INTERVAL_MIN = 5  # 最小轮询间隔（分钟）
MAX_BATTERY_POLL_INTERVAL_MIN = 7 * 24 * 60  # 最大轮询间隔（7天，分钟）

# 连接退避相关
MIN_CONNECT_BACKOFF_SECONDS = 2  # 最小退避时间（秒）
MAX_CONNECT_BACKOFF_SECONDS = 60  # 最大退避时间（秒）
MAX_CONNECT_FAIL_COUNT = 6  # 最大失败计数（2^6 = 64秒）

# BLE 连接相关
DEFAULT_BLEAK_TIMEOUT = 20.0  # 默认 bleak 超时（秒）
CONNECTION_SLOT_ACQUIRE_TIMEOUT = 20.0  # 连接槽位获取超时（秒）

# 更新防抖动
ENTITY_UPDATE_DEBOUNCE_SECONDS = 1.0  # 实体更新防抖动时间（秒）
