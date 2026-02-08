# 开发经验总结与最佳实践

## 文档信息

- **版本**: v1.0.0
- **日期**: 2026-02-09
- **范围**: Home Assistant KT6368A 防丢标签集成开发
- **目标**: 总结优化过程中的关键技巧、经验教训和最佳实践

---

## 1. 关键技巧总结

### 1.1 API 调用验证的三重验证原则

**教训来源**: v1.8.0 (commit 7547f55) 引入的严重 bug

**问题**:
```python
# 错误代码（会导致 AttributeError）
await client.get_services()  # ❌ 该方法不存在
```

**根本原因**:
- 仅依赖文档或猜测，未验证实际 API
- 混淆了 property（属性）和 method（方法）
- 未在实际运行环境中测试

**正确做法 - 三重验证原则**:

1. **文档验证**（第一重）
   ```python
   # bleak 官方文档明确说明：
   # *property* BleakClient.services: BleakGATTServiceCollection
   # services 是 property，不是 method
   ```

2. **代码验证**（第二重）
   ```python
   import inspect
   from bleak import BleakClient
   
   # 检查是属性还是方法
   services_attr = getattr(BleakClient, 'services')
   assert isinstance(services_attr, property), "services must be a property"
   
   # 验证不存在 get_services 方法
   assert not hasattr(BleakClient, 'get_services'), "get_services should not exist"
   ```

3. **运行时验证**（第三重）
   ```python
   # 在实际环境中测试
   client = BleakClient(address)
   await client.connect()
   
   # 正确用法：访问属性
   services = client.services  # ✅
   
   # 错误用法：调用方法
   # await client.get_services()  # ❌ AttributeError
   ```

**经验法则**:
- **永远不要假设 API 的存在**
- **property vs method 有本质区别**
- **在目标环境中测试，不能仅依赖文档**

---

### 1.2 错误消息处理的国际化考量

**教训来源**: v1.7.1 (commit 7547f55) 的错误消息匹配失败

**问题**:
```python
# 错误代码：检查中文错误消息
if "该 UUID 对应多个特征" in str(err):  # ❌
    # 重试逻辑
```

**根本原因**:
- bleak 抛出英文错误消息
- 代码检查中文消息，导致匹配失败
- 重试逻辑失效，用户遇到持续错误

**正确做法**:
```python
# 正确代码：检查英文错误消息
if "Multiple Characteristics with this UUID" in str(err):  # ✅
    # 重试逻辑
```

**最佳实践**:
1. **使用英文错误消息**（库的标准语言）
2. **提供错误码映射**（如果库支持）
3. **记录原始错误**（便于调试）
4. **用户可见消息使用中文**（国际化）

```python
def classify_ble_error(error: Exception) -> str:
    """分类 BLE 错误，返回错误类型"""
    error_str = str(error)
    
    if "Multiple Characteristics with this UUID" in error_str:
        return "multiple_uuid"
    elif "Device disconnected" in error_str:
        return "disconnected"
    elif "Service not found" in error_str:
        return "service_not_found"
    else:
        return "unknown"

# 使用
error_type = classify_ble_error(err)
LOGGER.error("操作失败: %s", _get_chinese_message(error_type))
```

---

### 1.3 渐进式优化与快速回滚策略

**教训来源**: Phase 1-3 的分阶段实施

**成功经验**:

1. **分阶段实施**（Phase 1 → Phase 2 → Phase 3）
   - 每个阶段独立验收
   - 及时发现并修复问题
   - 降低风险，避免大规模回滚

2. **每个阶段独立提交**
   ```bash
   # Phase 1
   git commit -m "feat(ble): Phase 1优化"
   git push
   git tag v1.8.0
   
   # Phase 2
   git commit -m "feat(ha-quality): Phase 2优化"
   git push
   git tag v1.9.0
   
   # Phase 3
   git commit -m "feat(diagnostics): Phase 3优化"
   git push
   git tag v2.0.0
   ```

3. **紧急修复独立版本**
   ```bash
   # 发现严重 bug 后立即修复
   git commit -m "fix(ble): 修复 get_services() bug"
   git push
   git tag v2.0.2  # 跳过 v2.0.1
   ```

**版本命名策略**:
- **主版本**: 重大变更（v1.x → v2.x）
- **次版本**: 功能阶段（v2.0 → v2.1）
- **修订版本**: Bug 修复（v2.0.0 → v2.0.1）
- **紧急修复**: 可跳过版本号（v2.0.0 → v2.0.2）

---

### 1.4 测试驱动的错误处理优化

**教训来源**: Phase 1 的测试补充

