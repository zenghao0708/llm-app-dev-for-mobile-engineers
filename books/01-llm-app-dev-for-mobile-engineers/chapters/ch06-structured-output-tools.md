# 第 6 章 结构化输出与工具调用

## 本章导读

大模型擅长生成自然语言，但业务系统不能只消费“看起来合理”的文字。移动端 App 最终要更新页面状态、展示卡片、调用服务端接口、创建工单或进入确认流程。这些动作需要明确字段、稳定类型和可审计的工具调用。

例如用户说“帮我查一下订单 A1024 到哪里了”，模型可以输出受约束的结构：

```json
{
  "tool_name": "query_order",
  "arguments": {
    "order_id": "A1024"
  },
  "requires_confirmation": false
}
```

图 6-1 展示了结构化输出和工具调用的工程边界。

![图 6-1 结构化输出与工具调用边界](../assets/diagrams/structured-tool-call.svg)

配套脚本：`examples/01-mobile-knowledge-assistant/scripts/structured_tool_router.py`

## 学习目标

- 理解结构化输出为什么是模型进入工程系统的关键边界。
- 用 JSON Schema 描述字段、类型、枚举、必填项和额外字段限制。
- 知道模型输出必须经过服务端校验，不能直接进入业务工具。
- 区分只读工具和高风险工具，并设计移动端确认卡。
- 运行配套脚本，观察订单查询、越权访问、取消订单确认和审计字段。

## 6.1 自然语言不能直接驱动业务动作

自然语言适合给人看，不适合直接执行。原因有 4 个：

- 字段不稳定：模型可能一会儿说“订单号”，一会儿说“编号”。
- 类型不稳定：金额、日期、布尔值可能被写成自然语言。
- 边界不稳定：模型可能补充没有依据的信息。
- 风险不稳定：模型可能把“查询”误判成“取消”或“退款”。

移动端页面需要稳定字段：

| 字段 | 页面用途 |
| --- | --- |
| `tool_name` | 决定调用哪个服务端工具 |
| `arguments.order_id` | 展示订单号并查询业务数据 |
| `requires_confirmation` | 记录模型风险建议，最终决策仍归服务端 |
| `tool_result.mobile_confirmation.risk_level` | 决定确认卡样式 |
| `tool_result.status` | 决定完成、失败、无权限或等待确认状态 |

结构化输出的目的，是让模型结果进入可校验、可测试、可审计的工程链路。

## 6.2 JSON Schema 是最低合格线

配套脚本中的工具调用 Schema 如下：

```python
TOOL_CALL_SCHEMA = {
    "type": "object",
    "required": ["tool_name", "arguments", "requires_confirmation"],
    "additionalProperties": False,
    "properties": {
        "tool_name": {
            "type": "string",
            "enum": ["query_order", "request_order_cancellation"],
        },
        "arguments": {
            "type": "object",
            "required": ["order_id"],
            "additionalProperties": False,
            "properties": {
                "order_id": {"type": "string"},
                "reason": {"type": "string"},
            },
        },
        "requires_confirmation": {"type": "boolean"},
    },
}
```

这里有 3 个重点。第一，`tool_name` 使用枚举，防止模型输出未授权工具。第二，`required` 写清楚必填字段，缺少 `order_id` 的调用不能进入业务系统。第三，`additionalProperties: False` 阻止模型加入 `admin`、`force` 等额外字段。

Schema 只说明“结构看起来像工具请求”，不代表可以执行。权限、状态、风险等级和确认卡仍要由服务端业务代码判断。`requires_confirmation` 只记录模型建议，不参与最终执行决策。

## 6.3 配套脚本执行流程

运行：

```bash
cd examples/01-mobile-knowledge-assistant
python3 scripts/structured_tool_router.py \
  --message '帮我查一下订单 A1024 到哪里了' \
  --user-id user_001
```

脚本执行 5 步：

1. 用确定性适配器模拟模型输出结构化 JSON。
2. 用 `TOOL_CALL_SCHEMA` 校验字段、类型、枚举和额外字段。
3. 把 JSON 转换为内部 `ToolCall` 对象。
4. 通过服务端工具策略完成白名单、权限、状态和确认判断。
5. 返回工具结果和审计字段。

典型输出包含 `model_output`、`tool_result` 和 `audit`。这里的模型输出由 `mock_model_structured_output()` 生成；把它替换成真实模型时，后面的 Schema 校验、白名单、权限和确认流程不应删除。

## 6.4 应用层校验不能省略

有些模型服务支持 `response_format` 或工具调用参数约束，但应用层仍然要校验。模型服务保证输出形状，业务系统要保证执行安全。

配套脚本实现了一个小型 JSON Schema 子集校验器。生产项目可以使用成熟 JSON Schema 库，但关键原则不变：模型输出不能因为“像 JSON”就被信任。

校验失败后常见处理方式有 3 种：

- 让模型重新生成一次，并把校验错误作为上下文。
- 返回错误给调用方，让移动端展示“无法理解该请求”。
- 把样本记录到评测集，后续优化 Prompt 或模型路由。

不要在校验失败后猜测字段含义继续执行。比如缺少 `order_id` 或订单号格式不合法时，服务端不应从历史会话里随便找一个订单号执行。

## 6.5 工具白名单与风险分级

工具调用的本质是让模型影响业务系统。只要涉及业务系统，就必须有白名单。

