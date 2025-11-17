"""
Base Agent - Agent基类
所有Agent都继承自此基类
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging
from ..core.message_bus import MessageBus
from ..core.shared_state import SharedState
from ..core.protocol import Message, MessageType, Task, TaskStatus
from ..llm.llm_client import LLMClient

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Agent基类
    定义所有Agent的通用行为和接口
    """

    def __init__(self,
                 agent_name: str,
                 role: str,
                 message_bus: MessageBus,
                 shared_state: SharedState,
                 llm_client: LLMClient):
        """
        初始化Agent

        Args:
            agent_name: Agent名称（唯一标识）
            role: Agent角色描述
            message_bus: 消息总线
            shared_state: 共享状态
            llm_client: LLM客户端
        """
        self.agent_name = agent_name
        self.role = role
        self.message_bus = message_bus
        self.shared_state = shared_state
        self.llm_client = llm_client

        # Agent状态
        self.is_active = False
        self.current_task: Optional[Task] = None

        # 注册到消息总线
        self.message_bus.subscribe(self.agent_name, self._handle_message)

        logger.info(f"{self.agent_name} ({self.role}) initialized")

    async def _handle_message(self, message: Message):
        """
        处理接收到的消息（内部方法）

        Args:
            message: 接收到的消息
        """
        try:
            logger.info(
                f"{self.agent_name} received message: "
                f"{message.type.value} from {message.from_agent}"
            )

            # 根据消息类型分发
            if message.type == MessageType.TASK_ASSIGNMENT:
                await self._handle_task_assignment(message)
            elif message.type == MessageType.DATA_REQUEST:
                await self._handle_data_request(message)
            elif message.type == MessageType.ERROR_REPORT:
                await self._handle_error_report(message)
            else:
                # 子类可以覆盖此方法处理其他消息
                await self.handle_message(message)

        except Exception as e:
            logger.error(
                f"Error handling message in {self.agent_name}: {e}",
                exc_info=True
            )
            await self._send_error_report(str(e))

    async def _handle_task_assignment(self, message: Message):
        """处理任务分配"""
        if not message.task:
            logger.warning(f"Task assignment message without task: {message.message_id}")
            return

        task = message.task
        self.current_task = task

        logger.info(f"{self.agent_name} received task: {task.task_id} - {task.title}")

        # 更新任务状态为进行中
        self.shared_state.update_task_status(task.task_id, TaskStatus.IN_PROGRESS)

        # 发送状态更新
        await self._send_status_update(task.task_id, TaskStatus.IN_PROGRESS)

        # 执行任务
        try:
            result = await self.execute_task(task)

            # 任务完成
            self.shared_state.update_task_status(
                task.task_id,
                TaskStatus.COMPLETED,
                metadata=result
            )

            await self._send_completion_report(task.task_id, result)

        except Exception as e:
            logger.error(f"Error executing task {task.task_id}: {e}", exc_info=True)

            # 任务失败
            self.shared_state.update_task_status(
                task.task_id,
                TaskStatus.FAILED,
                metadata={"error": str(e)}
            )

            await self._send_error_report(str(e), task.task_id)

        finally:
            self.current_task = None

    async def _handle_data_request(self, message: Message):
        """处理数据请求（子类可覆盖）"""
        logger.debug(f"{self.agent_name} received data request")
        await self.handle_data_request(message)

    async def _handle_error_report(self, message: Message):
        """处理错误报告（子类可覆盖）"""
        logger.debug(f"{self.agent_name} received error report")
        await self.handle_error_report(message)

    @abstractmethod
    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """
        执行任务（子类必须实现）

        Args:
            task: 要执行的任务

        Returns:
            任务执行结果
        """
        pass

    async def handle_message(self, message: Message):
        """
        处理其他类型的消息（子类可选实现）

        Args:
            message: 消息
        """
        logger.debug(f"{self.agent_name} received unhandled message type: {message.type}")

    async def handle_data_request(self, message: Message):
        """
        处理数据请求（子类可选实现）

        Args:
            message: 数据请求消息
        """
        pass

    async def handle_error_report(self, message: Message):
        """
        处理错误报告（子类可选实现）

        Args:
            message: 错误报告消息
        """
        pass

    async def send_message(self, to_agent: str, message_type: MessageType,
                          task: Optional[Task] = None,
                          payload: Optional[Dict[str, Any]] = None):
        """
        发送消息

        Args:
            to_agent: 目标Agent名称
            message_type: 消息类型
            task: 任务（可选）
            payload: 负载（可选）
        """
        message = Message(
            from_agent=self.agent_name,
            to_agent=to_agent,
            type=message_type,
            task=task,
            payload=payload or {}
        )

        await self.message_bus.publish(message)

    async def _send_status_update(self, task_id: str, status: TaskStatus):
        """发送状态更新"""
        await self.send_message(
            to_agent="PM_Agent",
            message_type=MessageType.STATUS_UPDATE,
            payload={
                "task_id": task_id,
                "status": status.value,
                "agent": self.agent_name
            }
        )

    async def _send_completion_report(self, task_id: str, result: Dict[str, Any]):
        """发送完成报告"""
        await self.send_message(
            to_agent="PM_Agent",
            message_type=MessageType.COMPLETION_REPORT,
            payload={
                "task_id": task_id,
                "result": result,
                "agent": self.agent_name
            }
        )

    async def _send_error_report(self, error_message: str,
                                task_id: Optional[str] = None):
        """发送错误报告"""
        await self.send_message(
            to_agent="PM_Agent",
            message_type=MessageType.ERROR_REPORT,
            payload={
                "task_id": task_id,
                "error": error_message,
                "agent": self.agent_name
            }
        )

    async def request_data(self, from_agent: str, data_type: str,
                          query: Optional[Dict] = None) -> None:
        """
        请求数据

        Args:
            from_agent: 数据源Agent
            data_type: 数据类型
            query: 查询参数
        """
        await self.send_message(
            to_agent=from_agent,
            message_type=MessageType.DATA_REQUEST,
            payload={
                "data_type": data_type,
                "query": query or {}
            }
        )

    def start(self):
        """启动Agent"""
        self.is_active = True
        logger.info(f"{self.agent_name} started")

    def stop(self):
        """停止Agent"""
        self.is_active = False
        logger.info(f"{self.agent_name} stopped")

    def get_status(self) -> Dict[str, Any]:
        """获取Agent状态"""
        return {
            "agent_name": self.agent_name,
            "role": self.role,
            "is_active": self.is_active,
            "current_task": self.current_task.to_dict() if self.current_task else None
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.agent_name} role={self.role}>"