**问题**: 修复 bug 时没有对应测试，导致回归

**正确做法**:

1. **先写测试，再修复**
   ```python
   # test_device_ble_operations.py
   
   async def test_multiple_uuid_fallback():
       """测试多特征 UUID 降级逻辑"""
       # 模拟 Multiple Characteristics 错误
       # 验证降级到 handle 重试
       # 验证最终成功
   ```

2. **覆盖边界情况**
   ```python
   async def test_disconnect_with_write():
       """测试断连时的写入行为"""
       # _client is None
       # 应该触发单次重连
       # 失败后明确返回错误
   ```

3. **集成测试覆盖关键流程**
   ```python
   async def test_full_button_press_flow():
       """测试完整的按钮按下流程"""
       # 按下按钮
       # 连接设备
       # 写入报警指令
       # 断开连接
       # 验证每一步的状态
   ```

---

## 2. 经验教训

### 2.1 代码审查清单

每次提交前必须检查：

- [ ] **API 调用验证**
  - [ ] 所有外部 API 调用都有文档依据
  - [ ] 属性访问 vs 方法调用明确区分
  - [ ] 在目标环境中测试通过

- [ ] **错误处理**
  - [ ] 错误消息使用库的标准语言（通常是英文）
  - [ ] 提供用户友好的中文错误提示
  - [ ] 记录原始错误用于调试

- [ ] **向后兼容性**
  - [ ] 不删除或修改现有的配置项
  - [ ] 不改变实体唯一 ID 生成策略
  - [ ] 保持 API 接口稳定

- [ ] **测试覆盖**
  - [ ] 新功能有对应的单元测试
  - [ ] 边界情况有测试覆盖
  - [ ] 回归测试通过

- [ ] **文档同步**
  - [ ] 更新 manifest.json 版本号
  - [ ] 更新 pyproject.toml 版本号
  - [ ] 更新 README 和相关文档
  - [ ] 创建对应的 git tag

---

### 2.2 调试技巧总结

1. **日志诊断**
   ```python
   # 启用调试日志
   import logging
   logging.getLogger("custom_components.anti_loss_tag").setLevel(logging.DEBUG)
   
   # 结构化日志输出
   _LOGGER.debug(
       "GATT 操作: char=%s, data=%s, response=%s",
       char_specifier, data, response
   )
   ```

2. **状态快照**
   ```python
   # 关键时刻记录状态快照
   _LOGGER.info("连接状态快照: connected=%s, available=%s, client=%s",
                self._connected, self._available, self._client is not None)
   ```

3. **错误追踪**
   ```python
   # 记录最后一次错误
   self._last_error = str(err)
   _LOGGER.error("操作失败: %s", err, exc_info=True)  # 包含堆栈信息
   ```

4. **使用诊断数据**
   ```python
   # HA 的诊断功能
   # 开发者 → 服务 → KT6368A → 诊断
   # 可以看到完整的设备状态和连接信息
   ```

---

### 2.3 性能优化经验

1. **特征缓存**
   ```python
   # 缓存已解析的特征 handle
   self._cached_chars: dict[str, BleakGATTCharacteristic] = {}
   
   # 使用时先查缓存
   if uuid in self._cached_chars:
       return self._cached_chars[uuid].handle
   ```

2. **连接池管理**
   ```python
   # 使用全局连接池限制并发
   _conn_mgr = BleConnectionManager(max_connections=3)
   
   # 使用 Semaphore 防止过载
   self._conn_slot_acquired = False
   async with self._conn_mgr:
       # 连接操作
   ```

3. **轮询间隔优化**
   ```python
   # 电量轮询间隔可配置（默认 6 小时）
   battery_poll_interval_min = entry.options.get(
       "battery_poll_interval_min",
       DEFAULT_BATTERY_POLL_INTERVAL_MIN
   )
   ```

4. **避免不必要的重连**
   ```python
   # 复用长连接，而不是每次操作都连接
   if self.maintain_connection:
       # 保持连接
       pass
   else:
       # 操作后断开
         await self._client.disconnect()
   ```

---

## 3. 最佳实践

### 3.1 Home Assistant 集成开发

1. **遵循 Integration Quality Scale**
   - [x] `diagnostics`: 提供诊断信息
   - [x] `parallel-updates`: 声明并发策略
   - [x] `log-when-unavailable`: 日志去重
   - [x] `runtime-data`: 使用 ConfigEntry.runtime_data

2. **实体平台规范**
   ```python
   class MyEntity(Entity):
       # 必须属性
       _attr_available = False
       _attr_should_poll = False
       _attr_has_entity_name = True
       
       # 并发控制
       PARALLEL_UPDATES = 0  # 或 1
   ```

