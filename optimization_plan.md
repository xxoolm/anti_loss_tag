# Home Assistant KT6368A 防丢标签集成 - 优化方案（审校更正版）

## 文档信息

- 版本: v2.1.0（审校更正）
- 日期: 2026-02-09
- 适用范围: `custom_components/anti_loss_tag/`
- 目标: 在现有架构上提升可靠性、可观测性、可测试性

---

## 0. 审核结论（基于官方文档 + 当前代码）

本次对旧版 `optimization_plan.md` 做了官方文档核对和技术纠偏，主要更正如下：

1. 移除不准确或不可执行示例
   - 原文包含无效Python标识符（如 `MULTI Characteristics`）和不可靠前提（依赖 `BleakError.code`）。
   - 现改为可落地的实现建议：优先按异常类型分流，必要时保留消息关键词回退。

2. 与 Bleak 官方行为对齐
   - 官方明确：同UUID多特征时，UUID寻址会失败，应使用特征对象（或先解析handle再读写）。
   - `services` 仅在连接期间有效，且需完成服务发现。
   - `write_gatt_char` 常见异常包含 `BleakCharacteristicNotFoundError` 和 `BleakGATTProtocolError`。

3. 与 Home Assistant Integration Quality Scale 对齐
   - 增补并强化以下规则落地：
     - `log-when-unavailable`
     - `parallel-updates`
     - `runtime-data`

4. 删除缺乏基线数据支撑的收益百分比
   - 改为“可测量目标 + 验证方法”，避免拍脑袋数字。

---

## 1. 当前实现基线（来自现有代码）

### 1.1 配置与选项

- 常量配置（`const.py`）
  - `DEFAULT_MAINTAIN_CONNECTION = True`
  - `DEFAULT_AUTO_RECONNECT = True`
  - `DEFAULT_BATTERY_POLL_INTERVAL_MIN = 360`
- Options Flow（`config_flow.py`）
  - `battery_poll_interval_min` 已有限制：`5 ~ 10080` 分钟

### 1.2 连接与写入关键流程

- `async_ensure_connected()` 已有：连接锁、全局连接槽位、超时与退避
- `_async_write_bytes()` 已有：
  - 优先/降级 response 写入策略
  - 同UUID多特征时刷新服务并解析handle重试
- `async_read_battery()` 已有：读失败时按同逻辑降级重试

### 1.3 已修复关键回归

- “多特征UUID错误消息匹配”由中文判断改为英文关键词判断
- 服务刷新由 `client.services` 改为 `await client.get_services()`

### 1.4 旧版本可复用实践（来自 `/home/qq/anti_loss_tag_v2/`）

以下实践已在旧版本验证有效，可作为本方案实施时的参考基线：

1. `ble.py` 的单设备串行化模型
   - `BleTagBle` 使用单个 `asyncio.Lock()` 串行化同设备的 connect/read/write。
   - 优点：并发模型简单，竞态少，问题可定位。

2. `ble.py` 的短连接上下文管理
   - 通过 `async with client:` 保证每次操作后释放连接。
   - 优点：资源生命周期清晰，异常时不易遗留脏连接。
   - 注意：当前主架构是长连接，不能直接回退为全量短连接；可用于“失败兜底路径”借鉴。

3. `coordinator.py` 的在线状态重算与缓存策略
   - 广播回调更新 RSSI/last_seen，统一经 `_recalc_online()` 计算在线状态。
   - 电量读取使用时间缓存（`DEFAULT_BATTERY_CACHE_SECONDS`）降低GATT压力。
   - 优点：状态更新单入口，行为可预测。

---

## 2. 优化目标（以可验证为准）

不再使用主观百分比，改为以下可测目标：

1. 稳定性目标
   - 30分钟压力测试内，无未捕获异常导致实体长期不可用
2. 可观测性目标
   - 设备离线仅记录一次不可用日志，恢复时记录一次恢复日志
3. 回归目标
   - 针对“同UUID多特征”和“断连后写入”补齐自动化测试
4. 兼容性目标
   - 不改变现有配置键与实体唯一ID策略

---

## 3. 优化方案（纠偏后）

### 3.1 错误降级与重试策略（高优先级）

