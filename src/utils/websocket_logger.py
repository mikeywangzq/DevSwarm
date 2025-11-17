"""
WebSocket实时日志处理器
WebSocket Real-time Log Handler

本模块提供实时日志流功能，通过WebSocket将系统日志推送到Web客户端。
用户可以在浏览器中实时查看Agent活动、任务执行和系统事件。

主要组件:
    - WebSocketLogHandler: 自定义logging.Handler，将日志广播到WebSocket
    - 集成Flask-SocketIO实现双向通信
    - 支持日志级别过滤和格式化

使用方式:
    >>> from src.utils.websocket_logger import WebSocketLogHandler
    >>> handler = WebSocketLogHandler(socketio_instance)
    >>> logger.addHandler(handler)
"""
import logging
from typing import Optional
from flask_socketio import SocketIO
from datetime import datetime


class WebSocketLogHandler(logging.Handler):
    """
    WebSocket日志处理器

    自定义logging.Handler，将日志记录通过WebSocket实时广播到所有连接的客户端。

    核心功能:
        1. **实时广播**: 每条日志立即推送到所有Web客户端
        2. **格式化**: 将日志记录转换为结构化JSON格式
        3. **级别过滤**: 支持标准Python logging级别过滤
        4. **时间戳**: 为每条日志添加ISO格式时间戳
        5. **颜色编码**: 为不同级别的日志添加前端显示提示

    日志格式:
        {
            "timestamp": "2024-01-15T10:30:45.123456Z",
            "level": "INFO",
            "logger": "PM_Agent",
            "message": "Task assigned to Backend_Agent",
            "color": "info"  // debug, info, warning, error, critical
        }

    Attributes:
        socketio (SocketIO): Flask-SocketIO实例

    Example:
        >>> socketio = SocketIO(app)
        >>> handler = WebSocketLogHandler(socketio)
        >>> handler.setLevel(logging.INFO)
        >>> logger = logging.getLogger('PM_Agent')
        >>> logger.addHandler(handler)
        >>> logger.info("Task started")  # 自动广播到所有客户端
    """

    def __init__(self, socketio: SocketIO, level=logging.NOTSET):
        """
        初始化WebSocket日志处理器

        Args:
            socketio (SocketIO): Flask-SocketIO实例，用于广播日志
            level: 日志级别，默认接受所有级别
        """
        super().__init__(level)
        self.socketio = socketio

        # 日志级别到颜色的映射（用于前端显示）
        self.level_colors = {
            'DEBUG': 'debug',
            'INFO': 'info',
            'WARNING': 'warning',
            'ERROR': 'error',
            'CRITICAL': 'critical'
        }

    def emit(self, record: logging.LogRecord):
        """
        发送日志记录到WebSocket

        当logger记录日志时自动调用此方法。将LogRecord转换为JSON格式，
        然后通过WebSocket广播到所有连接的客户端。

        Args:
            record (logging.LogRecord): Python标准日志记录对象

        处理流程:
            1. 格式化日志消息
            2. 提取日志元数据（级别、logger名称、时间戳）
            3. 转换为JSON结构
            4. 通过socketio.emit()广播到'log'事件
            5. 错误处理：如果广播失败，不影响日志系统其他部分
        """
        try:
            # 格式化日志消息
            log_message = self.format(record)

            # 构建结构化日志数据
            log_data = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'level': record.levelname,
                'logger': record.name,
                'message': log_message,
                'color': self.level_colors.get(record.levelname, 'info'),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }

            # 广播到所有WebSocket客户端
            self.socketio.emit('log', log_data, namespace='/logs')

        except Exception as e:
            # 如果WebSocket广播失败，不应影响日志系统
            # 静默处理错误，避免递归日志问题
            self.handleError(record)

    def handleError(self, record):
        """
        处理日志发送过程中的错误

        覆盖父类方法，避免在WebSocket断开时产生异常。
        WebSocket断开是正常情况，不应该抛出异常。

        Args:
            record: 导致错误的日志记录
        """
        # 静默处理，WebSocket断开是正常情况
        pass


def setup_websocket_logging(socketio: SocketIO,
                            min_level: int = logging.INFO) -> WebSocketLogHandler:
    """
    配置WebSocket日志系统

    便捷函数，用于快速设置WebSocket日志处理器并将其添加到根logger。
    推荐在Flask应用初始化时调用。

    Args:
        socketio (SocketIO): Flask-SocketIO实例
        min_level (int): 最小日志级别，默认INFO（不广播DEBUG日志）

    Returns:
        WebSocketLogHandler: 配置好的处理器实例

    副作用:
        - 创建WebSocket日志处理器
        - 添加到根logger
        - 设置日志格式

    Example:
        >>> from flask import Flask
        >>> from flask_socketio import SocketIO
        >>> app = Flask(__name__)
        >>> socketio = SocketIO(app)
        >>> handler = setup_websocket_logging(socketio, logging.INFO)
        >>> # 现在所有INFO及以上级别的日志都会广播到WebSocket
    """
    # 创建处理器
    handler = WebSocketLogHandler(socketio, level=min_level)

    # 设置日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    # 添加到根logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    return handler
