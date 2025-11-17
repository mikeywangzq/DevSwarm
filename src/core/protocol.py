"""
通信协议定义模块
Communication Protocol Definitions

本模块定义了DevSwarm系统中所有Agent间通信使用的标准消息格式和数据结构。
确保系统各组件之间能够通过统一的协议进行可靠的通信。

主要组件:
    - MessageType: 消息类型枚举，定义了系统支持的所有消息类型
    - TaskStatus: 任务状态枚举，定义了任务的生命周期状态
    - Task: 任务数据类，表示一个可执行的工作单元
    - Message: 消息数据类，Agent间通信的标准格式
    - BugReport: Bug报告数据类，用于QA Agent报告测试失败
    - APIContract: API契约数据类，定义前后端接口规范
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime
import uuid
import json


class MessageType(Enum):
    """
    消息类型枚举

    定义系统中所有可能的消息类型。每种消息类型都有特定的用途和处理方式。

    Attributes:
        TASK_ASSIGNMENT: 任务分配消息，PM Agent分配任务给Worker Agent时使用
        STATUS_UPDATE: 状态更新消息，Worker Agent向PM Agent报告任务状态变化
        ERROR_REPORT: 错误报告消息，Agent遇到错误时使用
        DATA_REQUEST: 数据请求消息，Agent需要从其他Agent获取数据时使用
        DATA_RESPONSE: 数据响应消息，响应DATA_REQUEST的数据
        BUG_REPORT: Bug报告消息，QA Agent发现Bug时使用
        COMPLETION_REPORT: 完成报告消息，Agent完成任务后的详细报告
    """
    TASK_ASSIGNMENT = "task_assignment"        # 任务分配
    STATUS_UPDATE = "status_update"            # 状态更新
    ERROR_REPORT = "error_report"              # 错误报告
    DATA_REQUEST = "data_request"              # 数据请求
    DATA_RESPONSE = "data_response"            # 数据响应
    BUG_REPORT = "bug_report"                  # Bug报告
    COMPLETION_REPORT = "completion_report"    # 完成报告


class TaskStatus(Enum):
    """
    任务状态枚举

    定义任务在其生命周期中可能处于的所有状态。
    状态转换通常遵循: PENDING → IN_PROGRESS → COMPLETED/FAILED

    Attributes:
        PENDING: 待处理，任务已创建但尚未开始执行
        IN_PROGRESS: 进行中，任务正在被Agent执行
        COMPLETED: 已完成，任务成功完成
        FAILED: 失败，任务执行过程中发生错误
        BLOCKED: 阻塞，任务因依赖未满足而无法执行
    """
    PENDING = "pending"              # 待处理
    IN_PROGRESS = "in_progress"      # 进行中
    COMPLETED = "completed"          # 已完成
    FAILED = "failed"                # 失败
    BLOCKED = "blocked"              # 阻塞


@dataclass
class Task:
    """
    任务数据类

    表示系统中的一个可执行工作单元。每个任务都有唯一的ID、明确的职责和分配的执行者。
    任务可以有依赖关系，只有当所有依赖都满足时，任务才能被执行。

    Attributes:
        task_id (str): 任务的唯一标识符，格式通常为 "T1_Backend", "T2_Frontend" 等
        title (str): 任务标题，简短描述任务内容
        description (str): 任务详细描述，包含具体的执行要求和上下文信息
        assigned_to (str): 负责执行此任务的Agent名称，如 "Backend_Agent"
        dependencies (List[str]): 任务依赖列表，可以是其他任务ID或文件路径
        status (TaskStatus): 当前任务状态，默认为PENDING
        type (str): 任务类型，如 "general"(常规), "bug_fix"(Bug修复), "test"(测试)
        metadata (Dict[str, Any]): 额外的元数据，存储任务特定的信息

    Example:
        >>> task = Task(
        ...     task_id="T1_Backend",
        ...     title="实现后端API",
        ...     description="根据API契约生成Flask代码",
        ...     assigned_to="Backend_Agent",
        ...     dependencies=["api_contract.json"]
        ... )
    """
    task_id: str                                               # 任务唯一标识符
    title: str                                                 # 任务标题
    description: str                                           # 任务详细描述
    assigned_to: str                                           # 负责的Agent名称
    dependencies: List[str] = field(default_factory=list)     # 依赖列表
    status: TaskStatus = TaskStatus.PENDING                    # 任务状态
    type: str = "general"                                      # 任务类型
    metadata: Dict[str, Any] = field(default_factory=dict)    # 额外元数据

    def to_dict(self) -> Dict[str, Any]:
        """
        将任务对象转换为字典格式

        用于序列化任务对象，以便存储或传输。状态枚举会被转换为字符串值。

        Returns:
            Dict[str, Any]: 包含所有任务字段的字典

        Example:
            >>> task.to_dict()
            {'task_id': 'T1', 'title': '...', 'status': 'pending', ...}
        """
        data = asdict(self)
        data['status'] = self.status.value  # 将枚举转换为字符串
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """
        从字典创建任务对象

        用于反序列化任务对象。如果状态字段是字符串，会自动转换为TaskStatus枚举。

        Args:
            data (Dict[str, Any]): 包含任务字段的字典

        Returns:
            Task: 新创建的任务对象

        Example:
            >>> task_dict = {'task_id': 'T1', 'status': 'pending', ...}
            >>> task = Task.from_dict(task_dict)
        """
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = TaskStatus(data['status'])  # 字符串转枚举
        return cls(**data)


@dataclass
class Message:
    """
    消息数据类

    定义Agent间通信的标准消息格式。所有Agent之间的通信都必须使用此格式，
    以确保系统中的通信协议统一和可追踪。

    消息格式遵循以下原则：
    1. 每条消息都有唯一ID，便于追踪和调试
    2. 包含时间戳，记录消息的发送时间
    3. 明确标识发送方和接收方
    4. 支持广播模式（to_agent设为"ALL"）
    5. 可以携带任务信息和自定义负载

    Attributes:
        message_id (str): 消息唯一标识符，自动生成UUID
        timestamp (str): 消息发送时间戳，ISO 8601格式，UTC时区
        from_agent (str): 发送消息的Agent名称
        to_agent (str): 接收消息的Agent名称，"ALL"表示广播给所有Agent
        type (MessageType): 消息类型，决定了消息的处理方式
        task (Optional[Task]): 相关的任务对象，某些消息类型会携带任务信息
        payload (Dict[str, Any]): 自定义负载，存储消息特定的数据

    Example:
        >>> msg = Message(
        ...     from_agent="PM_Agent",
        ...     to_agent="Backend_Agent",
        ...     type=MessageType.TASK_ASSIGNMENT,
        ...     task=task_object,
        ...     payload={"priority": "high"}
        ... )
    """
    # 消息唯一标识符，自动生成UUID
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    # 消息时间戳，ISO 8601格式
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    # 发送方Agent名称
    from_agent: str = ""
    # 接收方Agent名称，"ALL"表示广播
    to_agent: str = ""
    # 消息类型
    type: MessageType = MessageType.STATUS_UPDATE
    # 相关任务对象（可选）
    task: Optional[Task] = None
    # 自定义负载数据
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        将消息对象转换为字典格式

        将消息序列化为字典，便于存储到文件或通过网络传输。
        所有枚举类型会被转换为字符串值。

        Returns:
            Dict[str, Any]: 包含所有消息字段的字典
        """
        data = {
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "type": self.type.value,                            # 枚举转字符串
            "task": self.task.to_dict() if self.task else None, # 嵌套对象转字典
            "payload": self.payload
        }
        return data

    def to_json(self) -> str:
        """
        将消息对象转换为JSON字符串

        方便打印日志或通过HTTP传输。使用UTF-8编码和缩进格式化。

        Returns:
            str: 格式化的JSON字符串
        """
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """
        从字典创建消息对象

        用于反序列化消息。会自动处理类型转换：
        - 字符串类型转换为MessageType枚举
        - 任务字典转换为Task对象

        Args:
            data (Dict[str, Any]): 包含消息字段的字典

        Returns:
            Message: 新创建的消息对象
        """
        if 'type' in data and isinstance(data['type'], str):
            data['type'] = MessageType(data['type'])  # 字符串转枚举
        if 'task' in data and data['task'] is not None:
            data['task'] = Task.from_dict(data['task'])  # 字典转Task对象
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """
        从JSON字符串创建消息对象

        解析JSON字符串并创建消息对象。

        Args:
            json_str (str): JSON格式的消息字符串

        Returns:
            Message: 新创建的消息对象
        """
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class BugReport:
    """
    Bug报告数据类

    用于QA Agent向PM Agent报告测试过程中发现的Bug。
    包含足够的信息帮助PM Agent分析问题并生成修复建议。

    Attributes:
        test_name (str): 失败的测试用例名称
        error_message (str): 错误消息，简短描述问题
        logs (List[str]): 相关日志信息，用于调试
        relevant_code_context (str): 相关代码上下文，帮助定位问题
        stack_trace (str): 完整的堆栈跟踪信息
        severity (str): 严重程度，可选值: "low", "medium", "high", "critical"
    """
    test_name: str                                      # 测试用例名称
    error_message: str                                  # 错误消息
    logs: List[str] = field(default_factory=list)      # 日志信息
    relevant_code_context: str = ""                     # 相关代码上下文
    stack_trace: str = ""                               # 堆栈跟踪
    severity: str = "medium"                            # 严重程度

    def to_dict(self) -> Dict[str, Any]:
        """
        将Bug报告转换为字典格式

        Returns:
            Dict[str, Any]: 包含所有字段的字典
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BugReport':
        """
        从字典创建Bug报告对象

        Args:
            data (Dict[str, Any]): 包含Bug报告字段的字典

        Returns:
            BugReport: 新创建的Bug报告对象
        """
        return cls(**data)


@dataclass
class APIContract:
    """
    API契约数据类

    定义前后端之间的接口规范。PM Agent会根据用户需求生成API契约，
    然后Backend Agent和Frontend Agent分别根据契约实现后端API和前端调用。

    API契约确保了前后端的接口定义完全一致，避免了集成问题。

    Attributes:
        endpoints (List[Dict]): API端点列表，每个端点包含method, path等信息
        base_url (str): API的基础URL，默认为本地开发地址
        version (str): API版本号，用于版本管理

    Example:
        >>> contract = APIContract()
        >>> contract.add_endpoint(
        ...     method="GET",
        ...     path="/api/items",
        ...     description="获取所有项目",
        ...     response={"items": []}
        ... )
    """
    endpoints: List[Dict[str, Any]] = field(default_factory=list)  # 端点列表
    base_url: str = "http://localhost:5000"                         # 基础URL
    version: str = "1.0"                                            # API版本

    def to_dict(self) -> Dict[str, Any]:
        """
        将API契约转换为字典格式

        Returns:
            Dict[str, Any]: 包含所有字段的字典
        """
        return asdict(self)

    def to_json(self) -> str:
        """
        将API契约转换为JSON字符串

        用于保存到api_contract.json文件，供其他Agent读取。

        Returns:
            str: 格式化的JSON字符串
        """
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'APIContract':
        """
        从字典创建API契约对象

        Args:
            data (Dict[str, Any]): 包含API契约字段的字典

        Returns:
            APIContract: 新创建的API契约对象
        """
        return cls(**data)

    def add_endpoint(self, method: str, path: str, description: str,
                    request_body: Optional[Dict] = None,
                    response: Optional[Dict] = None):
        """
        添加API端点到契约中

        Args:
            method (str): HTTP方法，如 "GET", "POST", "PUT", "DELETE"
            path (str): API路径，如 "/api/items" 或 "/api/items/:id"
            description (str): 端点描述，说明接口的用途
            request_body (Optional[Dict]): 请求体结构示例
            response (Optional[Dict]): 响应体结构示例

        Example:
            >>> contract.add_endpoint(
            ...     method="POST",
            ...     path="/api/items",
            ...     description="创建新项目",
            ...     request_body={"title": "string"},
            ...     response={"id": "string", "title": "string"}
            ... )
        """
        endpoint = {
            "method": method,
            "path": path,
            "description": description,
            "request_body": request_body or {},
            "response": response or {}
        }
        self.endpoints.append(endpoint)
