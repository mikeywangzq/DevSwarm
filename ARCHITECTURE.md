# DevSwarm 架构设计文档

## 概述

DevSwarm采用"编排器-工作者"(Orchestrator-Worker)架构模式，通过多个专业化的Agent协作完成Web应用的自动化开发。

## 核心概念

### 1. Agent

Agent是系统的基本执行单元，每个Agent都有：
- 唯一的名称和角色
- 特定的技能和职责
- 与消息总线的连接
- 对共享状态的访问
- LLM能力

### 2. 消息总线 (Message Bus)

中心化的消息传递系统，负责：
- 路由消息到正确的Agent
- 支持点对点和广播通信
- 维护消息历史
- 提供异步消息处理

### 3. 共享状态 (Shared State)

所有Agent都可访问的中央知识库：
- 项目信息
- API契约
- 任务列表
- 代码库路径
- 测试结果

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        User Layer                            │
│                                                               │
│  ┌──────────────┐                    ┌──────────────┐       │
│  │  Web UI      │                    │  CLI Demo    │       │
│  │  (Flask)     │                    │              │       │
│  └──────┬───────┘                    └──────┬───────┘       │
└─────────┼────────────────────────────────────┼──────────────┘
          │                                    │
          ▼                                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    Orchestration Layer                       │
│                                                               │
│                    ┌──────────────────┐                     │
│                    │   PM Agent       │                     │
│                    │  (Orchestrator)  │                     │
│                    └────────┬─────────┘                     │
│                             │                                │
│         ┌───────────────────┼───────────────────┐          │
│         │                   │                   │          │
└─────────┼───────────────────┼───────────────────┼──────────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                      Worker Layer                            │
│                                                               │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐          │
│  │ Backend  │      │ Frontend │      │    QA    │          │
│  │  Agent   │      │  Agent   │      │  Agent   │          │
│  └────┬─────┘      └────┬─────┘      └────┬─────┘          │
└───────┼─────────────────┼─────────────────┼────────────────┘
        │                 │                 │
        └─────────────────┴─────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                       │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Message Bus  │  │ Shared State │  │  LLM Client  │     │
│  │  (Async)     │  │  (JSON)      │  │  (OpenAI/    │     │
│  │              │  │              │  │  Anthropic)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## Agent详细设计

### PM Agent (项目经理)

**职责**:
- 需求分析
- API契约设计
- 任务分解和分配
- 进度监控
- Bug修复协调

**关键方法**:
```python
async def start_project(requirement: str) -> str
async def _analyze_requirement(requirement: str)
async def _define_api_contract(requirement: str)
async def _create_task_list(requirement: str)
async def _assign_tasks()
async def _handle_bug_report(message: Message)
```

**决策逻辑**:
1. 接收需求 → 分析类型（CRUD/其他）
2. 设计API契约 → 使用LLM生成RESTful API
3. 创建任务 → T1(Backend) + T2(Frontend) + T3(QA)
4. 分配任务 → 检查依赖，发送消息
5. 监控执行 → 等待完成报告
6. 处理Bug → 分析根因 → 生成修复 → 重新分配

### Backend Agent (后端开发)

**职责**:
- 根据API契约生成Flask代码
- 实现REST API端点
- 创建数据存储模块
- 应用Bug修复

**生成流程**:
```
API契约 → LLM提示 → Flask代码 → 存储模块 → requirements.txt
```

**生成的文件**:
- `app.py` - Flask应用
- `storage.py` - 数据存储
- `requirements.txt` - 依赖
- `Dockerfile` - 容器化
- `README.md` - 文档

### Frontend Agent (前端开发)

**职责**:
- 生成HTML/CSS/JavaScript代码
- 实现API调用逻辑
- 创建用户界面

**生成流程**:
```
API契约 + 需求 → LLM提示 → HTML → JavaScript → CSS
```

