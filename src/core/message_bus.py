"""
Message Bus - 消息总线
所有Agent间的通信通过此总线进行
"""
import asyncio
from typing import Dict, List, Callable, Optional
from collections import defaultdict
import logging
from .protocol import Message, MessageType

logger = logging.getLogger(__name__)


class MessageBus:
    """
    中心化的消息传递系统
    支持点对点和广播通信
    """

    def __init__(self):
        # 订阅者字典: agent_name -> [callback_functions]
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        # 消息历史
        self._message_history: List[Message] = []
        # 消息队列
        self._message_queue: asyncio.Queue = asyncio.Queue()
        # 运行状态
        self._running = False
        # 事件循环任务
        self._task: Optional[asyncio.Task] = None

    def subscribe(self, agent_name: str, callback: Callable):
        """
        订阅消息

        Args:
            agent_name: Agent名称
            callback: 接收消息的回调函数，签名为 async def callback(message: Message)
        """
        self._subscribers[agent_name].append(callback)
        logger.info(f"Agent '{agent_name}' subscribed to message bus")

    def unsubscribe(self, agent_name: str):
        """取消订阅"""
        if agent_name in self._subscribers:
            del self._subscribers[agent_name]
            logger.info(f"Agent '{agent_name}' unsubscribed from message bus")

    async def publish(self, message: Message):
        """
        发布消息到总线

        Args:
            message: 要发送的消息
        """
        # 记录到历史
        self._message_history.append(message)

        logger.info(
            f"Message published: {message.from_agent} -> {message.to_agent} "
            f"[{message.type.value}]"
        )

        # 放入队列处理
        await self._message_queue.put(message)

    async def _process_messages(self):
        """处理消息队列（后台任务）"""
        while self._running:
            try:
                # 等待消息
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0
                )

                # 分发消息
                await self._dispatch_message(message)

            except asyncio.TimeoutError:
                # 超时继续等待
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)

    async def _dispatch_message(self, message: Message):
        """
        分发消息到订阅者

        Args:
            message: 要分发的消息
        """
        # 广播消息
        if message.to_agent == "ALL":
            for agent_name, callbacks in self._subscribers.items():
                # 不发送给自己
                if agent_name != message.from_agent:
                    await self._deliver_to_agent(agent_name, callbacks, message)
        # 点对点消息
        else:
            if message.to_agent in self._subscribers:
                callbacks = self._subscribers[message.to_agent]
                await self._deliver_to_agent(message.to_agent, callbacks, message)
            else:
                logger.warning(
                    f"No subscriber found for agent '{message.to_agent}'"
                )

    async def _deliver_to_agent(self, agent_name: str,
                                callbacks: List[Callable],
                                message: Message):
        """
        投递消息到特定Agent

        Args:
            agent_name: Agent名称
            callbacks: 回调函数列表
            message: 消息
        """
        for callback in callbacks:
            try:
                # 调用回调处理消息
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                logger.error(
                    f"Error delivering message to {agent_name}: {e}",
                    exc_info=True
                )

    async def start(self):
        """启动消息总线"""
        if self._running:
            logger.warning("Message bus is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._process_messages())
        logger.info("Message bus started")

    async def stop(self):
        """停止消息总线"""
        if not self._running:
            return

        self._running = False
        if self._task:
            await self._task
        logger.info("Message bus stopped")

    def get_message_history(self,
                           agent_name: Optional[str] = None,
                           message_type: Optional[MessageType] = None,
                           limit: int = 100) -> List[Message]:
        """
        获取消息历史

        Args:
            agent_name: 筛选特定Agent的消息（from或to）
            message_type: 筛选特定类型的消息
            limit: 返回的最大消息数

        Returns:
            消息列表
        """
        messages = self._message_history

        # 筛选
        if agent_name:
            messages = [
                m for m in messages
                if m.from_agent == agent_name or m.to_agent == agent_name
            ]

        if message_type:
            messages = [m for m in messages if m.type == message_type]

        # 限制数量（最新的）
        return messages[-limit:]

    def clear_history(self):
        """清空消息历史"""
        self._message_history.clear()
        logger.info("Message history cleared")

    @property
    def is_running(self) -> bool:
        """消息总线是否正在运行"""
        return self._running

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_messages": len(self._message_history),
            "subscribers": list(self._subscribers.keys()),
            "queue_size": self._message_queue.qsize(),
            "is_running": self._running
        }