3. **配置流程规范**
   ```python
   class ConfigFlow(ConfigFlow):
       VERSION = 1
       
       async def async_step_bluetooth(self, discovery_info):
           # 蓝牙发现步骤
           pass
       
       async def async_step_user(self, user_input):
           # 手动配置步骤
           pass
   ```

---

### 3.2 BLE 集成开发

1. **连接管理**
   ```python
   # 使用上下文管理器确保资源释放
   try:
       await client.connect()
       # 操作
   finally:
       await client.disconnect()
   ```

2. **错误重试**
   ```python
   # 指数退避策略
   backoff = 2 ** fail_count
   await asyncio.sleep(min(backoff, max_backoff))
   ```

3. **服务发现**
   ```python
   # 访问 services 属性触发服务发现
   services = client.services  # property，自动触发
   ```

4. **特征操作**
   ```python
   # 优先使用 handle，避免 UUID 歧义
   handle = char.handle
   await client.write_gatt_char(handle, data)
   ```

---

### 3.3 代码质量保证

1. **使用 ruff 进行 lint 检查**
   ```bash
   ruff check custom_components/anti_loss_tag/
   ruff check --fix custom_components/anti_loss_tag/
   ```

2. **使用 mypy 进行类型检查**
   ```bash
   mypy custom_components/anti_loss_tag/
   ```

3. **使用 pytest 进行测试**
   ```bash
   pytest tests/ -v
   pytest tests/ --cov=custom_components/anti_loss_tag
   ```

4. **Pre-commit 检查**
   ```bash
   # 在 .git/hooks/pre-push 中
   ruff check custom_components/anti_loss_tag/
   pytest tests/ -q
   ```

---

## 4. 常见陷阱与避免方法

### 4.1 陷阱：属性 vs 方法混淆

**错误**:
```python
await client.get_services()  # ❌ AttributeError
```

**正确**:
```python
services = client.services  # ✅ property
```

**避免方法**: 查阅官方文档，检查类型，实际测试

---

### 4.2 陷阱：错误消息语言不匹配

**错误**:
```python
if "该 UUID 对应多个特征" in str(err):  # ❌ 永远不匹配
```

**正确**:
```python
if "Multiple Characteristics with this UUID" in str(err):  # ✅
```

**避免方法**: 使用库的标准语言（英文），提供用户友好的中文提示

---

### 4.3 陷阱：版本号不一致

**错误**: manifest.json 和 pyproject.toml 版本不同步

**正确**: 同步更新所有版本号
```bash
# 检查一致性
grep version custom_components/anti_loss_tag/manifest.json
grep version pyproject.toml
git describe --tags
```

**避免方法**: 提交前检查清单

---

### 4.4 陷阱：忽略边界情况

**错误**: 只测试正常流程，忽略边界情况

**正确**: 编写全面的单元测试
```python
# 测试边界值
async def test_battery_poll_interval_boundaries():
    for value in [5, 10080, 4, 10081]:
        # 验证边界值处理
```

**避免方法**: TDD（测试驱动开发）

---

## 5. 工具与资源

### 5.1 开发工具

- **ruff**: 快速 Python linter
- **mypy**: 静态类型检查
- **pytest**: 测试框架
- **black**: 代码格式化（可选，我们使用 ruff format）

### 5.2 文档资源

- **Bleak 官方文档**: https://bleak.readthedocs.io/
- **Home Assistant 集成指南**: https://developers.home-assistant.io/
- **HA IQS 规则**: https://developers.home-assistant.io/docs/core/integration-quality-scale/

### 5.3 调试工具

- **HA 开发者工具**: 服务 → 日志
- **诊断功能**: 开发者 → 服务 → 设备 → 诊断
- **BLE 抓包**: Wireshark + bthci

---

## 6. 总结

### 核心原则

1. **验证一切**: API、类型、错误处理
2. **测试先行**: 先写测试，再实现功能
3. **渐进优化**: 分阶段实施，及时验收
4. **文档同步**: 代码和文档保持一致
5. **用户导向**: 提供清晰的错误提示和恢复建议

### 关键教训

1. **永远不要假设 API 的存在**
2. **property vs method 有本质区别**
3. **错误消息使用库的标准语言**
4. **每个阶段独立验收和版本管理**
5. **完善的测试是质量的保证**

### 持续改进

- 定期审查代码质量
- 收集用户反馈
- 更新文档和示例
- 优化性能和用户体验

---

**文档维护**: 本文档应随着项目发展持续更新，记录新的经验教训和最佳实践。