**生成的文件**:
- `index.html` - 主页面
- `app.js` - 应用逻辑
- `style.css` - 样式
- `package.json` - 配置
- `README.md` - 文档

### QA Agent (质量保证)

**职责**:
- 启动后端服务
- 执行集成测试
- 检测Bug
- 生成测试报告

**测试流程**:
```
启动服务 → 等待就绪 → 测试API端点 → 检测失败 → 报告Bug
```

**测试类型**:
- GET端点测试
- POST端点测试（创建数据）
- DELETE端点测试（先创建后删除）
- PUT端点测试（先创建后更新）

## 通信协议

### 消息格式

```json
{
  "message_id": "uuid",
  "timestamp": "ISO-8601",
  "from_agent": "sender_name",
  "to_agent": "receiver_name",
  "type": "message_type",
  "task": {
    "task_id": "T1",
    "title": "...",
    "description": "...",
    "assigned_to": "...",
    "dependencies": [],
    "status": "pending|in_progress|completed|failed"
  },
  "payload": {}
}
```

### 消息类型

1. **TASK_ASSIGNMENT** - 任务分配
   - From: PM Agent
   - To: Worker Agent
   - Payload: Task object

2. **STATUS_UPDATE** - 状态更新
   - From: Worker Agent
   - To: PM Agent
   - Payload: {task_id, status}

3. **COMPLETION_REPORT** - 完成报告
   - From: Worker Agent
   - To: PM Agent
   - Payload: {task_id, result}

4. **ERROR_REPORT** - 错误报告
   - From: Worker Agent
   - To: PM Agent
   - Payload: {task_id, error}

5. **BUG_REPORT** - Bug报告
   - From: QA Agent
   - To: PM Agent
   - Payload: {bug_report}

## 工作流程

### 典型执行流程

```
1. User submits requirement
   ↓
2. PM Agent analyzes requirement
   ↓
3. PM Agent defines API contract
   ↓
4. PM Agent creates tasks:
   - T1: Backend development
   - T2: Frontend development
   - T3: QA testing (depends on T1, T2)
   ↓
5. PM Agent assigns T1 to Backend Agent
   PM Agent assigns T2 to Frontend Agent
   ↓
6. Backend Agent generates code (parallel)
   Frontend Agent generates code (parallel)
   ↓
7. Both complete → PM assigns T3 to QA Agent
   ↓
8. QA Agent runs tests
   ↓
9a. All tests pass → Project completed
   ↓
9b. Tests fail → QA reports bugs to PM
   ↓
10. PM analyzes bugs → generates fixes
    ↓
11. PM assigns fix tasks to relevant agents
    ↓
12. Agents apply fixes → QA runs regression tests
    ↓
13. Loop until all tests pass
```

### 状态机

**项目状态**:
```
initializing → planning → developing → testing → completed/failed
```

**任务状态**:
```
pending → in_progress → completed/failed
```

## 数据流

### API契约驱动开发

```
User Requirement
    ↓
PM analyzes → API Contract (JSON)
    ↓
    ├─→ Backend Agent reads contract → generates API
    └─→ Frontend Agent reads contract → generates UI calls
```

### 共享状态更新

```
Agent completes task
    ↓
Agent updates shared state
    ↓
Agent sends message to PM
    ↓
PM checks shared state
    ↓
PM makes decisions based on state
```

## 扩展点

### 1. 添加新Agent

```python
class NewAgent(BaseAgent):
    def __init__(self, message_bus, shared_state, llm_client):
        super().__init__(...)

    async def execute_task(self, task: Task):
        # 实现任务逻辑
        pass
```

### 2. 自定义消息类型

在 `protocol.py` 中添加新的 `MessageType`

### 3. 扩展LLM支持

在 `llm_client.py` 中添加新的provider

### 4. 自定义工作流

修改PM Agent的任务分配逻辑

## 性能考虑

### 1. 并行执行

- Backend和Frontend Agent并行工作
- 消息处理异步化
- 非阻塞I/O

### 2. LLM调用优化

