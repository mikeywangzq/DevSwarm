"""
PostgreSQL状态存储实现
PostgreSQL-based State Store Implementation

使用PostgreSQL实现持久化共享状态存储，提供ACID保证和强一致性。

核心功能:
    - 关系型数据存储
    - ACID事务支持
    - SQL查询能力
    - 数据持久化
    - 历史记录追踪

Example:
    >>> store = PostgreSQLStateStore("postgresql://user:pass@localhost/devswarm")
    >>> store.set_api_contract("proj_123", api_contract)
    >>> contract = store.get_api_contract("proj_123")
"""
import psycopg2
import psycopg2.extras
import json
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class PostgreSQLStateStore:
    """
    基于PostgreSQL的持久化状态存储

    数据表结构:
        - projects: 项目信息
        - api_contracts: API契约
        - tasks: 任务信息
        - agent_statuses: Agent状态
        - state_history: 状态变更历史
    """

    def __init__(self, db_url: str):
        """
        初始化PostgreSQL状态存储

        Args:
            db_url: 数据库连接URL
                    格式: postgresql://user:password@host:port/database
        """
        self.db_url = db_url

        try:
            self.conn = psycopg2.connect(db_url)
            logger.info(f"Connected to PostgreSQL database")
            self._create_tables()
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    @contextmanager
    def _cursor(self):
        """获取数据库游标（上下文管理器）"""
        # 检查连接状态并在需要时重连
        if self.conn.closed:
            logger.warning("Database connection was closed, reconnecting...")
            try:
                self.conn = psycopg2.connect(self.db_url)
                logger.info("Successfully reconnected to database")
            except psycopg2.Error as e:
                logger.error(f"Failed to reconnect to database: {e}")
                raise

        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            yield cursor
            self.conn.commit()
        except psycopg2.OperationalError as e:
            # 连接相关错误
            self.conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()

    def _create_tables(self):
        """创建数据表"""
        with self._cursor() as cur:
            # 项目表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    project_id VARCHAR(100) PRIMARY KEY,
                    status VARCHAR(50) DEFAULT 'pending',
                    requirement TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # API契约表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS api_contracts (
                    project_id VARCHAR(100) PRIMARY KEY,
                    contract JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    FOREIGN KEY (project_id) REFERENCES projects(project_id)
                        ON DELETE CASCADE
                )
            """)

            # 任务表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id VARCHAR(100) PRIMARY KEY,
                    project_id VARCHAR(100) NOT NULL,
                    task_type VARCHAR(50),
                    title VARCHAR(200),
                    status VARCHAR(50) DEFAULT 'pending',
                    assigned_to VARCHAR(100),
                    result JSONB,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    FOREIGN KEY (project_id) REFERENCES projects(project_id)
                        ON DELETE CASCADE
                )
            """)

            # 代码库路径表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS codebase_paths (
                    project_id VARCHAR(100),
                    component VARCHAR(50),
                    path TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    PRIMARY KEY (project_id, component),
                    FOREIGN KEY (project_id) REFERENCES projects(project_id)
                        ON DELETE CASCADE
                )
            """)

            # Agent状态表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS agent_statuses (
                    agent_name VARCHAR(100) PRIMARY KEY,
                    status JSONB,
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # 状态历史表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS state_history (
                    id SERIAL PRIMARY KEY,
                    project_id VARCHAR(100),
                    event_type VARCHAR(50),
                    event_data JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # 创建索引
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_project
                ON tasks(project_id)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status
                ON tasks(status)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_project
                ON state_history(project_id)
            """)

            logger.info("Database tables created/verified")

    # ==================== 项目管理 ====================

    def create_project(self, project_id: str, requirement: str):
        """
        创建新项目

        Args:
            project_id: 项目ID
            requirement: 需求描述
        """
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO projects (project_id, requirement, status)
                VALUES (%s, %s, 'pending')
                ON CONFLICT (project_id) DO UPDATE
                SET requirement = EXCLUDED.requirement,
                    updated_at = NOW()
            """, (project_id, requirement))

            # 记录历史
            self._add_history(cur, project_id, 'project_created', {
                'requirement': requirement
            })

    def get_project_state(self, project_id: str) -> Optional[Dict]:
        """获取项目状态"""
        with self._cursor() as cur:
            cur.execute("""
                SELECT * FROM projects WHERE project_id = %s
            """, (project_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def update_project_status(self, project_id: str, status: str):
        """更新项目状态"""
        with self._cursor() as cur:
            cur.execute("""
                UPDATE projects
                SET status = %s, updated_at = NOW()
                WHERE project_id = %s
            """, (status, project_id))

            self._add_history(cur, project_id, 'status_changed', {
                'new_status': status
            })

    # ==================== API契约管理 ====================

    def get_api_contract(self, project_id: str = "current") -> Optional[Dict]:
        """
        获取API契约

        Args:
            project_id: 项目ID

        Returns:
            API契约字典
        """
        with self._cursor() as cur:
            cur.execute("""
                SELECT contract FROM api_contracts
                WHERE project_id = %s
            """, (project_id,))
            row = cur.fetchone()
            return row['contract'] if row else None

    def set_api_contract(self, contract: Dict, project_id: str = "current"):
        """
        设置API契约

        Args:
            contract: API契约字典
            project_id: 项目ID
        """
        with self._cursor() as cur:
            # 确保项目存在
            cur.execute("""
                INSERT INTO projects (project_id)
                VALUES (%s)
                ON CONFLICT (project_id) DO NOTHING
            """, (project_id,))

            # 保存契约
            cur.execute("""
                INSERT INTO api_contracts (project_id, contract)
                VALUES (%s, %s)
                ON CONFLICT (project_id)
                DO UPDATE SET contract = EXCLUDED.contract,
                             updated_at = NOW()
            """, (project_id, json.dumps(contract)))

            self._add_history(cur, project_id, 'api_contract_saved', {
                'endpoints_count': len(contract.get('endpoints', []))
            })

            logger.info(f"API contract saved for project {project_id}")

    # ==================== 任务管理 ====================

    def add_task(self, task: Dict, project_id: str = "current"):
        """
        添加任务

        Args:
            task: 任务字典
            project_id: 项目ID
        """
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO tasks (
                    task_id, project_id, task_type, title,
                    status, assigned_to, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                task.get('id'),
                project_id,
                task.get('type'),
                task.get('title'),
                task.get('status', 'pending'),
                task.get('assigned_to'),
                json.dumps(task.get('metadata', {}))
            ))

    def get_tasks(self, project_id: str = "current") -> List[Dict]:
        """
        获取所有任务

        Args:
            project_id: 项目ID

        Returns:
            任务列表
        """
        with self._cursor() as cur:
            cur.execute("""
                SELECT * FROM tasks
                WHERE project_id = %s
                ORDER BY created_at
            """, (project_id,))
            rows = cur.fetchall()
            return [dict(row) for row in rows]

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
        with self._cursor() as cur:
            if result:
                cur.execute("""
                    UPDATE tasks
                    SET status = %s, result = %s, updated_at = NOW()
                    WHERE task_id = %s
                """, (status, json.dumps(result), task_id))
            else:
                cur.execute("""
                    UPDATE tasks
                    SET status = %s, updated_at = NOW()
                    WHERE task_id = %s
                """, (status, task_id))

            self._add_history(cur, project_id, 'task_updated', {
                'task_id': task_id,
                'status': status
            })

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
        with self._cursor() as cur:
            # 确保项目存在
            cur.execute("""
                INSERT INTO projects (project_id)
                VALUES (%s)
                ON CONFLICT (project_id) DO NOTHING
            """, (project_id,))

            cur.execute("""
                INSERT INTO codebase_paths (project_id, component, path)
                VALUES (%s, %s, %s)
                ON CONFLICT (project_id, component)
                DO UPDATE SET path = EXCLUDED.path
            """, (project_id, component, path))

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
        with self._cursor() as cur:
            cur.execute("""
                SELECT path FROM codebase_paths
                WHERE project_id = %s AND component = %s
            """, (project_id, component))
            row = cur.fetchone()
            return row['path'] if row else None

    # ==================== Agent状态管理 ====================

    def set_agent_status(self, agent_name: str, status: Dict):
        """
        设置Agent状态

        Args:
            agent_name: Agent名称
            status: 状态字典
        """
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO agent_statuses (agent_name, status)
                VALUES (%s, %s)
                ON CONFLICT (agent_name)
                DO UPDATE SET status = EXCLUDED.status,
                             updated_at = NOW()
            """, (agent_name, json.dumps(status)))

    def get_agent_status(self, agent_name: str) -> Optional[Dict]:
        """
        获取Agent状态

        Args:
            agent_name: Agent名称

        Returns:
            状态字典
        """
        with self._cursor() as cur:
            cur.execute("""
                SELECT status FROM agent_statuses
                WHERE agent_name = %s
            """, (agent_name,))
            row = cur.fetchone()
            return row['status'] if row else None

    def get_all_agent_statuses(self) -> Dict[str, Dict]:
        """
        获取所有Agent状态

        Returns:
            Agent名称到状态的映射
        """
        with self._cursor() as cur:
            cur.execute("SELECT agent_name, status FROM agent_statuses")
            rows = cur.fetchall()
            return {row['agent_name']: row['status'] for row in rows}

    # ==================== 原始需求存储 ====================

    def set_original_requirement(self, requirement: str,
                                project_id: str = "current"):
        """
        保存原始需求

        Args:
            requirement: 需求文本
            project_id: 项目ID
        """
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO projects (project_id, requirement)
                VALUES (%s, %s)
                ON CONFLICT (project_id)
                DO UPDATE SET requirement = EXCLUDED.requirement,
                             updated_at = NOW()
            """, (project_id, requirement))

    def get_original_requirement(self, project_id: str = "current") -> Optional[str]:
        """
        获取原始需求

        Args:
            project_id: 项目ID

        Returns:
            需求文本
        """
        with self._cursor() as cur:
            cur.execute("""
                SELECT requirement FROM projects
                WHERE project_id = %s
            """, (project_id,))
            row = cur.fetchone()
            return row['requirement'] if row else None

    # ==================== 历史记录 ====================

    def _add_history(self, cursor, project_id: str, event_type: str,
                     event_data: Dict):
        """
        添加历史记录（内部方法）

        Args:
            cursor: 数据库游标
            project_id: 项目ID
            event_type: 事件类型
            event_data: 事件数据
        """
        cursor.execute("""
            INSERT INTO state_history (project_id, event_type, event_data)
            VALUES (%s, %s, %s)
        """, (project_id, event_type, json.dumps(event_data)))

    def get_history(self, project_id: str, limit: int = 100) -> List[Dict]:
        """
        获取项目历史记录

        Args:
            project_id: 项目ID
            limit: 最大记录数

        Returns:
            历史记录列表
        """
        with self._cursor() as cur:
            cur.execute("""
                SELECT * FROM state_history
                WHERE project_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (project_id, limit))
            rows = cur.fetchall()
            return [dict(row) for row in rows]

    # ==================== 统计和维护 ====================

    def get_stats(self) -> Dict:
        """
        获取存储统计信息

        Returns:
            统计信息字典
        """
        with self._cursor() as cur:
            cur.execute("SELECT COUNT(*) as count FROM projects")
            projects_count = cur.fetchone()['count']

            cur.execute("SELECT COUNT(*) as count FROM tasks")
            tasks_count = cur.fetchone()['count']

            cur.execute("SELECT COUNT(*) as count FROM state_history")
            history_count = cur.fetchone()['count']

            return {
                "total_projects": projects_count,
                "total_tasks": tasks_count,
                "total_history_records": history_count,
                "database_url": self.db_url.split('@')[1] if '@' in self.db_url else 'N/A'
            }

    def clear_project(self, project_id: str):
        """
        清除项目所有数据

        Args:
            project_id: 项目ID
        """
        with self._cursor() as cur:
            # 由于外键约束设置了ON DELETE CASCADE，只需删除project即可
            cur.execute("DELETE FROM projects WHERE project_id = %s", (project_id,))
            logger.info(f"Cleared all data for project {project_id}")

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("PostgreSQL connection closed")
