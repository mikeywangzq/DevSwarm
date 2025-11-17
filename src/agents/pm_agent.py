"""
PM Agent - 项目经理Agent（编排器）
负责需求分解、任务分配、协调和监控
"""
import json
import uuid
from typing import Dict, Any, List, Optional
import logging
from .base_agent import BaseAgent
from ..core.protocol import (
    Task, TaskStatus, Message, MessageType,
    APIContract, BugReport
)

logger = logging.getLogger(__name__)


class PMAgent(BaseAgent):
    """
    项目经理Agent
    系统的"大脑"，负责整体协调
    """

    def __init__(self, message_bus, shared_state, llm_client):
        super().__init__(
            agent_name="PM_Agent",
            role="Project Manager / Orchestrator",
            message_bus=message_bus,
            shared_state=shared_state,
            llm_client=llm_client
        )

        # 项目状态跟踪
        self.current_project_id: Optional[str] = None
        self.pending_tasks: List[str] = []
        self.completed_tasks: List[str] = []
        self.failed_tasks: List[str] = []

    async def start_project(self, requirement: str) -> str:
        """
        启动新项目

        Args:
            requirement: 用户需求

        Returns:
            项目ID
        """
        # 生成项目ID
        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        self.current_project_id = project_id

        logger.info(f"Starting new project: {project_id}")
        logger.info(f"Requirement: {requirement}")

        # 初始化项目
        self.shared_state.initialize_project(project_id, requirement)
        self.shared_state.set_project_status("planning")

        # 1. 需求分析和任务分解
        await self._analyze_requirement(requirement)

        # 2. 定义API契约
        await self._define_api_contract(requirement)

        # 3. 创建任务列表
        await self._create_task_list(requirement)

        # 4. 分配任务
        await self._assign_tasks()

        self.shared_state.set_project_status("developing")

        return project_id

    async def _analyze_requirement(self, requirement: str):
        """
        分析需求

        Args:
            requirement: 用户需求
        """
        logger.info("Analyzing requirement...")

        prompt = f"""
Analyze this software requirement and identify the key components:

Requirement: {requirement}

Identify:
1. Type of application (web app, API, etc.)
2. Core features needed
3. Data entities
4. Required APIs/endpoints
5. Technology recommendations

Provide a brief analysis.
"""

        analysis = await self.llm_client.generate(
            prompt,
            system_prompt="You are a senior software architect.",
            temperature=0.5
        )

        logger.info(f"Requirement analysis:\n{analysis}")
        self.shared_state.set_metadata("requirement_analysis", analysis)

    async def _define_api_contract(self, requirement: str):
        """
        定义API契约

        Args:
            requirement: 用户需求
        """
        logger.info("Defining API contract...")

        prompt = f"""
Define a RESTful API contract for this requirement:

Requirement: {requirement}

Return ONLY a valid JSON object with this exact structure (no markdown, no code blocks):
{{
  "base_url": "http://localhost:5000",
  "version": "1.0",
  "endpoints": [
    {{
      "method": "GET|POST|PUT|DELETE",
      "path": "/api/...",
      "description": "...",
      "request_body": {{}},
      "response": {{}}
    }}
  ]
}}

Define practical, RESTful endpoints that cover the main CRUD operations.
"""

        response = await self.llm_client.generate(
            prompt,
            system_prompt="You are an API architect. Return only valid JSON.",
            temperature=0.3
        )

        # 解析API契约
        try:
            # 清理响应（移除可能的markdown标记）
            response = response.strip()
            if response.startswith("```"):
                # 移除代码块标记
                lines = response.split("\n")
                response = "\n".join(
                    line for line in lines
                    if not line.strip().startswith("```")
                )

            contract_data = json.loads(response)
            contract = APIContract.from_dict(contract_data)

            # 保存API契约
            self.shared_state.set_api_contract(contract)
            logger.info(f"API contract defined with {len(contract.endpoints)} endpoints")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse API contract JSON: {e}")
            logger.error(f"Response was: {response}")

            # 使用fallback
            contract = self._create_fallback_api_contract(requirement)
            self.shared_state.set_api_contract(contract)

    def _create_fallback_api_contract(self, requirement: str) -> APIContract:
        """创建降级API契约"""
        contract = APIContract()

        # 基于需求关键词推断
        if "todo" in requirement.lower() or "task" in requirement.lower():
            contract.add_endpoint("GET", "/api/items", "Get all items",
                                response={"items": []})
            contract.add_endpoint("POST", "/api/items", "Create new item",
                                request_body={"title": "string"},
                                response={"id": "string", "title": "string"})
            contract.add_endpoint("DELETE", "/api/items/:id", "Delete an item",
                                response={"success": True})
        else:
            # 通用CRUD
            contract.add_endpoint("GET", "/api/data", "Get all data",
                                response={"data": []})
            contract.add_endpoint("POST", "/api/data", "Create data",
                                request_body={"content": "string"},
                                response={"id": "string"})

        logger.info("Using fallback API contract")
        return contract

    async def _create_task_list(self, requirement: str):
        """
        创建任务列表

        Args:
            requirement: 用户需求
        """
        logger.info("Creating task list...")

        api_contract = self.shared_state.get_api_contract()

        # 创建后端任务
        backend_task = Task(
            task_id="T1_Backend",
            title="Implement Backend API",
            description=f"Implement all API endpoints according to the API contract. "
                       f"Endpoints: {len(api_contract.endpoints) if api_contract else 0}",
            assigned_to="Backend_Agent",
            dependencies=["api_contract.json"],
            type="development"
        )
        self.shared_state.add_task(backend_task)
        self.pending_tasks.append(backend_task.task_id)

        # 创建前端任务
        frontend_task = Task(
            task_id="T2_Frontend",
            title="Implement Frontend UI",
            description="Create a user interface that consumes the backend API. "
                       "Must call APIs according to the API contract.",
            assigned_to="Frontend_Agent",
            dependencies=["api_contract.json"],
            type="development"
        )
        self.shared_state.add_task(frontend_task)
        self.pending_tasks.append(frontend_task.task_id)

        # 创建测试任务（依赖前端和后端）
        qa_task = Task(
            task_id="T3_QA",
            title="Integration Testing",
            description="Perform integration testing of frontend and backend. "
                       "Test all API endpoints and UI functionality.",
            assigned_to="QA_Agent",
            dependencies=["T1_Backend", "T2_Frontend", "api_contract.json"],
            type="testing"
        )
        self.shared_state.add_task(qa_task)
        self.pending_tasks.append(qa_task.task_id)

        logger.info(f"Created {len(self.pending_tasks)} tasks")

    async def _assign_tasks(self):
        """分配任务给Worker Agents"""
        logger.info("Assigning tasks...")

        # 分配可以立即执行的任务（没有依赖或依赖已满足）
        for task_id in self.pending_tasks[:]:
            task = self.shared_state.get_task(task_id)

            if self._can_execute_task(task):
                await self._assign_task_to_agent(task)

    def _can_execute_task(self, task: Task) -> bool:
        """
        检查任务是否可以执行

        Args:
            task: 任务

        Returns:
            是否可执行
        """
        # 检查依赖
        for dep in task.dependencies:
            # 如果依赖是文件，检查是否存在
            if dep.endswith(".json"):
                continue  # API契约已经创建

            # 如果依赖是其他任务，检查是否完成
            if dep.startswith("T"):
                dep_task = self.shared_state.get_task(dep)
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    return False

        return True

    async def _assign_task_to_agent(self, task: Task):
        """
        分配任务给特定Agent

        Args:
            task: 任务
        """
        logger.info(f"Assigning task {task.task_id} to {task.assigned_to}")

        message = Message(
            from_agent=self.agent_name,
            to_agent=task.assigned_to,
            type=MessageType.TASK_ASSIGNMENT,
            task=task
        )

        await self.message_bus.publish(message)

    async def handle_message(self, message: Message):
        """处理消息"""
        if message.type == MessageType.COMPLETION_REPORT:
            await self._handle_completion_report(message)
        elif message.type == MessageType.ERROR_REPORT:
            await self._handle_agent_error_report(message)
        elif message.type == MessageType.BUG_REPORT:
            await self._handle_bug_report(message)

    async def _handle_completion_report(self, message: Message):
        """处理任务完成报告"""
        task_id = message.payload.get("task_id")
        result = message.payload.get("result", {})

        logger.info(f"Task {task_id} completed by {message.from_agent}")
        logger.debug(f"Result: {result}")

        # 更新任务列表
        if task_id in self.pending_tasks:
            self.pending_tasks.remove(task_id)
        self.completed_tasks.append(task_id)

        # 检查是否有新的任务可以执行
        await self._check_and_assign_pending_tasks()

        # 检查项目是否完成
        await self._check_project_completion()

    async def _handle_agent_error_report(self, message: Message):
        """处理Agent错误报告"""
        task_id = message.payload.get("task_id")
        error = message.payload.get("error")

        logger.error(f"Task {task_id} failed: {error}")

        if task_id:
            if task_id in self.pending_tasks:
                self.pending_tasks.remove(task_id)
            self.failed_tasks.append(task_id)

    async def _handle_bug_report(self, message: Message):
        """
        处理Bug报告并生成修复任务

        Args:
            message: Bug报告消息
        """
        bug_data = message.payload.get("bug_report", {})
        failed_task_id = message.payload.get("task_id")

        logger.warning(f"Bug reported by {message.from_agent}")
        logger.warning(f"Bug: {bug_data}")

        # 创建Bug报告对象
        bug_report = BugReport.from_dict(bug_data) if bug_data else None

        if not bug_report:
            logger.error("Invalid bug report received")
            return

        # 使用LLM分析Bug并生成修复建议
        fix_suggestion = await self._analyze_bug_and_generate_fix(bug_report)

        # 创建修复任务
        fix_task = await self._create_fix_task(bug_report, fix_suggestion, failed_task_id)

        # 分配修复任务
        await self._assign_task_to_agent(fix_task)

    async def _analyze_bug_and_generate_fix(self, bug_report: BugReport) -> str:
        """
        分析Bug并生成修复建议

        Args:
            bug_report: Bug报告

        Returns:
            修复建议
        """
        logger.info("Analyzing bug and generating fix...")

        fix_suggestion = await self.llm_client.analyze_error(
            error_message=bug_report.error_message,
            code_context=bug_report.relevant_code_context,
            logs=bug_report.logs
        )

        logger.info(f"Fix suggestion generated:\n{fix_suggestion}")
        return fix_suggestion

    async def _create_fix_task(self, bug_report: BugReport,
                              fix_suggestion: str,
                              original_task_id: str) -> Task:
        """
        创建修复任务

        Args:
            bug_report: Bug报告
            fix_suggestion: 修复建议
            original_task_id: 原始任务ID

        Returns:
            修复任务
        """
        # 确定应该分配给哪个Agent
        original_task = self.shared_state.get_task(original_task_id)
        assigned_to = "Backend_Agent"  # 默认

        if original_task:
            # 根据原始任务判断
            if "frontend" in original_task.title.lower():
                assigned_to = "Frontend_Agent"
            elif "backend" in original_task.title.lower():
                assigned_to = "Backend_Agent"

        fix_task = Task(
            task_id=f"T_Fix_{uuid.uuid4().hex[:6]}",
            title=f"Fix: {bug_report.test_name}",
            description=f"Fix the bug reported in test: {bug_report.test_name}\n\n"
                       f"Error: {bug_report.error_message}\n\n"
                       f"Fix Suggestion:\n{fix_suggestion}",
            assigned_to=assigned_to,
            type="bug_fix",
            metadata={
                "bug_report": bug_report.to_dict(),
                "fix_suggestion": fix_suggestion,
                "original_task": original_task_id
            }
        )

        self.shared_state.add_task(fix_task)
        self.pending_tasks.append(fix_task.task_id)

        logger.info(f"Created fix task: {fix_task.task_id}")
        return fix_task

    async def _check_and_assign_pending_tasks(self):
        """检查并分配待处理的任务"""
        for task_id in self.pending_tasks[:]:
            task = self.shared_state.get_task(task_id)

            if task and task.status == TaskStatus.PENDING:
                if self._can_execute_task(task):
                    await self._assign_task_to_agent(task)

    async def _check_project_completion(self):
        """检查项目是否完成"""
        # 如果所有任务都完成了
        if not self.pending_tasks and len(self.completed_tasks) >= 3:
            logger.info("All tasks completed! Finalizing project...")
            await self._finalize_project()

    async def _finalize_project(self):
        """完成项目"""
        self.shared_state.set_project_status("completed")

        # 生成项目摘要
        summary = self.shared_state.export_summary()
        logger.info(f"Project Summary:\n{summary}")

        # 打包项目（在packaging工具中实现）
        logger.info("Project ready for packaging")

    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """
        PM Agent不直接执行任务，而是协调其他Agent
        """
        return {"status": "coordinating"}

    def get_project_status(self) -> Dict[str, Any]:
        """获取项目状态"""
        return {
            "project_id": self.current_project_id,
            "project_status": self.shared_state.get_project_status(),
            "pending_tasks": len(self.pending_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "total_tasks": len(self.shared_state.get_all_tasks())
        }
