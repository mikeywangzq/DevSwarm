# 🤖 DevSwarm - Multi-Agent Web Application Development Platform

**自动化Web应用开发的多Agent协作系统**

DevSwarm是一个基于大型语言模型(LLM)的多Agent协作系统，能够接收自然语言需求描述，自动生成包含前后端代码和测试用例的完整Web应用。

## ✨ 核心特性

- 🎯 **需求驱动**: 输入自然语言描述，自动生成应用
- 🤝 **多Agent协作**: PM、后端、前端、QA四个Agent协同工作
- 🔄 **自动化流程**: 从需求分析到代码生成、测试、打包全自动
- 🐛 **代码自愈**: QA Agent发现Bug后，PM自动协调修复
- 📊 **实时监控**: Web界面实时显示开发进度和Agent状态
- 🎨 **Web UI**: 友好的Web界面，无需命令行操作

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface (Web)                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              PM Agent (Orchestrator)                     │
│  • 需求分析    • 任务分解    • 协调调度    • Bug修复     │
└─────┬───────────────┬───────────────┬──────────────────┘
      │               │               │
      ▼               ▼               ▼
┌──────────┐   ┌──────────┐   ┌──────────┐
│ Backend  │   │ Frontend │   │    QA    │
│  Agent   │   │  Agent   │   │  Agent   │
└──────────┘   └──────────┘   └──────────┘
      │               │               │
      └───────────────┴───────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Message Bus & Shared State                  │
└─────────────────────────────────────────────────────────┘
```

### Agent职责

| Agent | 角色 | 职责 |
|-------|------|------|
| **PM Agent** | 项目经理/编排器 | 需求分析、API设计、任务分配、进度监控、Bug修复协调 |
| **Backend Agent** | 后端开发 | 根据API契约生成Flask后端代码、实现REST API |
| **Frontend Agent** | 前端开发 | 生成HTML/CSS/JavaScript前端代码、API调用 |
| **QA Agent** | 质量保证 | 执行集成测试、检测Bug、生成测试报告 |

## 🚀 快速开始

### 1. 环境要求

- Python 3.9+
- OpenAI API Key 或 Anthropic API Key

### 2. 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/DevSwarm.git
cd DevSwarm

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，添加你的API密钥
# OPENAI_API_KEY=your_key_here
```

### 4. 启动系统

```bash
# 启动Web服务器
python src/web/app.py
```

打开浏览器访问: http://localhost:3000

### 5. 使用示例

在Web界面输入需求，例如:

```
我想要一个简单的待办事项清单应用，支持添加、删除和查看所有待办事项
```

点击 "Generate App" 按钮，系统将：

1. ✅ 分析需求并设计API契约
2. ✅ 生成后端Flask代码
3. ✅ 生成前端HTML/JS/CSS代码
4. ✅ 执行集成测试
5. ✅ 自动修复发现的Bug
6. ✅ 打包完整项目

生成的项目位于 `workspace/proj_xxxxxxxx/` 目录。

## 📁 项目结构

```
DevSwarm/
├── src/
│   ├── agents/              # Agent实现
│   │   ├── base_agent.py    # Agent基类
│   │   ├── pm_agent.py      # PM Agent
│   │   ├── backend_agent.py # Backend Agent
│   │   ├── frontend_agent.py# Frontend Agent
│   │   └── qa_agent.py      # QA Agent
│   ├── core/                # 核心系统
│   │   ├── message_bus.py   # 消息总线
│   │   ├── shared_state.py  # 共享状态
│   │   └── protocol.py      # 通信协议
│   ├── llm/                 # LLM集成
│   │   └── llm_client.py    # LLM客户端
│   ├── utils/               # 工具函数
│   │   └── packaging.py     # 打包工具
│   └── web/                 # Web界面
│       ├── app.py           # Flask应用
│       └── templates/       # HTML模板
├── workspace/               # 生成的项目
├── config/                  # 配置文件
├── requirements.txt         # Python依赖
├── .env.example            # 环境变量模板
└── README.md               # 本文档
```

## 🔧 核心工作流程

### 1. 需求提交

用户在Web界面输入自然语言需求

### 2. PM Agent处理

```
[PM Agent]
  ├─► 分析需求
  ├─► 定义API契约 (api_contract.json)
  ├─► 分解任务
  │   ├─► T1: Backend开发任务
  │   ├─► T2: Frontend开发任务
  │   └─► T3: QA测试任务
  └─► 分配任务到Worker Agents
```

### 3. 并行开发

```
[Backend Agent]          [Frontend Agent]
  ├─► 读取API契约         ├─► 读取API契约
  ├─► 生成Flask代码       ├─► 生成HTML/CSS/JS
  ├─► 创建存储模块        ├─► 实现API调用
  └─► 报告完成            └─► 报告完成
```

### 4. 集成测试