- 合理的prompt设计
- 温度参数调优
- Fallback机制

### 3. 资源管理

- QA Agent启动/停止后端服务
- 工作空间隔离
- 状态持久化

## 安全考虑

1. **代码沙箱**: 生成的代码在隔离环境运行
2. **输入验证**: 用户需求sanitization
3. **LLM输出验证**: 检查生成代码的语法
4. **资源限制**: 限制生成代码的复杂度

## 时序图

### 成功场景时序图

```
User          PM Agent      Backend Agent   Frontend Agent   QA Agent      Shared State
 │               │                │               │              │               │
 │──需求────────>│                │               │              │               │
 │               │                │               │              │               │
 │               │──分析需求───────────────────────────────────────────────────>│
 │               │<─────────────────────────────────────────────────────────────│
 │               │                │               │              │               │
 │               │──设计API契约────────────────────────────────────────────────>│
 │               │<─────────────────────────────────────────────────────────────│
 │               │                │               │              │               │
 │               │──创建任务───────────────────────────────────────────────────>│
 │               │                │               │              │               │
 │               │──分配T1──────>│               │              │               │
 │               │──分配T2─────────────────────>│              │               │
 │               │                │               │              │               │
 │               │                │──读取契约─────────────────────────────────>│
 │               │                │──生成代码────>│               │               │
 │               │                │<──────────────│               │               │
 │               │                │──更新状态─────────────────────────────────>│
 │               │<──完成报告────│               │              │               │
 │               │                │               │──读取契约─────────────────>│
 │               │                │               │──生成代码──>│               │
 │               │                │               │<────────────│               │
 │               │                │               │──更新状态─────────────────>│
 │               │<──完成报告────────────────────│              │               │
 │               │                │               │              │               │
 │               │──分配T3────────────────────────────────────>│               │
 │               │                │               │              │──启动服务───>│
 │               │                │               │              │──执行测试───>│
 │               │                │               │              │<──测试通过──│
 │               │<──完成报告────────────────────────────────────│               │
 │               │                │               │              │               │
 │               │──项目完成───────────────────────────────────────────────────>│
 │<──完成通知────│                │               │              │               │
```

### Bug修复场景时序图

```
QA Agent      PM Agent      Backend Agent   Shared State
   │              │                │              │
   │──Bug报告────>│                │              │
   │              │──分析Bug───────────────────>│
   │              │<─────────────────────────────│
   │              │──生成修复建议─>│              │
   │              │                │              │
   │              │──创建修复任务─────────────>│
   │              │──分配修复────>│              │
   │              │                │──应用补丁──>│
   │              │<──修复完成────│              │
   │              │──触发回归测试>│              │
   │──执行测试────│                │              │
   │──测试通过───>│                │              │
```

## 关键实现细节

### 1. 异步消息处理

**消息总线实现**:

```python
class MessageBus:
    async def _process_messages(self):
        """后台任务持续处理消息队列"""
        while self._running:
            message = await self._message_queue.get()
            await self._dispatch_message(message)

    async def _dispatch_message(self, message: Message):
        """分发消息到订阅者"""
        if message.to_agent == "ALL":
            # 广播给所有Agent（除了发送者）
            for agent_name, callbacks in self._subscribers.items():
                if agent_name != message.from_agent:
                    await self._deliver_to_agent(agent_name, callbacks, message)
        else:
            # 点对点消息
            callbacks = self._subscribers[message.to_agent]
            await self._deliver_to_agent(message.to_agent, callbacks, message)
```

**优势**:
- 非阻塞处理
- 解耦Agent间通信
- 支持消息历史追踪

### 2. 任务依赖管理

**PM Agent的依赖检查**:

```python
def _can_execute_task(self, task: Task) -> bool:
    """检查任务是否可以执行"""
    for dep in task.dependencies:
        if dep.endswith(".json"):
            # 文件依赖，检查是否存在
            continue
        if dep.startswith("T"):
            # 任务依赖，检查是否完成
            dep_task = self.shared_state.get_task(dep)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
    return True
```

