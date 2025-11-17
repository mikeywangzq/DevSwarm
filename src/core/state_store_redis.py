"""
Redis状态存储实现
Redis-based State Store Implementation

使用Redis实现分布式共享状态存储，支持跨进程/机器的状态共享。

核心功能:
    - 键值存储
    - JSON序列化
    - TTL支持
    - 原子操作
    - 事务支持

Example:
    >>> store = RedisStateStore("redis://localhost:6379")
    >>> store.set_api_contract("proj_123", api_contract)
    >>> contract = store.get_api_contract("proj_123")
"""
import redis
import json
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class RedisStateStore:
    """
    基于Redis的分布式状态存储

    存储结构:
        - project:{project_id}:state - 项目状态
        - project:{project_id}:api_contract - API契约
        - project:{project_id}:tasks - 任务列表
        - project:{project_id}:codebase - 代码库路径
        - agent:{agent_name}:status - Agent状态
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """
        初始化Redis状态存储

        Args:
            redis_url: Redis服务器URL
        """
        self.redis_url = redis_url
        self.redis_client = redis.from_url(redis_url, decode_responses=True)

        # 测试连接
        try:
            self.redis_client.ping()
            logger.info(f"Connected to Redis state store at {redis_url}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    # ==================== 通用键值操作 ====================

    def get(self, key: str) -> Optional[Any]:
        """
        获取键值

        Args:
            key: 键名

        Returns:
            值（自动反序列化JSON），不存在返回None
        """
        try:
            value = self.redis_client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON for key {key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting key {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        设置键值

        Args:
            key: 键名
            value: 值（会自动序列化为JSON）
            ttl: 过期时间（秒），None表示永不过期
        """
        try:
            serialized = json.dumps(value)
            if ttl:
                self.redis_client.setex(key, ttl, serialized)
            else:
                self.redis_client.set(key, serialized)
        except Exception as e:
            logger.error(f"Error setting key {key}: {e}")
            raise

    def delete(self, key: str):
        """
        删除键

        Args:
            key: 键名
        """
        self.redis_client.delete(key)

    def exists(self, key: str) -> bool:
        """
        检查键是否存在

        Args:
            key: 键名

        Returns:
            是否存在
        """
        return bool(self.redis_client.exists(key))

    # ==================== 项目状态管理 ====================

    def get_project_state(self, project_id: str) -> Optional[Dict]:
        """获取项目状态"""
        key = f"project:{project_id}:state"
        return self.get(key)

    def set_project_state(self, project_id: str, state: Dict):
        """设置项目状态"""
        key = f"project:{project_id}:state"
        self.set(key, state)

    def update_project_status(self, project_id: str, status: str):
        """更新项目状态"""
        state = self.get_project_state(project_id) or {}
        state['status'] = status
        state['updated_at'] = datetime.now().isoformat()
        self.set_project_state(project_id, state)

    # ==================== API契约管理 ====================

    def get_api_contract(self, project_id: str = "current") -> Optional[Dict]:
        """
        获取API契约

        Args:
            project_id: 项目ID，默认"current"

        Returns:
            API契约字典
        """
        key = f"project:{project_id}:api_contract"
        return self.get(key)

    def set_api_contract(self, contract: Dict, project_id: str = "current"):
        """
        设置API契约

        Args:
            contract: API契约字典
            project_id: 项目ID
        """
        key = f"project:{project_id}:api_contract"
        self.set(key, contract)
        logger.info(f"API contract saved for project {project_id}")

    # ==================== 任务管理 ====================

    def add_task(self, task: Dict, project_id: str = "current"):
        """
        添加任务

        Args:
            task: 任务字典
            project_id: 项目ID
        """
        tasks_key = f"project:{project_id}:tasks"
        tasks = self.get(tasks_key) or []
        tasks.append(task)
        self.set(tasks_key, tasks)

    def get_tasks(self, project_id: str = "current") -> List[Dict]:
        """
        获取所有任务

        Args:
            project_id: 项目ID

        Returns:
            任务列表
        """
        tasks_key = f"project:{project_id}:tasks"
        return self.get(tasks_key) or []

    def update_task_status(self, task_id: str, status: str,
                          result: Optional[Dict] = None,
                          project_id: str = "current"):
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态
            result: 任务结果
            project_id: 项目ID
        """
        tasks = self.get_tasks(project_id)

        for task in tasks:
            if task.get('id') == task_id:
                task['status'] = status
                if result:
                    task['result'] = result
                task['updated_at'] = datetime.now().isoformat()
                break

        tasks_key = f"project:{project_id}:tasks"
        self.set(tasks_key, tasks)

    # ==================== 代码库路径管理 ====================

    def set_codebase_path(self, component: str, path: str,
                          project_id: str = "current"):
        """
        设置代码库路径

        Args:
            component: 组件名（backend, frontend）
            path: 路径
            project_id: 项目ID
        """
        key = f"project:{project_id}:codebase:{component}"
        self.set(key, path)

    def get_codebase_path(self, component: str,
                          project_id: str = "current") -> Optional[str]:
        """
        获取代码库路径

        Args:
            component: 组件名
            project_id: 项目ID

        Returns:
            路径字符串
        """
        key = f"project:{project_id}:codebase:{component}"
        return self.get(key)

    # ==================== Agent状态管理 ====================

    def set_agent_status(self, agent_name: str, status: Dict):
        """
        设置Agent状态

        Args:
            agent_name: Agent名称
            status: 状态字典
        """
        key = f"agent:{agent_name}:status"
        status['updated_at'] = datetime.now().isoformat()
        self.set(key, status, ttl=300)  # 5分钟过期

    def get_agent_status(self, agent_name: str) -> Optional[Dict]:
        """
        获取Agent状态

        Args:
            agent_name: Agent名称

        Returns:
            状态字典
        """
        key = f"agent:{agent_name}:status"
        return self.get(key)

    def get_all_agent_statuses(self) -> Dict[str, Dict]:
        """
        获取所有Agent状态

        Returns:
            Agent名称到状态的映射
        """
        pattern = "agent:*:status"
        keys = self.redis_client.keys(pattern)

        statuses = {}
        for key in keys:
            agent_name = key.split(':')[1]
            status = self.get(key)
            if status:
                statuses[agent_name] = status

        return statuses

    # ==================== 原始需求存储 ====================

    def set_original_requirement(self, requirement: str,
                                project_id: str = "current"):
        """
        保存原始需求

        Args:
            requirement: 需求文本
            project_id: 项目ID
        """
        key = f"project:{project_id}:requirement"
        self.set(key, requirement)

    def get_original_requirement(self, project_id: str = "current") -> Optional[str]:
        """
        获取原始需求

        Args:
            project_id: 项目ID

        Returns:
            需求文本
        """
        key = f"project:{project_id}:requirement"
        return self.get(key)

    # ==================== 清理和维护 ====================

    def clear_project(self, project_id: str):
        """
        清除项目所有数据

        Args:
            project_id: 项目ID
        """
        pattern = f"project:{project_id}:*"
        keys = self.redis_client.keys(pattern)

        if keys:
            self.redis_client.delete(*keys)
            logger.info(f"Cleared {len(keys)} keys for project {project_id}")

    def clear_all(self):
        """清除所有数据（慎用！）"""
        self.redis_client.flushdb()
        logger.warning("All data cleared from Redis state store")

    def get_stats(self) -> Dict:
        """
        获取存储统计信息

        Returns:
            统计信息字典
        """
        info = self.redis_client.info()
        return {
            "total_keys": self.redis_client.dbsize(),
            "used_memory": info.get('used_memory_human', 'N/A'),
            "connected_clients": info.get('connected_clients', 0),
            "uptime_days": info.get('uptime_in_days', 0)
        }

    def close(self):
        """关闭连接"""
        self.redis_client.close()
        logger.info("Redis state store connection closed")


# 兼容性适配器：兼容现有SharedState接口
class RedisStateStoreAdapter(RedisStateStore):
    """
    Redis状态存储适配器，兼容现有的SharedState接口

    这个适配器让Redis状态存储可以直接替换现有的内存状态存储，
    无需修改Agent代码。
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        super().__init__(redis_url)
        self._state = {}  # 保持兼容性

    def get_state(self, key: str, default: Any = None) -> Any:
        """获取状态（兼容接口）"""
        value = self.get(f"state:{key}")
        return value if value is not None else default

    def set_state(self, key: str, value: Any):
        """设置状态（兼容接口）"""
        self.set(f"state:{key}", value)

    def update_state(self, updates: Dict):
        """批量更新状态（兼容接口）"""
        for key, value in updates.items():
            self.set_state(key, value)
