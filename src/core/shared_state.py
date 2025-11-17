"""
Shared State Management - 共享状态管理
所有Agent都可以访问的中央知识库
"""
import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging
from datetime import datetime
from .protocol import Task, TaskStatus, APIContract

logger = logging.getLogger(__name__)


class SharedState:
    """
    中心化的项目状态存储
    用于存储项目信息、API契约、任务列表、测试结果等
    """

    def __init__(self, workspace_root: str = "./workspace"):
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)

        # 状态文件路径
        self.state_file = self.workspace_root / "project_state.json"

        # 内存中的状态
        self._state: Dict[str, Any] = {
            "project_id": None,
            "original_requirement": None,
            "api_contract": None,
            "tasks": {},  # task_id -> Task
            "codebase_paths": {
                "backend": None,
                "frontend": None,
                "tests": None
            },
            "test_results": [],
            "project_status": "initializing",  # initializing, planning, developing, testing, completed, failed
            "created_at": None,
            "updated_at": None,
            "metadata": {}
        }

        # 加载现有状态（如果存在）
        self._load_state()

    def _load_state(self):
        """从文件加载状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    self._state = json.load(f)
                logger.info(f"State loaded from {self.state_file}")
            except Exception as e:
                logger.error(f"Error loading state: {e}")
        else:
            logger.info("No existing state found, starting fresh")

    def _save_state(self):
        """保存状态到文件"""
        try:
            self._state["updated_at"] = datetime.utcnow().isoformat() + "Z"
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self._state, f, indent=2, ensure_ascii=False)
            logger.debug(f"State saved to {self.state_file}")
        except Exception as e:
            logger.error(f"Error saving state: {e}")

    def initialize_project(self, project_id: str, requirement: str):
        """
        初始化新项目

        Args:
            project_id: 项目ID
            requirement: 用户需求
        """
        self._state["project_id"] = project_id
        self._state["original_requirement"] = requirement
        self._state["created_at"] = datetime.utcnow().isoformat() + "Z"
        self._state["project_status"] = "planning"

        # 创建项目工作目录
        project_dir = self.workspace_root / project_id
        project_dir.mkdir(parents=True, exist_ok=True)

        for subdir in ["backend", "frontend", "tests"]:
            (project_dir / subdir).mkdir(parents=True, exist_ok=True)

        self._state["codebase_paths"]["backend"] = str(project_dir / "backend")
        self._state["codebase_paths"]["frontend"] = str(project_dir / "frontend")
        self._state["codebase_paths"]["tests"] = str(project_dir / "tests")

        self._save_state()
        logger.info(f"Project {project_id} initialized")

    def set_api_contract(self, contract: APIContract):
        """
        设置API契约

        Args:
            contract: API契约对象
        """
        self._state["api_contract"] = contract.to_dict()

        # 同时保存到文件
        if self._state["project_id"]:
            contract_file = (
                self.workspace_root /
                self._state["project_id"] /
                "api_contract.json"
            )
            with open(contract_file, 'w', encoding='utf-8') as f:
                f.write(contract.to_json())
            logger.info(f"API contract saved to {contract_file}")

        self._save_state()

    def get_api_contract(self) -> Optional[APIContract]:
        """获取API契约"""
        if self._state["api_contract"]:
            return APIContract.from_dict(self._state["api_contract"])
        return None

    def add_task(self, task: Task):
        """
        添加任务

        Args:
            task: 任务对象
        """
        self._state["tasks"][task.task_id] = task.to_dict()
        self._save_state()
        logger.info(f"Task {task.task_id} added: {task.title}")

    def update_task_status(self, task_id: str, status: TaskStatus,
                          metadata: Optional[Dict] = None):
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态
            metadata: 额外的元数据
        """
        if task_id in self._state["tasks"]:
            self._state["tasks"][task_id]["status"] = status.value
            if metadata:
                self._state["tasks"][task_id]["metadata"].update(metadata)
            self._save_state()
            logger.info(f"Task {task_id} status updated to {status.value}")
        else:
            logger.warning(f"Task {task_id} not found")

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        if task_id in self._state["tasks"]:
            return Task.from_dict(self._state["tasks"][task_id])
        return None

    def get_all_tasks(self) -> List[Task]:
        """获取所有任务"""
        return [
            Task.from_dict(task_data)
            for task_data in self._state["tasks"].values()
        ]

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """根据状态获取任务"""
        return [
            Task.from_dict(task_data)
            for task_data in self._state["tasks"].values()
            if task_data["status"] == status.value
        ]

    def get_tasks_by_agent(self, agent_name: str) -> List[Task]:
        """获取特定Agent的任务"""
        return [
            Task.from_dict(task_data)
            for task_data in self._state["tasks"].values()
            if task_data["assigned_to"] == agent_name
        ]

    def add_test_result(self, result: Dict[str, Any]):
        """添加测试结果"""
        self._state["test_results"].append({
            **result,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        self._save_state()

    def get_test_results(self) -> List[Dict[str, Any]]:
        """获取测试结果"""
        return self._state["test_results"]

    def set_project_status(self, status: str):
        """设置项目状态"""
        self._state["project_status"] = status
        self._save_state()
        logger.info(f"Project status updated to {status}")

    def get_project_status(self) -> str:
        """获取项目状态"""
        return self._state["project_status"]

    def get_codebase_path(self, component: str) -> Optional[str]:
        """
        获取代码库路径

        Args:
            component: 组件名称 (backend/frontend/tests)

        Returns:
            路径字符串
        """
        return self._state["codebase_paths"].get(component)

    def set_metadata(self, key: str, value: Any):
        """设置元数据"""
        self._state["metadata"][key] = value
        self._save_state()

    def get_metadata(self, key: str) -> Optional[Any]:
        """获取元数据"""
        return self._state["metadata"].get(key)

    def get_state_snapshot(self) -> Dict[str, Any]:
        """获取当前状态快照"""
        return self._state.copy()

    def reset(self):
        """重置状态"""
        self._state = {
            "project_id": None,
            "original_requirement": None,
            "api_contract": None,
            "tasks": {},
            "codebase_paths": {
                "backend": None,
                "frontend": None,
                "tests": None
            },
            "test_results": [],
            "project_status": "initializing",
            "created_at": None,
            "updated_at": None,
            "metadata": {}
        }
        self._save_state()
        logger.info("State reset")

    def export_summary(self) -> str:
        """导出项目摘要"""
        tasks = self.get_all_tasks()
        completed = len([t for t in tasks if t.status == TaskStatus.COMPLETED])
        total = len(tasks)

        summary = f"""
=== Project Summary ===
Project ID: {self._state['project_id']}
Status: {self._state['project_status']}
Original Requirement: {self._state['original_requirement']}

Tasks: {completed}/{total} completed
- Pending: {len(self.get_tasks_by_status(TaskStatus.PENDING))}
- In Progress: {len(self.get_tasks_by_status(TaskStatus.IN_PROGRESS))}
- Completed: {completed}
- Failed: {len(self.get_tasks_by_status(TaskStatus.FAILED))}

Codebase Paths:
- Backend: {self._state['codebase_paths']['backend']}
- Frontend: {self._state['codebase_paths']['frontend']}
- Tests: {self._state['codebase_paths']['tests']}

Test Results: {len(self._state['test_results'])} tests run
        """
        return summary.strip()
