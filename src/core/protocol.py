"""
Communication Protocol Definitions
定义Agent间通信的消息格式和类型
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime
import uuid
import json


class MessageType(Enum):
    """消息类型枚举"""
    TASK_ASSIGNMENT = "task_assignment"
    STATUS_UPDATE = "status_update"
    ERROR_REPORT = "error_report"
    DATA_REQUEST = "data_request"
    DATA_RESPONSE = "data_response"
    BUG_REPORT = "bug_report"
    COMPLETION_REPORT = "completion_report"


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class Task:
    """任务定义"""
    task_id: str
    title: str
    description: str
    assigned_to: str
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    type: str = "general"  # general, bug_fix, test, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['status'] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """从字典创建"""
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = TaskStatus(data['status'])
        return cls(**data)


@dataclass
class Message:
    """
    标准消息格式
    所有Agent间通信必须使用此格式
    """
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    from_agent: str = ""
    to_agent: str = ""  # "ALL" for broadcast
    type: MessageType = MessageType.STATUS_UPDATE
    task: Optional[Task] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = {
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "type": self.type.value,
            "task": self.task.to_dict() if self.task else None,
            "payload": self.payload
        }
        return data

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """从字典创建消息"""
        if 'type' in data and isinstance(data['type'], str):
            data['type'] = MessageType(data['type'])
        if 'task' in data and data['task'] is not None:
            data['task'] = Task.from_dict(data['task'])
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """从JSON字符串创建消息"""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class BugReport:
    """Bug报告格式"""
    test_name: str
    error_message: str
    logs: List[str] = field(default_factory=list)
    relevant_code_context: str = ""
    stack_trace: str = ""
    severity: str = "medium"  # low, medium, high, critical

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BugReport':
        """从字典创建"""
        return cls(**data)


@dataclass
class APIContract:
    """API契约定义"""
    endpoints: List[Dict[str, Any]] = field(default_factory=list)
    base_url: str = "http://localhost:5000"
    version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'APIContract':
        """从字典创建"""
        return cls(**data)

    def add_endpoint(self, method: str, path: str, description: str,
                    request_body: Optional[Dict] = None,
                    response: Optional[Dict] = None):
        """添加API端点"""
        endpoint = {
            "method": method,
            "path": path,
            "description": description,
            "request_body": request_body or {},
            "response": response or {}
        }
        self.endpoints.append(endpoint)
