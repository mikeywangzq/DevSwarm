"""
Redis消息总线实现
Redis-based Message Bus Implementation

使用Redis Pub/Sub实现分布式消息总线，支持跨进程/机器的Agent通信。

核心功能:
    - 发布/订阅模式消息传递
    - 支持多个订阅者
    - 消息序列化/反序列化
    - 异步消息处理
    - 连接重试机制

Example:
    >>> bus = RedisMessageBus("redis://localhost:6379")
    >>> bus.subscribe("task.backend", lambda msg: print(msg))
    >>> bus.publish("task.backend", {"task_id": "T1", "action": "execute"})
"""
import redis
import json
import logging
import threading
import time
from typing import Callable, Dict, Any, Optional

logger = logging.getLogger(__name__)


class RedisMessageBus:
    """
    基于Redis Pub/Sub的分布式消息总线

    Attributes:
        redis_client: Redis客户端
        pubsub: Redis Pub/Sub对象
        handlers: 消息处理器字典
        listening_thread: 消息监听线程
    """

    def __init__(self, redis_url: str = "redis://localhost:6379",
                 retry_attempts: int = 3,
                 retry_delay: float = 1.0):
        """
        初始化Redis消息总线

        Args:
            redis_url: Redis服务器URL
            retry_attempts: 连接重试次数
            retry_delay: 重试延迟（秒）
        """
        self.redis_url = redis_url
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay

        # 建立连接
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self._connect()

        # 消息处理器
        self.handlers: Dict[str, Callable] = {}

        # 监听线程
        self.listening_thread: Optional[threading.Thread] = None
        self._stop_listening = threading.Event()

    def _connect(self):
        """建立Redis连接（带重试）"""
        for attempt in range(self.retry_attempts):
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    decode_responses=False  # 二进制模式
                )
                # 测试连接
                self.redis_client.ping()
                self.pubsub = self.redis_client.pubsub()
                logger.info(f"Connected to Redis at {self.redis_url}")
                return
            except redis.ConnectionError as e:
                logger.warning(f"Redis connection attempt {attempt + 1} failed: {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))  # 指数退避
                else:
                    logger.error("Failed to connect to Redis after all attempts")
                    raise

    def publish(self, channel: str, message: Dict[str, Any]):
        """
        发布消息到指定频道

        Args:
            channel: 频道名称（如 "task.backend", "result.frontend"）
            message: 消息字典

        Raises:
            redis.ConnectionError: Redis连接失败
        """
        try:
            serialized = json.dumps(message)
            self.redis_client.publish(channel, serialized)
            logger.debug(f"Published message to {channel}: {message.get('type', 'unknown')}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to publish message to {channel}: {e}")
            # 尝试重连
            self._connect()
            raise
        except Exception as e:
            logger.error(f"Error publishing message: {e}")
            raise

    def subscribe(self, channel: str, handler: Callable[[Dict[str, Any]], None]):
        """
        订阅频道并注册消息处理器

        Args:
            channel: 频道名称
            handler: 消息处理函数，接收消息字典作为参数

        Example:
            >>> def on_task(msg):
            ...     print(f"Received task: {msg['task_id']}")
            >>> bus.subscribe("task.backend", on_task)
        """
        if not self.pubsub:
            raise RuntimeError("PubSub not initialized")

        self.handlers[channel] = handler
        self.pubsub.subscribe(channel)
        logger.info(f"Subscribed to channel: {channel}")

    def unsubscribe(self, channel: str):
        """
        取消订阅频道

        Args:
            channel: 频道名称
        """
        if channel in self.handlers:
            del self.handlers[channel]

        if self.pubsub:
            self.pubsub.unsubscribe(channel)
            logger.info(f"Unsubscribed from channel: {channel}")

    def start_listening(self, daemon: bool = True):
        """
        启动消息监听（在独立线程中）

        Args:
            daemon: 是否作为守护线程运行

        Example:
            >>> bus.start_listening()
            >>> # 消息将在后台线程中处理
        """
        if self.listening_thread and self.listening_thread.is_alive():
            logger.warning("Listening thread already running")
            return

        self._stop_listening.clear()
        self.listening_thread = threading.Thread(
            target=self._listen_loop,
            daemon=daemon
        )
        self.listening_thread.start()
        logger.info("Message listening thread started")

    def stop_listening(self, timeout: float = 5.0):
        """
        停止消息监听

        Args:
            timeout: 等待线程结束的超时时间（秒）
        """
        if not self.listening_thread:
            return

        logger.info("Stopping message listening...")
        self._stop_listening.set()
        self.listening_thread.join(timeout=timeout)

        if self.listening_thread.is_alive():
            logger.warning("Listening thread did not stop gracefully")
        else:
            logger.info("Message listening stopped")

    def _listen_loop(self):
        """消息监听循环（运行在独立线程）"""
        logger.info("Starting message listening loop...")

        try:
            while not self._stop_listening.is_set():
                try:
                    # 使用超时避免无限阻塞
                    message = self.pubsub.get_message(timeout=1.0)

                    if message and message['type'] == 'message':
                        channel = message['channel'].decode('utf-8')
                        data_bytes = message['data']

                        try:
                            # 反序列化消息
                            data = json.loads(data_bytes.decode('utf-8'))

                            # 调用处理器
                            if channel in self.handlers:
                                self.handlers[channel](data)
                            else:
                                logger.warning(f"No handler for channel: {channel}")

                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to decode message: {e}")
                        except Exception as e:
                            logger.error(f"Error handling message on {channel}: {e}", exc_info=True)

                except redis.ConnectionError as e:
                    logger.error(f"Redis connection error in listen loop: {e}")
                    # 尝试重连
                    try:
                        self._connect()
                    except Exception as reconnect_error:
                        logger.error(f"Failed to reconnect: {reconnect_error}")
                        time.sleep(5)  # 等待后重试

        except Exception as e:
            logger.error(f"Fatal error in listen loop: {e}", exc_info=True)

        finally:
            logger.info("Message listening loop ended")

    def close(self):
        """关闭连接"""
        self.stop_listening()

        if self.pubsub:
            self.pubsub.close()

        if self.redis_client:
            self.redis_client.close()

        logger.info("Redis message bus closed")

    def __enter__(self):
        """Context manager支持"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager支持"""
        self.close()


# 兼容性适配器：使Redis消息总线兼容现有MessageBus接口
class RedisMessageBusAdapter(RedisMessageBus):
    """
    Redis消息总线适配器，兼容现有的内存MessageBus接口

    这个适配器让Redis消息总线可以直接替换现有的内存消息总线，
    无需修改Agent代码。
    """

    def send_message(self, agent_name: str, message: Dict[str, Any]):
        """
        发送消息给指定Agent（兼容接口）

        Args:
            agent_name: Agent名称
            message: 消息字典
        """
        channel = f"agent.{agent_name}"
        self.publish(channel, message)

    def register_handler(self, message_type: str, handler: Callable):
        """
        注册消息处理器（兼容接口）

        Args:
            message_type: 消息类型
            handler: 处理函数
        """
        channel = f"message.{message_type}"
        self.subscribe(channel, handler)

    def broadcast(self, message: Dict[str, Any]):
        """
        广播消息给所有Agent（兼容接口）

        Args:
            message: 消息字典
        """
        self.publish("broadcast", message)