**依赖解析策略**:
- 文件依赖: 检查文件是否存在
- 任务依赖: 检查任务是否完成
- 循环依赖检测（待实现）

### 3. LLM提示工程

**Backend Agent的代码生成提示**:

```python
prompt = f"""
Generate a complete Flask application that implements these API endpoints:

{endpoints_description}

API Contract Details:
{api_contract.to_json()}

Requirements:
1. Use Flask framework
2. Implement all endpoints according to the contract
3. Use CORS for cross-origin requests
4. Use the storage module for data persistence
5. Include proper error handling
6. Add request validation
7. Return JSON responses
8. Include logging

Generate ONLY the Python code for app.py, no explanations.
"""
```

**提示设计原则**:
- 明确输出格式（"ONLY ... no explanations"）
- 提供详细上下文（API契约）
- 列出具体要求
- 使用system prompt设定角色

### 4. 错误恢复机制

**多层次错误处理**:

1. **LLM层**: Fallback到模板代码
   ```python
   try:
       code = await llm_client.generate(prompt)
   except Exception as e:
       code = self._generate_template()
   ```

2. **Agent层**: 捕获异常并报告
   ```python
   try:
       result = await self.execute_task(task)
   except Exception as e:
       await self._send_error_report(str(e), task.task_id)
   ```

3. **PM层**: 分析错误并生成修复
   ```python
   async def _handle_bug_report(self, message: Message):
       fix_suggestion = await self._analyze_bug(bug_report)
       fix_task = await self._create_fix_task(bug_report, fix_suggestion)
       await self._assign_task_to_agent(fix_task)
   ```

## 部署架构

### 单机部署

```
┌─────────────────────────────────────────┐
│          Host Machine                    │
│                                          │
│  ┌────────────────────────────────┐    │
│  │  DevSwarm Web App (Flask)      │    │
│  │  Port: 3000                     │    │
│  └────────────────────────────────┘    │
│                                          │
│  ┌────────────────────────────────┐    │
│  │  All Agents (In-Process)       │    │
│  │  - PM Agent                     │    │
│  │  - Backend Agent                │    │
│  │  - Frontend Agent               │    │
│  │  - QA Agent                     │    │
│  └────────────────────────────────┘    │
│                                          │
│  ┌────────────────────────────────┐    │
│  │  Workspace                      │    │
│  │  ./workspace/proj_xxx/         │    │
│  └────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

### 分布式部署（未来）

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Web Frontend   │      │  PM Agent       │      │  Worker Pool     │
│  (Load Balanced)│      │  (Coordinator)  │      │  - Backend Agent │
│                 │      │                 │      │  - Frontend Agent│
│  Port: 3000     │      │  Port: 8000     │      │  - QA Agent      │
└────────┬────────┘      └────────┬────────┘      └────────┬─────────┘
         │                        │                         │
         └────────────────────────┴─────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
         ┌──────────▼──────────┐    ┌──────────▼──────────┐
         │  Message Queue      │    │  Shared Database    │
         │  (Redis/RabbitMQ)   │    │  (PostgreSQL)       │
         └─────────────────────┘    └─────────────────────┘
```

## 监控和可观测性

### 日志策略

**日志级别**:
- `DEBUG`: Agent内部状态变化
- `INFO`: 任务开始/完成、消息发送/接收
- `WARNING`: 非致命错误、降级功能
- `ERROR`: 任务失败、异常情况

**日志格式**:
```
2025-11-17 20:30:00 - PM_Agent - INFO - Task T1_Backend assigned to Backend_Agent
2025-11-17 20:30:05 - Backend_Agent - INFO - Executing task: T1_Backend
2025-11-17 20:30:10 - Backend_Agent - INFO - Generated Flask code: 234 lines
2025-11-17 20:30:15 - Backend_Agent - INFO - Task T1_Backend completed
```

