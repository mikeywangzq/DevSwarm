# Contributing to DevSwarm

感谢您对DevSwarm项目的兴趣！我们欢迎各种形式的贡献。

## 如何贡献

### 报告Bug

如果您发现了Bug，请创建一个Issue并包含以下信息：

1. **Bug描述**: 清晰简洁的描述
2. **复现步骤**: 如何重现这个问题
3. **期望行为**: 您期望发生什么
4. **实际行为**: 实际发生了什么
5. **环境信息**: 操作系统、Python版本、依赖版本
6. **日志**: 相关的错误日志或截图

### 提出新功能

我们欢迎新功能建议！请创建一个Issue并说明：

1. **功能描述**: 您希望添加什么功能
2. **使用场景**: 为什么需要这个功能
3. **实现建议**: 如果有的话，您对实现的想法

### 提交代码

1. **Fork仓库**

2. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **编写代码**
   - 遵循项目的代码风格
   - 添加必要的注释
   - 编写单元测试

4. **运行测试**
   ```bash
   pytest tests/
   ```

5. **提交更改**
   ```bash
   git add .
   git commit -m "Add: your feature description"
   ```

6. **推送到GitHub**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **创建Pull Request**
   - 清晰描述您的更改
   - 链接相关的Issue
   - 确保所有测试通过

## 代码规范

### Python代码风格

- 遵循 PEP 8 规范
- 使用类型提示 (Type Hints)
- 函数和类都要有文档字符串

示例:
```python
def process_data(input: str, config: Dict[str, Any]) -> List[str]:
    """
    处理输入数据

    Args:
        input: 输入字符串
        config: 配置字典

    Returns:
        处理后的字符串列表
    """
    pass
```

### 提交信息规范

使用清晰的提交信息:

- `Add: 新增功能`
- `Fix: 修复Bug`
- `Update: 更新功能`
- `Refactor: 重构代码`
- `Docs: 更新文档`
- `Test: 添加测试`

## 项目结构

```
DevSwarm/
├── src/
│   ├── agents/      # Agent实现
│   ├── core/        # 核心组件
│   ├── llm/         # LLM集成
│   ├── utils/       # 工具函数
│   └── web/         # Web界面
├── tests/           # 测试文件
├── config/          # 配置文件
└── workspace/       # 生成的项目
```

## 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/yourusername/DevSwarm.git
cd DevSwarm

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装开发依赖
pip install -r requirements.txt
pip install -e .

# 运行测试
pytest tests/
```

## 添加新Agent

要添加新的Agent类型:

1. 在 `src/agents/` 创建新文件
2. 继承 `BaseAgent` 类
3. 实现 `execute_task()` 方法
4. 在 `src/agents/__init__.py` 中导出
5. 添加相应的测试

示例:
```python
from .base_agent import BaseAgent
from ..core.protocol import Task

class MyAgent(BaseAgent):
    def __init__(self, message_bus, shared_state, llm_client):
        super().__init__(
            agent_name="My_Agent",
            role="My Role",
            message_bus=message_bus,
            shared_state=shared_state,
            llm_client=llm_client
        )

    async def execute_task(self, task: Task) -> Dict[str, Any]:
        # 实现任务逻辑
        return {"status": "success"}
```

## 测试

我们使用 pytest 进行测试:

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_agents.py

# 运行特定测试
pytest tests/test_agents.py::test_pm_agent

# 查看覆盖率
pytest --cov=src tests/
```

## 文档

- 代码中的文档字符串使用中文
- README和用户文档使用中文
- API文档使用Sphinx生成

## 问题讨论

如有任何问题，欢迎：
- 创建Issue讨论
- 在Pull Request中评论
- 联系维护者

## 行为准则

- 尊重所有贡献者
- 建设性的反馈
- 专注于代码和技术讨论

## 许可证

提交代码即表示您同意您的代码使用MIT许可证。

---

感谢您的贡献！