```
[QA Agent]
  ├─► 启动后端服务
  ├─► 测试所有API端点
  ├─► 检测Bug
  └─► 报告结果
```

### 5. Bug修复循环（如果有Bug）

```
[PM Agent]                [Backend/Frontend Agent]
  ├─► 接收Bug报告          ├─► 接收修复任务
  ├─► 分析根因             ├─► 应用代码补丁
  ├─► 生成修复建议         └─► 报告完成
  ├─► 创建修复任务             ↓
  └─► 分配任务          [QA Agent]
                          └─► 回归测试
```

## 🌟 核心特性详解

### 1. 通信协议

所有Agent间通信遵循统一的消息格式:

```python
{
  "message_id": "uuid",
  "timestamp": "2025-11-17T20:30:00Z",
  "from_agent": "PM_Agent",
  "to_agent": "Backend_Agent",
  "type": "task_assignment",  # 任务分配/状态更新/错误报告等
  "task": { ... },
  "payload": { ... }
}
```

### 2. API契约驱动

PM Agent首先定义API契约，确保前后端开发对齐:

```json
{
  "base_url": "http://localhost:5000",
  "endpoints": [
    {
      "method": "GET",
      "path": "/api/items",
      "description": "获取所有项目",
      "response": {"items": []}
    }
  ]
}
```

### 3. 代码自愈机制

```
Bug检测 → 根因分析 → 生成修复 → 应用补丁 → 回归测试
```

## 📊 监控与调试

### Web界面功能

- **实时状态**: 查看项目状态、任务进度
- **Agent监控**: 查看每个Agent的当前任务
- **消息历史**: 查看Agent间的通信记录
- **项目摘要**: 查看详细的项目信息

### API端点

```bash
# 获取项目状态
GET /api/status

# 获取消息历史
GET /api/messages?limit=50

# 获取Agent状态
GET /api/agents

# 健康检查
GET /api/health
```

## 🎨 生成的应用示例

对于需求: "待办事项清单应用"

系统会生成:

```
workspace/proj_abc123/
├── backend/
│   ├── app.py              # Flask应用
│   ├── storage.py          # 数据存储
│   ├── requirements.txt    # 依赖
│   ├── Dockerfile
│   └── README.md
├── frontend/
│   ├── index.html          # 主页面
│   ├── app.js             # 应用逻辑
│   ├── style.css          # 样式
│   ├── Dockerfile
│   └── README.md
├── api_contract.json       # API规范
├── docker-compose.yml      # Docker配置
└── README.md              # 项目文档
```

### 运行生成的应用

```bash
cd workspace/proj_abc123

# 使用Docker Compose
docker-compose up

# 或手动运行
cd backend && python app.py    # 终端1
cd frontend && python -m http.server 8000  # 终端2
```

## 🔌 扩展性

### 添加新的Agent

```python
from src.agents.base_agent import BaseAgent

class CustomAgent(BaseAgent):
    def __init__(self, message_bus, shared_state, llm_client):
        super().__init__(
            agent_name="Custom_Agent",
            role="Custom Role",
            message_bus=message_bus,
            shared_state=shared_state,
            llm_client=llm_client
        )

    async def execute_task(self, task: Task) -> Dict[str, Any]:
        # 实现任务执行逻辑
        pass
```

### 支持新的LLM提供商

在 `src/llm/llm_client.py` 中添加新的provider支持。

## 🧪 测试

```bash
# 运行测试
pytest tests/

# 测试特定模块
pytest tests/test_agents.py
```

## 📝 配置

编辑 `config/config.yaml` 自定义系统行为:

```yaml
llm:
  provider: "openai"
  temperature: 0.7
  max_tokens: 2000

agents:
  backend_agent:
    default_framework: "flask"  # 或 fastapi

  frontend_agent:
    default_framework: "vanilla"  # 或 react, vue
```

## 🐛 故障排查

### 问题: LLM API调用失败

**解决**: 检查 `.env` 文件中的API密钥是否正确

### 问题: 生成的代码有语法错误

**解决**:
- 调低LLM的temperature参数
- 使用更强大的模型 (如 GPT-4)

### 问题: 测试失败

**解决**: QA Agent会自动报告Bug，PM会协调修复

## 🛣️ 路线图

- [ ] 支持更多后端框架 (FastAPI, Express.js)
- [ ] 支持React/Vue前端生成
- [ ] 数据库设计和迁移支持
- [ ] 用户认证模块生成
- [ ] Agent间直接协商机制
- [ ] 可视化工作流编辑器
- [ ] 云部署集成

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request!

## 📞 联系方式

- Issues: https://github.com/yourusername/DevSwarm/issues
- Email: your.email@example.com

## 🙏 致谢

本项目灵感来源于多Agent系统研究和AutoGPT、MetaGPT等项目。

---

**Built with ❤️ by DevSwarm Team**