#### A. 保留现有双通道写入策略并标准化

- 统一写入顺序：
  1) 使用 `prefer_response`
  2) 失败后反向 `not prefer_response`
  3) 两次都失败则记录 `_last_error` 并抛出
- 目的：减少不同固件对写入类型支持差异带来的失败。

#### B. 同UUID多特征处理策略收敛

- 官方依据：Bleak文档明确同UUID可能失败，建议特征对象/handle。
- 实施要点：
  - 保留当前“捕获错误后 `get_services()` + handle重试”路径。
  - 进一步减少对错误消息文本依赖：
    - 第一优先：已知异常类型（若版本可用）
    - 第二优先：包含 `Multiple Characteristics` 关键词
  - 将该逻辑封装为单独私有函数，读写共用，避免分叉回归。

#### C. 断连场景的一次性自愈重连

- 场景：`_client is None` 且操作来自button/switch服务调用。
- 策略：
  - 在单次业务调用内最多触发一次 `async_ensure_connected()`。
  - 若仍失败，返回明确错误，不进入无限重连。

#### D. 引入“旧版短连接兜底”作为最后一层降级（可选）

- 参考来源：旧版 `ble.py` 的 `async with client` 模式。
- 建议策略：
  - 仅在“长连接路径失败且本次调用允许重试”时，尝试一次短连接写入兜底。
  - 兜底成功后回到主路径，不改变默认长连接策略。
  - 兜底必须受 `_gatt_lock` 和重试次数上限约束，避免放大并发。
- 适用场景：蓝牙栈临时状态异常、连接对象失效但地址可直连。

### 3.2 防呆与边界设计（高优先级）

#### A. 并发边界明确化

- 现有 `_gatt_lock` 继续作为单设备GATT串行化保证。
- 将“可重入调用”入口统一到公共写接口，避免新功能绕过锁。

#### B. 状态一致性检查（轻量）

- 在调试级日志中输出关键状态组合：
  - `_connected`
  - `_client is None`
  - `_conn_slot_acquired`
- 不建议在生产路径大量 `assert`，避免误触发导致服务中断。

补充参考（旧版 `coordinator.py`）：
- 建议将“在线状态计算”收敛为单入口函数，避免在多处分散修改在线标记。
- 建议保留并明确“电量缓存窗口”语义，避免频繁读取导致设备负载上升。

#### C. 选项边界保持与补测

- 保持 `battery_poll_interval_min` 的现有范围 `5~10080`。
- 为极值增加测试：`5`、`10080`、非法值（<5、>10080、非整型）。

### 3.3 Home Assistant 质量规则对齐（高优先级）

#### A. `log-when-unavailable`

- 要求：不可用时记录一次，恢复时记录一次，级别建议 `info`。
- 落地：为设备对象增加“已记录不可用”标记位，避免日志刷屏。

#### B. `parallel-updates`

- 要求：显式设置 `PARALLEL_UPDATES`。
- 落地建议：
  - 读类平台可考虑 `PARALLEL_UPDATES = 0`（如果更新已集中管理）。
  - 触发动作的平台根据设备能力限制为 `1` 更稳妥。

#### C. `runtime-data`

- 要求：运行时对象存放到 `ConfigEntry.runtime_data`。
- 落地建议：将 `AntiLossTagDevice` / manager对象收敛到 `runtime_data`，减少 `hass.data` 分散状态。

---

### 3.4 代码位置与关键优化点（逐文件、可执行）

以下位置基于当前代码快照，实施时请以函数名优先定位，行号作为辅助。

#### A. `custom_components/anti_loss_tag/device.py`

1. 连接生命周期与回调
   - 位置：`_on_disconnect`（约 `device.py:416`）
   - 关键点：
     - 断连时必须原子清理 `_client`、连接槽位占用标记、特征缓存。
     - 增加“不可用日志只打一次，恢复再打一条”的状态位（对齐 `log-when-unavailable`）。
   - 验收：连续断连场景无日志刷屏；恢复后有单条恢复日志。

