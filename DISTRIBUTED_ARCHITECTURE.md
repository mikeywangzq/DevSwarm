# DevSwarm 分布式架构设计
# Distributed Architecture Design

## 📋 目录 Table of Contents

1. [概述 Overview](#概述-overview)
2. [架构原则 Design Principles](#架构原则-design-principles)
3. [分布式部署模式 Deployment Patterns](#分布式部署模式-deployment-patterns)
4. [技术选型 Technology Stack](#技术选型-technology-stack)
5. [实施路线图 Implementation Roadmap](#实施路线图-implementation-roadmap)
6. [监控与运维 Monitoring & Operations](#监控与运维-monitoring--operations)

---

## 概述 Overview

### 当前架构 Current Architecture

DevSwarm当前采用**单机多Agent架构**，所有Agent运行在同一进程中：

```
┌─────────────────────────────────────────┐
│         Single Process/Machine          │
│                                          │
│  ┌──────────┐  ┌──────────┐            │
│  │ PM Agent │  │ Backend  │            │
│  └──────────┘  │  Agent   │            │
│                 └──────────┘            │
│  ┌──────────┐  ┌──────────┐            │
│  │ Frontend │  │   QA     │            │
│  │  Agent   │  │  Agent   │            │
│  └──────────┘  └──────────┘            │
│                                          │
│       In-Memory Message Bus              │
│       In-Memory Shared State             │
└─────────────────────────────────────────┘
```

**优点**:
- 简单易部署
- 低延迟通信
- 无网络开销
- 易于调试

**限制**:
- 单点故障
- 资源竞争
- 无法水平扩展
- 性能瓶颈

### 分布式架构目标 Distributed Architecture Goals

1. **高可用性** - 消除单点故障
2. **水平扩展** - Agent可独立扩展
3. **资源隔离** - Agent运行在独立容器/机器
4. **负载均衡** - 智能任务分配
5. **容错能力** - 自动故障恢复

---

## 架构原则 Design Principles

### 1. 松耦合 Loose Coupling

Agent之间通过消息队列通信，不直接依赖：

```python
# ❌ 紧耦合 - 直接调用
backend_agent = BackendAgent()
result = backend_agent.execute_task(task)

# ✅ 松耦合 - 消息传递
message_bus.publish("task.backend", task)
# Backend Agent异步处理
```

### 2. 状态外部化 State Externalization

共享状态存储在外部数据库，而非内存：

```python
# ❌ 内存状态
self.shared_state = {}

# ✅ 外部状态
self.shared_state = RedisStateStore()
# 或
self.shared_state = PostgreSQLStateStore()
```

### 3. 服务发现 Service Discovery

Agent动态注册和发现：

```python
# Agent启动时注册
service_registry.register("backend_agent", {
    "host": "10.0.1.5",
    "port": 5001,
    "status": "healthy"
})

# PM Agent发现可用的Backend Agent
backend_agents = service_registry.discover("backend_agent")
```

### 4. 容错设计 Fault Tolerance

- **重试机制**: 任务失败自动重试
- **超时处理**: 长时间无响应则超时
- **降级策略**: 部分Agent失败不影响整体
- **健康检查**: 定期检查Agent状态

---

## 分布式部署模式 Deployment Patterns

### 模式1: 容器化分布式 Containerized Distribution

每个Agent运行在独立容器中：

```
┌─────────────────────────────────────────────────────────────────┐
│                      Kubernetes Cluster                         │
│                                                                   │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐           │
│  │   Pod 1    │    │   Pod 2    │    │   Pod 3    │           │
│  │            │    │            │    │            │           │
│  │ PM Agent   │    │ Backend    │    │ Frontend   │           │
│  │            │    │ Agent x 3  │    │ Agent x 2  │           │
│  └─────┬──────┘    └─────┬──────┘    └─────┬──────┘           │
│        │                 │                  │                   │
│        └─────────────────┼──────────────────┘                   │
│                          │                                      │
└──────────────────────────┼──────────────────────────────────────┘
                           │
                ┌──────────┴──────────┐
                │                     │
         ┌──────▼──────┐      ┌──────▼──────┐
         │   Redis     │      │ PostgreSQL  │
         │ Message Bus │      │ State Store │
         └─────────────┘      └─────────────┘
```

**特点**:
- 使用Kubernetes进行编排
- Agent通过Redis Pub/Sub通信
- 状态存储在PostgreSQL
- 自动扩缩容
- 滚动更新

**部署配置**:

```yaml
# k8s/backend-agent-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-agent
spec:
  replicas: 3  # 3个Backend Agent实例
  selector:
    matchLabels:
      app: backend-agent
  template:
    metadata:
      labels:
        app: backend-agent
    spec:
      containers:
      - name: backend-agent
        image: devswarm/backend-agent:latest
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        - name: POSTGRES_URL
          value: "postgresql://postgres-service:5432/devswarm"
        - name: AGENT_TYPE
          value: "backend"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

### 模式2: 微服务架构 Microservices Architecture

Agent作为独立微服务部署：

```
                    ┌────────────────┐
                    │   API Gateway  │
                    │   (Kong/Nginx) │
                    └────────┬───────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
         ┌────▼────┐    ┌────▼────┐   ┌────▼────┐
         │ PM Agent│    │ Backend │   │Frontend │
         │ Service │    │ Service │   │ Service │
         │ :8001   │    │ :8002   │   │ :8003   │
         └────┬────┘    └────┬────┘   └────┬────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────┴────────┐
                    │ RabbitMQ/Kafka  │
                    │  Message Queue  │
                    └─────────────────┘
```

**特点**:
- Agent暴露HTTP API
- 使用RabbitMQ/Kafka作为消息中间件
- API Gateway统一入口
- 独立扩展和部署

**Agent API示例**:

```python
# backend_agent_service.py
from flask import Flask, request, jsonify

app = Flask(__name__)
agent = BackendAgent(message_bus, state_store)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

@app.route('/execute', methods=['POST'])
def execute_task():
    task = request.json
    result = agent.execute_task(task)
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8002)
```

### 模式3: 混合架构 Hybrid Architecture

根据Agent特性选择部署方式：

```
┌─────────────────────────────────────────────────────────────┐
│                    Core Instance                            │
│  ┌──────────┐       ┌──────────┐                           │
│  │ PM Agent │       │ QA Agent │                           │
│  │ (单例)    │       │          │                           │
│  └────┬─────┘       └────┬─────┘                           │
└───────┼──────────────────┼──────────────────────────────────┘
        │                  │
        │     ┌────────────┴────────────┐
        │     │                         │
┌───────▼─────▼───┐            ┌────────▼────────┐
│  Backend Agent  │            │ Frontend Agent  │
│  Pool (3-5个)   │            │ Pool (2-3个)    │
│  ┌───┐ ┌───┐   │            │  ┌───┐ ┌───┐   │
│  │ B1│ │ B2│   │            │  │ F1│ │ F2│   │
│  └───┘ └───┘   │            │  └───┘ └───┘   │
└─────────────────┘            └─────────────────┘
```

**设计理由**:
- **PM Agent**: 编排器，需要单例避免冲突
- **QA Agent**: 测试协调，单例即可
- **Backend/Frontend**: 开发任务多，需要并发处理

---

## 技术选型 Technology Stack

### 消息队列对比 Message Queue Comparison

| 特性 | Redis Pub/Sub | RabbitMQ | Apache Kafka |
|------|---------------|----------|--------------|
| **部署复杂度** | ⭐ 简单 | ⭐⭐ 中等 | ⭐⭐⭐ 复杂 |
| **吞吐量** | 中等 (10k/s) | 高 (50k/s) | 极高 (1M/s) |
| **持久化** | ❌ 无 | ✅ 可选 | ✅ 强持久化 |
| **消息顺序** | ❌ 不保证 | ✅ 保证 | ✅ 分区有序 |
| **运维成本** | 低 | 中 | 高 |
| **DevSwarm推荐** | ✅ **推荐** | ✅ 备选 | ⚠️ 过度设计 |

**推荐**: **Redis Pub/Sub**
- 理由: DevSwarm消息量不大，Redis足够且运维简单

### 状态存储对比 State Store Comparison

| 特性 | JSON文件 | Redis | PostgreSQL |
|------|---------|-------|------------|
| **持久化** | ✅ 文件 | ⚠️ 需配置 | ✅ 强一致 |
| **并发读写** | ❌ 锁竞争 | ✅ 高并发 | ✅ 事务支持 |
| **查询能力** | ❌ 全扫描 | ⚠️ 简单查询 | ✅ SQL查询 |
| **数据一致性** | ❌ 弱 | ⚠️ 最终一致 | ✅ 强一致 |
| **DevSwarm推荐** | ❌ 仅开发 | ✅ **推荐** | ✅ 生产环境 |

**推荐**:
- **开发/测试**: Redis (快速迭代)
- **生产环境**: PostgreSQL (可靠性)

---

## 技术实施方案 Implementation Plan

### 第一阶段: 消息队列集成 Phase 1: Message Queue Integration

**目标**: 将内存消息总线替换为Redis

```python
# src/core/message_bus_redis.py
import redis
import json
from typing import Callable, Dict

class RedisMessageBus:
    """Redis-based distributed message bus"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)
        self.pubsub = self.redis.pubsub()
        self.handlers: Dict[str, Callable] = {}

    def publish(self, channel: str, message: dict):
        """发布消息到Redis频道"""
        self.redis.publish(channel, json.dumps(message))

    def subscribe(self, channel: str, handler: Callable):
        """订阅Redis频道"""
        self.handlers[channel] = handler
        self.pubsub.subscribe(channel)

    def start_listening(self):
        """启动消息监听循环"""
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                channel = message['channel'].decode()
                data = json.loads(message['data'])

                if channel in self.handlers:
                    self.handlers[channel](data)
```

**使用方式**:

```python
# 替换现有MessageBus
from src.core.message_bus_redis import RedisMessageBus

# 创建分布式消息总线
message_bus = RedisMessageBus(redis_url="redis://redis-server:6379")

# Agent订阅消息
pm_agent = PMAgent(message_bus, shared_state, llm_client)
message_bus.subscribe("task.backend", pm_agent.handle_backend_result)

# 启动监听
message_bus.start_listening()
```

### 第二阶段: 状态外部化 Phase 2: State Externalization

**目标**: 共享状态存储到Redis/PostgreSQL

```python
# src/core/state_store_redis.py
import redis
import json
from typing import Any, Optional

class RedisStateStore:
    """Redis-based distributed state store"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)

    def get(self, key: str) -> Optional[Any]:
        """获取状态"""
        value = self.redis.get(key)
        return json.loads(value) if value else None

    def set(self, key: str, value: Any):
        """设置状态"""
        self.redis.set(key, json.dumps(value))

    def delete(self, key: str):
        """删除状态"""
        self.redis.delete(key)

    def get_api_contract(self, project_id: str):
        """获取API契约"""
        key = f"project:{project_id}:api_contract"
        return self.get(key)

    def set_api_contract(self, project_id: str, contract: dict):
        """设置API契约"""
        key = f"project:{project_id}:api_contract"
        self.set(key, contract)
```

**PostgreSQL实现**:

```python
# src/core/state_store_postgres.py
import psycopg2
import json
from typing import Any, Optional

class PostgreSQLStateStore:
    """PostgreSQL-based state store"""

    def __init__(self, db_url: str):
        self.conn = psycopg2.connect(db_url)
        self._create_tables()

    def _create_tables(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS project_state (
                    project_id VARCHAR(100) PRIMARY KEY,
                    api_contract JSONB,
                    status VARCHAR(50),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id VARCHAR(100) PRIMARY KEY,
                    project_id VARCHAR(100),
                    task_type VARCHAR(50),
                    status VARCHAR(50),
                    result JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            self.conn.commit()

    def get_api_contract(self, project_id: str):
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT api_contract FROM project_state WHERE project_id = %s",
                (project_id,)
            )
            row = cur.fetchone()
            return row[0] if row else None

    def set_api_contract(self, project_id: str, contract: dict):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO project_state (project_id, api_contract)
                VALUES (%s, %s)
                ON CONFLICT (project_id)
                DO UPDATE SET api_contract = %s, updated_at = NOW()
            """, (project_id, json.dumps(contract), json.dumps(contract)))
            self.conn.commit()
```

### 第三阶段: Agent容器化 Phase 3: Agent Containerization

**Docker Compose配置**:

```yaml
# docker-compose.distributed.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: devswarm
      POSTGRES_USER: devswarm
      POSTGRES_PASSWORD: devswarm123
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data

  pm-agent:
    build:
      context: .
      dockerfile: docker/Dockerfile.agent
    environment:
      AGENT_TYPE: pm
      REDIS_URL: redis://redis:6379
      POSTGRES_URL: postgresql://devswarm:devswarm123@postgres:5432/devswarm
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    depends_on:
      - redis
      - postgres

  backend-agent:
    build:
      context: .
      dockerfile: docker/Dockerfile.agent
    environment:
      AGENT_TYPE: backend
      REDIS_URL: redis://redis:6379
      POSTGRES_URL: postgresql://devswarm:devswarm123@postgres:5432/devswarm
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    depends_on:
      - redis
      - postgres
    deploy:
      replicas: 3  # 3个Backend Agent实例

  frontend-agent:
    build:
      context: .
      dockerfile: docker/Dockerfile.agent
    environment:
      AGENT_TYPE: frontend
      REDIS_URL: redis://redis:6379
      POSTGRES_URL: postgresql://devswarm:devswarm123@postgres:5432/devswarm
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    depends_on:
      - redis
      - postgres
    deploy:
      replicas: 2  # 2个Frontend Agent实例

  qa-agent:
    build:
      context: .
      dockerfile: docker/Dockerfile.agent
    environment:
      AGENT_TYPE: qa
      REDIS_URL: redis://redis:6379
      POSTGRES_URL: postgresql://devswarm:devswarm123@postgres:5432/devswarm
    depends_on:
      - redis
      - postgres

  web-ui:
    build:
      context: .
      dockerfile: docker/Dockerfile.web
    ports:
      - "3000:3000"
    environment:
      REDIS_URL: redis://redis:6379
      POSTGRES_URL: postgresql://devswarm:devswarm123@postgres:5432/devswarm
    depends_on:
      - redis
      - postgres
      - pm-agent

volumes:
  redis-data:
  postgres-data:
```

**Agent Dockerfile**:

```dockerfile
# docker/Dockerfile.agent
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY config/ ./config/

# Agent启动脚本
COPY docker/start-agent.sh .
RUN chmod +x start-agent.sh

CMD ["./start-agent.sh"]
```

**启动脚本**:

```bash
#!/bin/bash
# docker/start-agent.sh

echo "Starting ${AGENT_TYPE} agent..."

case $AGENT_TYPE in
  "pm")
    python -m src.agents.pm_agent_service
    ;;
  "backend")
    python -m src.agents.backend_agent_service
    ;;
  "frontend")
    python -m src.agents.frontend_agent_service
    ;;
  "qa")
    python -m src.agents.qa_agent_service
    ;;
  *)
    echo "Unknown agent type: $AGENT_TYPE"
    exit 1
    ;;
esac
```

### 第四阶段: Kubernetes部署 Phase 4: Kubernetes Deployment

**命名空间配置**:

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: devswarm
```

**ConfigMap**:

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: devswarm-config
  namespace: devswarm
data:
  REDIS_URL: "redis://redis-service:6379"
  POSTGRES_URL: "postgresql://postgres-service:5432/devswarm"
  LOG_LEVEL: "INFO"
```

**Secret**:

```yaml
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: devswarm-secrets
  namespace: devswarm
type: Opaque
stringData:
  OPENAI_API_KEY: "sk-your-key-here"
  POSTGRES_PASSWORD: "devswarm123"
```

**Backend Agent Deployment**:

```yaml
# k8s/backend-agent-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-agent
  namespace: devswarm
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend-agent
  template:
    metadata:
      labels:
        app: backend-agent
    spec:
      containers:
      - name: backend-agent
        image: devswarm/backend-agent:v1.0.0
        envFrom:
        - configMapRef:
            name: devswarm-config
        - secretRef:
            name: devswarm-secrets
        env:
        - name: AGENT_TYPE
          value: "backend"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
```

**HorizontalPodAutoscaler**:

```yaml
# k8s/backend-agent-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-agent-hpa
  namespace: devswarm
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend-agent
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

**Service配置**:

```yaml
# k8s/services.yaml
apiVersion: v1
kind: Service
metadata:
  name: redis-service
  namespace: devswarm
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
  namespace: devswarm
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
---
apiVersion: v1
kind: Service
metadata:
  name: web-ui-service
  namespace: devswarm
spec:
  type: LoadBalancer
  selector:
    app: web-ui
  ports:
  - port: 80
    targetPort: 3000
```

---

## 监控与运维 Monitoring & Operations

### 健康检查 Health Checks

每个Agent需要实现健康检查端点：

```python
# Agent健康检查
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "agent_type": os.getenv("AGENT_TYPE"),
        "uptime": time.time() - start_time,
        "tasks_processed": metrics.tasks_count
    })

@app.route('/ready', methods=['GET'])
def readiness_check():
    # 检查依赖服务
    redis_ok = check_redis_connection()
    postgres_ok = check_postgres_connection()

    if redis_ok and postgres_ok:
        return jsonify({"status": "ready"}), 200
    else:
        return jsonify({"status": "not_ready"}), 503
```

### Prometheus监控

```yaml
# k8s/prometheus-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s

    scrape_configs:
    - job_name: 'devswarm-agents'
      kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
          - devswarm
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        regex: '.*-agent'
        action: keep
```

### Grafana仪表板

监控指标:
- Agent健康状态
- 任务处理速度
- 消息队列长度
- 资源使用率（CPU/内存）
- 错误率和延迟

### 日志聚合

使用ELK Stack或Loki:

```yaml
# k8s/fluentd-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/*.log
      tag kubernetes.*
      format json
    </source>

    <match kubernetes.**>
      @type elasticsearch
      host elasticsearch-service
      port 9200
      index_name devswarm
    </match>
```

---

## 实施路线图 Implementation Roadmap

### 阶段1: 准备 (1-2周)

- [ ] 研究Redis Pub/Sub和RabbitMQ
- [ ] 设计分布式消息协议
- [ ] 制定状态存储schema
- [ ] 编写POC代码

### 阶段2: 核心改造 (2-3周)

- [ ] 实现RedisMessageBus
- [ ] 实现RedisStateStore
- [ ] 实现PostgreSQLStateStore
- [ ] 修改Agent支持分布式模式
- [ ] 编写单元测试

### 阶段3: 容器化 (1-2周)

- [ ] 编写Dockerfile
- [ ] 创建docker-compose配置
- [ ] 测试容器化部署
- [ ] 编写部署文档

### 阶段4: K8s部署 (2-3周)

- [ ] 编写K8s配置文件
- [ ] 实现健康检查
- [ ] 配置自动扩缩容
- [ ] 集成监控告警

### 阶段5: 测试和优化 (2周)

- [ ] 负载测试
- [ ] 故障注入测试
- [ ] 性能优化
- [ ] 编写运维手册

**总计时间**: 8-12周

---

## 性能对比 Performance Comparison

| 指标 | 单机模式 | 分布式模式 |
|------|---------|-----------|
| **并发任务** | 1-2个 | 10+个 |
| **故障恢复** | 手动重启 | 自动恢复 |
| **扩展性** | 垂直扩展 | 水平扩展 |
| **资源利用** | CPU竞争 | 资源隔离 |
| **消息延迟** | <1ms | 5-10ms |
| **运维复杂度** | ⭐ | ⭐⭐⭐ |

---

## 总结 Summary

分布式架构为DevSwarm带来：

✅ **优势**:
- 高可用和容错
- 水平扩展能力
- 资源隔离
- 负载均衡

⚠️ **挑战**:
- 运维复杂度增加
- 网络延迟
- 分布式调试困难
- 成本增加

**建议**:
- 小型项目: 使用单机模式
- 中型项目: Docker Compose分布式
- 大型项目/生产: Kubernetes集群

---

## 参考资源 References

- [Redis Pub/Sub Documentation](https://redis.io/docs/manual/pubsub/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [Microservices Patterns](https://microservices.io/patterns/)
- [The Twelve-Factor App](https://12factor.net/)