```python
TOOL_POLICIES = {
    "query_order": {"requires_confirmation": False, "risk_level": "none"},
    "request_order_cancellation": {"requires_confirmation": True, "risk_level": "high"},
}
```

Prompt 中写“不要调用危险工具”不够可靠。Prompt 是给模型看的，白名单是服务端强制执行的边界。即使模型输出 `delete_order`，服务端也必须拒绝。

工具可以分为：

| 工具类型 | 示例 | 是否需要确认 |
| --- | --- | --- |
| 只读查询 | 查询订单、查询物流、读取知识库 | 通常不需要 |
| 低风险写入 | 创建草稿、添加待办、保存临时备注 | 视业务而定 |
| 高风险动作 | 取消订单、退款、删除数据、发布配置 | 必须确认 |

风险等级不能由模型直接决定，应由服务端工具策略绑定。

## 6.6 权限检查在工具执行前完成

工具调用不能绕过业务权限。配套数据中订单 `B2048` 属于 `user_002`。如果 `user_001` 查询它：

```bash
python3 scripts/structured_tool_router.py \
  --message '帮我查一下订单 B2048' \
  --user-id user_001
```

结果会返回 `forbidden`。这说明权限判断发生在工具执行前。模型识别出订单号，并不代表当前用户有权查看。生产系统中，权限维度可能包括用户 ID、租户 ID、团队、角色、数据范围和文档可见性。

## 6.7 高风险动作需要移动端确认

取消订单属于高风险动作。即使模型正确识别意图，服务端也不能直接执行。脚本会先检查参数、订单归属和订单状态；如果前置检查通过，返回 `confirmation_required` 和服务端生成的确认卡。

```bash
python3 scripts/structured_tool_router.py \
  --message '我要取消订单 P3001' \
  --user-id user_001
```

确认卡至少包含：

- 将要执行的动作。
- 影响对象，例如订单号。
- 风险说明。
- 取消按钮和确认按钮。
- 是否需要再次输入密码、验证码或生物识别。

用户确认后，移动端再发起带确认态的请求。本章脚本用 `--confirm` 模拟：

```bash
python3 scripts/structured_tool_router.py \
  --message '我要取消订单 P3001' \
  --user-id user_001 \
  --confirm
```

生产系统中，确认态应绑定 `request_id` 或 `confirmation_id`，并设置过期时间和幂等保护，不能只依赖页面按钮状态。

## 6.8 移动端状态设计

结构化输出和工具调用最终都会落到移动端状态机。建议至少区分：

| 状态 | 含义 | 页面表现 |
| --- | --- | --- |
| `parsing` | 正在理解用户请求 | 输入区禁用或显示加载 |
| `tool_calling` | 服务端正在执行只读工具 | 显示“正在查询订单” |
| `waiting_confirmation` | 高风险动作等待用户确认 | 展示确认卡 |
| `success` | 工具执行成功 | 展示结果卡片 |
| `forbidden` | 无权访问目标资源 | 展示权限错误 |
| `invalid_arguments` | 参数缺失或格式错误 | 引导用户补充信息 |
| `failed` | 工具或服务异常 | 展示重试入口 |

不要把所有异常都塞进“模型回答失败”。`forbidden`、`confirmation_required`、`not_cancellable` 和 `not_found` 对用户意味着完全不同的下一步动作。

确认卡对象可以设计为：

```json
{
  "card_type": "tool_confirmation",
  "request_id": "req_001",
  "confirmation_id": "confirm_001",
  "tool_name": "request_order_cancellation",
  "title": "确认取消订单",
  "risk_level": "high",
  "expires_at": "2026-06-21T10:15:00+08:00",
  "primary_action": "确认取消",
  "secondary_action": "返回"
}
```

该对象应由服务端返回，移动端负责展示和收集用户确认。移动端不应自行拼装高风险工具参数，更不应绕过服务端直接调用业务系统。

## 6.9 迁移到真实模型

真实模型接入后，流程仍然不变：

1. Prompt 要求模型只能输出指定 JSON 或工具调用。
2. 模型服务最好开启结构化输出或工具调用模式。
3. 服务端用 Schema 再校验一次。
4. 服务端把工具名映射到白名单。
5. 服务端根据工具策略绑定风险等级和确认要求。
6. 服务端做参数、权限和业务状态前置检查。
7. 高风险动作返回服务端生成的确认卡。
8. 用户确认后，服务端再次校验并执行工具。
9. 工具结果进入审计日志和移动端状态机。

结构化输出只是把不稳定自然语言收束成更容易校验的格式。真正的可靠性来自 Schema、白名单、权限、确认、审计和测试。

## 本章小结

结构化输出让模型结果能够进入程序流程，工具调用让大模型应用连接真实业务系统。但模型不能直接执行业务动作。移动端负责交互、状态展示和用户确认；服务端负责结构校验、工具白名单、权限判断、业务执行和审计。

## 实践练习

1. 在 `TOOL_CALL_SCHEMA` 中为 `order_id` 增加格式校验说明，并在服务端补充确定性校验。
2. 新增只读工具 `list_recent_orders`，要求只能返回当前用户自己的订单。
3. 为 `request_order_cancellation` 增加取消原因枚举。
4. 设计移动端确认卡 UI，分别处理 `confirmation_required`、`forbidden` 和 `not_cancellable`。
5. 接入真实模型提供方时，列出仍然必须保留在服务端的校验步骤。
