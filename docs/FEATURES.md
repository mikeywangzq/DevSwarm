# DevSwarm 功能文档
# Features Documentation

本文档详细介绍DevSwarm多Agent系统的所有核心功能和高级特性。

---

## 📑 目录

1. [核心功能](#核心功能)
2. [高级特性](#高级特性)
3. [多语言后端支持](#多语言后端支持)
4. [多框架前端支持](#多框架前端支持)
5. [测试与质量保证](#测试与质量保证)
6. [分布式部署](#分布式部署)
7. [监控与调试](#监控与调试)
8. [配置选项](#配置选项)

---

## 🎯 核心功能

### 1. 智能需求理解

DevSwarm的PM Agent能够理解自然语言需求，自动分析并生成完整的技术方案。

**功能特点:**
- 自然语言需求输入
- 自动需求分析和拆解
- API契约自动生成
- 智能任务分配

**使用示例:**
```python
# 简单的需求描述
requirement = "创建一个待办事项管理应用，支持添加、查看、删除待办事项"

# PM Agent自动生成API契约
api_contract = {
    "base_url": "http://localhost:5000",
    "endpoints": [
        {"method": "GET", "path": "/api/items", "description": "获取所有待办事项"},
        {"method": "POST", "path": "/api/items", "description": "添加新待办事项"},
        {"method": "DELETE", "path": "/api/items/:id", "description": "删除待办事项"}
    ]
}
```

### 2. 多Agent协作

4个专业化Agent协同工作，模拟真实的软件开发团队。

**Agent角色:**

| Agent | 职责 | 输入 | 输出 |
|-------|------|------|------|
| **PM Agent** | 项目管理、需求分析 | 用户需求 | API契约、任务分配 |
| **Backend Agent** | 后端开发 | API契约 | 后端代码 |
| **Frontend Agent** | 前端开发 | API契约 | 前端代码 |
| **QA Agent** | 测试与质量保证 | 完整应用 | 测试报告、Bug列表 |

**协作流程:**
```mermaid
graph LR
    A[用户需求] --> B[PM Agent分析]
    B --> C[生成API契约]
    C --> D[Backend开发]
    C --> E[Frontend开发]
    D --> F[QA测试]
    E --> F
    F --> G{测试通过?}
    G -->|否| H[Bug修复]
    H --> F
    G -->|是| I[项目完成]
```

### 3. 自动化Bug修复

QA Agent发现Bug后，会自动分配给相应的Agent进行修复。

**自愈流程:**
1. QA Agent运行集成测试
2. 检测到API错误或前端问题
3. 生成详细的Bug报告
4. 自动分配给Backend/Frontend Agent
5. Agent分析并修复Bug
6. 重新运行测试验证
7. 循环直到所有测试通过

**Bug报告示例:**
```python
bug_report = {
    "bug_id": "BUG_001",
    "severity": "high",
    "component": "backend",
    "error_type": "API Error",
    "description": "POST /api/items returns 500",
    "stack_trace": "...",
    "reproduction_steps": [...]
}
```

---

## ✨ 高级特性

### 1. 实时日志流 (WebSocket)

**文件:** `src/web/app.py`
**端点:** `ws://localhost:3000/logs`

通过WebSocket实时查看Agent执行日志。

**前端连接:**
```javascript
const ws = new WebSocket('ws://localhost:3000/logs');

ws.onmessage = (event) => {
    const log = JSON.parse(event.data);
    console.log(`[${log.timestamp}] ${log.agent}: ${log.message}`);
};
```

**日志格式:**
```json
{
    "timestamp": "2025-11-18T10:30:45Z",
    "level": "INFO",
    "agent": "Backend_Agent",
    "message": "Generated Flask application",
    "metadata": {
        "files_count": 3,
        "lines_of_code": 150
    }
}
```

### 2. 代码预览功能

**端点:** `GET /api/preview/<path:file_path>`

在Web界面直接预览生成的代码，支持语法高亮。

**支持的文件类型:**
- Python (.py)
- JavaScript (.js, .jsx)
- TypeScript (.ts, .tsx)
- HTML (.html)
- CSS (.css)
- JSON (.json)
- Markdown (.md)

**API响应:**
```json
{
    "file_path": "backend/app.py",
    "content": "from flask import Flask...",
    "language": "python",
    "lines": 120,
    "size_bytes": 3500
}
```

### 3. 性能测试

**文件:** `src/testing/performance_testing.py`
**端点:** `POST /api/performance/run`

自动对生成的后端API进行性能测试。

**测试指标:**
- 响应时间 (平均/最小/最大/P95/P99)
- 吞吐量 (请求/秒)
- 并发处理能力
- 错误率

**性能报告示例:**
```json
{
    "endpoint": "GET /api/items",
    "total_requests": 1000,
    "duration_seconds": 10.5,
    "throughput_rps": 95.2,
    "response_times": {
        "avg_ms": 105,
        "min_ms": 45,
        "max_ms": 350,
        "p95_ms": 180,
        "p99_ms": 250
    },
    "success_rate": 99.8
}
```

### 4. 安全扫描

**文件:** `src/testing/security_scanner.py`
**端点:** `POST /api/security/scan`

自动扫描代码中的安全漏洞。

**检测的漏洞类型:**
- SQL注入
- XSS (跨站脚本)
- 硬编码密钥
- 不安全的加密
- 路径遍历
- 命令注入
- CSRF漏洞

**扫描报告:**
```json
{
    "total_issues": 3,
    "critical": 1,
    "high": 0,
    "medium": 2,
    "low": 0,
    "issues": [
        {
            "severity": "critical",
            "type": "hardcoded_secret",
            "file": "backend/app.py",
            "line": 25,
            "code": "SECRET_KEY = 'hardcoded-secret'",
            "recommendation": "使用环境变量存储密钥"
        }
    ]
}
```

---

## 🐍 多语言后端支持

DevSwarm支持生成3种后端语言/框架。

### Python + Flask (默认)

**配置:**
```bash
export DEVSWARM_BACKEND_LANGUAGE=flask
```

**生成的项目结构:**
```
backend/
├── app.py              # Flask应用主文件
├── storage.py          # 数据存储层
├── requirements.txt    # Python依赖
└── README.md
```

**特点:**
- Flask web框架
- CORS支持
- JSON文件存储
- 简单易部署

**生成的代码示例:**
```python
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/items', methods=['GET'])
def get_items():
    items = storage.load_all()
    return jsonify({'items': items})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### Node.js + Express

**配置:**
```bash
export DEVSWARM_BACKEND_LANGUAGE=nodejs
```

**生成的项目结构:**
```
backend/
├── server.js           # Express服务器
├── storage.js          # 数据存储
├── package.json        # npm依赖
└── README.md
```

**特点:**
- Express.js框架
- 异步/await支持
- npm包管理
- nodemon热重载

**生成的代码示例:**
```javascript
const express = require('express');
const cors = require('cors');
const storage = require('./storage');

const app = express();
app.use(cors());
app.use(express.json());

app.get('/api/items', async (req, res) => {
    const items = await storage.loadAll();
    res.json({ items });
});

app.listen(5000, () => {
    console.log('Server running on port 5000');
});
```

### Go + Gin

**配置:**
```bash
export DEVSWARM_BACKEND_LANGUAGE=go
```

**生成的项目结构:**
```
backend/
├── main.go             # Go主文件
├── storage.go          # 数据存储
├── go.mod              # Go模块
└── README.md
```

**特点:**
- 高性能Gin框架
- 并发处理
- 类型安全
- 编译型语言

**生成的代码示例:**
```go
package main

import (
    "github.com/gin-gonic/gin"
    "github.com/gin-contrib/cors"
)

func main() {
    r := gin.Default()
    r.Use(cors.Default())

    r.GET("/api/items", func(c *gin.Context) {
        items := storage.LoadAll()
        c.JSON(200, gin.H{"items": items})
    })

    r.Run(":5000")
}
```

### 后端语言对比

| 特性 | Flask | Node.js | Go |
|------|-------|---------|-----|
| **性能** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **开发速度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **并发处理** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **生态系统** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **学习曲线** | 平缓 | 中等 | 陡峭 |
| **适用场景** | 快速原型 | 全栈开发 | 高性能服务 |

---

## ⚛️ 多框架前端支持

DevSwarm支持生成3种前端框架。

### Vanilla JavaScript (默认)

**配置:**
```bash
export DEVSWARM_FRONTEND_FRAMEWORK=vanilla
```

**项目结构:**
```
frontend/
├── index.html          # HTML页面
├── app.js              # JavaScript逻辑
├── style.css           # 样式
└── README.md
```

**特点:**
- 无框架依赖
- 轻量级
- 快速加载
- 简单直接

**代码示例:**
```javascript
// app.js
const API_URL = 'http://localhost:5000';

async function loadItems() {
    const response = await fetch(`${API_URL}/api/items`);
    const data = await response.json();
    renderItems(data.items);
}

function renderItems(items) {
    const container = document.getElementById('items-container');
    container.innerHTML = items.map(item => `
        <div class="item">
            <span>${item.title}</span>
            <button onclick="deleteItem('${item.id}')">Delete</button>
        </div>
    `).join('');
}
```

### React 18

**配置:**
```bash
export DEVSWARM_FRONTEND_FRAMEWORK=react
```

**项目结构:**
```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── App.jsx         # React主组件
│   ├── App.css         # 组件样式
│   ├── index.js        # 入口文件
│   └── services/
│       └── api.js      # API服务层
├── package.json
└── README.md
```

**特点:**
- React Hooks (useState, useEffect)
- 组件化开发
- 现代化开发体验
- create-react-app配置

**代码示例:**
```jsx
// src/App.jsx
import React, { useState, useEffect } from 'react';
import { getItems, createItem, deleteItem } from './services/api';

function App() {
    const [items, setItems] = useState([]);
    const [newItem, setNewItem] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        loadItems();
    }, []);

    const loadItems = async () => {
        setLoading(true);
        try {
            const data = await getItems();
            setItems(data.items || []);
        } catch (error) {
            console.error('Failed to load items:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleAddItem = async (e) => {
        e.preventDefault();
        if (!newItem.trim()) return;

        try {
            await createItem({ title: newItem });
            setNewItem('');
            loadItems();
        } catch (error) {
            console.error('Failed to add item:', error);
        }
    };

    return (
        <div className="App">
            <h1>Todo List</h1>
            <form onSubmit={handleAddItem}>
                <input
                    type="text"
                    value={newItem}
                    onChange={(e) => setNewItem(e.target.value)}
                    placeholder="Add new item"
                />
                <button type="submit">Add</button>
            </form>
            {loading ? (
                <p>Loading...</p>
            ) : (
                <div className="items">
                    {items.map(item => (
                        <div key={item.id} className="item">
                            <span>{item.title}</span>
                            <button onClick={() => deleteItem(item.id).then(loadItems)}>
                                Delete
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default App;
```

### Vue 3

**配置:**
```bash
export DEVSWARM_FRONTEND_FRAMEWORK=vue
```

**项目结构:**
```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── App.vue         # Vue主组件
│   ├── main.js         # 入口文件
│   └── services/
│       └── api.js      # API服务层
├── package.json
└── README.md
```

**特点:**
- Composition API
- 单文件组件(.vue)
- Vite构建工具
- 响应式数据绑定

**代码示例:**
```vue
<!-- src/App.vue -->
<template>
    <div id="app">
        <h1>Todo List</h1>
        <form @submit.prevent="handleAddItem">
            <input
                v-model="newItem"
                type="text"
                placeholder="Add new item"
                :disabled="loading"
            />
            <button type="submit" :disabled="loading">
                {{ loading ? 'Loading...' : 'Add' }}
            </button>
        </form>
        <div v-if="loading" class="loading">Loading...</div>
        <div v-else class="items">
            <div v-for="item in items" :key="item.id" class="item">
                <span>{{ item.title }}</span>
                <button @click="handleDeleteItem(item.id)">Delete</button>
            </div>
        </div>
    </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { getItems, createItem, deleteItem } from './services/api';

export default {
    setup() {
        const items = ref([]);
        const newItem = ref('');
        const loading = ref(false);

        const loadItems = async () => {
            loading.value = true;
            try {
                const data = await getItems();
                items.value = data.items || [];
            } catch (error) {
                console.error('Failed to load items:', error);
            } finally {
                loading.value = false;
            }
        };

        const handleAddItem = async () => {
            if (!newItem.value.trim()) return;

            try {
                await createItem({ title: newItem.value });
                newItem.value = '';
                loadItems();
            } catch (error) {
                console.error('Failed to add item:', error);
            }
        };

        const handleDeleteItem = async (id) => {
            try {
                await deleteItem(id);
                loadItems();
            } catch (error) {
                console.error('Failed to delete item:', error);
            }
        };

        onMounted(() => {
            loadItems();
        });

        return {
            items,
            newItem,
            loading,
            handleAddItem,
            handleDeleteItem
        };
    }
};
</script>

<style scoped>
.app {
    max-width: 600px;
    margin: 0 auto;
    padding: 20px;
}
/* ... */
</style>
```

### 前端框架对比

| 特性 | Vanilla JS | React | Vue |
|------|-----------|-------|-----|
| **学习曲线** | ⭐ 最简单 | ⭐⭐⭐ 中等 | ⭐⭐ 较简单 |
| **性能** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **开发效率** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **生态系统** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **构建大小** | ~5KB | ~45KB | ~35KB |
| **适用场景** | 简单页面 | 大型应用 | 中小型应用 |

---

## 🧪 测试与质量保证

### 1. E2E测试 (Playwright)

**文件:** `src/testing/e2e_testing.py`
**端点:** `POST /api/e2e/run`

使用Playwright进行端到端浏览器测试。

**安装:**
```bash
pip install playwright
playwright install
```

**自动生成的测试用例:**

1. **页面加载测试**
   ```python
   test_case = {
       "name": "test_page_load",
       "steps": [
           {"action": "navigate", "url": "http://localhost:8000"},
           {"action": "wait_for_selector", "selector": "body"},
           {"action": "assert_title_contains", "text": "DevSwarm"}
       ]
   }
   ```

2. **添加项目测试**
   ```python
   test_case = {
       "name": "test_add_item",
       "steps": [
           {"action": "fill", "selector": "input", "value": "Test Item"},
           {"action": "click", "selector": "button[type='submit']"},
           {"action": "assert_text_present", "text": "Test Item"}
       ]
   }
   ```

3. **删除项目测试**
4. **API健康检查测试**

**测试报告:**
```json
{
    "total_tests": 4,
    "passed_tests": 4,
    "failed_tests": 0,
    "test_cases": [
        {
            "name": "test_page_load",
            "passed": true,
            "duration_ms": 1250,
            "screenshot_path": ""
        }
    ]
}
```

### 2. 集成测试

QA Agent自动运行的集成测试。

**测试流程:**
1. 启动后端服务器
2. 启动前端服务器
3. 等待服务就绪
4. 执行API测试
5. 执行UI测试
6. 生成测试报告

### 3. 性能基准测试

**测试类型:**
- 吞吐量测试
- 延迟测试
- 并发测试
- 压力测试

**报告示例:**
```
性能测试报告
=============
端点: GET /api/items
并发用户: 100
请求总数: 10000

结果:
- 吞吐量: 1250 req/s
- 平均响应时间: 80ms
- P95响应时间: 150ms
- P99响应时间: 250ms
- 成功率: 99.95%
```

---

## 🌐 分布式部署

### 概述

DevSwarm设计了完整的分布式架构，支持水平扩展和高可用部署。

**架构文档:** `DISTRIBUTED_ARCHITECTURE.md`

### 部署模式

#### 模式1: Docker Compose (推荐用于开发)

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: devswarm
    ports:
      - "5432:5432"

  pm-agent:
    build: .
    environment:
      AGENT_TYPE: pm
      REDIS_URL: redis://redis:6379
      POSTGRES_URL: postgresql://postgres:5432/devswarm

  backend-agent:
    build: .
    environment:
      AGENT_TYPE: backend
    deploy:
      replicas: 3  # 3个实例

  frontend-agent:
    build: .
    environment:
      AGENT_TYPE: frontend
    deploy:
      replicas: 2  # 2个实例
```

**启动:**
```bash
docker-compose -f docker-compose.distributed.yml up
```

#### 模式2: Kubernetes (生产环境)

**部署Backend Agent:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-agent
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: backend-agent
        image: devswarm/backend-agent:v1.0.0
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379"
```

**自动扩缩容:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-agent-hpa
spec:
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        averageUtilization: 70
```

### 分布式组件

#### Redis消息总线

**文件:** `src/core/message_bus_redis.py`

```python
from src.core.message_bus_redis import RedisMessageBus

# 创建分布式消息总线
bus = RedisMessageBus("redis://localhost:6379")

# 发布消息
bus.publish("task.backend", {
    "task_id": "T1",
    "action": "execute"
})

# 订阅消息
def handle_task(message):
    print(f"Received: {message}")

bus.subscribe("task.backend", handle_task)
bus.start_listening()
```

**特性:**
- Pub/Sub模式
- 自动重连
- 消息重试
- 线程安全

#### PostgreSQL状态存储

**文件:** `src/core/state_store_postgres.py`

```python
from src.core.state_store_postgres import PostgreSQLStateStore

# 创建状态存储
store = PostgreSQLStateStore("postgresql://user:pass@localhost/devswarm")

# 保存API契约
store.set_api_contract(api_contract, project_id="proj_123")

# 获取API契约
contract = store.get_api_contract("proj_123")

# 添加任务
store.add_task({
    "id": "T1",
    "type": "backend_dev",
    "status": "pending"
}, project_id="proj_123")
```

**特性:**
- ACID事务
- 关系型数据
- 历史记录追踪
- 自动重连

---

## 📊 监控与调试

### Web界面监控

访问 `http://localhost:3000` 查看实时状态。

**功能:**
- 项目进度可视化
- Agent状态监控
- 实时日志流
- 代码预览
- 测试报告查看

### API端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/status` | GET | 项目状态 |
| `/api/messages` | GET | 消息历史 |
| `/api/preview/<path>` | GET | 代码预览 |
| `/api/logs` | WS | 实时日志流 |
| `/api/e2e/run` | POST | 运行E2E测试 |
| `/api/performance/run` | POST | 运行性能测试 |
| `/api/security/scan` | POST | 安全扫描 |

### 状态查询示例

```bash
# 查看项目状态
curl http://localhost:3000/api/status

# 响应
{
    "project": {
        "project_id": "proj_abc123",
        "status": "developing",
        "progress": 75
    },
    "agents": [
        {
            "name": "Backend_Agent",
            "status": "active",
            "current_task": "T1_Backend"
        }
    ],
    "tasks": {
        "total": 3,
        "completed": 2,
        "pending": 1
    }
}
```

---

## ⚙️ 配置选项

### 环境变量

所有配置通过环境变量设置，支持`.env`文件。

**核心配置:**
```bash
# LLM提供商
DEVSWARM_LLM_PROVIDER=openai        # openai 或 anthropic
DEVSWARM_LLM_MODEL=gpt-4            # 模型名称
OPENAI_API_KEY=sk-...               # OpenAI API密钥
ANTHROPIC_API_KEY=sk-...            # Anthropic API密钥

# 后端语言
DEVSWARM_BACKEND_LANGUAGE=flask     # flask, nodejs, go

# 前端框架
DEVSWARM_FRONTEND_FRAMEWORK=react   # vanilla, react, vue

# 工作区
DEVSWARM_WORKSPACE_ROOT=./workspace # 代码生成目录

# 功能开关
DEVSWARM_ENABLE_PERFORMANCE=true    # 性能测试
DEVSWARM_ENABLE_SECURITY=true       # 安全扫描
DEVSWARM_ENABLE_E2E=true            # E2E测试

# 分布式支持
REDIS_URL=redis://localhost:6379    # Redis连接
POSTGRES_URL=postgresql://...       # PostgreSQL连接

# 日志
DEVSWARM_LOG_LEVEL=INFO             # DEBUG, INFO, WARNING, ERROR
```

### 配置文件

**`.env.example`:**
```bash
# 复制并重命名为 .env
cp .env.example .env

# 编辑配置
vim .env
```

### 配置验证

```python
from src.config.settings import get_config

config = get_config()
print(f"Backend Language: {config.backend_language}")
print(f"Frontend Framework: {config.frontend_framework}")
print(f"LLM Provider: {config.llm_provider}")
```

---

## 📚 文档索引

- **[README.md](../README.md)** - 项目概述和快速开始
- **[ARCHITECTURE.md](../ARCHITECTURE.md)** - 系统架构详解
- **[DISTRIBUTED_ARCHITECTURE.md](../DISTRIBUTED_ARCHITECTURE.md)** - 分布式部署设计
- **[BUG_REPORT.md](../BUG_REPORT.md)** - Bug修复记录
- **[CONTRIBUTING.md](../CONTRIBUTING.md)** - 贡献指南

---

## 🎓 使用教程

### 快速开始

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **配置API密钥**
   ```bash
   export OPENAI_API_KEY=sk-your-key
   ```

3. **启动系统**
   ```bash
   python src/web/app.py
   ```

4. **访问Web界面**
   ```
   http://localhost:3000
   ```

5. **提交需求**
   ```
   输入: "创建一个图书管理系统"
   等待: DevSwarm自动生成完整应用
   下载: workspace/目录下的生成代码
   ```

### 高级用法

**选择后端语言:**
```bash
export DEVSWARM_BACKEND_LANGUAGE=nodejs
python src/web/app.py
```

**选择前端框架:**
```bash
export DEVSWARM_FRONTEND_FRAMEWORK=vue
python src/web/app.py
```

**启用所有测试:**
```bash
export DEVSWARM_ENABLE_PERFORMANCE=true
export DEVSWARM_ENABLE_SECURITY=true
export DEVSWARM_ENABLE_E2E=true
python src/web/app.py
```

**分布式部署:**
```bash
# 启动Redis和PostgreSQL
docker-compose up redis postgres

# 配置连接
export REDIS_URL=redis://localhost:6379
export POSTGRES_URL=postgresql://user:pass@localhost/devswarm

# 启动Agent
python -m src.agents.pm_agent_service
python -m src.agents.backend_agent_service
python -m src.agents.frontend_agent_service
```

---

## 🔧 故障排查

### 常见问题

**Q: LLM API调用失败**
```bash
# 检查API密钥
echo $OPENAI_API_KEY

# 测试连接
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**Q: 生成的代码质量差**
- 使用GPT-4而非GPT-3.5
- 调低temperature参数 (0.2-0.5)
- 提供更详细的需求描述

**Q: E2E测试失败**
```bash
# 安装Playwright浏览器
playwright install

# 检查服务是否运行
curl http://localhost:5000/health
curl http://localhost:8000
```

**Q: 分布式模式连接失败**
```bash
# 检查Redis
redis-cli ping

# 检查PostgreSQL
psql -h localhost -U devswarm -d devswarm -c "SELECT 1"
```

---

## 📈 性能优化

### 建议

1. **使用更快的LLM模型** - GPT-4 Turbo比GPT-4快2-3倍
2. **并行执行任务** - Backend和Frontend Agent可并行工作
3. **缓存API契约** - 避免重复生成相同的契约
4. **使用分布式模式** - 水平扩展Backend/Frontend Agent
5. **启用Redis缓存** - 缓存中间结果

### 性能基准

**单机模式:**
- 简单应用: 2-3分钟
- 中等应用: 5-8分钟
- 复杂应用: 10-15分钟

**分布式模式 (3个Backend Agent):**
- 简单应用: 1-2分钟
- 中等应用: 3-5分钟
- 复杂应用: 6-10分钟

---

## 🚀 未来计划

见 [README.md](../README.md#发展路线图)

---

**文档版本:** v1.0.0
**最后更新:** 2025-11-18
**维护者:** DevSwarm Team
