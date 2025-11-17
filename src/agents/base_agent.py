"""
Agent基类模块
Base Agent Module

本模块定义了DevSwarm系统中所有Agent的基类。BaseAgent提供了Agent的通用行为、
消息处理机制和任务执行框架，所有专业Agent（PM、Backend、Frontend、QA）都继承此类。

设计原则:
    1. 抽象基类: 使用ABC定义接口契约，强制子类实现execute_task()
    2. 消息驱动: Agent通过消息总线接收任务和通信
    3. 状态管理: 自动管理任务状态（PENDING → IN_PROGRESS → COMPLETED/FAILED）
    4. 错误处理: 统一的异常捕获和错误报告机制
    5. 可扩展: 子类可以覆盖方法扩展功能

主要组件:
    - BaseAgent: Agent抽象基类

Agent生命周期:
    1. 初始化: __init__() - 注册到消息总线
    2. 启动: start() - 激活Agent
    3. 接收任务: _handle_task_assignment() - 接收PM分配的任务
    4. 执行任务: execute_task() - 子类实现具体逻辑
    5. 报告结果: _send_completion_report() 或 _send_error_report()
    6. 停止: stop() - 停用Agent

消息处理流程:
    消息到达 → _handle_message() → 根据类型分发 → 具体处理方法

子类实现要求:
    - 必须实现: execute_task()
    - 可选实现: handle_message(), handle_data_request(), handle_error_report()

Example:
    >>> class MyAgent(BaseAgent):
    ...     def __init__(self, message_bus, shared_state, llm_client):
    ...         super().__init__(
    ...             agent_name="My_Agent",
    ...             role="My specialized role",
    ...             message_bus=message_bus,
    ...             shared_state=shared_state,
    ...             llm_client=llm_client
    ...         )
    ...
    ...     async def execute_task(self, task: Task) -> Dict[str, Any]:
    ...         # 实现任务执行逻辑
    ...         return {"status": "success"}
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
    Agent抽象基类

    定义了DevSwarm系统中所有Agent的通用接口和行为。作为抽象基类，
    它不能直接实例化，必须由具体的Agent类（如PMAgent、BackendAgent）继承。

    核心职责:
        1. **消息处理**: 接收并处理来自消息总线的消息
        2. **任务执行**: 执行PM Agent分配的任务
        3. **状态管理**: 维护Agent和任务的状态
        4. **通信协调**: 通过消息总线与其他Agent通信
        5. **错误处理**: 捕获异常并报告错误

    Attributes:
        agent_name (str): Agent的唯一名称标识
        role (str): Agent的角色描述
        message_bus (MessageBus): 消息总线引用
        shared_state (SharedState): 共享状态引用
        llm_client (LLMClient): LLM客户端引用
        is_active (bool): Agent是否处于激活状态
        current_task (Optional[Task]): 当前正在执行的任务

    抽象方法:
        execute_task(): 子类必须实现的任务执行方法

    可覆盖方法:
        handle_message(): 处理自定义消息类型
        handle_data_request(): 处理数据请求
        handle_error_report(): 处理错误报告
    """

    def __init__(self,
                 agent_name: str,
                 role: str,
                 message_bus: MessageBus,
                 shared_state: SharedState,
                 llm_client: LLMClient):
        """
        初始化Agent

        创建Agent实例并注册到消息总线。初始化后Agent处于未激活状态，
        需要调用start()方法启动。

        Args:
            agent_name (str): Agent的唯一名称，如"Backend_Agent"、"PM_Agent"
                - 用于消息路由和身份识别
                - 必须在系统中唯一
            role (str): Agent的角色描述，如"后端开发Agent"、"项目经理Agent"
                - 用于日志和用户界面显示
            message_bus (MessageBus): 消息总线实例
                - Agent通过它接收和发送消息
            shared_state (SharedState): 共享状态实例
                - Agent通过它读写项目数据
            llm_client (LLMClient): LLM客户端实例
                - Agent通过它调用大语言模型生成代码、分析需求等

        初始化步骤:
            1. 保存基础属性
            2. 初始化Agent状态（未激活、无当前任务）
            3. 注册到消息总线（订阅以agent_name为目标的消息）
            4. 记录初始化日志

        Example:
            >>> agent = MyAgent(
            ...     agent_name="My_Agent",
            ...     role="My Role",
            ...     message_bus=bus,
            ...     shared_state=state,
            ...     llm_client=client
            ... )
        """
        # 基础属性
        self.agent_name = agent_name
        self.role = role
        self.message_bus = message_bus
        self.shared_state = shared_state
        self.llm_client = llm_client

        # Agent运行状态
        self.is_active = False                      # 是否激活
        self.current_task: Optional[Task] = None    # 当前任务

        # 注册到消息总线，接收发送给自己的消息
        self.message_bus.subscribe(self.agent_name, self._handle_message)

        logger.info(f"{self.agent_name} ({self.role}) initialized")

    async def _handle_message(self, message: Message):
        """
        处理接收到的消息（内部方法）

        这是消息总线回调函数，当有消息发送给此Agent时被调用。
        根据消息类型将消息分发到相应的处理方法。

        消息分发逻辑:
            - TASK_ASSIGNMENT → _handle_task_assignment() (任务分配)
            - DATA_REQUEST → _handle_data_request() (数据请求)
            - ERROR_REPORT → _handle_error_report() (错误报告)
            - 其他类型 → handle_message() (子类自定义处理)

        错误处理:
            - 捕获所有异常，避免单个消息处理失败影响Agent运行
            - 将异常转换为错误报告发送给PM Agent

        Args:
            message (Message): 从消息总线接收到的消息

        Note:
            此方法是私有的，不应直接调用。由消息总线自动调用。
        """
        try:
            # 记录消息接收日志
            logger.info(
                f"{self.agent_name} received message: "
                f"{message.type.value} from {message.from_agent}"
            )

            # 根据消息类型分发到对应的处理方法
            if message.type == MessageType.TASK_ASSIGNMENT:
                # PM Agent分配任务
                await self._handle_task_assignment(message)
            elif message.type == MessageType.DATA_REQUEST:
                # 其他Agent请求数据
                await self._handle_data_request(message)
            elif message.type == MessageType.ERROR_REPORT:
                # 接收错误报告
                await self._handle_error_report(message)
            else:
                # 其他消息类型，交给子类处理
                await self.handle_message(message)

        except Exception as e:
            # 捕获消息处理过程中的任何异常
            logger.error(
                f"Error handling message in {self.agent_name}: {e}",
                exc_info=True
            )
            # 向PM Agent报告错误
            await self._send_error_report(str(e))

    async def _handle_task_assignment(self, message: Message):
        """
        处理任务分配

        当PM Agent分配任务时调用此方法。完整处理任务的生命周期：
        接收 → 执行 → 更新状态 → 报告结果。

        处理流程:
            1. 验证消息中包含任务对象
            2. 设置为当前任务
            3. 更新共享状态中的任务状态为IN_PROGRESS
            4. 向PM Agent发送状态更新消息
            5. 调用execute_task()执行具体任务逻辑（子类实现）
            6. 根据执行结果:
               - 成功: 更新状态为COMPLETED，发送完成报告
               - 失败: 更新状态为FAILED，发送错误报告
            7. 清空当前任务

        Args:
            message (Message): 包含任务对象的消息

        错误处理:
            - 如果消息不包含任务对象，记录警告并返回
            - 如果执行任务时抛出异常，捕获并报告给PM Agent
            - 无论成功失败，都会清空current_task

        Note:
            此方法是私有的，由_handle_message()自动调用
        """
        # 验证消息中是否包含任务
        if not message.task:
            logger.warning(f"Task assignment message without task: {message.message_id}")
            return

        task = message.task
        self.current_task = task

        logger.info(f"{self.agent_name} received task: {task.task_id} - {task.title}")

        # 更新共享状态：任务状态 → IN_PROGRESS
        self.shared_state.update_task_status(task.task_id, TaskStatus.IN_PROGRESS)

        # 通知PM Agent任务已开始
        await self._send_status_update(task.task_id, TaskStatus.IN_PROGRESS)

        # 执行任务（调用子类实现的execute_task方法）
        try:
            # 执行具体任务逻辑，子类必须实现此方法
            result = await self.execute_task(task)

            # 任务执行成功
            # 更新共享状态：任务状态 → COMPLETED
            self.shared_state.update_task_status(
                task.task_id,
                TaskStatus.COMPLETED,
                metadata=result
            )

            # 向PM Agent发送完成报告
            await self._send_completion_report(task.task_id, result)

        except Exception as e:
            # 任务执行失败
            logger.error(f"Error executing task {task.task_id}: {e}", exc_info=True)

            # 更新共享状态：任务状态 → FAILED
            self.shared_state.update_task_status(
                task.task_id,
                TaskStatus.FAILED,
                metadata={"error": str(e)}
            )

            # 向PM Agent发送错误报告
            await self._send_error_report(str(e), task.task_id)

        finally:
            # 清空当前任务（无论成功失败）
            self.current_task = None

    async def _handle_data_request(self, message: Message):
        """
        处理数据请求（内部方法）

        转发给子类的handle_data_request()方法处理。

        Args:
            message (Message): 数据请求消息

        Note:
            此方法是私有的，由_handle_message()自动调用
        """
        logger.debug(f"{self.agent_name} received data request")
        await self.handle_data_request(message)

    async def _handle_error_report(self, message: Message):
        """
        处理错误报告（内部方法）

        转发给子类的handle_error_report()方法处理。

        Args:
            message (Message): 错误报告消息

        Note:
            此方法是私有的，由_handle_message()自动调用
        """
        logger.debug(f"{self.agent_name} received error report")
        await self.handle_error_report(message)

    @abstractmethod
    async def execute_task(self, task: Task) -> Dict[str, Any]:
        """
        执行任务（抽象方法，子类必须实现）

        这是Agent的核心方法，子类必须实现具体的任务执行逻辑。
        此方法由_handle_task_assignment()调用。

        实现要求:
            - 必须是异步方法（async def）
            - 接收Task对象作为参数
            - 返回任务执行结果字典
            - 如果执行失败，应抛出异常

        Args:
            task (Task): 要执行的任务对象，包含:
                - task_id: 任务ID
                - title: 任务标题
                - description: 任务详细描述
                - dependencies: 依赖列表
                - metadata: 元数据

        Returns:
            Dict[str, Any]: 任务执行结果，通常包含:
                - status: 执行状态
                - output_files: 生成的文件列表
                - 其他任务特定的结果数据

        Raises:
            Exception: 任务执行失败时抛出异常

        Example:
            >>> async def execute_task(self, task: Task) -> Dict[str, Any]:
            ...     # 读取依赖
            ...     contract = self.shared_state.get_api_contract()
            ...
            ...     # 生成代码
            ...     code = await self.llm_client.generate(...)
            ...
            ...     # 写入文件
            ...     output_path = self.shared_state.get_codebase_path("backend")
            ...     with open(f"{output_path}/app.py", "w") as f:
            ...         f.write(code)
            ...
            ...     # 返回结果
            ...     return {
            ...         "status": "success",
            ...         "output_files": ["backend/app.py"]
            ...     }
        """
        pass

    async def handle_message(self, message: Message):
        """
        处理其他类型的消息（可选覆盖）

        用于处理自定义消息类型。基类提供空实现，子类可以根据需要覆盖。

        Args:
            message (Message): 未被基类处理的消息

        Example:
            >>> async def handle_message(self, message: Message):
            ...     if message.type == MessageType.CUSTOM:
            ...         # 处理自定义消息
            ...         pass
        """
        logger.debug(f"{self.agent_name} received unhandled message type: {message.type}")

    async def handle_data_request(self, message: Message):
        """
        处理数据请求（可选覆盖）

        当其他Agent请求数据时调用。基类提供空实现，子类可以根据需要覆盖。

        Args:
            message (Message): 数据请求消息，payload通常包含:
                - data_type: 请求的数据类型
                - query: 查询参数

        Example:
            >>> async def handle_data_request(self, message: Message):
            ...     data_type = message.payload.get("data_type")
            ...     if data_type == "api_spec":
            ...         # 返回API规范
            ...         await self.send_message(
            ...             to_agent=message.from_agent,
            ...             message_type=MessageType.DATA_RESPONSE,
            ...             payload={"data": api_spec}
            ...         )
        """
        pass

    async def handle_error_report(self, message: Message):
        """
        处理错误报告（可选覆盖）

        当接收到错误报告时调用。基类提供空实现，子类可以根据需要覆盖。

        Args:
            message (Message): 错误报告消息，payload通常包含:
                - task_id: 相关任务ID
                - error: 错误消息
                - agent: 报告错误的Agent

        Example:
            >>> async def handle_error_report(self, message: Message):
            ...     error = message.payload.get("error")
            ...     logger.error(f"Received error report: {error}")
            ...     # 可以采取补救措施
        """
        pass

    async def send_message(self, to_agent: str, message_type: MessageType,
                          task: Optional[Task] = None,
                          payload: Optional[Dict[str, Any]] = None):
        """
        发送消息到其他Agent

        封装消息创建和发送逻辑，简化Agent间通信。

        Args:
            to_agent (str): 目标Agent名称，或"ALL"表示广播
            message_type (MessageType): 消息类型
            task (Optional[Task]): 任务对象，用于TASK_ASSIGNMENT消息
            payload (Optional[Dict[str, Any]]): 消息负载数据

        Example:
            >>> # 发送状态更新
            >>> await self.send_message(
            ...     to_agent="PM_Agent",
            ...     message_type=MessageType.STATUS_UPDATE,
            ...     payload={"task_id": "T1", "status": "completed"}
            ... )
            >>>
            >>> # 广播消息
            >>> await self.send_message(
            ...     to_agent="ALL",
            ...     message_type=MessageType.STATUS_UPDATE,
            ...     payload={"info": "Starting work"}
            ... )
        """
        # 创建消息对象
        message = Message(
            from_agent=self.agent_name,
            to_agent=to_agent,
            type=message_type,
            task=task,
            payload=payload or {}
        )

        # 发布到消息总线
        await self.message_bus.publish(message)

    async def _send_status_update(self, task_id: str, status: TaskStatus):
        """
        发送任务状态更新给PM Agent

        Args:
            task_id (str): 任务ID
            status (TaskStatus): 新状态

        Note:
            此方法是私有的，由_handle_task_assignment()自动调用
        """
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
        """
        发送任务完成报告给PM Agent

        Args:
            task_id (str): 任务ID
            result (Dict[str, Any]): 任务执行结果

        Note:
            此方法是私有的，由_handle_task_assignment()自动调用
        """
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
        """
        发送错误报告给PM Agent

        Args:
            error_message (str): 错误消息
            task_id (Optional[str]): 相关任务ID（如果有）

        Note:
            此方法是私有的，用于报告任务执行或消息处理中的错误
        """
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
        向其他Agent请求数据

        Agent间数据共享的标准方法。

        Args:
            from_agent (str): 数据源Agent名称
            data_type (str): 请求的数据类型
            query (Optional[Dict]): 查询参数

        Example:
            >>> # 请求API规范
            >>> await self.request_data(
            ...     from_agent="Backend_Agent",
            ...     data_type="api_spec",
            ...     query={"endpoint": "/api/items"}
            ... )
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
        """
        启动Agent

        将Agent设置为激活状态。激活后Agent可以接收和处理消息。

        Example:
            >>> agent.start()
            >>> # Agent现在可以接收任务了
        """
        self.is_active = True
        logger.info(f"{self.agent_name} started")

    def stop(self):
        """
        停止Agent

        将Agent设置为未激活状态。通常在系统关闭时调用。

        Note:
            停止后Agent仍然订阅消息总线，但is_active标志为False

        Example:
            >>> agent.stop()
            >>> # Agent已停止
        """
        self.is_active = False
        logger.info(f"{self.agent_name} stopped")

    def get_status(self) -> Dict[str, Any]:
        """
        获取Agent当前状态

        Returns:
            Dict[str, Any]: 状态字典，包含:
                - agent_name: Agent名称
                - role: Agent角色
                - is_active: 是否激活
                - current_task: 当前任务（如果有）

        Example:
            >>> status = agent.get_status()
            >>> print(f"Agent: {status['agent_name']}")
            >>> print(f"Active: {status['is_active']}")
            >>> if status['current_task']:
            ...     print(f"Working on: {status['current_task']['title']}")
        """
        return {
            "agent_name": self.agent_name,
            "role": self.role,
            "is_active": self.is_active,
            "current_task": self.current_task.to_dict() if self.current_task else None
        }

    def __repr__(self) -> str:
        """
        Agent的字符串表示

        Returns:
            str: Agent的可读字符串表示

        Example:
            >>> agent = BackendAgent(...)
            >>> print(agent)
            <BackendAgent name=Backend_Agent role=后端开发Agent>
        """
        return f"<{self.__class__.__name__} name={self.agent_name} role={self.role}>"
