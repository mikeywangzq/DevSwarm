# DevSwarm 快速开始指南

## 5分钟快速体验

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置API密钥

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，添加你的OpenAI API密钥
# OPENAI_API_KEY=sk-...
```

### 3. 启动系统

**方式1: 使用Web界面（推荐）**

```bash
# 使用启动脚本
./start.sh

# 或直接运行
python src/web/app.py
```

然后访问: http://localhost:3000

**方式2: 使用命令行Demo**

```bash
python demo.py
```

### 4. 创建你的第一个应用

在Web界面输入需求，例如:

```
我想要一个简单的待办事项清单应用，支持添加、删除和查看所有待办事项
```

点击"Generate App"，等待几分钟，系统将自动：

✅ 分析需求
✅ 设计API
✅ 生成后端代码
✅ 生成前端代码
✅ 执行测试
✅ 打包项目

### 5. 运行生成的应用

```bash
# 进入生成的项目目录
cd workspace/proj_xxxxxxxx

# 启动后端（终端1）
cd backend
pip install -r requirements.txt
python app.py

# 启动前端（终端2）
cd frontend
python -m http.server 8000
```

访问: http://localhost:8000

## 常见问题

**Q: 没有OpenAI API密钥怎么办？**

A: 系统会使用fallback模式，生成基础的模板代码，虽然不如使用LLM智能，但仍可演示整个流程。

**Q: 生成的代码质量如何？**

A: 使用GPT-4可以获得较好的代码质量。代码包含注释、错误处理和基本的最佳实践。

**Q: 可以生成什么类型的应用？**

A: 目前支持简单的CRUD Web应用，如：
- 待办事项列表
- 笔记应用
- 简单的博客系统
- 联系人管理
- 等等

**Q: 如何自定义生成的代码？**

A: 在 `workspace/proj_xxx/` 目录下直接编辑生成的代码即可。

## 下一步

- 阅读 [README.md](README.md) 了解完整功能
- 查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解如何贡献
- 探索 `src/` 目录了解系统架构

## 示例需求

试试这些需求：

1. "创建一个简单的书签管理应用"
2. "我需要一个联系人管理系统，可以添加、编辑、删除联系人"
3. "制作一个简单的日记应用，可以记录每日心情"
4. "创建一个产品清单应用，显示产品名称和价格"

---

祝您使用愉快！🚀
