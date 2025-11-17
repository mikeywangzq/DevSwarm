"""
消息总线模块
Message Bus Module

本模块实现了DevSwarm系统的中心化消息传递系统。消息总线是Agent间通信的核心基础设施，
负责路由、分发和管理所有Agent之间的消息通信。

设计原则:
    1. 异步消息处理: 使用asyncio实现非阻塞的消息传递
    2. 发布-订阅模式: Agent订阅消息，总线负责分发
    3. 支持广播: 可以向所有Agent广播消息（to_agent="ALL"）
    4. 消息历史: 记录所有消息用于调试和追踪
    5. 错误隔离: 单个Agent的错误不影响其他Agent

主要组件:
    - MessageBus: 消息总线主类，管理订阅者和消息分发

通信模式:
    - 点对点通信: PM Agent -> Backend Agent
    - 广播通信: PM Agent -> ALL
    - 异步消息队列: 确保消息按序处理

使用示例:
    >>> bus = MessageBus()
    >>> await bus.start()
    >>> bus.subscribe("Backend_Agent", callback_function)
    >>> await bus.publish(message)
"""
import asyncio
from typing import Dict, List, Callable, Optional
from collections import defaultdict
import logging
from .protocol import Message, MessageType

logger = logging.getLogger(__name__)


class MessageBus:
    """
    消息总线类

    实现中心化的消息传递系统，是DevSwarm多Agent系统的通信枢纽。
    采用发布-订阅（Pub-Sub）模式，支持点对点和广播两种通信方式。

    核心功能:
        1. **消息路由**: 根据目标Agent将消息路由到正确的接收者
        2. **异步处理**: 使用asyncio队列实现非阻塞消息处理
        3. **广播支持**: 支持向所有订阅者广播消息
        4. **历史记录**: 保存所有消息用于调试和审计
        5. **错误恢复**: 单个Agent故障不影响整体消息传递

    工作流程:
        1. Agent通过subscribe()注册回调函数
        2. Agent通过publish()发送消息到总线
        3. 消息被放入异步队列
        4. 后台任务(_process_messages)不断处理队列中的消息
        5. 根据to_agent字段将消息分发给订阅者
        6. 调用订阅者的回调函数处理消息

    Attributes:
        _subscribers (Dict[str, List[Callable]]): 订阅者字典，键为Agent名称，值为回调函数列表
        _message_history (List[Message]): 消息历史记录，存储所有已发送的消息
        _message_queue (asyncio.Queue): 异步消息队列，缓冲待处理的消息
        _running (bool): 总线运行状态标志
        _task (Optional[asyncio.Task]): 后台消息处理任务

    Example:
        >>> # 创建消息总线
        >>> bus = MessageBus()
        >>>
        >>> # 启动总线
        >>> await bus.start()
        >>>
        >>> # Agent订阅消息
        >>> async def handle_message(msg: Message):
        ...     print(f"Received: {msg.type}")
        >>> bus.subscribe("Backend_Agent", handle_message)
        >>>
        >>> # 发送消息
        >>> msg = Message(
        ...     from_agent="PM_Agent",
        ...     to_agent="Backend_Agent",
        ...     type=MessageType.TASK_ASSIGNMENT
        ... )
        >>> await bus.publish(msg)
        >>>
        >>> # 查看统计
        >>> stats = bus.get_stats()
        >>> print(f"Total messages: {stats['total_messages']}")
    """

    def __init__(self):
        """
        初始化消息总线

        创建空的订阅者字典、消息历史列表和消息队列。
        总线初始状态为未运行，需要调用start()方法启动。
        """
        # 订阅者字典: agent_name -> [callback_functions]
        # 使用defaultdict自动初始化空列表，避免KeyError
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)

        # 消息历史记录，存储所有已处理的消息
        # 用于调试、追踪和故障排查
        self._message_history: List[Message] = []

        # 异步消息队列，实现生产者-消费者模式
        # 发布者将消息放入队列，后台任务从队列取出并分发
        self._message_queue: asyncio.Queue = asyncio.Queue()

        # 运行状态标志，控制后台任务的生命周期
        self._running = False

        # 后台消息处理任务的引用
        # 用于在停止总线时等待任务完成
        self._task: Optional[asyncio.Task] = None

    def subscribe(self, agent_name: str, callback: Callable):
        """
        注册Agent订阅消息

        Agent通过此方法注册一个回调函数，用于接收发送给它的消息。
        一个Agent可以注册多个回调函数，所有回调都会被依次调用。

        回调函数要求:
            - 必须接受一个Message类型的参数
            - 推荐使用async函数以支持异步处理
            - 也支持同步函数，但会阻塞消息处理

        Args:
            agent_name (str): Agent的唯一名称，如 "Backend_Agent", "PM_Agent"
            callback (Callable): 消息处理回调函数
                - 异步函数签名: async def callback(message: Message) -> None
                - 同步函数签名: def callback(message: Message) -> None

        Example:
            >>> async def handle_task(msg: Message):
            ...     if msg.type == MessageType.TASK_ASSIGNMENT:
            ...         print(f"New task: {msg.task.title}")
            >>>
            >>> bus.subscribe("Backend_Agent", handle_task)
        """
        self._subscribers[agent_name].append(callback)
        logger.info(f"Agent '{agent_name}' subscribed to message bus")

    def unsubscribe(self, agent_name: str):
        """
        取消Agent的消息订阅

        移除指定Agent的所有回调函数，该Agent将不再接收任何消息。
        通常在Agent停止工作或系统清理时调用。

        Args:
            agent_name (str): 要取消订阅的Agent名称

        Note:
            如果Agent不存在于订阅列表中，此方法不会产生任何效果

        Example:
            >>> bus.unsubscribe("Backend_Agent")
        """
        if agent_name in self._subscribers:
            del self._subscribers[agent_name]
            logger.info(f"Agent '{agent_name}' unsubscribed from message bus")

    async def publish(self, message: Message):
        """
        发布消息到总线

        Agent通过此方法发送消息。消息会被记录到历史，然后放入异步队列等待处理。
        此方法是异步的，会立即返回，不会等待消息被实际分发。

        消息流程:
            1. 消息被添加到历史记录
            2. 记录日志（from -> to, type）
            3. 消息放入异步队列
            4. 后台任务从队列取出消息并分发

        Args:
            message (Message): 要发送的消息对象，必须包含:
                - from_agent: 发送方Agent名称
                - to_agent: 接收方Agent名称或"ALL"（广播）
                - type: 消息类型（MessageType枚举）
                - payload: 消息负载数据

        Note:
            此方法是异步的，需要使用await调用

        Example:
            >>> msg = Message(
            ...     from_agent="PM_Agent",
            ...     to_agent="Backend_Agent",
            ...     type=MessageType.TASK_ASSIGNMENT,
            ...     task=task_object
            ... )
            >>> await bus.publish(msg)
        """
        # 记录到历史，用于调试和审计
        self._message_history.append(message)

        # 记录消息路由日志
        logger.info(
            f"Message published: {message.from_agent} -> {message.to_agent} "
            f"[{message.type.value}]"
        )

        # 放入异步队列，由后台任务处理
        await self._message_queue.put(message)

    async def _process_messages(self):
        """
        后台消息处理任务

        这是一个长期运行的协程，不断从消息队列中取出消息并分发。
        在start()方法中作为asyncio.Task启动，在stop()方法中停止。

        处理流程:
            1. 从队列中等待消息（1秒超时）
            2. 如果有消息，调用_dispatch_message()分发
            3. 如果超时，继续下一轮循环
            4. 如果发生异常，记录错误但不中断循环

        错误处理:
            - 单个消息处理失败不影响后续消息
            - 所有异常都被捕获并记录
            - 确保消息总线的持续可用性

        Note:
            此方法是私有的，只应由start()方法调用
        """
        while self._running:
            try:
                # 从队列中等待消息，设置1秒超时
                # 超时设计允许定期检查_running标志，实现优雅停止
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0
                )

                # 将消息分发给相应的订阅者
                await self._dispatch_message(message)

            except asyncio.TimeoutError:
                # 队列为空且超时，继续下一轮等待
                # 这是正常情况，不需要记录
                continue
            except Exception as e:
                # 捕获所有其他异常，避免后台任务崩溃
                logger.error(f"Error processing message: {e}", exc_info=True)

    async def _dispatch_message(self, message: Message):
        """
        分发消息到订阅者

        根据消息的目标Agent（to_agent字段）决定分发方式:
        - 如果to_agent是"ALL"，则广播给所有订阅者（除发送者自己）
        - 否则，点对点发送给指定的Agent

        Args:
            message (Message): 要分发的消息对象

        分发逻辑:
            广播模式 (to_agent="ALL"):
                - 遍历所有订阅者
                - 跳过发送者自己（避免自己收到自己的消息）
                - 向其他所有Agent投递消息

            点对点模式:
                - 查找目标Agent的订阅回调
                - 如果找到，投递消息
                - 如果找不到，记录警告日志

        Note:
            此方法是私有的，只由_process_messages()调用
        """
        # 广播消息模式: 发送给所有Agent（除了发送者）
        if message.to_agent == "ALL":
            for agent_name, callbacks in self._subscribers.items():
                # 跳过发送者自己，避免循环
                if agent_name != message.from_agent:
                    await self._deliver_to_agent(agent_name, callbacks, message)

        # 点对点消息模式: 发送给特定Agent
        else:
            if message.to_agent in self._subscribers:
                # 找到目标Agent的回调函数列表
                callbacks = self._subscribers[message.to_agent]
                await self._deliver_to_agent(message.to_agent, callbacks, message)
            else:
                # 目标Agent未订阅，记录警告
                # 这可能是配置错误或Agent尚未启动
                logger.warning(
                    f"No subscriber found for agent '{message.to_agent}'"
                )

    async def _deliver_to_agent(self, agent_name: str,
                                callbacks: List[Callable],
                                message: Message):
        """
        投递消息到特定Agent的所有回调函数

        遍历Agent的所有注册回调函数，依次调用它们处理消息。
        支持异步和同步两种回调函数。

        Args:
            agent_name (str): 目标Agent的名称
            callbacks (List[Callable]): Agent注册的回调函数列表
            message (Message): 要投递的消息对象

        错误处理:
            - 单个回调函数的异常不影响其他回调
            - 异常会被记录但不会中断消息投递流程
            - 确保所有回调都有机会处理消息

        Note:
            - 优先支持异步回调函数（性能更好）
            - 也兼容同步回调函数（但会阻塞）
            - 此方法是私有的，只由_dispatch_message()调用
        """
        for callback in callbacks:
            try:
                # 检查回调函数是否为协程函数
                if asyncio.iscoroutinefunction(callback):
                    # 异步回调，使用await调用
                    await callback(message)
                else:
                    # 同步回调，直接调用（会阻塞当前协程）
                    callback(message)
            except Exception as e:
                # 捕获回调函数中的任何异常
                # 记录详细错误信息但不中断投递流程
                logger.error(
                    f"Error delivering message to {agent_name}: {e}",
                    exc_info=True
                )

    async def start(self):
        """
        启动消息总线

        启动后台消息处理任务，开始处理消息队列。
        总线必须先启动才能分发消息，否则消息会积压在队列中。

        工作流程:
            1. 检查总线是否已经在运行
            2. 设置运行标志为True
            3. 创建后台任务运行_process_messages()
            4. 记录启动日志

        Note:
            - 重复调用start()不会创建多个后台任务
            - 此方法是异步的，需要使用await调用
            - 通常在系统初始化时调用一次

        Example:
            >>> bus = MessageBus()
            >>> await bus.start()
            >>> # 现在可以发送和接收消息了
        """
        if self._running:
            logger.warning("Message bus is already running")
            return

        # 设置运行标志，控制后台任务的循环
        self._running = True

        # 创建异步任务运行消息处理循环
        self._task = asyncio.create_task(self._process_messages())

        logger.info("Message bus started")

    async def stop(self):
        """
        停止消息总线

        优雅地停止后台消息处理任务。会等待当前正在处理的消息完成，
        但不会处理队列中剩余的消息。

        停止流程:
            1. 检查总线是否正在运行
            2. 设置运行标志为False（通知后台任务停止）
            3. 等待后台任务完成（最多等待1秒，因为超时设置）
            4. 记录停止日志

        Note:
            - 队列中未处理的消息会保留
            - 再次调用start()可以继续处理剩余消息
            - 此方法是异步的，需要使用await调用
            - 通常在系统关闭时调用

        Example:
            >>> await bus.stop()
            >>> # 总线已停止，不再处理新消息
        """
        if not self._running:
            return

        # 设置运行标志为False，通知后台任务停止
        self._running = False

        # 等待后台任务完成
        # 由于_process_messages有1秒超时，最多等待1秒
        if self._task:
            await self._task

        logger.info("Message bus stopped")

    def get_message_history(self,
                           agent_name: Optional[str] = None,
                           message_type: Optional[MessageType] = None,
                           limit: int = 100) -> List[Message]:
        """
        获取消息历史记录

        提供灵活的消息历史查询功能，支持按Agent和消息类型筛选。
        主要用于调试、监控和故障排查。

        Args:
            agent_name (Optional[str]): 筛选特定Agent的消息
                - 如果指定，返回该Agent发送或接收的所有消息
                - 如果为None，返回所有Agent的消息
            message_type (Optional[MessageType]): 筛选特定类型的消息
                - 如果指定，只返回该类型的消息
                - 如果为None，返回所有类型的消息
            limit (int): 返回的最大消息数，默认100条
                - 返回最新的N条消息
                - 用于限制内存使用和提高性能

        Returns:
            List[Message]: 消息列表，按时间顺序排列（最新的在最后）

        Example:
            >>> # 获取所有消息（最多100条）
            >>> all_messages = bus.get_message_history()
            >>>
            >>> # 获取Backend Agent的消息
            >>> backend_messages = bus.get_message_history(agent_name="Backend_Agent")
            >>>
            >>> # 获取所有任务分配消息
            >>> task_messages = bus.get_message_history(
            ...     message_type=MessageType.TASK_ASSIGNMENT
            ... )
            >>>
            >>> # 组合筛选：Backend Agent的错误报告
            >>> errors = bus.get_message_history(
            ...     agent_name="Backend_Agent",
            ...     message_type=MessageType.ERROR_REPORT,
            ...     limit=10
            ... )
        """
        messages = self._message_history

        # 按Agent名称筛选（发送方或接收方）
        if agent_name:
            messages = [
                m for m in messages
                if m.from_agent == agent_name or m.to_agent == agent_name
            ]

        # 按消息类型筛选
        if message_type:
            messages = [m for m in messages if m.type == message_type]

        # 返回最新的N条消息
        return messages[-limit:]

    def clear_history(self):
        """
        清空消息历史记录

        删除所有已保存的消息历史，释放内存。
        通常在测试环境或长期运行的系统中定期调用，避免内存持续增长。

        Warning:
            此操作不可逆，清空后无法恢复历史消息

        Example:
            >>> bus.clear_history()
            >>> # 所有历史消息已被清除
        """
        self._message_history.clear()
        logger.info("Message history cleared")

    @property
    def is_running(self) -> bool:
        """
        消息总线运行状态

        Returns:
            bool: True表示总线正在运行，False表示已停止

        Example:
            >>> if bus.is_running:
            ...     print("Message bus is active")
            ... else:
            ...     await bus.start()
        """
        return self._running

    def get_stats(self) -> Dict:
        """
        获取消息总线统计信息

        返回总线的当前状态和统计数据，用于监控和诊断。

        Returns:
            Dict: 包含以下键的字典:
                - total_messages (int): 历史消息总数
                - subscribers (List[str]): 所有订阅者的Agent名称列表
                - queue_size (int): 当前队列中待处理的消息数
                - is_running (bool): 总线是否正在运行

        Example:
            >>> stats = bus.get_stats()
            >>> print(f"Total messages: {stats['total_messages']}")
            >>> print(f"Active agents: {', '.join(stats['subscribers'])}")
            >>> print(f"Pending messages: {stats['queue_size']}")
            >>>
            >>> # 监控队列积压
            >>> if stats['queue_size'] > 100:
            ...     print("Warning: Message queue is backed up!")
        """
        return {
            "total_messages": len(self._message_history),
            "subscribers": list(self._subscribers.keys()),
            "queue_size": self._message_queue.qsize(),
            "is_running": self._running
        }