2. 连接建立主路径
   - 位置：`async_ensure_connected`（约 `device.py:446`）
   - 关键点：
     - 保持连接锁与全局连接槽位语义不变。
     - 明确“单次调用最多一次自愈重连”，避免按钮/开关触发无限重试。
     - 将“服务发现失败后的资源释放”作为硬约束（失败即释放槽位）。
   - 验收：连接失败不泄漏槽位；重试次数受控；错误信息可操作。

3. 报警与策略写入入口
   - 位置：
     - `async_start_alarm`（约 `device.py:685`）
     - `async_stop_alarm`（约 `device.py:693`）
     - `async_set_disconnect_alarm_policy`（约 `device.py:701`）
   - 关键点：
     - 三个入口都必须收敛到统一写入通道 `_async_write_bytes`，不得新增绕过锁的写入路径。
     - 断连下统一走“最多一次自愈重连 + 明确失败返回”。
   - 验收：按钮/开关所有写入路径行为一致，失败语义一致。

4. 电量读取
   - 位置：`async_read_battery`（约 `device.py:718`）
   - 关键点：
     - 保留“同UUID多特征 -> `get_services()` -> handle重试”降级链。
     - 明确 force_connect 行为边界：仅在调用方要求时主动连。
     - 电量值继续夹紧 `0..100`，异常必须写 `_last_error`。
   - 验收：多特征设备可稳定读取；非法电量不污染状态。

5. 核心写入函数（最高优先）
   - 位置：`_async_write_bytes`（约 `device.py:770`）
   - 关键点：
     - 固化写入顺序：`prefer_response` -> 反向 response。
     - 同UUID多特征逻辑抽成单私有函数，读写共用，避免后续再分叉。
     - 可选兜底：仅在本次调用内允许一次“短连接写入兜底”（参考旧版 `ble.py`），且必须受 `_gatt_lock` 与重试上限约束。
   - 验收：
     - `Multiple Characteristics` 场景可自动回退。
     - 断连写入不会出现无限重试或锁竞争放大。

6. 后台轮询
   - 位置：`_async_battery_loop`（约 `device.py:832`）
   - 关键点：
     - 保留随机抖动，避免多设备同秒轮询。
     - 捕获异常后仅更新错误状态，不允许任务静默退出（`CancelledError` 除外）。
   - 验收：长时间运行任务稳定，不因偶发异常停止轮询。

#### B. `custom_components/anti_loss_tag/button.py`

1. 按钮动作调用链
   - 位置：
     - `AntiLossTagStartAlarmButton.async_press`（约 `button.py:57`）
     - `AntiLossTagStopAlarmButton.async_press`（约 `button.py:67`）
   - 关键点：
     - 按钮仅调用 device 层API，不在实体层做连接逻辑。
     - 明确错误透传策略：失败抛出由 HA 服务层处理，不吞异常。
   - 验收：实体层保持薄封装，无重复连接代码。

#### C. `custom_components/anti_loss_tag/switch.py`

1. 选项更新与设备写入一致性
   - 位置：
     - `async_turn_on`（约 `switch.py:48`）
     - `async_turn_off`（约 `switch.py:58`）
   - 关键点：
     - `async_update_entry` 与设备写入的先后关系需明确（建议记录失败补偿策略）。
     - 失败时要有可诊断日志，避免“UI已改但设备未改”无提示。
   - 验收：配置与设备状态一致性可追踪，可回放。

#### D. `custom_components/anti_loss_tag/config_flow.py`

1. 选项边界校验
   - 位置：`OptionsFlowHandler.async_step_init`（约 `config_flow.py:167`，`vol.Range` 在约 `197`）
   - 关键点：
     - 保持 `battery_poll_interval_min` 范围 `5..10080`。
     - 补齐边界测试：`5`、`10080`、`4`、`10081`、非整型。
   - 验收：非法输入稳定拦截，错误提示明确。

#### E. `custom_components/anti_loss_tag/__init__.py` 与运行时数据

1. runtime_data 与全局对象边界
   - 位置：
     - `entry.runtime_data = device`（约 `__init__.py:35`）
     - `_conn_mgr` 初始化（约 `__init__.py:32`）
   - 关键点：
     - 设备实例继续走 `entry.runtime_data`（已符合 IQS）。
     - `hass.data[DOMAIN]["_conn_mgr"]` 作为全局连接池可保留，但需文档明确“全局共享”的并发语义。
   - 验收：多entry下连接池行为可预测，无跨设备污染。