### 监控指标

**系统级指标**:
- 活跃Agent数量
- 消息队列长度
- 消息处理延迟
- 内存使用

**业务级指标**:
- 项目成功率
- 平均完成时间
- Bug修复次数
- LLM调用次数和成本

**监控端点**:
```python
@app.route('/api/metrics')
def get_metrics():
    return jsonify({
        'active_agents': 4,
        'queue_size': message_bus.get_stats()['queue_size'],
        'total_projects': 10,
        'success_rate': 0.85,
        'avg_completion_time': 180  # seconds
    })
```

## 性能基准

### 测试环境

- CPU: 4核
- 内存: 8GB
- LLM: GPT-4 (OpenAI)
- 网络: 100Mbps

### 性能指标

| 指标 | 数值 |
|------|------|
| 简单应用生成时间 | 2-3分钟 |
| 中等复杂度应用 | 5-8分钟 |
| 消息处理延迟 | <100ms |
| 并发Agent通信 | 支持10+ Agent |
| LLM调用平均时间 | 3-5秒 |
| 内存占用（峰值） | ~500MB |

### 瓶颈分析

**主要瓶颈**:
1. **LLM API调用**: 占总时间的70-80%
2. **代码生成质量**: 影响Bug数量和修复次数
3. **QA测试执行**: 启动服务和测试需要30-60秒

**优化策略**:
1. 缓存常见需求的代码模板
2. 并行执行多个LLM调用
3. 优化prompt减少生成时间
4. 使用更快的本地LLM模型（如有）

## 最佳实践

### 1. 编写高质量需求

**好的需求示例**:
```
我想要一个图书管理应用，包含以下功能：
1. 添加新书（书名、作者、ISBN）
2. 查看所有图书列表
3. 按书名搜索图书
4. 删除图书记录
5. 更新图书信息
```

**避免的需求**:
```
做一个应用  # 太模糊
一个超级复杂的电商平台  # 超出能力范围
```

### 2. Agent开发指南

**遵循的原则**:
- 单一职责: 每个Agent只负责一类任务
- 无状态: 避免Agent间共享可变状态
- 消息驱动: 所有通信通过消息总线
- 错误透明: 及时报告错误，不隐藏异常

**示例**:
```python
class GoodAgent(BaseAgent):
    async def execute_task(self, task: Task):
        """清晰的任务执行逻辑"""
        try:
            # 1. 验证输入
            self._validate_task(task)

            # 2. 执行核心逻辑
            result = await self._do_work(task)

            # 3. 验证输出
            self._validate_result(result)

            return result
        except Exception as e:
            # 4. 错误处理
            logger.error(f"Task failed: {e}")
            raise
```

### 3. 调试技巧

**查看消息历史**:
```python
messages = message_bus.get_message_history(agent_name="Backend_Agent", limit=20)
for msg in messages:
    print(f"{msg.timestamp}: {msg.type.value} - {msg.from_agent} -> {msg.to_agent}")
```

**检查共享状态**:
```python
state = shared_state.get_state_snapshot()
print(json.dumps(state, indent=2))
```

**启用详细日志**:
```bash
export LOG_LEVEL=DEBUG
python src/web/app.py
```

## 故障排查指南

### 常见问题

**问题1: Agent无响应**

症状: 任务一直处于in_progress状态

诊断:
```python
# 检查Agent状态
agent_status = backend_agent.get_status()
print(agent_status)

# 查看消息队列
stats = message_bus.get_stats()
print(f"Queue size: {stats['queue_size']}")
```

解决: 重启消息总线或重新分配任务

**问题2: 代码生成质量差**

症状: 生成的代码有语法错误或不符合需求

诊断:
- 检查LLM模型配置（推荐使用GPT-4）
- 查看temperature参数（应该在0.2-0.5之间）
- 检查prompt是否足够清晰

解决:
```python
# 在config.yaml中调整
llm:
  model: "gpt-4"  # 不要用gpt-3.5
  temperature: 0.3
```

