"""
共享状态管理模块
Shared State Management Module

本模块实现了DevSwarm系统的中心化状态存储和管理。共享状态是所有Agent可以访问
的中央知识库，存储项目的完整状态信息，包括需求、任务、代码路径、测试结果等。

设计原则:
    1. 单一数据源: 所有Agent从共享状态读取和更新项目信息
    2. 持久化存储: 状态自动保存到JSON文件，支持系统重启恢复
    3. 结构化数据: 使用明确的数据结构，便于Agent理解和使用
    4. 原子操作: 每次更新都会立即保存，避免数据丢失
    5. 查询灵活: 提供多种查询方法，支持按状态、Agent等维度筛选

主要组件:
    - SharedState: 共享状态管理类

状态结构:
    - project_id: 项目唯一标识符
    - original_requirement: 用户原始需求
    - api_contract: API契约定义
    - tasks: 任务字典（task_id -> Task）
    - codebase_paths: 代码库路径（backend/frontend/tests）
    - test_results: 测试结果列表
    - project_status: 项目状态（initializing/planning/developing/testing/completed/failed）
    - metadata: 其他元数据

使用场景:
    - PM Agent: 创建项目、分配任务、设置API契约
    - Worker Agent: 查询任务、更新任务状态、获取API契约
    - QA Agent: 提交测试结果
    - Web UI: 展示项目进度和状态

Example:
    >>> # 创建共享状态
    >>> state = SharedState(workspace_root="./workspace")
    >>>
    >>> # 初始化项目
    >>> state.initialize_project("proj_001", "创建一个待办事项应用")
    >>>
    >>> # 添加任务
    >>> task = Task(task_id="T1", title="实现后端API", ...)
    >>> state.add_task(task)
    >>>
    >>> # 更新任务状态
    >>> state.update_task_status("T1", TaskStatus.COMPLETED)
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
    共享状态类

    中心化的项目状态存储和管理系统，为DevSwarm多Agent系统提供统一的数据访问层。
    所有Agent通过共享状态进行协作和信息共享。

    核心功能:
        1. **项目管理**: 创建项目、初始化工作目录、设置项目状态
        2. **任务管理**: 添加任务、更新任务状态、查询任务
        3. **API契约**: 存储和检索前后端接口规范
        4. **代码路径**: 管理生成代码的目录结构
        5. **测试结果**: 收集和查询测试执行结果
        6. **持久化**: 自动保存状态到JSON文件

    状态生命周期:
        1. initialize_project() - 创建新项目
        2. set_api_contract() - PM Agent设置API契约
        3. add_task() - PM Agent添加任务
        4. update_task_status() - Worker Agent更新任务进度
        5. add_test_result() - QA Agent提交测试结果
        6. set_project_status() - 更新项目总体状态

    Attributes:
        workspace_root (Path): 工作空间根目录
        state_file (Path): 状态文件路径（project_state.json）
        _state (Dict[str, Any]): 内存中的状态数据

    Example:
        >>> # 初始化共享状态
        >>> state = SharedState()
        >>>
        >>> # 创建项目
        >>> state.initialize_project("proj_001", "待办事项应用")
        >>>
        >>> # 设置API契约
        >>> contract = APIContract()
        >>> contract.add_endpoint("GET", "/api/items", "获取所有项目")
        >>> state.set_api_contract(contract)
        >>>
        >>> # 添加和更新任务
        >>> task = Task(task_id="T1_Backend", ...)
        >>> state.add_task(task)
        >>> state.update_task_status("T1_Backend", TaskStatus.COMPLETED)
        >>>
        >>> # 查询任务
        >>> pending_tasks = state.get_tasks_by_status(TaskStatus.PENDING)
    """

    def __init__(self, workspace_root: str = "./workspace"):
        """
        初始化共享状态

        创建工作空间目录，初始化状态数据结构，并尝试从文件加载已有状态。

        Args:
            workspace_root (str): 工作空间根目录路径，默认为"./workspace"
                - 如果目录不存在，会自动创建
                - 所有生成的项目都会存放在此目录下

        状态结构说明:
            - project_id: 项目唯一标识符（如"proj_20240101_123456"）
            - original_requirement: 用户的原始需求描述
            - api_contract: API契约字典（序列化的APIContract对象）
            - tasks: 任务字典，键为task_id，值为Task对象的字典表示
            - codebase_paths: 代码库路径字典
                - backend: 后端代码目录
                - frontend: 前端代码目录
                - tests: 测试代码目录
            - test_results: 测试结果列表
            - project_status: 项目状态
                - initializing: 初始化中
                - planning: 规划中
                - developing: 开发中
                - testing: 测试中
                - completed: 已完成
                - failed: 失败
            - created_at: 项目创建时间（ISO 8601格式）
            - updated_at: 最后更新时间（ISO 8601格式）
            - metadata: 自定义元数据字典
        """
        # 工作空间根目录
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)

        # 状态文件路径，用于持久化存储
        self.state_file = self.workspace_root / "project_state.json"

        # 内存中的状态数据结构
        self._state: Dict[str, Any] = {
            "project_id": None,                      # 项目ID
            "original_requirement": None,            # 原始需求
            "api_contract": None,                    # API契约
            "tasks": {},                             # 任务字典: task_id -> Task
            "codebase_paths": {                      # 代码库路径
                "backend": None,
                "frontend": None,
                "tests": None
            },
            "test_results": [],                      # 测试结果列表
            "project_status": "initializing",        # 项目状态
            "created_at": None,                      # 创建时间
            "updated_at": None,                      # 更新时间
            "metadata": {}                           # 额外元数据
        }

        # 从文件加载现有状态（如果存在）
        self._load_state()

    def _load_state(self):
        """
        从文件加载状态

        在初始化时尝试从JSON文件恢复之前保存的状态。
        如果文件不存在（首次运行），使用默认状态。

        错误处理:
            - 如果文件损坏或格式错误，记录错误但不中断初始化
            - 确保系统可以在任何情况下启动

        Note:
            此方法是私有的，只在__init__()中调用
        """
        if self.state_file.exists():
            try:
                # 从JSON文件读取状态
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    self._state = json.load(f)
                logger.info(f"State loaded from {self.state_file}")
            except Exception as e:
                # 文件可能损坏，记录错误但不中断启动
                logger.error(f"Error loading state: {e}")
        else:
            # 首次运行，没有保存的状态
            logger.info("No existing state found, starting fresh")

    def _save_state(self):
        """
        保存状态到文件

        将内存中的状态序列化为JSON并写入文件。
        每次状态更新都会自动调用此方法，确保数据持久化。

        持久化策略:
            - 同步写入：每次更新立即保存，避免数据丢失
            - UTF-8编码：支持中文和其他Unicode字符
            - 格式化输出：使用缩进，便于人工查看和调试
            - 自动更新时间戳：记录最后更新时间

        Note:
            此方法是私有的，由各种状态更新方法自动调用
        """
        try:
            # 更新时间戳
            self._state["updated_at"] = datetime.utcnow().isoformat() + "Z"

            # 序列化并写入文件
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self._state, f, indent=2, ensure_ascii=False)

            logger.debug(f"State saved to {self.state_file}")
        except Exception as e:
            # 保存失败可能是权限问题或磁盘空间不足
            logger.error(f"Error saving state: {e}")

    def initialize_project(self, project_id: str, requirement: str):
        """
        初始化新项目

        创建新项目的完整目录结构和初始状态。
        这是项目生命周期的第一步，通常由PM Agent在接收到用户需求后调用。

        执行步骤:
            1. 设置项目ID和原始需求
            2. 记录创建时间
            3. 设置项目状态为"planning"
            4. 创建项目工作目录结构：
               - {project_id}/backend/  - 后端代码目录
               - {project_id}/frontend/ - 前端代码目录
               - {project_id}/tests/    - 测试代码目录
            5. 保存状态到文件

        Args:
            project_id (str): 项目的唯一标识符，通常格式为"proj_YYYYMMdd_HHmmss"
            requirement (str): 用户的原始需求描述

        Example:
            >>> state.initialize_project(
            ...     project_id="proj_20240101_120000",
            ...     requirement="创建一个待办事项管理应用，支持增删改查"
            ... )
        """
        # 设置项目基本信息
        self._state["project_id"] = project_id
        self._state["original_requirement"] = requirement
        self._state["created_at"] = datetime.utcnow().isoformat() + "Z"
        self._state["project_status"] = "planning"

        # 创建项目根目录
        project_dir = self.workspace_root / project_id
        project_dir.mkdir(parents=True, exist_ok=True)

        # 创建子目录：backend, frontend, tests
        for subdir in ["backend", "frontend", "tests"]:
            (project_dir / subdir).mkdir(parents=True, exist_ok=True)

        # 记录代码库路径
        self._state["codebase_paths"]["backend"] = str(project_dir / "backend")
        self._state["codebase_paths"]["frontend"] = str(project_dir / "frontend")
        self._state["codebase_paths"]["tests"] = str(project_dir / "tests")

        # 持久化状态
        self._save_state()
        logger.info(f"Project {project_id} initialized")

    def set_api_contract(self, contract: APIContract):
        """
        设置API契约

        PM Agent在分析用户需求后生成API契约，通过此方法保存到共享状态。
        契约会同时保存到内存状态和独立的JSON文件中。

        API契约作用:
            - Backend Agent根据契约生成后端API实现
            - Frontend Agent根据契约生成前端API调用代码
            - 确保前后端接口定义完全一致

        Args:
            contract (APIContract): API契约对象，包含所有端点定义

        文件输出:
            - 状态文件: workspace_root/project_state.json（更新api_contract字段）
            - 契约文件: workspace_root/{project_id}/api_contract.json（独立文件）

        Example:
            >>> contract = APIContract()
            >>> contract.add_endpoint("GET", "/api/items", "获取所有项目")
            >>> contract.add_endpoint("POST", "/api/items", "创建新项目")
            >>> state.set_api_contract(contract)
        """
        # 序列化契约对象并保存到状态
        self._state["api_contract"] = contract.to_dict()

        # 同时保存为独立的JSON文件，便于Agent直接读取
        if self._state["project_id"]:
            contract_file = (
                self.workspace_root /
                self._state["project_id"] /
                "api_contract.json"
            )
            with open(contract_file, 'w', encoding='utf-8') as f:
                f.write(contract.to_json())
            logger.info(f"API contract saved to {contract_file}")

        # 持久化状态
        self._save_state()

    def get_api_contract(self) -> Optional[APIContract]:
        """
        获取API契约

        Worker Agent通过此方法获取API契约定义，以便生成相应的代码。

        Returns:
            Optional[APIContract]: API契约对象，如果未设置则返回None

        Example:
            >>> contract = state.get_api_contract()
            >>> if contract:
            ...     for endpoint in contract.endpoints:
            ...         print(f"{endpoint['method']} {endpoint['path']}")
        """
        if self._state["api_contract"]:
            return APIContract.from_dict(self._state["api_contract"])
        return None

    def add_task(self, task: Task):
        """
        添加任务到状态

        PM Agent在任务分解阶段创建任务，并通过此方法添加到共享状态。
        每个任务都有唯一ID和分配的执行者。

        Args:
            task (Task): 任务对象，包含以下信息:
                - task_id: 唯一标识符
                - title: 任务标题
                - description: 详细描述
                - assigned_to: 负责的Agent名称
                - dependencies: 依赖的任务或文件
                - status: 任务状态（默认PENDING）

        Example:
            >>> task = Task(
            ...     task_id="T1_Backend",
            ...     title="实现后端API",
            ...     description="根据API契约生成Flask代码",
            ...     assigned_to="Backend_Agent",
            ...     dependencies=["api_contract.json"]
            ... )
            >>> state.add_task(task)
        """
        # 序列化任务并保存到任务字典
        self._state["tasks"][task.task_id] = task.to_dict()
        self._save_state()
        logger.info(f"Task {task.task_id} added: {task.title}")

    def update_task_status(self, task_id: str, status: TaskStatus,
                          metadata: Optional[Dict] = None):
        """
        更新任务状态

        Worker Agent在执行任务时通过此方法更新任务状态。
        状态变化记录了任务的进展情况。

        状态转换流程:
            PENDING → IN_PROGRESS → COMPLETED
                                 → FAILED

        Args:
            task_id (str): 任务的唯一标识符
            status (TaskStatus): 新的任务状态
            metadata (Optional[Dict]): 额外的元数据，如错误信息、结果路径等

        Example:
            >>> # Agent开始执行任务
            >>> state.update_task_status("T1_Backend", TaskStatus.IN_PROGRESS)
            >>>
            >>> # 任务完成
            >>> state.update_task_status(
            ...     "T1_Backend",
            ...     TaskStatus.COMPLETED,
            ...     metadata={"output_file": "backend/app.py"}
            ... )
            >>>
            >>> # 任务失败
            >>> state.update_task_status(
            ...     "T1_Backend",
            ...     TaskStatus.FAILED,
            ...     metadata={"error": "API generation failed"}
            ... )
        """
        if task_id in self._state["tasks"]:
            # 更新状态
            self._state["tasks"][task_id]["status"] = status.value

            # 合并元数据
            if metadata:
                self._state["tasks"][task_id]["metadata"].update(metadata)

            self._save_state()
            logger.info(f"Task {task_id} status updated to {status.value}")
        else:
            # 任务不存在，可能是配置错误
            logger.warning(f"Task {task_id} not found")

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        获取单个任务

        Args:
            task_id (str): 任务ID

        Returns:
            Optional[Task]: 任务对象，如果不存在则返回None

        Example:
            >>> task = state.get_task("T1_Backend")
            >>> if task:
            ...     print(f"Status: {task.status.value}")
        """
        if task_id in self._state["tasks"]:
            return Task.from_dict(self._state["tasks"][task_id])
        return None

    def get_all_tasks(self) -> List[Task]:
        """
        获取所有任务

        Returns:
            List[Task]: 所有任务的列表

        Example:
            >>> tasks = state.get_all_tasks()
            >>> print(f"Total tasks: {len(tasks)}")
        """
        return [
            Task.from_dict(task_data)
            for task_data in self._state["tasks"].values()
        ]

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """
        根据状态筛选任务

        用于查询特定状态的任务，如查找所有待处理或失败的任务。

        Args:
            status (TaskStatus): 要筛选的任务状态

        Returns:
            List[Task]: 指定状态的任务列表

        Example:
            >>> # 获取所有待处理任务
            >>> pending = state.get_tasks_by_status(TaskStatus.PENDING)
            >>>
            >>> # 获取所有失败任务
            >>> failed = state.get_tasks_by_status(TaskStatus.FAILED)
            >>> for task in failed:
            ...     print(f"Failed: {task.title}")
        """
        return [
            Task.from_dict(task_data)
            for task_data in self._state["tasks"].values()
            if task_data["status"] == status.value
        ]

    def get_tasks_by_agent(self, agent_name: str) -> List[Task]:
        """
        获取特定Agent的所有任务

        用于查询分配给特定Agent的任务，便于Agent找到自己的工作。

        Args:
            agent_name (str): Agent名称，如"Backend_Agent"

        Returns:
            List[Task]: 分配给该Agent的任务列表

        Example:
            >>> # Backend Agent查询自己的任务
            >>> my_tasks = state.get_tasks_by_agent("Backend_Agent")
            >>> for task in my_tasks:
            ...     print(f"My task: {task.title} - {task.status.value}")
        """
        return [
            Task.from_dict(task_data)
            for task_data in self._state["tasks"].values()
            if task_data["assigned_to"] == agent_name
        ]

    def add_test_result(self, result: Dict[str, Any]):
        """
        添加测试结果

        QA Agent在执行测试后通过此方法提交测试结果。
        每个测试结果都会自动添加时间戳。

        Args:
            result (Dict[str, Any]): 测试结果字典，通常包含:
                - test_name: 测试用例名称
                - status: 测试状态（passed/failed）
                - error_message: 错误消息（如果失败）
                - logs: 测试日志
                - 其他自定义字段

        Example:
            >>> # 提交成功的测试结果
            >>> state.add_test_result({
            ...     "test_name": "test_api_get_items",
            ...     "status": "passed",
            ...     "duration": 0.5
            ... })
            >>>
            >>> # 提交失败的测试结果
            >>> state.add_test_result({
            ...     "test_name": "test_api_create_item",
            ...     "status": "failed",
            ...     "error_message": "404 Not Found",
            ...     "logs": ["Request to /api/items failed"]
            ... })
        """
        # 添加时间戳并保存
        self._state["test_results"].append({
            **result,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        self._save_state()

    def get_test_results(self) -> List[Dict[str, Any]]:
        """
        获取所有测试结果

        Returns:
            List[Dict[str, Any]]: 测试结果列表，包含时间戳

        Example:
            >>> results = state.get_test_results()
            >>> failed = [r for r in results if r['status'] == 'failed']
            >>> print(f"Failed tests: {len(failed)}")
        """
        return self._state["test_results"]

    def set_project_status(self, status: str):
        """
        设置项目整体状态

        更新项目在生命周期中的当前阶段。

        Args:
            status (str): 项目状态，可选值:
                - "initializing": 初始化中
                - "planning": 规划中（PM Agent正在分析需求）
                - "developing": 开发中（Worker Agent正在生成代码）
                - "testing": 测试中（QA Agent正在测试）
                - "completed": 已完成（所有任务成功）
                - "failed": 失败（存在无法解决的错误）

        Example:
            >>> state.set_project_status("developing")
        """
        self._state["project_status"] = status
        self._save_state()
        logger.info(f"Project status updated to {status}")

    def get_project_status(self) -> str:
        """
        获取项目当前状态

        Returns:
            str: 项目状态字符串

        Example:
            >>> status = state.get_project_status()
            >>> if status == "completed":
            ...     print("Project is done!")
        """
        return self._state["project_status"]

    def get_codebase_path(self, component: str) -> Optional[str]:
        """
        获取代码库路径

        Agent通过此方法获取应该写入代码的目录路径。

        Args:
            component (str): 组件名称，可选值:
                - "backend": 后端代码目录
                - "frontend": 前端代码目录
                - "tests": 测试代码目录

        Returns:
            Optional[str]: 路径字符串，如果未设置则返回None

        Example:
            >>> backend_path = state.get_codebase_path("backend")
            >>> # backend_path: "./workspace/proj_001/backend"
            >>> # Backend Agent将代码写入此目录
        """
        return self._state["codebase_paths"].get(component)

    def set_metadata(self, key: str, value: Any):
        """
        设置自定义元数据

        用于存储项目特定的额外信息。

        Args:
            key (str): 元数据键
            value (Any): 元数据值（必须可JSON序列化）

        Example:
            >>> state.set_metadata("llm_model", "gpt-4")
            >>> state.set_metadata("retry_count", 3)
        """
        self._state["metadata"][key] = value
        self._save_state()

    def get_metadata(self, key: str) -> Optional[Any]:
        """
        获取自定义元数据

        Args:
            key (str): 元数据键

        Returns:
            Optional[Any]: 元数据值，如果不存在则返回None

        Example:
            >>> model = state.get_metadata("llm_model")
            >>> print(f"Using model: {model}")
        """
        return self._state["metadata"].get(key)

    def get_state_snapshot(self) -> Dict[str, Any]:
        """
        获取当前状态的完整快照

        返回状态的深拷贝，用于备份或分析，不会影响原状态。

        Returns:
            Dict[str, Any]: 状态快照字典

        Example:
            >>> snapshot = state.get_state_snapshot()
            >>> print(json.dumps(snapshot, indent=2))
        """
        return self._state.copy()

    def reset(self):
        """
        重置状态到初始值

        清除所有项目数据，恢复到刚创建时的状态。
        通常用于测试或开始新项目前的清理。

        Warning:
            此操作会清除所有数据，包括任务、测试结果等

        Example:
            >>> state.reset()
            >>> # 所有数据已清除，可以开始新项目
        """
        # 恢复默认状态结构
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
        """
        导出项目摘要

        生成项目的可读文本摘要，包含项目状态、任务进度、测试结果等关键信息。
        用于日志记录、报告生成或用户界面显示。

        Returns:
            str: 格式化的项目摘要文本

        摘要内容:
            - 项目ID和状态
            - 原始需求
            - 任务统计（总数、完成数、各状态数量）
            - 代码库路径
            - 测试执行情况

        Example:
            >>> summary = state.export_summary()
            >>> print(summary)
            === Project Summary ===
            Project ID: proj_001
            Status: completed
            ...
        """
        # 获取所有任务并统计
        tasks = self.get_all_tasks()
        completed = len([t for t in tasks if t.status == TaskStatus.COMPLETED])
        total = len(tasks)

        # 生成格式化摘要
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