#### F. 平台并发声明（当前缺口）

1. `PARALLEL_UPDATES`
   - 位置：平台文件当前未声明（`grep` 结果为空）
   - 涉及文件：`sensor.py`、`binary_sensor.py`、`switch.py`、`button.py`、`event.py`
   - 关键点：
     - 显式声明并发策略，避免默认行为不透明。
     - 建议按平台能力设定（读类可偏保守，动作类建议 `1`）。
   - 验收：并发行为可控，无突发并发写入导致的不稳定。

#### G. 旧版本参考映射（仅作设计借鉴）

1. `anti_loss_tag_v2/ble.py`
   - 借鉴点：`asyncio.Lock` + `async with client` 的短连接兜底模式。
   - 落地位置：`device.py::_async_write_bytes` 的最后一层可选降级。

2. `anti_loss_tag_v2/coordinator.py`
   - 借鉴点：`_recalc_online()` 单入口在线状态重算 + 电量缓存窗口。
   - 落地位置：`device.py` 在线状态变更与轮询结果写回路径统一。

---

## 4. 分阶段实施计划

### Phase 1（本周可完成）

1. 统一同UUID多特征降级逻辑为单一私有函数
2. 为断连写入增加“单次调用一次重连”防护
3. 增加不可用/恢复日志去重机制
4. 新增单元测试：
   - 同UUID读写重试
   - `_client is None` 时写入行为
   - `battery_poll_interval_min` 边界
5. 增加“短连接兜底开关”设计评审（仅评审，不默认启用）

验收标准：
- 新测试通过
- 无新增 lint/type 错误

### Phase 2（1-2周）

1. 对齐 `parallel-updates`
2. 引入/收敛 `runtime_data`
3. 梳理实体可用性状态更新路径（避免“假在线”）
4. 将在线状态重算逻辑收敛为单入口（参考旧版 `_recalc_online` 思路）

验收标准：
- 配置加载/卸载流程无回归
- 并发操作下无日志刷屏、无死锁

### Phase 3（2周+）

1. 增加 diagnostics 与故障快照能力（按HA规范）
2. 增强集成测试（多设备并发、长时间稳定性）
3. 文档补齐：已知限制、故障排查、数据更新机制

---

## 5. 风险与非目标

### 风险

1. 不同平台Bleak后端异常行为差异（BlueZ/CoreBluetooth/WinRT）
2. 过度重试导致设备侧负载升高
3. 日志治理不当导致问题定位信息不足或刷屏

### 非目标（本方案不做）

1. 不引入复杂自学习算法（如动态健康评分）
2. 不改动现有配置键命名与存储结构
3. 不在无证据前提下承诺固定百分比收益

---

## 6. 验证与交付清单

### 6.1 开发验证

- `ruff check custom_components/anti_loss_tag/`
- `mypy custom_components/anti_loss_tag/`
- `pytest tests/ -v`

### 6.2 场景验证

1. 设备断连后触发按钮/开关写入，确认可自愈或给出可操作错误
2. 同UUID多特征设备上，读写可回退到handle路径
3. 设备离线/恢复日志各仅一次

### 6.3 发布前检查

1. `manifest.json` / `pyproject.toml` 版本一致
2. 新增测试随变更同提交
3. 文档同步更新

---

## 7. 参考依据（官方）

1. Bleak Usage
   - https://bleak.readthedocs.io/en/latest/usage.html
2. Bleak Client API
   - https://bleak.readthedocs.io/en/latest/api/client.html
3. Home Assistant Integration Quality Scale - Rules
   - https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/
4. HA `log-when-unavailable`
   - https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/log-when-unavailable/
5. HA `parallel-updates`
   - https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/parallel-updates/
6. HA `runtime-data`
   - https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/runtime-data/

---

## 8. 备注

- 本文档为“审校更正版本”，用于替代旧版中不准确示例与未经验证的收益描述。
- 若后续实施代码改动，请按“每次变更同步版本号 + 测试证明”流程执行。