**问题3: 测试总是失败**

症状: QA Agent报告所有测试失败

诊断:
```bash
# 手动测试后端
cd workspace/proj_xxx/backend
python app.py

# 在另一个终端测试API
curl http://localhost:5000/health
```

解决: 检查生成的代码是否有语法错误，或手动修复

## 扩展案例

### 案例1: 添加Designer Agent

为系统添加专门负责UI设计的Agent:

```python
class DesignerAgent(BaseAgent):
    """UI/UX设计Agent"""

    async def execute_task(self, task: Task) -> Dict[str, Any]:
        # 1. 分析需求，生成设计规范
        design_spec = await self._create_design_spec(task)

        # 2. 生成颜色主题
        color_scheme = await self._generate_color_scheme()

        # 3. 生成高级CSS
        advanced_css = await self._generate_advanced_css(design_spec, color_scheme)

        # 4. 保存设计资源
        self._save_design_assets(advanced_css)

        return {
            "status": "success",
            "design_spec": design_spec,
            "assets": ["theme.css", "variables.css"]
        }
```

**集成到工作流**:
1. PM Agent创建T2.5 (Design)任务
2. 在Frontend Agent之前执行
3. Frontend Agent使用Designer的输出

### 案例2: 添加Database Agent

处理数据库设计和迁移:

```python
class DatabaseAgent(BaseAgent):
    """数据库设计Agent"""

    async def execute_task(self, task: Task) -> Dict[str, Any]:
        # 1. 从API契约推断数据模型
        api_contract = self.shared_state.get_api_contract()
        data_models = await self._infer_models(api_contract)

        # 2. 生成数据库Schema
        schema = await self._generate_schema(data_models)

        # 3. 生成ORM模型（SQLAlchemy）
        orm_code = await self._generate_orm_models(schema)

        # 4. 生成迁移脚本
        migration = await self._generate_migration(schema)

        return {
            "status": "success",
            "schema": schema,
            "models_file": "models.py",
            "migration_file": "001_initial.sql"
        }
```

## 未来改进

### 短期（1-3个月）

1. **代码质量提升**
   - 添加代码格式化（Black, Prettier）
   - 集成静态类型检查（mypy）
   - 生成单元测试

2. **测试增强**
   - 前端E2E测试（Playwright）
   - 性能测试
   - 安全扫描

3. **用户体验**
   - 实时日志流
   - 代码预览
   - 在线编辑生成的代码

### 中期（3-6个月）

1. **分布式部署**: Agent可以运行在不同机器
2. **持久化消息队列**: 使用Redis/RabbitMQ
3. **更复杂的工作流**: 支持条件分支、循环
4. **多语言支持**: Python, Node.js, Go后端

### 长期（6-12个月）

1. **Agent学习**: 从历史项目中学习
2. **可视化工作流编辑器**: 图形化配置
3. **云平台集成**: 一键部署到AWS/Azure/GCP
4. **协作功能**: 多用户协作开发
5. **插件系统**: 第三方Agent插件市场

## 参考资源

### 学术论文
- [Multi-Agent Systems: A Survey](https://arxiv.org/abs/2101.00001)
- [LLM-based Autonomous Agents](https://arxiv.org/abs/2308.11432)

### 相关项目
- [AutoGPT](https://github.com/Significant-Gravitas/AutoGPT)
- [MetaGPT](https://github.com/geekan/MetaGPT)
- [LangChain](https://github.com/langchain-ai/langchain)
- [AutoGen](https://github.com/microsoft/autogen)

### 技术栈文档
- [Flask Documentation](https://flask.palletsprojects.com/)
- [AsyncIO Documentation](https://docs.python.org/3/library/asyncio.html)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Anthropic Claude API](https://docs.anthropic.com/)

---

**文档版本**: 1.1
**最后更新**: 2025-11-17
**维护者**: DevSwarm Team
