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

## 未来改进

1. **分布式部署**: Agent可以运行在不同机器
2. **持久化消息队列**: 使用Redis/RabbitMQ
3. **更复杂的工作流**: 支持条件分支、循环
4. **Agent学习**: 从历史项目中学习
5. **可视化编辑器**: 图形化配置工作流

---

**文档版本**: 1.0
**最后更新**: 2025-11-17
